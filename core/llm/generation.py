"""Submission-scoped cancellation and streaming; no model output enters progress events."""
from __future__ import annotations

import asyncio
import json
import threading
from typing import Callable

import httpx

from core.llm.backends import ProviderRequestError, chat_sampling


class SubmissionCancelled(RuntimeError):
    pass


class GenerationControl:
    def __init__(self, on_progress: Callable[[str], None] | None = None, timeout: float = 180.0):
        self.on_progress = on_progress
        self.timeout = timeout
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self.committed = False
        self.status = ""

    def cancel(self) -> bool:
        with self._lock:
            if self.committed:
                return False
            self._cancelled.set()
            return True

    def check(self) -> None:
        if self._cancelled.is_set():
            raise SubmissionCancelled("Submission cancelled")

    def commit(self) -> None:
        with self._lock:
            self.check()
            self.committed = True

    def progress(self, status: str) -> None:
        self.check()
        self.status = status
        if self.on_progress:
            self.on_progress(status)


async def _read_response(client, url, payload, control):
    async with client.stream("POST", url, json=payload) as response:
        if response.status_code in {404, 405}:
            return None
        response.raise_for_status()
        kind = response.headers.get("content-type", "").lower()
        if "application/json" in kind and "ndjson" not in kind:
            data = json.loads(await response.aread())
            if data.get("error"):
                raise ProviderRequestError("Provider rejected generation")
            choices = data.get("choices", [])
            text = data.get("response") if "response" in data else (choices[0].get("message", {}).get("content") if choices else None)
            if not isinstance(text, str) or not text.strip():
                raise ProviderRequestError("Provider returned no completed response")
            control.progress("GENERATING")
            return text
        parts = []
        size = 0
        finished = False
        started = False
        async for line in response.aiter_lines():
            control.check()
            line = line.strip()
            if not line or line.startswith(":") or line.startswith(("event:", "id:")):
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if line == "[DONE]":
                finished = True
                break
            data = json.loads(line)
            if data.get("error"):
                raise ProviderRequestError("Provider interrupted generation")
            # Only provider-reported loading is labelled LOADING. Waiting for the
            # first token may also include queueing or prompt preparation.
            if str(data.get("status", "")).lower() in {"loading", "loading model"}:
                control.progress("LOADING")
            choices = data.get("choices", [])
            chunk = data.get("response", "")
            if choices:
                chunk = choices[0].get("delta", {}).get("content") or ""
                if choices[0].get("finish_reason") in {"length", "content_filter"}:
                    raise ProviderRequestError("Provider did not complete the requested response")
                if choices[0].get("finish_reason") is not None:
                    finished = True
            if data.get("done") is True:
                finished = True
            if chunk:
                if not isinstance(chunk, str):
                    raise ProviderRequestError("Invalid provider content")
                if not started:
                    control.progress("GENERATING")
                    started = True
                parts.append(chunk)
                size += len(chunk)
                if size > 1_000_000:
                    raise ProviderRequestError("Provider response exceeded limit")
        if not finished or not parts:
            raise ProviderRequestError("Provider stream ended before a completed response")
        return "".join(parts)


async def _generate(base_url, payload, control):
    async with httpx.AsyncClient(timeout=control.timeout) as client:
        response = await _read_response(client, base_url.rstrip("/") + "/api/generate", payload, control)
        if response is not None:
            return response
        control.check()
        options = payload.get("options", {})
        response = await _read_response(client, base_url.rstrip("/") + "/v1/chat/completions", {
            "model": payload["model"], "messages": [{"role": "user", "content": payload["prompt"]}],
            "stream": True, "temperature": options.get("temperature", .2),
            "max_tokens": options.get("num_predict", 900), **chat_sampling(options),
        }, control)
        if response is None:
            raise ProviderRequestError("Provider exposes no supported generation route")
        return response


async def _monitor(base_url, payload, control):
    control.progress("WAITING")
    task = asyncio.create_task(_generate(base_url, payload, control))
    async def observe_loading():
        # Inventory is not evidence of loading. Msty reports an explicit state;
        # other providers can omit this endpoint without affecting generation.
        async with httpx.AsyncClient(timeout=1.0) as client:
            while not task.done() and control.status != "GENERATING":
                try:
                    response = await client.get(base_url.rstrip("/") + "/v1/models")
                    response.raise_for_status()
                    for model in response.json().get("data", []):
                        if model.get("id") == payload["model"]:
                            status = model.get("status", {})
                            value = status.get("value") if isinstance(status, dict) else status
                            if value == "loading" and control.status != "GENERATING":
                                control.progress("LOADING")
                except (httpx.HTTPError, ValueError, AttributeError):
                    pass
                await asyncio.sleep(3)
    observer = asyncio.create_task(observe_loading())
    deadline = asyncio.get_running_loop().time() + control.timeout
    try:
        while not task.done():
            control.check()
            if asyncio.get_running_loop().time() >= deadline:
                raise ProviderRequestError("Model response timed out")
            await asyncio.wait({task}, timeout=.1)
        control.check()
        return await task
    finally:
        observer.cancel()
        if not task.done():
            task.cancel()
        # Closing the response/client is completed before the worker releases its
        # submission lock. A retry can never overlap a detached local reader.
        await asyncio.gather(task, observer, return_exceptions=True)


def generate_response(base_url: str, payload: dict, control: GenerationControl) -> str:
    control.check()
    try:
        result = asyncio.run(_monitor(base_url, {**payload, "stream": True}, control))
        control.check()
        return result
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise ProviderRequestError("Provider generation failed; inspect local diagnostics") from exc
