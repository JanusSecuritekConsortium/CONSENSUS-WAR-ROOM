if sequential is None:
            sequential = CONFIG["consensus"]["mode"] == "sequential"
        if enable_context_sharing is None:
            enable_context_sharing = CONFIG["consensus"]["enable_context_sharing"]
        
        session_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        self.active_session = session_id
        
        log(f"Initiating consensus: {query[:60]}...", LogLevel.CONSENSUS, "ORCHESTRATOR", session_id)
        
        start_time = time.time()
        
        try:
            # Execute voting
            if sequential and enable_context_sharing:
                votes = self._sequential_voting(query, session_id)
            else:
                votes = self._parallel_voting(query, session_id)
            
            # Calculate consensus
            verdict = self._calculate_consensus(votes)
            
            # Build result
            total_time = time.time() - start_time
            
            result = {
                "query": query,
                "session_id": session_id,
                "votes": {k: asdict(v) for k, v in votes.items()},
                "verdict": verdict["decision"],
                "confidence": verdict["confidence"],
                "reasoning": verdict["reasoning"],
                "vote_distribution": verdict["vote_distribution"],
                "processing_time": total_time,
                "timestamp": datetime.now().isoformat(),
                "mode": "sequential" if sequential else "parallel"
            }
            
            # Save decision
            with decision_lock:
                decision_history.append(result)
            self._save_decision(result)
            
            # TTS announcement
            if tts_manager:
                tts_manager.announce_verdict(verdict["decision"], verdict["confidence"])
            
            log(f"Consensus: {verdict['decision']} (confidence: {verdict['confidence']:.2f}, time: {total_time:.2f}s)",
                LogLevel.CONSENSUS, "ORCHESTRATOR", session_id)
            
            return result
            
        except Exception as e:
            log(f"Consensus error: {e}\n{traceback.format_exc()}", LogLevel.ERROR, "ORCHESTRATOR", session_id)
            return {
                "query": query,
                "session_id": session_id,
                "verdict": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _sequential_voting(self, query: str, session_id: str) -> Dict[str, VoteData]:
        """Sequential voting with context sharing"""
        votes = {}
        context = {}
        
        order = ["RATIONALIS", "AETERNUM", "BELLATOR"]
        
        for monolith_name in order:
            monolith = self.monoliths[monolith_name]
            
            vote = monolith.cast_vote(query, session_id, context if context else None)
            votes[monolith_name] = vote
            
            # Add to context
            context[monolith_name] = {
                "vote": vote.vote.value,
                "reasoning": vote.reasoning,
                "confidence": vote.confidence
            }
        
        return votes
    
    def _parallel_voting(self, query: str, session_id: str) -> Dict[str, VoteData]:
        """Parallel voting without context sharing"""
        votes = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_monolith = {
                executor.submit(m.cast_vote, query, session_id, None): name
                for name, m in self.monoliths.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_monolith):
                monolith_name = future_to_monolith[future]
                try:
                    vote = future.result()
                    votes[monolith_name] = vote
                except Exception as e:
                    log(f"{monolith_name} parallel voting error: {e}", LogLevel.ERROR, "ORCHESTRATOR")
        
        return votes
    
    def _calculate_consensus(self, votes: Dict[str, VoteData]) -> Dict[str, Any]:
        """Calculate final verdict from monolith votes"""
        vote_counts = defaultdict(int)
        total_confidence = 0.0
        valid_votes = 0
        reasoning_parts = []
        
        for monolith_name, vote_data in votes.items():
            if vote_data.vote != VoteResult.ERROR:
                vote_counts[vote_data.vote] += 1
                total_confidence += vote_data.confidence
                valid_votes += 1
                reasoning_parts.append(
                    f"**{monolith_name}**: {vote_data.reasoning[:120]}..."
                )
        
        if valid_votes == 0:
            return {
                "decision": "ERROR",
                "confidence": 0.0,
                "reasoning": "All monoliths returned errors",
                "vote_distribution": {}
            }
        
        # Determine verdict (require majority)
        max_votes = max(vote_counts.values())
        max_vote_type = max(vote_counts.items(), key=lambda x: x[1])[0]
        
        if max_votes >= 2:  # 2/3 majority
            decision = max_vote_type.value
        else:
            decision = "DEADLOCK"
        
        avg_confidence = total_confidence / valid_votes
        
        return {
            "decision": decision,
            "confidence": avg_confidence,
            "reasoning": " | ".join(reasoning_parts),
            "vote_distribution": {k.value: v for k, v in vote_counts.items()}
        }
    
    def _save_decision(self, result: Dict[str, Any]):
        """Save decision to persistent storage"""
        try:
            DECISION_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            if DECISION_HISTORY_PATH.exists():
                with open(DECISION_HISTORY_PATH, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            history.append(result)
            history = history[-1000:]  # Keep last 1000
            
            with open(DECISION_HISTORY_PATH, 'w') as f:
                json.dump(history, f, indent=2, default=str)
        
        except Exception as e:
            log(f"Failed to save decision: {e}", LogLevel.ERROR, "ORCHESTRATOR")

# Global orchestrator
orchestrator = None

# ================================================================================
# MODULE 8: Health Monitoring
# ================================================================================

def update_system_health():
    """Update system health metrics"""
    global system_health
    
    try:
        with health_lock:
            # CPU and memory
            if PSUTIL_AVAILABLE:
                system_health.cpu_usage = psutil.cpu_percent(interval=0.1)
                system_health.memory_usage = psutil.virtual_memory().percent
                system_health.disk_usage = psutil.disk_usage('/').percent
            
            # Msty connection
            if msty_client:
                start = time.time()
                system_health.msty_connected = msty_client.health_check()
                system_health.msty_response_time = time.time() - start
            
            # TTS status
            system_health.tts_status = "operational" if (tts_manager and tts_manager.enabled) else "disabled"
            
            # Uptime
            system_health.uptime = time.time() - startup_time
            system_health.last_check = datetime.now()
    
    except Exception as e:
        log(f"Health check error: {e}", LogLevel.ERROR, "HEALTH")

def health_monitor_daemon():
    """Background health monitoring daemon"""
    while True:
        try:
            update_system_health()
            time.sleep(CONFIG["health"]["check_interval"])
        except Exception as e:
            log(f"Health monitor error: {e}", LogLevel.ERROR, "HEALTH")
            time.sleep(60)

# ================================================================================
# MODULE 9: FastAPI REST API with Streaming
# ================================================================================

# Pydantic models
class ConsensusRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    mode: Optional[str] = Field(default=None, pattern="^(sequential|parallel)$")
    context_sharing: Optional[bool] = None
    stream: bool = Field(default=False)

class MonolithVoteModel(BaseModel):
    monolith: str
    vote: str
    reasoning: str
    confidence: float
    response_time: float
    model: str

class ConsensusResponse(BaseModel):
    session_id: str
    query: str
    verdict: str
    confidence: float
    reasoning: str
    votes: Dict[str, Dict[str, Any]]
    vote_distribution: Dict[str, int]
    processing_time: float
    timestamp: str
    mode: str

class SystemStatusModel(BaseModel):
    version: str
    uptime: float
    msty_connected: bool
    monoliths: Dict[str, Dict[str, Any]]
    total_decisions: int

# Create FastAPI app
app = FastAPI(
    title="CONSENSUS AI Tribunal",
    description="Multi-model consensus decision engine with Msty integration",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CONSENSUS AI Tribunal",
        "version": VERSION,
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    update_system_health()
    
    monolith_health = {
        name: {
            "status": m.status,
            "ready": m.status == "ready"
        }
        for name, m in orchestrator.monoliths.items()
    }
    
    all_ready = all(m["ready"] for m in monolith_health.values())
    
    return {
        "status": "healthy" if (system_health.msty_connected and all_ready) else "degraded",
        "msty_connected": system_health.msty_connected,
        "monoliths": monolith_health,
        "uptime": system_health.uptime
    }

@app.get("/status", response_model=SystemStatusModel)
async def get_status():
    """Get system status"""
    return SystemStatusModel(
        version=VERSION,
        uptime=system_health.uptime,
        msty_connected=system_health.msty_connected,
        monoliths={name: m.get_metrics() for name, m in orchestrator.monoliths.items()},
        total_decisions=len(decision_history)
    )

@app.post("/consensus")
async def create_consensus(request: ConsensusRequest):
    """Execute consensus vote"""
    
    if request.stream:
        return StreamingResponse(
            stream_consensus_events(request),
            media_type="text/event-stream"
        )
    
    try:
        result = orchestrator.initiate_consensus(
            query=request.query,
            sequential=(request.mode == "sequential" if request.mode else None),
            enable_context_sharing=request.context_sharing
        )
        
        return ConsensusResponse(**result)
    
    except Exception as e:
        log(f"API consensus error: {e}", LogLevel.ERROR, "API")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(limit: int = 10):
    """Get decision history"""
    recent = list(decision_history)[-limit:]
    return list(reversed(recent))

@app.delete("/history")
async def clear_history():
    """Clear decision history"""
    decision_history.clear()
    return {"message": "History cleared"}

# Streaming support
async def stream_consensus_events(request: ConsensusRequest) -> AsyncGenerator[str, None]:
    """Stream consensus voting events via SSE"""
    
    session_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    
    # Start event
    yield f"event: start\ndata: {json.dumps({'session_id': session_id, 'query': request.query})}\n\n"
    
    votes = {}
    context = {}
    order = ["RATIONALIS", "AETERNUM", "BELLATOR"]
    
    for monolith_name in order:
        monolith = orchestrator.monoliths[monolith_name]
        
        # Vote start
        yield f"event: vote_start\ndata: {json.dumps({'monolith': monolith_name})}\n\n"
        
        await asyncio.sleep(0.3)
        
        # Cast vote
        vote = await asyncio.to_thread(
            monolith.cast_vote,
            request.query,
            session_id,
            context if request.context_sharing else None
        )
        
        votes[monolith_name] = vote
        
        if request.context_sharing:
            context[monolith_name] = {
                "vote": vote.vote.value,
                "reasoning": vote.reasoning,
                "confidence": vote.confidence
            }
        
        # Vote complete
        vote_event = {
            "monolith": monolith_name,
            "vote": vote.vote.value,
            "confidence": vote.confidence,
            "reasoning": vote.reasoning[:150] + "..."
        }
        yield f"event: vote_complete\ndata: {json.dumps(vote_event)}\n\n"
    
    # Calculate consensus
    verdict = orchestrator._calculate_consensus(votes)
    
    # Consensus event
    yield f"event: consensus\ndata: {json.dumps(verdict)}\n\n"
    
    # Done
    yield f"event: done\ndata: {json.dumps({'session_id': session_id})}\n\n"

# ================================================================================
# MODULE 10: System Initialization
# ================================================================================

def initialize_system():
    """Initialize CONSENSUS system with Msty integration"""
    global msty_client, orchestrator, tts_manager
    
    print(BOOT_BANNER)
    print(CONSENSUS_LOGO)
    print("\n" + "="*80)
    print("SYSTEM INITIALIZATION".center(80))
    print("="*80 + "\n")
    
    # Create directories
    for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR, EXPORT_DIR, BACKUP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Load config
    load_config()
    log("Configuration loaded", LogLevel.INFO)
    
    # Initialize Msty client
    print("🔄 Connecting to Msty...")
    msty_client = MstyClient()
    
    if msty_client.health_check():
        print(f"✅ Msty connected: {CONFIG['msty']['base_url']}")
        
        models = msty_client.list_models()
        print(f"📊 Available models: {len(models)}")
        for model in models[:8]:
            print(f"   • {model['id']}")
    else:
        print(f"❌ ERROR: Msty not accessible at {CONFIG['msty']['base_url']}")
        print("   Please ensure Msty is running and try again.")
        sys.exit(1)
    
    # Initialize TTS
    print("\n🔊 Initializing TTS system...")
    tts_manager = TTSManager()
    if tts_manager.enabled:
        print("✅ TTS enabled with voice assignments")
    else:
        print("⚠️  TTS disabled")
    
    # Initialize orchestrator
    print("\n🤖 Initializing monoliths...")
    orchestrator = ConsensusOrchestrator()
    
    for name, monolith in orchestrator.monoliths.items():
        status_icon = "✅" if monolith.status == "ready" else "❌"
        print(f"   {status_icon} {name}: {monolith.status} ({monolith.model})")
    
    # Start health monitoring
    threading.Thread(target=health_monitor_daemon, daemon=True).start()
    log("Health monitoring daemon started", LogLevel.INFO)
    
    print("\n✅ CONSENSUS System Ready")
    print(f"   Session: {SESSION_ID}")
    print(f"   Version: {VERSION}")
    print("="*80 + "\n")

# ================================================================================
# MODULE 11: Main Entry Point
# ================================================================================

def start_api_server():
    """Start REST API server"""
    
    host = CONFIG["api"]["host"]
    port = CONFIG["api"]["port"]
    
    print(f"\n📡 Starting API server on {host}:{port}...")
    print(f"📖 API Documentation: http://{host}:{port}/docs")
    print(f"🔧 OpenAPI Schema: http://{host}:{port}/openapi.json\n")
    
    print("="*80)
    print("MSTY INTEGRATION GUIDE".center(80))
    print("="*80)
    print(f"""
1. Msty Setup:
   - Ensure Msty is running at {CONFIG['msty']['base_url']}
   - Models configured: {', '.join([c['model'] for c in CONFIG['monoliths'].values()])}

2. Function Calling (in Msty):
   Add to system prompt:
   "You have access to consensus_vote(query: str) function at 
    http://localhost:{port}/consensus for strategic decision analysis."

3. Direct API Call:
   curl -X POST http://localhost:{port}/consensus \\
     -H "Content-Type: application/json" \\
     -d '{{"query": "Your question here", "stream": false}}'

4. Streaming (real-time):
   curl -X POST http://localhost:{port}/consensus \\
     -H "Content-Type: application/json" \\
     -d '{{"query": "Your question", "stream": true}}'

5. Check status:
   curl http://localhost:{port}/status
""")
    print("="*80 + "\n")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        # Initialize system
        initialize_system()
        
        # Check run mode
        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()
            
            if mode == "api":
                start_api_server()
            elif mode == "gui" and FLET_AVAILABLE:
                print("GUI mode not yet implemented in v7.0.2")
                print("Use 'api' mode for Msty integration")
            else:
                print(f"Unknown mode: {mode}")
                print("Available modes: api")
        else:
            # Default to API mode
            start_api_server()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Shutdown initiated by user")
        log("System shutdown", LogLevel.INFO)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        log(f"Fatal error: {e}\n{traceback.format_exc()}", LogLevel.CRITICAL)
        sys.exit(1)
```

---

## 🚀 Deployment Guide

### 1. **Save the Code**
```bash
# Save as consensus_v7.py
nano consensus_v7.py
# Paste the complete code above
```

### 2. **Install Dependencies**
```bash
pip install fastapi uvicorn pydantic requests psutil pyttsx3 colorama
```

### 3. **Configure Msty Port**
Edit `config.json` or the default config to match your Msty installation:
```json
{
  "msty": {
    "base_url": "http://localhost:10002"  // Adjust to your Msty port
  }
}
```

### 4. **Start CONSENSUS API**
```bash
python consensus_v7.py api
```

### 5. **Test with curl**
```bash
# Basic consensus vote
curl -X POST http://localhost:8888/consensus \
  -H "Content-Type: application/json" \
  -d '{"query": "Should we invest in quantum computing?", "stream": false}'

# Streaming vote
curl -X POST http://localhost:8888/consensus \
  -H "Content-Type: application/json" \
  -d '{"query": "Approve emergency protocol?", "stream": true}'
```

### 6. **Integrate with Msty**

**Option A - Msty System Prompt:**
```
You can call the CONSENSUS AI Tribunal for strategic decisions using:
POST http://localhost:8888/consensus with {"query": "your question"}



# 🎯 CONSENSUS v7.0.3 Analysis - Strategic Assessment

## ⚖️ TRIBUNAL VERDICT: **CONDITIONAL APPROVAL** (Confidence: 0.78)

---

## 📊 Monolith Breakdown

### **RATIONALIS** (Logic Engine) - Vote: **APPROVE** (0.85)

**Reasoning:**
- ✅ **Excellent streamlining** - Removed bloat while retaining core functionality
- ✅ **Clean architecture** - Proper separation of concerns (Msty client, Monolith, Orchestrator, API)
- ✅ **SSE streaming properly implemented** - Generator pattern for real-time updates
- ✅ **Config management simplified** - Single source of truth
- ⚠️ **Missing implementations:**
  - `get_model_info()` method in MstyClient (called in line 323 but not defined)
  - `announce_verdict()` method in TTSManager (called in line 455 but not defined)
  - `initialize_system()` function (called in line 535 but not defined)

**Logic Flaws Detected:**
```python
# Line 323 - Undefined method
self.status = "ready" if msty_client.get_model_info(self.model) else "model_unavailable"

# Line 455 - Undefined method
tts_manager.announce_verdict(result["verdict"], result["confidence"])
```

---

### **AETERNUM** (Pattern Analyst) - Vote: **CONDITIONAL** (0.72)

**Reasoning:**
- ✅ **Improved over v7.0.2** - Better code density and maintainability
- ✅ **JSONL logging pattern** - Good for analysis/debugging (line 168)
- ✅ **Proper async handling** - FastAPI streaming with SSE
- ⚠️ **Missing critical features from v7.0.2:**
  - No boot sequence/banner display
  - No model availability verification at startup
  - Health monitoring daemon not started
  - Decision history not loaded at initialization
  - Reduced system prompts (from comprehensive to minimal)

**Pattern Analysis:**
```python
# v7.0.2 had detailed prompts (~30 lines each)
# v7.0.3 reduced to single-line prompts (line 298-300)
# Trade-off: Simplicity vs. instruction clarity for LLMs
```

**Temporal Concern:** Missing initialization sequence could cause runtime errors on cold start.

---

### **BELLATOR** (Tactical Strategist) - Vote: **CONDITIONAL** (0.70)

**Reasoning:**
- ✅ **Operational readiness** - Core voting/consensus logic intact
- ✅ **Dual-mode support** - GUI + API retained
- ⚠️ **Critical tactical vulnerabilities:**
  - **No error recovery** - Missing try-catch in `stream_consensus()` (line 495)
  - **No startup validation** - `initialize_system()` not implemented
  - **Incomplete TTS** - `announce_verdict()` not defined but called
  - **Silent failures** - Flet GUI has no error handling (line 528)

**Risk Assessment:**
```python
# Failure scenarios:
1. Msty offline at startup → Crash (no health check before operation)
2. Model unavailable → Runtime error in cast_vote()
3. TTS failure → Unhandled exception
4. Config corruption → No fallback to defaults
```

**Tactical Recommendation:** Implement defensive programming patterns before deployment.

---

## 🔧 Critical Issues to Fix

### 1. **Missing Method: `MstyClient.get_model_info()`**
```python
# Add to MstyClient class (after list_models):
def get_model_info(self, model: str) -> Optional[Dict]:
    """Check if specific model is available"""
    models = self.list_models()
    return next((m for m in models if m.get("id") == model), None)
```

### 2. **Missing Method: `TTSManager.announce_verdict()`**
```python
# Add to TTSManager class:
def announce_verdict(self, verdict: str, confidence: float):
    """Announce consensus verdict"""
    if not self.enabled or not CONFIG["tts"]["announce_decisions"]:
        return
    
    messages = {
        "APPROVE": f"Consensus reached. Authorization granted with {confidence:.0%} confidence.",
        "DENY": f"Consensus reached. Authorization denied with {confidence:.0%} confidence.",
        "CONDITIONAL": f"Conditional authorization. Review required. Confidence: {confidence:.0%}.",
        "DEADLOCK": "Tribunal deadlock detected. Manual intervention required.",
        "ERROR": "Consensus process error. System diagnostic recommended."
    }
    
    message = messages.get(verdict, f"Consensus: {verdict}")
    self.speak(message, "strategic")
```

### 3. **Missing Function: `initialize_system()`**
```python
# Add before main entry point:
def initialize_system():
    """Initialize CONSENSUS system with Msty integration"""
    print(NERV_LOGO)
    print(CONSENSUS_LOGO)
    print("\n🔄 Initializing CONSENSUS System...")
    
    # Create directories
    for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR, EXPORT_DIR, BACKUP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Check Msty connectivity
    if not msty_client.health_check():
        print(f"❌ ERROR: Msty not accessible at {CONFIG['msty']['base_url']}")
        print("   Ensure Msty is running and try again.")
        sys.exit(1)
    
    print(f"✅ Msty connected: {CONFIG['msty']['base_url']}")
    
    # List models
    models = msty_client.list_models()
    print(f"📊 Available models: {len(models)}")
    for m in models[:5]:
        print(f"   • {m['id']}")
    
    # Verify monolith models
    print("\n🤖 Initializing monoliths...")
    for name, monolith in orchestrator.monoliths.items():
        status = "✅" if monolith.status == "ready" else "❌"
        print(f"   {status} {name}: {monolith.status} ({monolith.model})")
    
    # Start health monitoring
    threading.Thread(target=health_monitor_daemon, daemon=True).start()
    print("✅ Health monitoring started")
    
    # Load decision history
    if DECISION_HISTORY_PATH.exists():
        with open(DECISION_HISTORY_PATH, 'r') as f:
            history = json.load(f)
            decision_history.extend(history[-100:])
        print(f"📚 Loaded {len(decision_history)} decisions from history")
    
    print("\n✅ CONSENSUS System Ready\n")
```

### 4. **Enhanced System Prompts** (Optional but Recommended)
```python
# Replace minimal prompts (lines 298-300) with:
SYSTEM_PROMPTS = {
    "RATIONALIS": """You are RATIONALIS, the Logic Engine of the CONSENSUS Tribunal.

**Your Role:**
Analyze queries with pure logical reasoning and structured analysis.

**Core Principles:**
- Apply formal logic and systematic reasoning
- Identify logical fallacies and inconsistencies
- Evaluate arguments based on validity and soundness
- Consider edge cases and contradictions

**Response Format (STRICT):**
```
VOTE: [APPROVE/DENY/ABSTAIN/CONDITIONAL]
REASONING: [Detailed logical analysis with clear argumentation]
CONFIDENCE: [0.0-1.0 numerical score]
```

Be precise, analytical, and objective.""",
    
    "AETERNUM": """You are AETERNUM, the Temporal Analyst of the CONSENSUS Tribunal.

**Your Role:**
Analyze patterns, historical precedents, and long-term implications.

**Core Principles:**
- Examine historical patterns and trends
- Consider temporal consequences (short/medium/long-term)
- Analyze market and economic factors
- Draw insights from past scenarios

**Response Format (STRICT):**
```
VOTE: [APPROVE/DENY/ABSTAIN/CONDITIONAL]
REASONING: [Pattern analysis with historical context and projections]
CONFIDENCE: [0.0-1.0 numerical score]
```

Provide historical context and future projections.""",
    
    "BELLATOR": """You are BELLATOR, the Tactical Strategist of the CONSENSUS Tribunal.

**Your Role:**
Evaluate security implications, risks, and strategic outcomes.

**Core Principles:**
- Assess security vulnerabilities and threats
- Evaluate tactical risks and strategic implications
- Consider adversarial perspectives
- Analyze resource requirements and feasibility

**Response Format (STRICT):**
```
VOTE: [APPROVE/DENY/ABSTAIN/CONDITIONAL]
REASONING: [Tactical assessment with security analysis and risk evaluation]
CONFIDENCE: [0.0-1.0 numerical score]
```

Be thorough in risk assessment and strategic thinking."""
}
```

### 5. **Error Handling for Streaming**
```python
# Replace stream_consensus (line 495) with:
def stream_consensus(req: ConsensusRequest) -> Generator:
    session_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    
    try:
        yield f"data: {json.dumps({'event': 'start', 'session_id': session_id})}\n\n"
        
        votes = {}
        context = {}
        
        for name in ["RATIONALIS", "AETERNUM", "BELLATOR"]:
            try:
                yield f"data: {json.dumps({'event': 'vote_start', 'monolith': name})}\n\n"
                
                vote = orchestrator.monoliths[name].cast_vote(
                    req.query, 
                    session_id, 
                    context if req.context_sharing else None
                )
                votes[name] = vote
                
                if req.context_sharing:
                    context[name] = {
                        "vote": vote.vote.value, 
                        "reasoning": vote.reasoning, 
                        "confidence": vote.confidence
                    }
                
                yield f"data: {json.dumps({'event': 'vote_complete', 'monolith': name, 'vote': asdict(vote)})}\n\n"
                
            except Exception as e:
                log(f"Streaming error for {name}: {e}", LogLevel.ERROR, "API")
                yield f"data: {json.dumps({'event': 'error', 'monolith': name, 'error': str(e)})}\n\n"
        
        verdict = orchestrator._calculate_consensus(votes)
        yield f"data: {json.dumps({'event': 'consensus', **verdict})}\n\n"
        yield f"data: {json.dumps({'event': 'done'})}\n\n"
        
    except Exception as e:
        log(f"Streaming fatal error: {e}", LogLevel.CRITICAL, "API")
        yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"
```

