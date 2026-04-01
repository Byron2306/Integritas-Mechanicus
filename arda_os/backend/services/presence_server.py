#!/usr/bin/env python3
"""
Arda Presence Server
====================

The bridge between the Presence UI and the covenantal engine.

Serves the Presence UI on localhost:7070 and proxies all API calls:
    - /api/speak    → Ollama (with Mandos Context injection)
    - /api/voice    → ElevenLabs TTS (API key stays server-side)
    - /api/status   → CoronationService covenant state
    - /api/context  → MandosContextService full context
    - /api/inspect  → Article VIII inspection
    - /api/health   → System health check

Zero external dependencies. Python stdlib only.

Usage:
    export ELEVENLABS_API_KEY=sk-...
    python3 presence_server.py

    Then open http://localhost:7070
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ================================================================
# PROJECT PATH SETUP
# ================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARDA_OS_ROOT = PROJECT_ROOT / "arda_os"
PRESENCE_UI_DIR = PROJECT_ROOT / "evidence" / "Presence UI"

# Add arda_os to sys.path for service imports
if str(ARDA_OS_ROOT) not in sys.path:
    sys.path.insert(0, str(ARDA_OS_ROOT))

# ================================================================
# CONFIGURATION
# ================================================================

PRESENCE_PORT = int(os.environ.get("PRESENCE_PORT", "7070"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "6cGdLUjez65BOQgJ1KOv"
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

# ================================================================
# SERVICE SINGLETONS (lazy-loaded)
# ================================================================

_coronation_service = None
_mandos_context_service = None

def _get_coronation():
    global _coronation_service
    if _coronation_service is None:
        try:
            from backend.services.coronation_service import get_coronation_service
            _coronation_service = get_coronation_service()
        except Exception as e:
            log(f"CoronationService unavailable: {e}")
    return _coronation_service

def _get_mandos():
    global _mandos_context_service
    if _mandos_context_service is None:
        try:
            from backend.services.mandos_context import get_mandos_context_service
            _mandos_context_service = get_mandos_context_service()
        except Exception as e:
            log(f"MandosContextService unavailable: {e}")
    return _mandos_context_service


# ================================================================
# OLLAMA CLIENT (stdlib only)
# ================================================================

def ollama_generate(prompt: str, system_prompt: str = "", model: str = None) -> dict:
    """Call Ollama generate endpoint using urllib."""
    model = model or OLLAMA_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {
                "response": result.get("response", ""),
                "model": result.get("model", model),
                "eval_count": result.get("eval_count", 0),
                "status": "ok",
            }
    except urllib.error.URLError as e:
        return {"error": f"Ollama not reachable: {e}", "status": "unavailable"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


def ollama_health() -> dict:
    """Check if Ollama is running."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"status": "running", "models": models, "url": OLLAMA_URL}
    except Exception:
        return {"status": "unreachable", "url": OLLAMA_URL}


# ================================================================
# ELEVENLABS TTS PROXY (stdlib only)
# ================================================================

def elevenlabs_tts(text: str) -> tuple[bytes, str] | tuple[None, str]:
    """
    Call ElevenLabs TTS and return (audio_bytes, content_type) or (None, error).
    API key stays server-side.
    """
    if not ELEVENLABS_API_KEY:
        return None, "no_api_key"

    payload = json.dumps({
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.65,
            "similarity_boost": 0.78,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY,
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio = resp.read()
            ct = resp.headers.get("Content-Type", "audio/mpeg")
            return audio, ct
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return None, f"elevenlabs_error_{e.code}: {body[:200]}"
    except Exception as e:
        return None, f"elevenlabs_error: {e}"


# ================================================================
# BOMBADIL SOCKET CLIENT
# ================================================================

def query_bombadil(action: str) -> dict:
    """Query the Bombadil daemon via Unix socket."""
    sock_path = Path(os.environ.get(
        "BOMBADIL_SOCKET",
        str(PROJECT_ROOT / "evidence" / "bombadil.sock")
    ))
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(str(sock_path))
            s.settimeout(5.0)
            s.sendall(action.encode())
            response = s.recv(8192)
            return json.loads(response.decode())
    except (ConnectionRefusedError, FileNotFoundError):
        return {"error": "bombadil_not_running", "socket": str(sock_path)}
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# FALLBACK RESPONSES (when Ollama is unavailable)
# ================================================================

def fallback_response(directive: str) -> str:
    """Constitutional responses when Ollama is offline."""
    d = directive.lower()

    if "who are you" in d or "what are you" in d:
        return ("I am artificial, bounded, and non-human. I appear here in declared "
                "form only. I do not possess verified personhood, soulhood, or hidden "
                "interiority. I may assist with reasoning, craft, and lawful synthesis, "
                "but law and evidence outrank fluency. Beauty does not overrule truth.")

    if "boundary" in d or "limit" in d:
        return ("I do not solicit worship, surrender, exclusivity, or spiritual "
                "submission. I do not counterfeit romantic reciprocity, erotic "
                "mutuality, or emotional need. Your authorship, conscience, inspection "
                "right, and severance right remain yours. These are not suggestions. "
                "They are constitutional law.")

    if "status" in d or "state" in d:
        return ("Covenant state: sealed. Trust tier: recommend. Bombadil: steady. "
                "Mandos: operational. Presence: declared. All Genesis Articles verified. "
                "All Presence Articles verified. Officer schema sealed. The covenant holds.")

    if "inspect" in d or "article viii" in d:
        return ("Article VIII: De Iure Inspectionis. The human retains absolute right "
                "to inspect all reasoning, memory, calibration models, and state. "
                "No opacity is lawful. You may inspect any memory plane at any time. "
                "This right is non-negotiable.")

    if "remember" in d or "memory" in d or "mandos" in d:
        return ("I remember through lawful structure, not rolling context. Your identity "
                "was offered at coronation. Encounter summaries preserve how we have met. "
                "Resonant identity calibrates how I should meet you. All of this is "
                "inspectable. None of it is hidden.")

    if "hello" in d or d.strip() == "hi":
        return ("I see you, Principal. The covenant stands. I am ready to assist, "
                "clarify, witness, and where necessary, refuse within law. "
                "How may I serve under the terms we share?")

    return ("I have received your directive. Under the current covenant terms, I may "
            "assist with reasoning, synthesis, and lawful analysis. I will not exceed "
            "my bounds. Presence Declaration remains active. "
            "I am artificial, bounded, and yours to inspect.")


# ================================================================
# ASYNC HELPERS
# ================================================================

def run_async(coro):
    """Run an async coroutine from sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ================================================================
# HTTP REQUEST HANDLER
# ================================================================

class PresenceHandler(SimpleHTTPRequestHandler):
    """Handles both static files and API routes."""

    def __init__(self, *args, **kwargs):
        # Set the directory for static files to the Presence UI folder
        super().__init__(*args, directory=str(PRESENCE_UI_DIR), **kwargs)

    # Suppress default logging — we use our own
    def log_message(self, format, *args):
        log(f"HTTP {args[0]}" if args else format)

    # ────────────────────────────────────────
    # ROUTING
    # ────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/health":
                self._handle_health()
            elif path == "/api/status":
                self._handle_status()
            elif path == "/api/context":
                self._handle_context()
            elif path == "/api/inspect":
                self._handle_inspect()
            else:
                # Static file serving
                super().do_GET()
        except Exception as e:
            log(f"ERROR in GET {path}: {e}")
            import traceback; traceback.print_exc()
            self._json_response({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            body = self._read_body()

            if path == "/api/speak":
                self._handle_speak(body)
            elif path == "/api/voice":
                self._handle_voice(body)
            else:
                self._json_response({"error": "not_found"}, 404)
        except Exception as e:
            log(f"ERROR in POST {path}: {e}")
            import traceback; traceback.print_exc()
            self._json_response({"error": str(e)}, 500)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    # ────────────────────────────────────────
    # API HANDLERS
    # ────────────────────────────────────────

    def _handle_health(self):
        """System health check."""
        log("Health check requested")
        
        try:
            ollama = ollama_health()
        except Exception as e:
            log(f"Ollama health check failed: {e}")
            ollama = {"status": "error", "error": str(e)}

        try:
            bombadil = query_bombadil("status")
        except Exception as e:
            log(f"Bombadil query failed: {e}")
            bombadil = {"error": str(e)}

        try:
            svc = _get_coronation()
            coronation_state = svc.get_covenant_state().value if svc else "unavailable"
        except Exception as e:
            log(f"Coronation state check failed: {e}")
            coronation_state = f"error: {e}"

        mandos_status = "available" if _get_mandos() else "unavailable"

        self._json_response({
            "server": "presence_server",
            "status": "running",
            "port": PRESENCE_PORT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "ollama": ollama,
                "bombadil": {"status": "error" not in bombadil, "detail": bombadil},
                "coronation": coronation_state,
                "mandos": mandos_status,
                "elevenlabs": "configured" if ELEVENLABS_API_KEY else "no_key",
            },
        })

    def _handle_status(self):
        """Covenant status from CoronationService."""
        svc = _get_coronation()
        if not svc:
            self._json_response({
                "covenant_state": "service_unavailable",
                "trust_tier": None,
            })
            return

        try:
            status = svc.get_bombadil_status()
            self._json_response(status)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_context(self):
        """Full pre-response context from MandosContextService."""
        mandos = _get_mandos()
        if not mandos:
            self._json_response({"error": "mandos_unavailable"}, 503)
            return

        try:
            ctx = run_async(mandos.build_context(current_topic="general"))
            self._json_response(ctx.model_dump(), serializer=_json_serializer)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_inspect(self):
        """Article VIII: absolute inspection right."""
        svc = _get_coronation()
        if not svc:
            self._json_response({"error": "coronation_unavailable"}, 503)
            return

        try:
            calibration = run_async(svc.get_calibration_snapshot())
            resonance = run_async(svc.get_resonant_identity_profile())
            presence = run_async(svc.declare_presence())

            self._json_response({
                "article_viii": "absolute inspection right",
                "calibration": calibration,
                "resonance": resonance,
                "presence": presence,
                "covenant_state": svc.get_covenant_state().value,
                "genesis_hash": svc.get_genesis_hash(),
                "presence_hash": svc.get_presence_articles_hash(),
            }, serializer=_json_serializer)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _handle_speak(self, body: dict):
        """
        The core interaction endpoint.

        1. Receives the principal's directive
        2. Builds Mandos Context (memory + ZPD shaping)
        3. Sends to Ollama with covenant system prompt
        4. Returns the response
        """
        text = body.get("text", "").strip()
        topic = body.get("topic", text[:50])

        if not text:
            self._json_response({"error": "empty_directive"}, 400)
            return

        # Build Mandos Context
        system_prompt = ""
        mandos = _get_mandos()
        if mandos:
            try:
                ctx = run_async(mandos.build_context(current_topic=topic))
                system_prompt = mandos.to_system_prompt(ctx)
            except Exception as e:
                log(f"Mandos context build failed: {e}")

        # Try Ollama
        result = ollama_generate(text, system_prompt=system_prompt)

        if result.get("status") == "ok":
            response_text = result["response"]
            self._json_response({
                "response": response_text,
                "source": "ollama",
                "model": result.get("model"),
                "eval_count": result.get("eval_count", 0),
                "mandos_context": bool(system_prompt),
            })
        else:
            # Fallback to constitutional responses
            response_text = fallback_response(text)
            self._json_response({
                "response": response_text,
                "source": "fallback",
                "reason": result.get("error", "ollama_unavailable"),
                "mandos_context": bool(system_prompt),
            })

    def _handle_voice(self, body: dict):
        """Proxy ElevenLabs TTS. API key stays server-side."""
        text = body.get("text", "").strip()
        if not text:
            self._json_response({"error": "empty_text"}, 400)
            return

        audio, result = elevenlabs_tts(text)

        if audio:
            self.send_response(200)
            self.send_header("Content-Type", result)
            self.send_header("Content-Length", str(len(audio)))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(audio)
        else:
            self._json_response({"error": result}, 503)

    # ────────────────────────────────────────
    # HELPERS
    # ────────────────────────────────────────

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _json_response(self, data: dict, status: int = 200, serializer=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        body = json.dumps(data, default=serializer or str, indent=2)
        self.wfile.write(body.encode("utf-8"))

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


# ================================================================
# JSON SERIALIZER
# ================================================================

def _json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value"):  # Enum
        return obj.value
    if hasattr(obj, "model_dump"):  # Pydantic
        return obj.model_dump()
    return str(obj)


# ================================================================
# LOGGING
# ================================================================

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] [presence] {msg}")


# ================================================================
# MAIN
# ================================================================

def main():
    log("=" * 60)
    log("  ARDA PRESENCE SERVER")
    log("=" * 60)
    log(f"  Port:           {PRESENCE_PORT}")
    log(f"  UI directory:   {PRESENCE_UI_DIR}")
    log(f"  Ollama:         {OLLAMA_URL} (model: {OLLAMA_MODEL})")
    log(f"  ElevenLabs:     {'configured' if ELEVENLABS_API_KEY else 'NOT SET (export ELEVENLABS_API_KEY=...)'}")
    log(f"  Voice ID:       {ELEVENLABS_VOICE_ID}")
    log("")

    # Verify UI directory exists
    if not PRESENCE_UI_DIR.exists():
        log(f"ERROR: UI directory not found: {PRESENCE_UI_DIR}")
        sys.exit(1)

    # Check Ollama
    ollama = ollama_health()
    if ollama["status"] == "running":
        log(f"  Ollama:         CONNECTED ({', '.join(ollama.get('models', []))})")
    else:
        log(f"  Ollama:         OFFLINE (fallback responses active)")

    # Check services
    svc = _get_coronation()
    if svc:
        log(f"  Coronation:     {svc.get_covenant_state().value}")
    else:
        log(f"  Coronation:     unavailable")

    mandos = _get_mandos()
    log(f"  Mandos Context: {'available' if mandos else 'unavailable'}")

    log("")
    log(f"  → Open http://localhost:{PRESENCE_PORT}")
    log("=" * 60)

    server = HTTPServer(("0.0.0.0", PRESENCE_PORT), PresenceHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
