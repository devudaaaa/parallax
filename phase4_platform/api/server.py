"""
Platform API Server — FastAPI backend for the digital twin.

Exposes the twin's capabilities as REST endpoints:
- Chat with the twin
- Make decisions
- View memories and stats
- Divergence tracking for Phase 3
- WebSocket for real-time messaging

This connects to the dashboard (Phase 4) and messaging connectors.

Usage:
    python -m phase4_platform.api.server
    # or
    uvicorn phase4_platform.api.server:app --reload --port 8000
"""

import json
import time
import collections
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Security, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from loguru import logger

from config_loader import settings, ensure_directories


# ── Rate Limiting ────────────────────────────────────────
# Simple in-process token bucket. Per-IP, 30 requests/minute default.
# For production behind a reverse proxy, also use nginx limit_req.

class RateLimiter:
    """In-process rate limiter using sliding window."""
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = collections.defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window
        # Prune old entries
        self._hits[key] = [t for t in self._hits[key] if t > window_start]
        if len(self._hits[key]) >= self.max_requests:
            return False
        self._hits[key].append(now)
        return True

_rate_limiter = RateLimiter()

async def rate_limit(request: Request):
    """Rate limit middleware — per-IP, 30 req/min."""
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")


# ── API Key Security ─────────────────────────────────
# Set PARALLAX_API_KEY in .env to enable authentication.
# When set, all REST endpoints require: Authorization: Bearer <key>
# When unset, auth is disabled (local development only).

API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify the API key if one is configured."""
    expected = getattr(settings, 'parallax_api_key', '') or ''
    if not expected:
        return True  # No key configured — local dev mode
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    # Support both "Bearer <key>" and raw key
    token = api_key.replace("Bearer ", "").strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


# ── Request/Response Models ────────────────────────────

class ChatRequest(BaseModel):
    message: str
    sender: str = "user"
    access_tier: str = "friends"
    context: str = ""


class ChatResponse(BaseModel):
    response: str
    twin_name: str
    access_tier: str
    memories_used: int = 0
    timestamp: str


class DecisionRequest(BaseModel):
    question: str
    context: str = ""
    options: list[str] = []


class DecisionResponse(BaseModel):
    decision_id: str
    question: str
    chosen: str
    outcome: str
    confidence: float
    reasoning: str
    arguments_for: list[str]
    arguments_against: list[str]
    below_faith_threshold: bool
    timestamp: str


class HumanChoiceRequest(BaseModel):
    decision_id: str
    human_choice: str
    notes: str = ""


class TwinStatusResponse(BaseModel):
    twin_name: str
    provider: str
    model: str
    access_tier: str
    memory_stats: dict
    divergence_stats: dict


# ── App Setup ──────────────────────────────────────────

# Global twin instance
_twin = None


def get_twin():
    """Get or create the global twin instance."""
    global _twin
    if _twin is None:
        from phase2_logic_twin.twin import DigitalTwin
        _twin = DigitalTwin()
    return _twin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    ensure_directories()
    logger.info("🧠 Digital Twin Platform starting...")
    logger.info(f"   Provider: {settings.primary_llm_provider}")
    logger.info(f"   Model: {settings.primary_model}")
    yield
    logger.info("Digital Twin Platform shutting down.")


app = FastAPI(
    title="Parallax — Generative Agent API",
    description=(
        "API for the Parallax generative agent system. "
        "Chat, make decisions, and track divergence for behavioral research."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — restrict in production
_allowed_origins = settings.cors_origins.split(",") if hasattr(settings, 'cors_origins') and settings.cors_origins else ["http://localhost:3000", "http://localhost:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Chat Endpoints ─────────────────────────────────────

@app.post("/api/v1/chat", response_model=ChatResponse, dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def chat(request: ChatRequest):
    """Send a message to the digital twin and get a response."""
    twin = get_twin()
    twin.set_access_tier(request.access_tier)
    
    start = time.time()
    response = twin.respond(
        message=request.message,
        sender=request.sender,
        context=request.context,
    )
    elapsed = time.time() - start
    
    logger.info(f"Chat response in {elapsed:.2f}s ({len(response)} chars)")
    
    return ChatResponse(
        response=response,
        twin_name=settings.twin_name,
        access_tier=request.access_tier,
        timestamp=datetime.now().isoformat(),
    )


@app.post("/api/v1/chat/clear", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def clear_chat():
    """Clear the conversation history."""
    twin = get_twin()
    twin.clear_conversation()
    return {"status": "cleared"}


# ── Decision Endpoints ─────────────────────────────────

@app.post("/api/v1/decide", response_model=DecisionResponse, dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def decide(request: DecisionRequest):
    """
    Ask the twin to make a structured decision.
    
    The decision is logged for Phase 3 divergence analysis.
    Use the /record endpoint afterward to log what the real human chose.
    """
    twin = get_twin()
    
    result = twin.decide(
        question=request.question,
        context=request.context,
        options=request.options,
    )
    
    return DecisionResponse(
        decision_id=result["decision_id"],
        question=result["question"],
        chosen=result["chosen"],
        outcome=result["outcome"],
        confidence=result["confidence"],
        reasoning=result["reasoning"],
        arguments_for=result["arguments_for"],
        arguments_against=result["arguments_against"],
        below_faith_threshold=result["below_faith_threshold"],
        timestamp=result["timestamp"],
    )


@app.post("/api/v1/decide/record", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def record_human_choice(request: HumanChoiceRequest):
    """
    Record what the real human chose for a decision.
    
    This is the Phase 3 data collection endpoint.
    The divergence between twin's choice and human's choice
    is the faith-variable signal.
    """
    twin = get_twin()
    twin.reasoning.record_human_choice(
        decision_id=request.decision_id,
        human_choice=request.human_choice,
        notes=request.notes,
    )
    return {"status": "recorded", "decision_id": request.decision_id}


# ── Status & Analytics ─────────────────────────────────

@app.get("/api/v1/status", response_model=TwinStatusResponse, dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def get_status():
    """Get the digital twin's current status and statistics."""
    twin = get_twin()
    status = twin.get_status()
    
    return TwinStatusResponse(
        twin_name=status["twin_name"],
        provider=status["provider"],
        model=status["model"],
        access_tier=status["access_tier"],
        memory_stats=status["memory"],
        divergence_stats=status["divergence"],
    )


@app.get("/api/v1/divergence", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def get_divergence_stats():
    """
    Get divergence statistics for Phase 3 analysis.
    
    Returns the faith-variable signal strength and related metrics.
    """
    twin = get_twin()
    return twin.reasoning.get_divergence_stats()


@app.get("/api/v1/memory/search", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def search_memories(
    query: str,
    n: int = 5,
    tier: str = "friends",
    source: Optional[str] = None,
):
    """Search the twin's memories."""
    twin = get_twin()
    memories = twin.memory.recall(
        query=query,
        n_results=n,
        access_tier=tier,
        source_type=source,
    )
    return {"query": query, "results": memories}


@app.get("/api/v1/memory/stats", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def memory_stats():
    """Get memory system statistics."""
    twin = get_twin()
    return twin.memory.get_stats()


# ── Temporal Engine Endpoints ──────────────────────

@app.get("/api/v1/temporal/status", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def temporal_status():
    """
    Get the GTRBAC temporal engine status.
    
    Shows current role states, active constraints, personality mode,
    and access tier — all governed by periodic expressions from
    Bertino et al. (1998) as implemented in the AIT research.
    """
    twin = get_twin()
    return twin.temporal_engine.get_status()


@app.post("/api/v1/temporal/tick", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def force_tick():
    """Force an engine tick (evaluate all constraints now)."""
    twin = get_twin()
    changes = twin.temporal_engine.tick()
    return {
        "changes": changes,
        "current_mode": twin.temporal_engine.get_current_personality_mode(),
        "current_tier": twin.temporal_engine.get_current_access_tier(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/temporal/schedule", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def get_schedule(hours_ahead: int = 24):
    """
    Preview the temporal schedule for the next N hours.
    
    Shows when each mode/tier will be active based on periodic expressions.
    """
    from datetime import timedelta
    
    twin = get_twin()
    now = datetime.now()
    schedule = []
    
    # Simulate ticks for the next N hours
    for minutes in range(0, hours_ahead * 60, 5):  # every 5 min
        t = now + timedelta(minutes=minutes)
        active_constraints = {}
        
        for name, constraint in twin.temporal_engine.constraints.items():
            if constraint.enabled and constraint.is_active_at(t):
                active_constraints[name] = {
                    "target": constraint.target,
                    "event": constraint.event_mode.value,
                }
        
        if active_constraints:
            schedule.append({
                "time": t.strftime("%Y-%m-%d %H:%M"),
                "active_constraints": active_constraints,
            })
    
    return {"schedule": schedule, "hours_ahead": hours_ahead}


# ── WebSocket for Real-time Chat ───────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Real-time chat via WebSocket. Auth via ?token= query param."""
    # Verify auth if key is configured
    expected = getattr(settings, 'parallax_api_key', '') or ''
    if expected:
        token = websocket.query_params.get("token", "")
        if token != expected:
            await websocket.close(code=4003, reason="Invalid or missing token")
            return
    
    await websocket.accept()
    twin = get_twin()
    
    logger.info("WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            response = twin.respond(
                message=msg.get("message", ""),
                sender=msg.get("sender", "user"),
            )
            
            await websocket.send_json({
                "response": response,
                "twin_name": settings.twin_name,
                "timestamp": datetime.now().isoformat(),
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# ── Webhook for External Integrations ──────────────────

@app.post("/api/v1/webhook", dependencies=[Depends(rate_limit), Depends(verify_api_key)])
async def webhook(payload: dict):
    """
    Generic webhook endpoint for external integrations.
    
    Accepts messages from Slack, Discord, or custom services
    and returns the twin's response.
    """
    message = payload.get("text", payload.get("message", payload.get("content", "")))
    sender = payload.get("user", payload.get("sender", "webhook"))
    
    if not message:
        raise HTTPException(status_code=400, detail="No message found in payload")
    
    twin = get_twin()
    response = twin.respond(message=message, sender=sender)
    
    return {
        "response": response,
        "twin_name": settings.twin_name,
        "timestamp": datetime.now().isoformat(),
    }


# ── Dashboard ──────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard."""
    from pathlib import Path
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return HTMLResponse(dashboard_path.read_text())
    return HTMLResponse(
        "<html><body><h1>Parallax</h1>"
        "<p>Dashboard not built yet. API is running at /api/v1/</p>"
        "<p><a href='/docs'>API Documentation</a></p></body></html>"
    )


# ── Run ────────────────────────────────────────────────

def main():
    """Run the server."""
    import uvicorn
    uvicorn.run(
        "phase4_platform.api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
