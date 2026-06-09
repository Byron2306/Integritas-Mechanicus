# KnowEdge Merger Playbook V4.7.0-NWU-FORENSIC-CERTIFIED

## 1. System Overview
KnowEdge Merger is a forensic-grade intelligence platform designed for the NWU cluster to ensure academic integrity through neural artifact analysis and multi-provider cross-referencing. Version 4.7.0 introduces the **Automated Forensic Pipeline (v4.7.0)**.

## 2. Architecture
*   **Frontend**: React 19 / Vite / Tailwind 4 / Framer Motion / Lucide.
*   **Backend**: FastAPI (Python 3.12).
*   **Databases**: 
    *   **SQLite**: `app.db` (uploads, sessions) & `datadriven.db` (forensic telemetry).
    *   **Firestore**: Real-time audit trails and user registration.
    *   **Qdrant**: Vector semantic search for neural ingest.

## 3. Automated Forensic Pipeline (New in v4.7.0)
The system now features a 7-step autonomous analysis sequence triggered via the **INITIALISE NEURAL MERGE** command:
1.  **CONTENT VECTORISER**: Semantic embedding and dimensional mapping.
2.  **AI PATTERN SCANNER**: Detection of LLM stylistic artifacts.
3.  **SIMILARITY ENGINE**: Cross-document affinity calcs (Jaccard/Cosine).
4.  **ACADEMIC INTEGRITY**: NWU Integrity Policy cross-referencing.
5.  **REPORT SYNTHESISER**: Construction of the Forensic Result object.
6.  **FORENSIC MATRIX SCAN**: Population of the 9x9 Forensic Sudoku Matrix.
7.  **CERTIFICATION**: Generation of the NWU Forensic Certificate.

## 4. Forensic Sudoku Grid
A display-driven 81-cell matrix representing neural pattern density.
*   **Color Scale**:
    *   **0-30 (Green)**: High Originality.
    *   **31-60 (Amber)**: Low Affinity.
    *   **61-80 (Orange)**: Suspected Pattern.
    *   **81-100 (Red)**: Critical Affinity/AI Flag.
*   **Integrity Check**: Displays 'PATTERN INTEGRITY' count reflecting high-risk cells.

## 5. ERTP Review & Certification
The **ERTP REVIEW** module synthesizes all pipeline data into a legal-grade forensic report:
*   **Case Identification**: Secure timestamping and user tracking.
*   **Affinity Summary**: Statistical overview of document mirrors.
*   **Agent Log**: Full chronological telemetry from the automated pipeline.
*   **Redacted Overlaps**: Segmented evidence extracts.
*   **Recommendation**: Final forensic verdict (Low/Medium/High/Critical Risk).

## 6. Control Plane Architecture (v5.0.0)
The system identity is defined by the **Run Controller Control Plane**, a Python-first, evidence-gated architecture.
*   **Identity**: UI is the shell; the Control Plane is the authority.
*   **Durable Memory**: SQLite-backed state ledger across 5 tables (runs, heartbeats, receipts, checkpoints, decision_state).
*   **Evidence Gate**: No run promotes to 'finalizing' without at least 6 verified module receipts.
*   **Heartbeat**: High-fidelity 16-field telemetry including checksums, hashes, and quarantine status.

## 7. Run States & Lifecycle
KnowEdge Merger enforces 14 specific linear and emergency states:
1.  **created**: Run ID issued.
2.  **validating**: Artifact length/identity verification.
3.  **ingesting**: Neural artifact normalization.
4.  **indexing**: Vector dimensional mapping.
5.  **mapping**: Semantic alignment.
6.  **comparing**: Cross-artifact affinity scan.
7.  **blueprints_generating**: Structural synthesis.
8.  **scoring**: Final metric calculation.
9.  **qa**: Consistency audit.
10. **auditing**: Forensic trail verification.
11. **finalizing**: Evidence consolidation.
12. **completed**: Success terminal state.
*   **Emergency States**: `failed` (logic gate), `rolled_back` (user action), `quarantined` (security anomaly).

## 8. First-Run Registration (v4.6+)
Mandatory initialization for all nodes.
*   **Tethering**: Links node to NWU Username and encrypted Access Code.
*   **Backdoor**: Master admin access remains via `ADMIN / 22807365`.

## 9. Integration & Deployment
*   **PowerShell Ingest**: Use `setup/Create-KnowEdgeMergerZip.ps1` for node replication.
*   **Local Backend**: FastAPI port 8000; Frontend port 3000 (standardized).

## 10. Smoke Test Checklist (v4.7.0)
1. Launch app and verify Registration/Login flow.
2. Load Source and Target artifacts (PDF/DOCX/TXT).
3. Click 'INITIALISE NEURAL MERGE'.
4. Observe 7-step pipeline in terminal UI.
5. Verify Sudoku Grid populates and color-codes automatically.
6. Navigate to 'ERTP REVIEW' and verify the synthesized report.
7. Click 'EXPORT CERTIFIED NWU FORENSIC CERTIFICATE' to test output.

### 15. DEPLOYMENT & STRESS TESTING

### 14.1 PowerShell Deployment Guide
To package the project for institutional distribution, use the automated build script:
1. Open PowerShell as **Administrator**.
2. Run: `setup/Create-KnowEdgeMergerZip.ps1`.
3. The script will validate dependencies and generate a secure ZIP at `C:\Merger Test\KnowEdgeMerger-v4.4.0-NWU.zip`.

### 14.2 Installation Guide
To deploy the platform on a new NWU workstation:
1. Extract the ZIP archive provided by IT compliance.
2. Open PowerShell as **Administrator**.
3. Run: `setup/Install-KnowEdgeMerger.ps1`.
4. Follow the on-screen tips and progress indicators. The installer will configure the Python environment, download the local Mistral model, and register firewall rules.

### 14.3 Startup Guide
The system requires both backend and frontend nodes to be active:
- **Full System**: Run `setup/Start-KnowEdge-Full.bat` to launch everything simultaneously.
- **Manual Backend**: Run `setup/Start-KnowEdge-Backend.bat` (Port 8000).
- **Manual Frontend**: Run `setup/Start-KnowEdge-Frontend.bat` (Port 5173).

### 14.4 Stress Test Guide
To verify node performance and saturation thresholds:
1. Ensure the system is running locally.
2. Run: `setup/Stress-Test-KnowEdge.ps1`.
3. Review the health scores and response time deltas. A final report will be saved to `C:\Merger Test\`.

### 14.5 Environment Comparison Table
| Feature | Google AI Studio Preview | Local MSI Install |
|---|---|---|
| Backend (FastAPI) | Simulated/Preview | Full Python runtime |
| Mistral AI | API only | Local Ollama model |
| Qdrant | In-memory | Persistent storage |
| File persistence | Session only | Full disk persistence |
| Firestore | Emulated | Production Firebase |
| Performance | Preview throttled | Full hardware |
| Port 8000/5173 | Internal only | Localhost accessible |
