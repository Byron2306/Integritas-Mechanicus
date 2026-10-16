"""
Local AI Reasoning Engine
=========================
Free local AI model for threat analysis, incident triage, and decision support.
Uses lightweight models that can run on CPU without external API calls.
"""

from __future__ import annotations


import os
import asyncio
try:
    from services.world_events import emit_world_event
except Exception:
    try:
        from backend.services.world_events import emit_world_event
    except Exception:
        emit_world_event = None
import json
import hashlib
import logging
import re
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


def _run_awaitable_sync(awaitable):
    """Run an awaitable from sync code in both loop and no-loop contexts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    result_box: Dict[str, Any] = {"value": None, "error": None}

    def _runner():
        try:
            result_box["value"] = asyncio.run(awaitable)
        except Exception as exc:
            result_box["error"] = exc

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout=30)
    if t.is_alive():
        raise TimeoutError("Timed out running async operation from sync wrapper")
    if result_box["error"] is not None:
        raise result_box["error"]
    return result_box["value"]


@dataclass
class ReasoningResult:
    """Result from AI reasoning"""
    result_id: str
    query: str
    reasoning_type: str
    
    # Analysis
    conclusion: str
    confidence: float
    evidence: List[str]
    recommendations: List[str]
    
    # Metadata
    model_used: str
    reasoning_time_ms: int
    timestamp: str


@dataclass
class ThreatAnalysis:
    """Threat analysis result"""
    analysis_id: str
    threat_type: str
    severity: str
    
    # Analysis
    description: str
    indicators: List[str]
    mitre_techniques: List[str]
    
    # Risk
    risk_score: int
    exploitability: str
    impact: str
    
    # Response
    recommended_actions: List[str]
    playbook_id: Optional[str]
    
    # Reasoning
    reasoning_chain: List[str]
    confidence: float


class LocalAIReasoningEngine:
    """
    Local AI reasoning engine for security analysis.
    
    Features:
    - Rule-based threat classification
    - Pattern matching for MITRE ATT&CK techniques
    - Risk scoring with explainable reasoning
    - Incident triage and prioritization
    - Response recommendation
    
    Note: This is a lightweight rule-based engine.
    For full LLM capabilities, integrate with local models like:
    - Ollama (llama2, mistral, codellama)
    - llama.cpp
    - GPT4All
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Analysis history
        self.reasoning_history: List[ReasoningResult] = []
        self.threat_analyses: Dict[str, ThreatAnalysis] = {}
        
        # Load knowledge bases
        self._load_mitre_knowledge()
        self._load_threat_patterns()
        self._load_response_playbooks()
        
        # Model configuration
        self.model_name = "seraph-reasoning-v1"
        self.use_local_llm = os.environ.get('LOCAL_LLM_ENABLED', 'false').lower() == 'true'
        self.ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        # Ollama client wrapper (lazy import to avoid hard dependency at import time)
        try:
            from backend.ai.ollama_client import OllamaClient
            self.ollama_client = OllamaClient(self.ollama_url, os.environ.get('OLLAMA_MODEL', 'mistral'))
        except Exception:
            self.ollama_client = None
        
        logger.info(f"Local AI Reasoning Engine initialized (LLM: {self.use_local_llm})")
    
    def _load_mitre_knowledge(self):
        """Load MITRE ATT&CK knowledge base"""
        self.mitre_techniques = {
            # Initial Access
            "T1566": {"name": "Phishing", "tactic": "initial-access", "severity": "high"},
            "T1190": {"name": "Exploit Public-Facing Application", "tactic": "initial-access", "severity": "critical"},
            "T1133": {"name": "External Remote Services", "tactic": "initial-access", "severity": "high"},
            
            # Execution
            "T1059": {"name": "Command and Scripting Interpreter", "tactic": "execution", "severity": "high"},
            "T1059.001": {"name": "PowerShell", "tactic": "execution", "severity": "high"},
            "T1059.003": {"name": "Windows Command Shell", "tactic": "execution", "severity": "medium"},
            "T1204": {"name": "User Execution", "tactic": "execution", "severity": "medium"},
            
            # Persistence
            "T1547": {"name": "Boot or Logon Autostart Execution", "tactic": "persistence", "severity": "high"},
            "T1053": {"name": "Scheduled Task/Job", "tactic": "persistence", "severity": "medium"},
            "T1136": {"name": "Create Account", "tactic": "persistence", "severity": "high"},
            
            # Privilege Escalation
            "T1548": {"name": "Abuse Elevation Control Mechanism", "tactic": "privilege-escalation", "severity": "high"},
            "T1068": {"name": "Exploitation for Privilege Escalation", "tactic": "privilege-escalation", "severity": "critical"},
            
            # Defense Evasion
            "T1070": {"name": "Indicator Removal", "tactic": "defense-evasion", "severity": "high"},
            "T1562": {"name": "Impair Defenses", "tactic": "defense-evasion", "severity": "critical"},
            "T1027": {"name": "Obfuscated Files or Information", "tactic": "defense-evasion", "severity": "medium"},
            
            # Credential Access
            "T1003": {"name": "OS Credential Dumping", "tactic": "credential-access", "severity": "critical"},
            "T1003.001": {"name": "LSASS Memory", "tactic": "credential-access", "severity": "critical"},
            "T1110": {"name": "Brute Force", "tactic": "credential-access", "severity": "high"},
            "T1555": {"name": "Credentials from Password Stores", "tactic": "credential-access", "severity": "high"},
            
            # Discovery
            "T1087": {"name": "Account Discovery", "tactic": "discovery", "severity": "low"},
            "T1082": {"name": "System Information Discovery", "tactic": "discovery", "severity": "low"},
            "T1046": {"name": "Network Service Discovery", "tactic": "discovery", "severity": "medium"},
            
            # Lateral Movement
            "T1021": {"name": "Remote Services", "tactic": "lateral-movement", "severity": "high"},
            "T1021.001": {"name": "Remote Desktop Protocol", "tactic": "lateral-movement", "severity": "high"},
            "T1021.002": {"name": "SMB/Windows Admin Shares", "tactic": "lateral-movement", "severity": "high"},
            "T1021.006": {"name": "Windows Remote Management", "tactic": "lateral-movement", "severity": "high"},
            
            # Collection
            "T1560": {"name": "Archive Collected Data", "tactic": "collection", "severity": "medium"},
            "T1005": {"name": "Data from Local System", "tactic": "collection", "severity": "medium"},
            
            # Command and Control
            "T1071": {"name": "Application Layer Protocol", "tactic": "command-and-control", "severity": "high"},
            "T1571": {"name": "Non-Standard Port", "tactic": "command-and-control", "severity": "medium"},
            "T1573": {"name": "Encrypted Channel", "tactic": "command-and-control", "severity": "medium"},
            "T1105": {"name": "Ingress Tool Transfer", "tactic": "command-and-control", "severity": "high"},
            
            # Exfiltration
            "T1041": {"name": "Exfiltration Over C2 Channel", "tactic": "exfiltration", "severity": "critical"},
            "T1567": {"name": "Exfiltration Over Web Service", "tactic": "exfiltration", "severity": "critical"},
            
            # Impact
            "T1486": {"name": "Data Encrypted for Impact", "tactic": "impact", "severity": "critical"},
            "T1489": {"name": "Service Stop", "tactic": "impact", "severity": "high"},
            "T1490": {"name": "Inhibit System Recovery", "tactic": "impact", "severity": "critical"},
        }
    
    def _load_threat_patterns(self):
        """Load threat detection patterns"""
        self.threat_patterns = {
            # Credential theft
            "credential_theft": {
                "patterns": ["mimikatz", "lsass", "sekurlsa", "lazagne", "procdump", "comsvcs.dll"],
                "techniques": ["T1003", "T1003.001"],
                "severity": "critical"
            },
            
            # Ransomware
            "ransomware": {
                "patterns": ["encrypt", "ransom", ".locked", ".crypt", "bitcoin", "decrypt"],
                "techniques": ["T1486", "T1490"],
                "severity": "critical"
            },
            
            # Lateral movement
            "lateral_movement": {
                "patterns": ["psexec", "wmiexec", "smbexec", "winrm", "enter-pssession"],
                "techniques": ["T1021", "T1021.002", "T1021.006"],
                "severity": "high"
            },
            
            # Command and control
            "c2_activity": {
                "patterns": ["beacon", "meterpreter", "cobalt", "empire", "callback"],
                "techniques": ["T1071", "T1573"],
                "severity": "critical"
            },
            
            # Data exfiltration
            "exfiltration": {
                "patterns": ["rclone", "megasync", "upload", "exfil", "transfer"],
                "techniques": ["T1041", "T1567"],
                "severity": "critical"
            },
            
            # Privilege escalation
            "privilege_escalation": {
                "patterns": ["getsystem", "elevate", "runas", "sudo", "uac bypass"],
                "techniques": ["T1548", "T1068"],
                "severity": "high"
            },
            
            # Defense evasion
            "defense_evasion": {
                "patterns": ["disable av", "stop defender", "clear logs", "uninstall"],
                "techniques": ["T1562", "T1070"],
                "severity": "high"
            },
            
            # Persistence
            "persistence": {
                "patterns": ["startup", "scheduled task", "registry run", "cron", "systemd"],
                "techniques": ["T1547", "T1053"],
                "severity": "medium"
            }
        }
    
    def _load_response_playbooks(self):
        """Load response playbook mappings"""
        self.playbook_mappings = {
            "credential_theft": "playbook-credential-theft-response",
            "ransomware": "playbook-ransomware-containment",
            "lateral_movement": "playbook-lateral-movement-block",
            "c2_activity": "playbook-c2-isolation",
            "exfiltration": "playbook-data-breach-response",
            "privilege_escalation": "playbook-privilege-escalation",
            "defense_evasion": "playbook-defense-evasion",
            "persistence": "playbook-persistence-removal"
        }

    # =========================================================================
    # WORLD-SNAPSHOT / REASONING CONTEXT
    # =========================================================================


@dataclass
class ReasoningContext:
    """Canonical reasoning input: a snapshot of world state and recent evidence."""
    entities: List[Dict[str, Any]]
    relationships: Dict[str, Any]
    evidence_set: List[Dict[str, Any]]
    trust_state: Dict[str, Any]
    timeline_window: List[Dict[str, Any]]
    window_seconds: int = 3600

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "evidence_set": self.evidence_set,
            "trust_state": self.trust_state,
            "timeline_window": self.timeline_window,
            "window_seconds": self.window_seconds,
        }

    # Short helper to compute uncertainty zones and simple predictions
    def _compute_uncertainty_zones(self) -> Dict[str, float]:
        zones = {}
        for e in (self.entities or []):
            attrs = e.get("attributes", {})
            # low visibility if no recent timestamp, few telemetry points, or missing sensors
            last_seen = attrs.get("last_seen")
            telemetry_count = len(attrs.get("telemetry", [])) if attrs.get("telemetry") else 0
            score = 0.0
            if not last_seen:
                score += 0.6
            if telemetry_count < 3:
                score += 0.3
            if attrs.get("agent_online") is False:
                score += 0.4
            zones[e.get("id")] = min(1.0, max(0.0, score))
        return zones

    
    # =========================================================================
    # THREAT ANALYSIS
    # =========================================================================
    
    def analyze_threat(self, threat_data: Dict[str, Any]) -> ThreatAnalysis:
        """
        Analyze a threat with reasoning.
        
        Args:
            threat_data: Dict containing threat information
                - title: Threat title
                - description: Threat description
                - source: Where it came from
                - indicators: List of IOCs
                - process_name: Process involved (optional)
                - command_line: Command executed (optional)
        
        Returns:
            ThreatAnalysis with reasoning chain
        """
        import time
        start_time = time.time()
        
        analysis_id = f"analysis-{uuid.uuid4().hex[:8]}"
        
        # Extract information (handle None values)
        title = (threat_data.get("title") or "").lower()
        description = (threat_data.get("description") or "").lower()
        command_line = (threat_data.get("command_line") or "").lower()
        process_name = (threat_data.get("process_name") or "").lower()
        indicators = threat_data.get("indicators") or []
        
        # Combine all text for analysis
        all_text = f"{title} {description} {command_line} {process_name}"

        # Lightweight deterministic threat matching that works offline.
        matched_patterns: List[str] = []
        threat_hits: Dict[str, int] = {}
        for candidate_type, patterns in self.threat_patterns.items():
            hits = 0
            for pattern in patterns:
                if pattern in all_text:
                    matched_patterns.append(pattern)
                    hits += 1
            if hits:
                threat_hits[candidate_type] = hits

        for indicator in indicators:
            value = str(indicator or "").lower()
            if not value:
                continue
            for candidate_type, patterns in self.threat_patterns.items():
                if any(pattern in value for pattern in patterns):
                    threat_hits[candidate_type] = threat_hits.get(candidate_type, 0) + 1
                    matched_patterns.append(value[:80])

        if threat_hits:
            threat_type = max(threat_hits.items(), key=lambda item: item[1])[0]
        else:
            threat_type = "unknown"

        severity = str(threat_data.get("severity") or "").strip().lower()
        if severity not in {"critical", "high", "medium", "low"}:
            if len(matched_patterns) >= 5:
                severity = "critical"
            elif len(matched_patterns) >= 3:
                severity = "high"
            elif len(matched_patterns) >= 1:
                severity = "medium"
            else:
                severity = "low"

        mitre_techniques: List[str] = []
        if any(k in all_text for k in ["mimikatz", "lsass", "credential", "sekurlsa"]):
            mitre_techniques.append("T1003")
        if any(k in all_text for k in ["powershell", "cmd.exe", "bash -c", "wscript", "cscript"]):
            mitre_techniques.append("T1059")
        if any(k in all_text for k in ["rundll32", "regsvr32", "mshta", "wmic"]):
            mitre_techniques.append("T1218")
        if any(k in all_text for k in ["http://", "https://", "dns", "beacon", "c2"]):
            mitre_techniques.append("T1071")
        mitre_techniques = list(dict.fromkeys(mitre_techniques))
        mitre_details = [self.mitre_techniques.get(tid, {}).get("name", tid) for tid in mitre_techniques]
        if not mitre_details:
            mitre_details = ["none_observed"]

        risk_score = self._calculate_risk_score(threat_type, severity, [str(i) for i in indicators])
        exploitability = min(1.0, 0.2 + 0.15 * len(matched_patterns))
        impact = min(1.0, 0.25 + (risk_score / 100.0) * 0.75)
        
        # Reasoning chain
        reasoning_chain = []
        reasoning_chain.append(f"Analyzing threat: {threat_data.get('title', 'Unknown')}")
        reasoning_chain.append(f"MITRE ATT&CK techniques: {', '.join(mitre_details)}")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(threat_type, severity)
        reasoning_chain.append(f"Generated {len(recommendations)} recommendations")
        
        # Get playbook
        playbook_id = self.playbook_mappings.get(threat_type)
        if playbook_id:
            reasoning_chain.append(f"Recommended playbook: {playbook_id}")
        
        # Calculate confidence
        confidence = min(0.9, 0.3 + (len(matched_patterns) * 0.15))
        
        analysis = ThreatAnalysis(
            analysis_id=analysis_id,
            threat_type=threat_type,
            severity=severity,
            description=f"Detected {threat_type.replace('_', ' ')} activity with {len(matched_patterns)} pattern matches",
            indicators=indicators[:10],
            mitre_techniques=mitre_techniques,
            risk_score=risk_score,
            exploitability=exploitability,
            impact=impact,
            recommended_actions=recommendations,
            playbook_id=playbook_id,
            reasoning_chain=reasoning_chain,
            confidence=confidence
        )
        
        self.threat_analyses[analysis_id] = analysis
        
        # Log reasoning result
        elapsed_ms = int((time.time() - start_time) * 1000)
        result = ReasoningResult(
            result_id=f"reason-{uuid.uuid4().hex[:8]}",
            query=threat_data.get("title", "threat analysis"),
            reasoning_type="threat_analysis",
            conclusion=f"{threat_type} ({severity})",
            confidence=confidence,
            evidence=matched_patterns,
            recommendations=recommendations[:3],
            model_used=self.model_name,
            reasoning_time_ms=elapsed_ms,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        self.reasoning_history.append(result)
        
        return analysis

    # =========================================================================
    # SNAPSHOT-BASED ANALYSIS & PREDICTION HOOKS
    # =========================================================================

    def analyze_snapshot(self, context: ReasoningContext) -> Dict[str, Any]:
        """Analyze a full world-state snapshot and produce structured reasoning.

        Returns a dict containing hypotheses, uncertainty_zones, suggested actions,
        campaign candidates and a short explanation for each top hypothesis.
        """
        try:
            # uncertainty zones
            uncertainty = context._compute_uncertainty_zones()

            # aggregate simple signals from evidence
            evidence = context.evidence_set or []
            indicator_counts = defaultdict(int)
            for ev in evidence:
                t = ev.get("type") or ev.get("indicator_type") or "generic"
                indicator_counts[t] += 1

            # naive campaign candidate detection: look for repeated technique indicators
            campaign_candidates = []
            if indicator_counts:
                # find top indicator types
                top = sorted(indicator_counts.items(), key=lambda x: -x[1])[:3]
                camp = {
                    "id": f"camp-{uuid.uuid4().hex[:6]}",
                    "objective": ",".join([t for t, _ in top]),
                    "confidence": min(0.95, 0.2 + sum(c for _, c in top) * 0.05),
                    "entities": [e.get("id") for e in context.entities[:5]]
                }
                campaign_candidates.append(camp)

            # suggested actions: reuse existing playbook mappings heuristics
            suggested = []
            for c in campaign_candidates:
                if "ransomware" in (c.get("objective") or ""):
                    suggested.append({"action": "isolate_hosts", "reason": "ransomware_signals"})
                else:
                    suggested.append({"action": "investigate", "reason": "campaign_candidate"})

            # prediction hooks
            predicted = {
                "next_step": self.predict_next_step(context),
                "lateral_path": self.predict_lateral_path(context),
                "objective": campaign_candidates[0].get("objective") if campaign_candidates else None,
            }

            # explanations: provide short reasoning chains per suggested action
            explanations = {}
            for s in suggested:
                explanations[s["action"]] = {
                    "explanation": f"Action {s['action']} suggested due to campaign signals and aggregated evidence counts ({sum(indicator_counts.values())}).",
                    "components": {"evidence_count": sum(indicator_counts.values()), "uncertainty_mean": (sum(uncertainty.values()) / len(uncertainty)) if uncertainty else 0.0}
                }

            return {
                "hypotheses": campaign_candidates,
                "uncertainty_zones": uncertainty,
                "suggested_actions": suggested,
                "predictions": predicted,
                "explanations": explanations,
                "raw": context.to_dict()
            }
        except Exception:
            return {}

    def predict_next_step(self, context: ReasoningContext) -> Optional[str]:
        """Simple heuristic to predict the most-likely next attacker move."""
        try:
            evidence = context.evidence_set or []
            patterns = [e.get("pattern") or e.get("type") for e in evidence]
            if any("exfil" in (p or "") for p in patterns):
                return "exfiltration_attempt"
            if any("c2" in (p or "") or "beacon" in (p or "") for p in patterns):
                return "establish_c2"
            if any("privilege" in (p or "") for p in patterns):
                return "privilege_escalation"
            return "reconnaissance"
        except Exception:
            return None

    def predict_lateral_path(self, context: ReasoningContext) -> List[str]:
        """Return a short list of entity IDs likely to be involved in next lateral moves."""
        try:
            # naive: return top connected nodes from relationships if present
            rels = context.relationships or {}
            # rels expected as {'nodes': [...], 'edges': [...]}
            edges = rels.get("edges", []) if isinstance(rels, dict) else []
            counts = defaultdict(int)
            for ed in edges:
                counts[ed.get("source")] += 1
                counts[ed.get("target")] += 1
            top = sorted(counts.items(), key=lambda x: -x[1])[:5]
            return [t for t, _ in top]
        except Exception:
            return []

    def explain_candidates(self, candidates: List[str], context: ReasoningContext = None) -> Dict[str, Dict[str, Any]]:
        """Provide short AI explanations for a list of candidate actions.

        This is intentionally lightweight and deterministic so it can run
        in tests and offline environments.
        """
        out = {}
        try:
            for c in (candidates or []):
                # infer entity if candidate contains ':'
                ent = None
                if ":" in c:
                    _, ent = c.split(":", 1)
                base_expl = f"Candidate '{c}' evaluated."
                comps = {"keyword": 0.3, "risk": 0.2, "recency": 0.1, "ai": {"provider": "local_rule_based"}}
                if ent and context is not None:
                    # reward if entity appears in top hotspots
                    ids = [e.get("id") for e in context.entities or []]
                    if ent in ids:
                        comps["risk"] = 0.6
                        base_expl += f" Entity {ent} present in snapshot."
                out[c] = {"explanation": base_expl, "components": comps}
            return out
        except Exception:
            return {}
    
    def _calculate_risk_score(self, threat_type: str, severity: str, 
                              indicators: List[str]) -> int:
        """Calculate risk score (0-100)"""
        base_scores = {
            "credential_theft": 90,
            "ransomware": 95,
            "c2_activity": 85,
            "exfiltration": 90,
            "lateral_movement": 75,
            "privilege_escalation": 70,
            "defense_evasion": 65,
            "persistence": 50,
            "unknown": 40
        }
        
        score = base_scores.get(threat_type, 40)
        
        # Adjust for indicators
        if len(indicators) > 5:
            score += 5
        
        # Adjust for severity
        if severity == "critical":
            score = min(100, score + 10)
        elif severity == "low":
            score = max(0, score - 15)
        
        return score
    
    def _generate_recommendations(self, threat_type: str, severity: str) -> List[str]:
        """Generate response recommendations"""
        recommendations = []
        
        # Common recommendations
        recommendations.append("Collect additional forensic evidence before containment")
        
        if threat_type == "credential_theft":
            recommendations.extend([
                "Immediately isolate affected systems",
                "Reset credentials for compromised accounts",
                "Enable multi-factor authentication",
                "Review authentication logs for lateral movement",
                "Consider forcing password reset for all users"
            ])
        elif threat_type == "ransomware":
            recommendations.extend([
                "IMMEDIATELY isolate affected systems from network",
                "Do NOT pay the ransom",
                "Preserve encrypted files for potential decryption",
                "Check backup integrity and restore from clean backups",
                "Report to law enforcement (FBI, CISA)"
            ])
        elif threat_type == "lateral_movement":
            recommendations.extend([
                "Block identified lateral movement paths",
                "Segment network to contain spread",
                "Review admin credentials on compromised segments",
                "Enable enhanced logging on domain controllers"
            ])
        elif threat_type == "c2_activity":
            recommendations.extend([
                "Block C2 IPs/domains at perimeter firewall",
                "Isolate beaconing hosts",
                "Capture memory dump for malware analysis",
                "Hunt for additional compromised hosts with same patterns"
            ])
        elif threat_type == "exfiltration":
            recommendations.extend([
                "Block outbound traffic to identified destinations",
                "Preserve network logs for forensic analysis",
                "Assess scope of data exposure",
                "Prepare for breach notification if PII involved"
            ])
        else:
            recommendations.extend([
                "Investigate suspicious activity further",
                "Collect additional evidence",
                "Monitor for escalation",
                "Consider containment if risk increases"
            ])
        
        return recommendations
    
    # =========================================================================
    # INCIDENT TRIAGE
    # =========================================================================
    
    def triage_incident(self, incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Triage and prioritize multiple incidents.
        
        Returns incidents sorted by priority with reasoning.
        """
        prioritized = []
        
        for incident in incidents:
            # Analyze each incident
            analysis = self.analyze_threat(incident)
            
            # Calculate priority score
            priority_score = analysis.risk_score
            
            # Adjust for active attack indicators
            if "active" in incident.get("status", "").lower():
                priority_score += 10
            
            # Adjust for business criticality
            if incident.get("affects_critical_system", False):
                priority_score += 15
            
            # Adjust for data sensitivity
            if incident.get("involves_pii", False):
                priority_score += 10
            
            prioritized.append({
                "incident": incident,
                "analysis": asdict(analysis),
                "priority_score": min(100, priority_score),
                "triage_recommendation": self._get_triage_recommendation(priority_score)
            })
        
        # Sort by priority (highest first)
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return prioritized
    
    def _get_triage_recommendation(self, priority_score: int) -> str:
        """Get triage recommendation based on priority score"""
        if priority_score >= 90:
            return "IMMEDIATE - Drop everything and respond"
        elif priority_score >= 70:
            return "HIGH - Respond within 1 hour"
        elif priority_score >= 50:
            return "MEDIUM - Respond within 4 hours"
        elif priority_score >= 30:
            return "LOW - Respond within 24 hours"
        else:
            return "INFORMATIONAL - Monitor and review"
    
    # =========================================================================
    # NATURAL LANGUAGE QUERIES
    # =========================================================================
    
    def query(self, question: str, context: Dict[str, Any] = None) -> ReasoningResult:
        """
        Answer a natural language security question.
        
        Uses rule-based reasoning or local LLM if enabled.
        """
        import time
        start_time = time.time()
        
        question_lower = question.lower()
        
        # Rule-based responses
        conclusion = ""
        evidence = []
        recommendations = []
        confidence = 0.7
        
        if "prioritize" in question_lower or "triage" in question_lower:
            conclusion = "Use the triage_incident method for systematic prioritization based on risk scores"
            recommendations = ["Submit incidents to triage_incident()", "Review priority_score for each"]
        
        elif "mitre" in question_lower or "technique" in question_lower:
            # Extract technique ID if present
            match = re.search(r'T\d{4}(?:\.\d{3})?', question)
            if match:
                tid = match.group()
                if tid in self.mitre_techniques:
                    tech = self.mitre_techniques[tid]
                    conclusion = f"{tid} is '{tech['name']}' - a {tech['tactic']} technique with {tech['severity']} severity"
                    evidence = [f"MITRE ATT&CK: {tid}"]
                else:
                    conclusion = f"Technique {tid} not found in local knowledge base"
            else:
                conclusion = f"Found {len(self.mitre_techniques)} MITRE techniques in knowledge base"
        
        elif "credential" in question_lower or "password" in question_lower:
            conclusion = "Credential theft detected - this is a CRITICAL severity event"
            recommendations = [
                "Isolate affected systems",
                "Reset compromised credentials",
                "Enable MFA",
                "Review for lateral movement"
            ]
            evidence = list(self.threat_patterns["credential_theft"]["patterns"])
        
        elif "ransomware" in question_lower:
            conclusion = "Ransomware is a CRITICAL threat requiring immediate isolation"
            recommendations = [
                "Immediately isolate infected systems",
                "Do NOT pay ransom",
                "Restore from clean backups",
                "Report to authorities"
            ]
        
        else:
            conclusion = "Query processed. For detailed threat analysis, use analyze_threat() method."
            confidence = 0.5
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        result = ReasoningResult(
            result_id=f"query-{uuid.uuid4().hex[:8]}",
            query=question,
            reasoning_type="query",
            conclusion=conclusion,
            confidence=confidence,
            evidence=evidence,
            recommendations=recommendations,
            model_used=self.model_name,
            reasoning_time_ms=elapsed_ms,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        self.reasoning_history.append(result)
        
        return result
    
    # =========================================================================
    # OLLAMA INTEGRATION
    # =========================================================================
    
    def configure_ollama(self, base_url: str = "http://localhost:11434", 
                        model: str = "mistral") -> Dict:
        """Configure Ollama for local AI reasoning"""
        self.ollama_url = base_url
        self.ollama_model = model
        os.environ['OLLAMA_URL'] = base_url
        os.environ['OLLAMA_MODEL'] = model
        
        # Test connection
        try:
            if self.ollama_client is None:
                from backend.ai.ollama_client import OllamaClient
                self.ollama_client = OllamaClient(base_url, model)

            tags = self.ollama_client.get_tags(timeout=5)
            if tags and not tags.get("error"):
                self.use_local_llm = True
                os.environ['LOCAL_LLM_ENABLED'] = 'true'
                models = tags.get("models") or []
                return {
                    "status": "connected",
                    "base_url": base_url,
                    "model": model,
                    "available_models": [m.get("name") for m in models]
                }
        except Exception as e:
            return {
                "status": "connection_failed",
                "error": str(e),
                "note": f"Ollama not reachable at {base_url}. Ensure Ollama is running on your server at {base_url}"
            }
        
        return {"status": "configured", "note": "Using rule-based reasoning until Ollama connected"}
    
    async def ollama_generate(self, prompt: str, model: str = None,
                              system_prompt: str = None) -> Dict:
        """Generate response using Ollama"""
        model = model or getattr(self, 'ollama_model', 'mistral')
        try:
            if self.ollama_client is None:
                from backend.ai.ollama_client import OllamaClient
                self.ollama_client = OllamaClient(getattr(self, 'ollama_url', 'http://localhost:11434'), model)

            return await self.ollama_client.agenerate(prompt, model=model, system=system_prompt, timeout=120)
        except Exception as e:
            return {"error": str(e)}
    
    async def ollama_analyze_threat(self, threat_data: Dict[str, Any]) -> Dict:
        """
        Analyze threat using Ollama LLM for enhanced reasoning.
        Falls back to rule-based analysis if Ollama unavailable.
        """
        if not self.use_local_llm:
            # Use rule-based analysis
            analysis = self.analyze_threat(threat_data)
            return {
                "analysis": analysis,
                "method": "rule_based",
                "note": "Ollama not configured. Using rule-based analysis."
            }
        
        # Build security analysis prompt
        system_prompt = """You are Seraph AI, an expert security analyst. Analyze the following threat data and provide:
1. Threat classification (credential_theft, ransomware, c2_activity, lateral_movement, exfiltration, etc.)
2. Severity assessment (critical, high, medium, low)
3. MITRE ATT&CK technique mapping
4. Risk score (0-100)
5. Recommended response actions
6. Confidence level (0-1)

Respond in JSON format with keys: threat_type, severity, mitre_techniques, risk_score, recommendations, confidence, reasoning_chain"""
        
        prompt = f"""Analyze this security threat:

Title: {threat_data.get('title', 'Unknown')}
Description: {threat_data.get('description', 'N/A')}
Process: {threat_data.get('process_name', 'N/A')}
Command Line: {threat_data.get('command_line', 'N/A')}
Indicators: {', '.join(threat_data.get('indicators', []))}

Provide a comprehensive threat analysis."""
        
        ollama_response = await self.ollama_generate(prompt, system_prompt=system_prompt)
        
        if "error" in ollama_response:
            # Fallback to rule-based
            analysis = self.analyze_threat(threat_data)
            return {
                "analysis": analysis,
                "method": "rule_based_fallback",
                "ollama_error": ollama_response.get("error")
            }
        
        return {
            "analysis": ollama_response.get("response", ""),
            "method": "ollama_llm",
            "model": getattr(self, 'ollama_model', 'mistral'),
            "eval_count": ollama_response.get("eval_count", 0)
        }
    
    def get_ollama_status(self) -> Dict:
        """Get Ollama connection status"""
        try:
            if self.ollama_client is None:
                from backend.ai.ollama_client import OllamaClient
                self.ollama_client = OllamaClient(getattr(self, 'ollama_url', 'http://localhost:11434'), getattr(self, 'ollama_model', 'mistral'))

            tags = self.ollama_client.get_tags(timeout=5)
            if tags and not tags.get("error"):
                models = tags.get("models", [])
                return {
                    "status": "connected",
                    "url": getattr(self, 'ollama_url', 'http://localhost:11434'),
                    "models": [m.get("name") for m in models],
                    "configured_model": getattr(self, 'ollama_model', 'mistral')
                }
        except Exception:
            pass

        return {
            "status": "disconnected",
            "url": getattr(self, 'ollama_url', 'http://localhost:11434'),
            "note": "Ollama not reachable. Install with: curl -fsSL https://ollama.com/install.sh | sh"
        }

    # =========================================================================
    # INTEGRATION WRAPPERS (AATL / AATR / CCE / ML / SOAR)
    # =========================================================================

    def analyze_with_aatl(self, event: Dict[str, Any], db: Any = None) -> Optional[Dict]:
        """
        Best-effort wrapper to run AATL processing on an event.
        If `db` is provided it will be passed to the AATL initializer when needed.
        Returns the AATL assessment dict or None when not available.
        """
        try:
            # Lazy import to avoid import-time coupling
            try:
                from services.aatl import get_aatl_engine, init_aatl_engine
            except Exception:
                from backend.services.aatl import get_aatl_engine, init_aatl_engine

            engine = get_aatl_engine()
            if engine is None and db is not None:
                # initialize engine if not yet created
                _run_awaitable_sync(init_aatl_engine(db))
                engine = get_aatl_engine()

            if engine is None:
                return None

            # process_cli_event is async
            assessment = _run_awaitable_sync(engine.process_cli_event(event))
            if assessment is not None and db is not None and emit_world_event is not None:
                try:
                    _run_awaitable_sync(emit_world_event(db, event_type="cognition_aatl_assessed", entity_refs=[str(event.get("session_id", "")), str(event.get("host_id", ""))], payload={"threat_score": getattr(assessment, "threat_score", None), "threat_level": getattr(assessment, "threat_level", None)}, trigger_triune=False))
                except Exception:
                    pass
            return assessment.to_dict() if assessment is not None else None
        except Exception:
            return None

    def query_aatr(self, behavior_data: Dict[str, Any]) -> List[Dict]:
        """Query the Autonomous AI Threat Registry (AATR) for matching patterns."""
        try:
            try:
                from services.aatr import get_aatr, init_aatr
            except Exception:
                from backend.services.aatr import get_aatr, init_aatr

            reg = get_aatr()
            if reg is None:
                return []
            # prefer match_behavior when available
            if hasattr(reg, "match_behavior"):
                matches = reg.match_behavior(behavior_data)
                if emit_world_event is not None and isinstance(behavior_data, dict):
                    try:
                        db_obj = behavior_data.get("db")
                        if db_obj is not None:
                            _run_awaitable_sync(emit_world_event(db_obj, event_type="cognition_aatr_queried", entity_refs=[], payload={"match_count": len(matches)}, trigger_triune=False))
                    except Exception:
                        pass
                return matches
            return []
        except Exception:
            return []

    def run_cognition(self, host_id: str, session_id: str, db: Any = None, window_s: int = None) -> Optional[Dict]:
        """Run the Cognition/Correlation Engine (CCE) to produce a session summary."""
        try:
            try:
                from services.cognition_engine import CognitionEngine
            except Exception:
                from backend.services.cognition_engine import CognitionEngine

            if db is None:
                return None

            engine = CognitionEngine(db)
            summary = _run_awaitable_sync(engine.analyze_session(host_id, session_id, window_s))
            if db is not None and emit_world_event is not None:
                try:
                    _run_awaitable_sync(emit_world_event(db, event_type="cognition_session_analyzed", entity_refs=[host_id, session_id], payload={"has_summary": summary is not None}, trigger_triune=False))
                except Exception:
                    pass
            return summary
        except Exception:
            return None

    def ml_predict(self, features: Dict[str, Any]) -> Optional[Dict]:
        """Invoke the ML threat predictor (best-effort). Returns prediction dict or None."""
        try:
            try:
                from ml_threat_prediction import ml_predictor
            except Exception:
                # fallback import path
                from backend.ml_threat_prediction import ml_predictor

            # many ml_predictor methods are async; use the network/process prediction helpers
            # choose prediction method heuristically
            if features.get("entity_type") == "network":
                pred = _run_awaitable_sync(ml_predictor.predict_network_threat(features))
            elif features.get("entity_type") == "process":
                pred = _run_awaitable_sync(ml_predictor.predict_process_threat(features))
            elif features.get("entity_type") == "file":
                pred = _run_awaitable_sync(ml_predictor.predict_file_threat(features))
            else:
                pred = _run_awaitable_sync(ml_predictor.predict_user_threat(features))

            return pred
        except Exception:
            return None

    def trigger_soar(self, playbook_id: str, event: Dict[str, Any]) -> Optional[Dict]:
        """Trigger or execute a SOAR playbook (best-effort). Returns execution result or None."""
        try:
            try:
                from soar_engine import soar_engine
            except Exception:
                from backend.soar_engine import soar_engine

            # execute_playbook may be async depending on implementation
            if hasattr(soar_engine, "execute_playbook"):
                exec_result = _run_awaitable_sync(soar_engine.execute_playbook(playbook_id, event))
                return exec_result

            return None
        except Exception:
            return None
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    def get_reasoning_stats(self) -> Dict:
        """Get reasoning engine statistics"""
        ollama_status = self.get_ollama_status()
        
        return {
            "model_name": self.model_name,
            "local_llm_enabled": self.use_local_llm,
            "ollama": ollama_status,
            "mitre_techniques_loaded": len(self.mitre_techniques),
            "threat_patterns_loaded": len(self.threat_patterns),
            "playbooks_mapped": len(self.playbook_mappings),
            "analyses_performed": len(self.threat_analyses),
            "queries_processed": len(self.reasoning_history)
        }


ai_reasoning = LocalAIReasoningEngine()

# Ensure commonly-called methods are bound on the class and the singleton instance.
# Some methods are defined at module level (accidentally or intentionally). To be
# robust we bind module-level callables onto the class when missing, then bind
# the resulting class attributes onto the singleton instance.
_expected_methods = [
    # Core reasoning APIs expected by routers/services
    "analyze_threat",
    "analyze_snapshot",
    "predict_next_step",
    "predict_lateral_path",
    "explain_candidates",
    "triage_incident",
    "query",
    # Internal helpers used by core reasoning APIs
    "_calculate_risk_score",
    "_generate_recommendations",
    "_get_triage_recommendation",
    # LLM / integration wrappers
    "get_reasoning_stats",
    "configure_ollama",
    "get_ollama_status",
    "ollama_generate",
    "ollama_analyze_threat",
    "analyze_with_aatl",
    "query_aatr",
    "run_cognition",
    "ml_predict",
    "trigger_soar",
]
import sys as _sys
_mod = _sys.modules.get(__name__)
for _m in _expected_methods:
    # If the class is missing the method but a module-level function exists,
    # attach it to the class so it becomes a proper descriptor.
    try:
        if not hasattr(LocalAIReasoningEngine, _m):
            _candidate = None
            # First preference: methods accidentally placed on ReasoningContext.
            if hasattr(ReasoningContext, _m) and callable(getattr(ReasoningContext, _m)):
                _candidate = getattr(ReasoningContext, _m)
            # Fallback: module-level function with same name.
            elif _mod and hasattr(_mod, _m) and callable(getattr(_mod, _m)):
                _candidate = getattr(_mod, _m)
            if _candidate is not None:
                try:
                    setattr(LocalAIReasoningEngine, _m, _candidate)
                except Exception:
                    pass
        # Now bind the attribute from the class onto the singleton instance.
        if not hasattr(ai_reasoning, _m) and hasattr(LocalAIReasoningEngine, _m):
            try:
                setattr(ai_reasoning, _m, getattr(LocalAIReasoningEngine, _m).__get__(ai_reasoning, LocalAIReasoningEngine))
            except Exception:
                pass
    except Exception:
        # best-effort binding; swallow errors to avoid breaking startup
        pass
