from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import sqlite3
import asyncio
import hashlib
import time
import threading
import queue
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="KnowEdge Merger Control Plane", version="5.0.0")

# --- Globals & Stores ---
ollama_online_event = threading.Event()
mistral_queue = queue.Queue()
chronicle_queue = queue.Queue()
mistral_results = {} # task_id -> result

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
STORAGE_PATH = os.getenv("STORAGE_PATH", "./data/objects")
DB_PATH = os.getenv("APP_DB", "./data/app.db").replace("sqlite:", "").replace("///", "")
RUNS_DB_PATH = "./data/runs.db"
USERS_FILE = "./data/users.json"

if GEMINI_API_KEY:
    genai.configure(apiKey=GEMINI_API_KEY)
    TARGET_MODEL = "gemini-1.5-flash" 
else:
    TARGET_MODEL = None

os.makedirs("data", exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(STORAGE_PATH, exist_ok=True)

# --- Control Plane Models ---
class RunState(str, Enum):
    created = "created"
    validating = "validating"
    ingesting = "ingesting"
    indexing = "indexing"
    mapping = "mapping"
    comparing = "comparing"
    blueprints_generating = "blueprints_generating"
    scoring = "scoring"
    qa = "qa"
    auditing = "auditing"
    finalizing = "finalizing"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"
    quarantined = "quarantined"

STATE_SEQUENCE = [
    RunState.created.value, RunState.validating.value, RunState.ingesting.value, RunState.indexing.value, 
    RunState.mapping.value, RunState.comparing.value, RunState.blueprints_generating.value, 
    RunState.scoring.value, RunState.qa.value, RunState.auditing.value, 
    RunState.finalizing.value, RunState.completed.value
]

class Heartbeat(BaseModel):
    run_id: str
    phase: str
    status: str
    progress_pct: float
    last_checkpoint: str
    last_module: str
    warning_count: int
    anomaly_count: int
    receipt_count: int
    memory_checksum: str
    artifact_hash: str
    retry_count: int
    quarantine: bool
    last_exception: Optional[str] = None
    updated_at_utc: str

class RunCreateRequest(BaseModel):
    operator: str
    source_file: str
    target_file: str

class TransitionRequest(BaseModel):
    to_state: RunState

class ReceiptRequest(BaseModel):
    module: str
    payload: Dict[str, Any]

# --- Database Initialization ---
def init_db():
    # Primary App DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, runId TEXT, content TEXT, status TEXT, timestamp TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS uploads (id TEXT PRIMARY KEY, filename TEXT, hash TEXT, path TEXT, timestamp TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, userId TEXT, lastActive TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS learning_sessions (id TEXT PRIMARY KEY, concept TEXT, level TEXT, state TEXT, history TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()
    
    # Runs DB (Control Plane)
    run_conn = sqlite3.connect(RUNS_DB_PATH)
    run_cursor = run_conn.cursor()
    run_cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            state TEXT,
            created_at TEXT,
            updated_at TEXT,
            operator TEXT,
            source_file TEXT,
            target_file TEXT,
            receipt_count INTEGER DEFAULT 0,
            anomaly_count INTEGER DEFAULT 0,
            corpus_normalized BOOLEAN DEFAULT 0,
            retry_count INTEGER DEFAULT 0
        )
    """)
    run_cursor.execute("""
        CREATE TABLE IF NOT EXISTS heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            phase TEXT,
            progress_pct REAL,
            updated_at_utc TEXT,
            data TEXT
        )
    """)
    run_cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            module TEXT,
            receipt_hash TEXT,
            issued_at TEXT,
            payload TEXT
        )
    """)
    run_cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            phase TEXT,
            checkpoint_data TEXT,
            created_at TEXT
        )
    """)
    run_cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_state (
            run_id TEXT PRIMARY KEY,
            entities TEXT,
            constraints TEXT,
            goals TEXT,
            unresolved_refs TEXT,
            schema_anchors TEXT,
            policy_pack_id TEXT,
            updated_at TEXT
        )
    """)
    run_conn.commit()
    run_conn.close()

    # DataDriven DB
    dd_conn = sqlite3.connect("datadriven.db")
    dd_cursor = dd_conn.cursor()
    dd_cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            student_id TEXT,
            timestamp TEXT,
            file_hash TEXT,
            similarity_score REAL,
            ai_detection_percent REAL,
            metadata TEXT
        )
    """)
    dd_conn.commit()
    dd_conn.close()

init_db()

# --- Run Controller Utilities ---

def get_run_db(run_id: str):
    conn = sqlite3.connect(RUNS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_run_state_db(run_id: str, state: RunState, retry_increment=0):
    conn = sqlite3.connect(RUNS_DB_PATH)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        UPDATE runs SET state = ?, updated_at = ?, retry_count = retry_count + ?
        WHERE run_id = ?
    """, (state.value, now, retry_increment, run_id))
    conn.commit()
    conn.close()

def write_heartbeat_db(hb: Heartbeat):
    conn = sqlite3.connect(RUNS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO heartbeats (run_id, phase, progress_pct, updated_at_utc, data)
        VALUES (?, ?, ?, ?, ?)
    """, (hb.run_id, hb.phase, hb.progress_pct, hb.updated_at_utc, hb.json()))
    conn.commit()
    conn.close()

def get_latest_heartbeat_db(run_id: str):
    conn = sqlite3.connect(RUNS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM heartbeats WHERE run_id = ? ORDER BY id DESC LIMIT 1", (run_id,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row['data']) if row else None

# --- API Endpoints ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/runs")
async def create_run_endpoint(req: RunCreateRequest):
    run_id = f"RUN-{datetime.now().strftime('%Y%m%d')}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:4].upper()}"
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(RUNS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO runs (run_id, state, created_at, updated_at, operator, source_file, target_file)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (run_id, RunState.created.value, now, now, req.operator, req.source_file, req.target_file))
    conn.commit()
    conn.close()
    
    # Write initial heartbeat
    hb = Heartbeat(
        run_id=run_id,
        phase=RunState.created.value,
        status="OK",
        progress_pct=0,
        last_checkpoint="START",
        last_module="SYSTEM",
        warning_count=0,
        anomaly_count=0,
        receipt_count=0,
        memory_checksum="INIT",
        artifact_hash=hashlib.sha256(req.source_file.encode()).hexdigest()[:8],
        retry_count=0,
        quarantine=False,
        updated_at_utc=now
    )
    write_heartbeat_db(hb)
    return {"run_id": run_id, "state": RunState.created}

@app.get("/api/v1/runs/{run_id}")
async def get_run_endpoint(run_id: str):
    run = get_run_db(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    hb = get_latest_heartbeat_db(run_id)
    return {"run": run, "heartbeat": hb}

@app.post("/api/v1/runs/{run_id}/transition")
async def transition_endpoint(run_id: str, req: TransitionRequest):
    run = get_run_db(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    current_state = run['state']
    to_state = req.to_state
    
    # Emergency transitions allowed from any state
    if to_state in [RunState.failed, RunState.rolled_back, RunState.quarantined]:
        update_run_state_db(run_id, to_state)
        return {"run_id": run_id, "state": to_state}

    # Strict Validation Gate
    if to_state == RunState.validating:
        if len(run['source_file']) < 50 or len(run['target_file']) < 50:
            update_run_state_db(run_id, RunState.failed)
            raise HTTPException(status_code=400, detail="Artifacts too short for forensic analysis (min 50 chars)")
        if run['source_file'] == run['target_file']:
            update_run_state_db(run_id, RunState.failed)
            raise HTTPException(status_code=400, detail="Source and Target are identical")

    # Stop Rules
    if to_state == RunState.finalizing:
        if run['receipt_count'] < 6:
            raise HTTPException(status_code=409, detail=f"Insufficient evidence. Receipt count ({run['receipt_count']}) < 6")
    
    if to_state == RunState.completed:
        if run['anomaly_count'] > 0:
             raise HTTPException(status_code=409, detail="Unresolved anomalies block completion. Manual override required.")

    # State sequence enforcement
    try:
        curr_idx = STATE_SEQUENCE.index(current_state)
        target_idx = STATE_SEQUENCE.index(to_state.value)
        if target_idx > curr_idx + 1:
             raise HTTPException(status_code=400, detail=f"Invalid jump: {current_state} -> {to_state}")
    except ValueError:
        pass

    update_run_state_db(run_id, to_state)
    
    # Write checkpoint
    conn = sqlite3.connect(RUNS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO checkpoints (run_id, phase, checkpoint_data, created_at) VALUES (?, ?, ?, ?)",
                   (run_id, to_state.value, json.dumps(run), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    # Update Heartbeat
    old_hb = get_latest_heartbeat_db(run_id)
    progress = 0
    if to_state.value in STATE_SEQUENCE:
        progress = (STATE_SEQUENCE.index(to_state.value) / (len(STATE_SEQUENCE)-1)) * 100
        
    new_hb = Heartbeat(
        **old_hb,
        phase=to_state.value,
        progress_pct=progress,
        updated_at_utc=datetime.utcnow().isoformat()
    )
    write_heartbeat_db(new_hb)
    
    return {"run_id": run_id, "state": to_state}

@app.post("/api/v1/runs/{run_id}/receipt")
async def issue_receipt_endpoint(run_id: str, req: ReceiptRequest):
    run = get_run_db(run_id)
    if not run: raise HTTPException(status_code=404, detail="Run not found")
    
    payload_str = json.dumps(req.payload)
    h = hashlib.sha256(payload_str.encode()).hexdigest()
    now = datetime.utcnow().isoformat()
    
    conn = sqlite3.connect(RUNS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO receipts (run_id, module, receipt_hash, issued_at, payload) VALUES (?, ?, ?, ?, ?)",
                   (run_id, req.module, h, now, payload_str))
    cursor.execute("UPDATE runs SET receipt_count = receipt_count + 1 WHERE run_id = ?", (run_id,))
    conn.commit()
    conn.close()
    
    return {"receipt_hash": h}

@app.post("/api/v1/runs/{run_id}/rollback")
async def rollback_endpoint(run_id: str):
    update_run_state_db(run_id, RunState.rolled_back)
    return {"status": "rolled_back"}

@app.post("/api/v1/runs/{run_id}/quarantine")
async def quarantine_endpoint(run_id: str):
    update_run_state_db(run_id, RunState.quarantined)
    return {"status": "quarantined"}

@app.get("/api/v1/runs/{run_id}/heartbeat")
async def get_heartbeat_endpoint(run_id: str):
    hb = get_latest_heartbeat_db(run_id)
    if not hb: raise HTTPException(status_code=404, detail="Heartbeat not found")
    return hb

@app.get("/api/v1/runs")
async def list_runs_endpoint():
    conn = sqlite3.connect(RUNS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        d = dict(r)
        d['heartbeat'] = get_latest_heartbeat_db(r['run_id'])
        res.append(d)
    return res

@app.get("/api/v1/runs/{run_id}/decision-state")
async def get_decision_state_endpoint(run_id: str):
    conn = sqlite3.connect(RUNS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM decision_state WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()
    if not row: return {}
    return dict(row)

# --- Restoration of existing logic ---

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "backend": "Control Plane v5.0.0",
        "ollama_online": ollama_online_event.is_set(),
        "timestamp": datetime.now().isoformat()
    }

class CircleAIDetectionRequest(BaseModel):
    text: str

@app.post("/api/circleai/detect")
async def circleai_detect(req: CircleAIDetectionRequest):
    if not TARGET_MODEL:
        raise HTTPException(status_code=503, detail="Gemini Engine Offline")
    prompt = f"[CIRCLEAI FORENSIC DETECTION LAYER] Analyze text: {req.text[:5000]}"
    try:
        model = genai.GenerativeModel(TARGET_MODEL)
        response = model.generate_content(prompt)
        res_text = response.text
        if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0].strip()
        return json.loads(res_text)
    except:
        return {"circle_score": 0, "verdict": "ERROR"}

@app.get("/api/datadriven/analytics")
async def datadriven_analytics():
    try:
        conn = sqlite3.connect("datadriven.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM submissions")
        total = cursor.fetchone()[0]
        conn.close()
        return {"total_submissions": total or 0, "avg_ai_score": 0.15}
    except: return {"total_submissions": 0}

@app.post("/api/v1/register")
async def register_user(req: Dict[str, Any]):
    username = req.get("username")
    accessCode = req.get("accessCode")
    fullName = req.get("fullName")
    users = []
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f: users = json.load(f)
    users.append({"username": username, "accessCode": accessCode, "fullName": fullName, "registeredAt": int(time.time() * 1000), "role": "USER"})
    with open(USERS_FILE, "w") as f: json.dump(users, f, indent=2)
    return {"success": True}

@app.get("/api/v1/users/check")
async def check_users():
    if not os.path.exists(USERS_FILE): return {"registered": False}
    with open(USERS_FILE, "r") as f: users = json.load(f)
    return {"registered": len(users) > 0}

@app.on_event("startup")
def startup_event():
    print("[SYSTEM] Control Plane v5.0.0 Online.")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=3000)
