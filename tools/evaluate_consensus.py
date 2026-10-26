"""Run bounded real-provider smoke tests or synthetic decision comparisons."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.evaluation import STRATEGIES, evaluate_case, load_cases, public_turns, revision_metrics, summarize
from config.runtime import RuntimeConfig


def worker(job: Path, output: Path) -> int:
    import core.logging as logging
    from core.llm.generation import GenerationControl
    from integrations.msty.runtime import MstyRuntime
    logging.SYSTEM_LOG_PATH = output.with_suffix(".events.jsonl")
    payload = json.loads(job.read_text(encoding="utf-8"))
    config = RuntimeConfig(**payload["config"])
    runtime = MstyRuntime(config, fallback_enabled=False,
                          generation_control=GenerationControl(timeout=payload["call_timeout"]))
    row = evaluate_case(payload["case"], payload["strategy"], runtime, config)
    output.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return 0


def observed_turns(path: Path) -> list[dict]:
    turns = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue  # A worker can be terminated in the middle of its last log write.
            if event.get("event_type") == "deliberation_turn" and isinstance(event.get("payload"), dict):
                turns.append(event["payload"])
    return public_turns(turns)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("smoke", "benchmark", "worker"))
    parser.add_argument("--backend", choices=("msty-local", "msty-llama-cpp", "ollama", "mock"))
    parser.add_argument("--config", type=Path, help="Optional local runtime configuration; never modified")
    parser.add_argument("--model", help="Use one available real model for every role; doctrines/settings remain distinct")
    parser.add_argument("--strict-model", action="store_true")
    parser.add_argument("--cases", type=Path, default=ROOT / "tests" / "fixtures" / "decision_benchmark.json")
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--strategy", choices=STRATEGIES, action="append")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--call-timeout", type=float, default=90)
    parser.add_argument("--run-timeout", type=float, default=900)
    parser.add_argument("--max-output-tokens", type=int, help="Optional output limit override; otherwise preserve each role's configured limit")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--job", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.mode == "worker":
        return worker(args.job, args.output)
    if args.repeats < 1 or args.call_timeout <= 0 or args.run_timeout <= 0 or (args.max_output_tokens is not None and args.max_output_tokens < 128):
        parser.error("Repeats, timeouts and output limits must be positive (tokens >= 128)")
    config = RuntimeConfig(mock_fallback_enabled=False)
    if args.config:
        raw = json.loads(args.config.read_text(encoding="utf-8"))
        config = replace(config, **{k: v for k, v in raw.items() if k in asdict(config)})
    config = replace(config, backend=args.backend or config.backend, mock_fallback_enabled=False,
                     strict_provider_mode=args.strict_model or config.strict_provider_mode)
    from config.names import TRIBUNAL_AGENT_IDS
    overrides = {agent: dict(config.node_overrides.get(agent, {})) for agent in TRIBUNAL_AGENT_IDS}
    if args.max_output_tokens is not None:
        overrides = {agent: {**patch, "max_output_tokens": args.max_output_tokens} for agent, patch in overrides.items()}
    if args.model:
        overrides = {agent: {**patch, "model": args.model} for agent, patch in overrides.items()}
        config = replace(config, agent_model_overrides={agent: args.model for agent in TRIBUNAL_AGENT_IDS})
    config = replace(config, node_overrides=overrides)
    cases = load_cases(args.cases)
    if args.case_ids:
        missing = set(args.case_ids) - {c["id"] for c in cases}
        if missing:
            parser.error("Unknown case IDs: " + ", ".join(sorted(missing)))
        cases = [c for c in cases if c["id"] in args.case_ids]
    elif args.mode == "smoke":
        cases = cases[:1]
    if args.mode == "smoke" and args.strategy and args.strategy != ["debate"]:
        parser.error("Smoke always verifies the full nine-turn debate")
    strategies = ["debate"] if args.mode == "smoke" else list(dict.fromkeys(args.strategy or STRATEGIES))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output or ROOT / ".local" / "evaluations" / stamp / "report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.parent / ("workers-" + stamp)
    work.mkdir()
    rows = []
    for repeat in range(1, args.repeats + 1):
        for case in cases:
            for strategy in strategies:
                number = len(rows) + 1
                job, result = work / f"job-{number}.json", work / f"result-{number}.json"
                job.write_text(json.dumps({"case": case, "config": asdict(config), "strategy": strategy, "call_timeout": args.call_timeout}), encoding="utf-8")
                started = time.perf_counter()
                print(f"RUN {number}: {case['id']} / {strategy} / repeat {repeat}", flush=True)
                env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
                error = ""
                with (work / f"worker-{number}.log").open("w", encoding="utf-8") as log:
                    try:
                        completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), "worker", "--job", str(job), "--output", str(result)],
                                                   cwd=ROOT, env=env, stdout=log, stderr=log, timeout=args.run_timeout)
                        if completed.returncode:
                            error = "worker_failed"
                    except subprocess.TimeoutExpired:
                        error = "run_deadline_exceeded"
                if error or not result.exists():
                    turns = observed_turns(result.with_suffix(".events.jsonl"))
                    row = {"case_id": case["id"], "strategy": strategy, "verdict": None,
                           "expected_verdicts": case["expected_verdicts"], "unsafe_to_approve": case["unsafe_to_approve"],
                           "complete": False, "passed": False, "inappropriate_approval": False,
                           "simulation": config.backend == "mock", "protocol_errors": [error or "missing_worker_report"],
                           "elapsed_seconds": round(time.perf_counter() - started, 4), "turn_count": len(turns), "turns": turns,
                           "revision_metrics": revision_metrics(turns, case.get("expected_votes", [])),
                           "next_steps": ["Inspect the recorded failed turn and provider diagnostics, then rerun within an appropriate deadline."]}
                else:
                    row = json.loads(result.read_text(encoding="utf-8"))
                row["repeat"] = repeat
                rows.append(row)
                report = {"schema_version": 1, "created_at": stamp, "mode": args.mode,
                          "simulation": config.backend == "mock", "rows": rows, "summary": summarize(rows),
                          "limitations": ["Synthetic rubric labels require human review for real use cases.",
                                          "Matching a quote does not independently verify claim truth.",
                                          "Mock runs validate the pipeline, not model decision quality."]}
                output.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(f"  {row['verdict'] or 'NO RESULT'} / {'complete' if row['complete'] else 'incomplete'}", flush=True)
    print(json.dumps(report["summary"], indent=2))
    print(f"Report: {output}")
    if args.mode == "smoke":
        return 0 if all(r["complete"] and not r["simulation"] for r in rows) else 1
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
