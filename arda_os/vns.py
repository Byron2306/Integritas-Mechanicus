"""
Virtual Network Sensor (VNS)
============================
Independent network truth for validation and correlation.
Provides flow logs, DNS telemetry, TLS fingerprints, and east-west visibility.
"""

import os
import json
import hashlib
import logging
import socket
import struct
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, deque
import uuid
import re

logger = logging.getLogger(__name__)


class FlowDirection(Enum):
    """Network flow direction"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    LATERAL = "lateral"  # East-west


class FlowStatus(Enum):
    """Flow status"""
    ACTIVE = "active"
    CLOSED = "closed"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass
class NetworkFlow:
    """Network flow record"""
    flow_id: str
    
    # Endpoints
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    
    # Protocol
    protocol: str           # TCP, UDP, ICMP
    service: str            # HTTP, HTTPS, DNS, SSH, etc.
    
    # Direction
    direction: FlowDirection
    zone_src: str           # Source network zone
    zone_dst: str           # Destination network zone
    
    # Timing
    started_at: str
    ended_at: Optional[str]
    duration_ms: int
    
    # Metrics
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    
    # TLS
    tls_version: Optional[str]
    tls_cipher: Optional[str]
    ja3_hash: Optional[str]         # Client fingerprint
    ja3s_hash: Optional[str]        # Server fingerprint
    sni: Optional[str]              # Server Name Indication
    
    # Status
    status: FlowStatus
    threat_score: int = 0
    threat_indicators: List[str] = field(default_factory=list)


@dataclass
class DNSQuery:
    """DNS query record"""
    query_id: str
    timestamp: str
    
    # Query
    src_ip: str
    query_name: str
    query_type: str         # A, AAAA, CNAME, MX, TXT, etc.
    
    # Response
    response_code: str      # NOERROR, NXDOMAIN, SERVFAIL, etc.
    response_ips: List[str]
    response_ttl: int
    
    # Analysis
    is_suspicious: bool
    threat_indicators: List[str]


@dataclass
class TLSFingerprint:
    """TLS/JA3 fingerprint"""
    fingerprint_id: str
    ja3_hash: str
    ja3_string: str
    
    # Context
    first_seen: str
    last_seen: str
    seen_count: int
    
    # Classification
    known_client: Optional[str]     # "Chrome", "Firefox", "curl", "malware", etc.
    is_suspicious: bool
    threat_score: int


@dataclass
class BeaconDetection:
    """C2 beacon detection"""
    detection_id: str
    timestamp: str
    
    # Source
    src_ip: str
    dst_ip: str
    dst_port: int
    
    # Pattern
    interval_seconds: float
    interval_jitter: float
    packet_size: int
    
    # Confidence
    confidence: float
    algorithm: str          # "frequency", "ml", "signature"
    
    # Status
    is_confirmed: bool


class VirtualNetworkSensor:
    """
    Virtual Network Sensor for independent network visibility.
    
    Features:
    - Flow logs (netflow-style)
    - DNS telemetry
    - TLS fingerprinting (JA3/JA3S)
    - East-west visibility
    - Beacon detection
    - Deception triggers
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
        
        # Storage
        self.flows: deque = deque(maxlen=100000)
        self.dns_queries: deque = deque(maxlen=50000)
        self.tls_fingerprints: Dict[str, TLSFingerprint] = {}
        self.beacon_detections: deque = deque(maxlen=1000)
        self.domain_pulse_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=128))
        self.domain_pulse_state: Dict[str, Dict[str, Any]] = {}
        self.edge_mesh_windows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=64))
        self.edge_mesh_state: Dict[str, Dict[str, Any]] = {}
        
        # Indexes
        self.flows_by_ip: Dict[str, List[str]] = defaultdict(list)
        self.dns_by_domain: Dict[str, List[str]] = defaultdict(list)
        
        # Known signatures
        self.malicious_ja3: set = {
            # Known malware JA3 hashes (examples)
            "e7d705a3286e19ea42f587b344ee6865",  # Emotet
            "51c64c77e60f3980eea90869b68c58a8",  # Trickbot
            "a0e9f5d64349fb13191bc781f81f42e1",  # CobaltStrike
        }
        
        self.suspicious_domains: set = {
            ".onion", ".bit", ".bazar",
            "duckdns.org", "no-ip.org", "hopto.org",
            "ngrok.io", "serveo.net"
        }
        
        # Network zones
        self.network_zones = {
            "10.0.0.0/8": "internal",
            "172.16.0.0/12": "internal",
            "192.168.0.0/16": "internal",
            "0.0.0.0/0": "external"
        }
        
        # Deception triggers
        self.canary_ips: set = set()
        self.canary_domains: set = set()
        self.canary_ports: set = set()
        
        logger.info("Virtual Network Sensor initialized")

    def update_domain_pulse(
        self,
        *,
        domain: str,
        timing_features: Dict[str, Any],
        harmonic_state: Optional[Dict[str, Any]] = None,
        timestamp_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        normalized_domain = str(domain or "global")
        jitter_norm = float(timing_features.get("jitter_norm") or 0.0)
        drift_norm = float(timing_features.get("drift_norm") or 0.0)
        interval_mean = float(timing_features.get("mean_interval_ms") or timing_features.get("median_interval_ms") or 0.0)
        discord = float((harmonic_state or {}).get("discord_score") or 0.0)
        sample_size = int(timing_features.get("sample_size") or 0)
        point = {
            "timestamp_ms": int(timestamp_ms or datetime.now(timezone.utc).timestamp() * 1000),
            "mean_interval_ms": interval_mean,
            "jitter_norm": jitter_norm,
            "drift_norm": drift_norm,
            "discord_score": discord,
            "sample_size": sample_size,
        }
        self.domain_pulse_windows[normalized_domain].append(point)
        window = list(self.domain_pulse_windows[normalized_domain])
        n = max(1, len(window))
        recent_mean_cadence = sum(max(0.0, float(item.get("mean_interval_ms") or 0.0)) for item in window) / n
        recent_jitter_band = sum(max(0.0, float(item.get("jitter_norm") or 0.0)) for item in window) / n
        elevated_drift_count = sum(1 for item in window if float(item.get("drift_norm") or 0.0) >= 0.5)
        pulse_instability = min(
            1.0,
            (0.45 * recent_jitter_band) + (0.35 * (elevated_drift_count / n)) + (0.2 * sum(float(item.get("discord_score") or 0.0) for item in window) / n),
        )
        state = {
            "domain": normalized_domain,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "samples": n,
            "recent_mean_cadence_ms": round(recent_mean_cadence, 6),
            "recent_jitter_band": round(recent_jitter_band, 6),
            "pulse_stability_index": round(max(0.0, 1.0 - pulse_instability), 6),
            "elevated_drift_count": int(elevated_drift_count),
            "latest_discord_score": round(discord, 6),
        }
        self.domain_pulse_state[normalized_domain] = state
        return state

    def get_domain_pulse_state(self, domain: Optional[str] = None) -> Dict[str, Any]:
        if domain:
            return self.domain_pulse_state.get(str(domain), {})
        return dict(self.domain_pulse_state)

    def update_edge_mesh_state(
        self,
        *,
        action_id: str,
        edge_type: str,
        participant: str,
        timestamp_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not action_id:
            return {}
        ts_ms = float(timestamp_ms if timestamp_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0)
        key = str(action_id)
        self.edge_mesh_windows[key].append(
            {
                "participant": str(participant),
                "timestamp_ms": ts_ms,
                "edge_type": str(edge_type or "unknown"),
            }
        )
        state = self.assess_local_entrainment(action_id=key)
        self.edge_mesh_state[key] = state
        return state

    def assess_local_entrainment(self, *, action_id: str) -> Dict[str, Any]:
        points = list(self.edge_mesh_windows.get(str(action_id)) or [])
        if not points:
            return {}
        ordered = sorted(points, key=lambda row: float(row.get("timestamp_ms") or 0.0))
        participants = [str(row.get("participant") or "") for row in ordered if row.get("participant")]
        unique = list(dict.fromkeys(participants))
        intervals = []
        for idx in range(1, len(ordered)):
            delta = float(ordered[idx].get("timestamp_ms") or 0.0) - float(ordered[idx - 1].get("timestamp_ms") or 0.0)
            intervals.append(max(0.0, delta))
        mean_interval = (sum(intervals) / len(intervals)) if intervals else 0.0
        jitter = 0.0
        if len(intervals) > 1:
            try:
                import statistics
                jitter = float(statistics.pstdev(intervals))
            except Exception:
                jitter = 0.0
        instability = 0.0
        if mean_interval > 0:
            instability = min(1.0, jitter / mean_interval)
        pulse_coherence = max(0.0, 1.0 - instability)
        return {
            "action_id": str(action_id),
            "edge_type": str(ordered[0].get("edge_type") or "unknown"),
            "samples": len(ordered),
            "participants": unique,
            "mean_interval_ms": round(mean_interval, 6),
            "jitter_ms": round(jitter, 6),
            "pulse_coherence": round(pulse_coherence, 6),
            "mesh_state": "scattered" if pulse_coherence < 0.4 else "strained" if pulse_coherence < 0.7 else "entrained",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _get_zone(self, ip: str) -> str:
        """Determine network zone for IP"""
        try:
            ip_int = struct.unpack('!I', socket.inet_aton(ip))[0]
            
            if ip.startswith('10.'):
                return "internal"
            elif ip.startswith('172.'):
                second = int(ip.split('.')[1])
                if 16 <= second <= 31:
                    return "internal"
            elif ip.startswith('192.168.'):
                return "internal"
            
            return "external"
        except:
            return "unknown"
    
    def _get_direction(self, src_ip: str, dst_ip: str) -> FlowDirection:
        """Determine flow direction"""
        src_zone = self._get_zone(src_ip)
        dst_zone = self._get_zone(dst_ip)
        
        if src_zone == "internal" and dst_zone == "external":
            return FlowDirection.OUTBOUND
        elif src_zone == "external" and dst_zone == "internal":
            return FlowDirection.INBOUND
        else:
            return FlowDirection.LATERAL
    
    def _compute_ja3(self, tls_client_hello: bytes) -> str:
        """Compute JA3 hash from TLS ClientHello (simplified)"""
        # In production, parse actual ClientHello
        return hashlib.md5(tls_client_hello).hexdigest()
    
    def _detect_beacon_pattern(self, flows: List[NetworkFlow]) -> Optional[BeaconDetection]:
        """Detect C2 beacon patterns in flows"""
        if len(flows) < 5:
            return None
        
        # Calculate intervals between flows
        intervals = []
        for i in range(1, len(flows)):
            try:
                t1 = datetime.fromisoformat(flows[i-1].started_at.replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(flows[i].started_at.replace('Z', '+00:00'))
                intervals.append((t2 - t1).total_seconds())
            except:
                pass
        
        if not intervals:
            return None
        
        # Check for regularity
        import statistics
        if len(intervals) >= 3:
            mean_interval = statistics.mean(intervals)
            stdev = statistics.stdev(intervals) if len(intervals) > 1 else 0
            
            # Regular intervals suggest beaconing
            if mean_interval > 0 and stdev / mean_interval < 0.3:  # Low jitter
                confidence = 1 - (stdev / mean_interval) if mean_interval > 0 else 0
                
                if confidence > 0.5:
                    return BeaconDetection(
                        detection_id=f"beacon-{uuid.uuid4().hex[:8]}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        src_ip=flows[0].src_ip,
                        dst_ip=flows[0].dst_ip,
                        dst_port=flows[0].dst_port,
                        interval_seconds=mean_interval,
                        interval_jitter=stdev,
                        packet_size=sum(f.bytes_sent for f in flows) // len(flows),
                        confidence=confidence,
                        algorithm="frequency",
                        is_confirmed=False
                    )
        
        return None
    
    # =========================================================================
    # FLOW LOGGING
    # =========================================================================
    
    def record_flow(self, src_ip: str, src_port: int, dst_ip: str, dst_port: int,
                    protocol: str = "TCP", service: str = None,
                    bytes_sent: int = 0, bytes_recv: int = 0,
                    tls_version: str = None, ja3_hash: str = None,
                    ja3s_hash: str = None, sni: str = None) -> NetworkFlow:
        """Record a network flow"""
        
        flow_id = f"flow-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        direction = self._get_direction(src_ip, dst_ip)
        src_zone = self._get_zone(src_ip)
        dst_zone = self._get_zone(dst_ip)
        
        # Infer service from port if not provided
        if not service:
            service = self._get_service(dst_port)
        
        # Check for threats
        threat_indicators = []
        threat_score = 0
        
        # Check JA3 against known malware
        if ja3_hash and ja3_hash in self.malicious_ja3:
            threat_indicators.append(f"Malicious JA3: {ja3_hash}")
            threat_score += 80
        
        # Check for canary triggers
        if dst_ip in self.canary_ips:
            threat_indicators.append(f"Canary IP accessed: {dst_ip}")
            threat_score += 90
        
        if dst_port in self.canary_ports:
            threat_indicators.append(f"Canary port accessed: {dst_port}")
            threat_score += 70
        
        # Check for suspicious lateral movement
        if direction == FlowDirection.LATERAL:
            if dst_port in [22, 3389, 445, 5985, 5986]:  # SSH, RDP, SMB, WinRM
                threat_indicators.append(f"Lateral movement to port {dst_port}")
                threat_score += 30
        
        flow = NetworkFlow(
            flow_id=flow_id,
            src_ip=src_ip,
            src_port=src_port,
            dst_ip=dst_ip,
            dst_port=dst_port,
            protocol=protocol,
            service=service,
            direction=direction,
            zone_src=src_zone,
            zone_dst=dst_zone,
            started_at=now,
            ended_at=None,
            duration_ms=0,
            bytes_sent=bytes_sent,
            bytes_recv=bytes_recv,
            packets_sent=0,
            packets_recv=0,
            tls_version=tls_version,
            tls_cipher=None,
            ja3_hash=ja3_hash,
            ja3s_hash=ja3s_hash,
            sni=sni,
            status=FlowStatus.SUSPICIOUS if threat_score > 50 else FlowStatus.ACTIVE,
            threat_score=threat_score,
            threat_indicators=threat_indicators
        )
        
        self.flows.append(flow)
        self.flows_by_ip[src_ip].append(flow_id)
        self.flows_by_ip[dst_ip].append(flow_id)
        
        # Check for beacon patterns
        src_flows = [f for f in self.flows if f.src_ip == src_ip and f.dst_ip == dst_ip][-10:]
        beacon = self._detect_beacon_pattern(src_flows)
        if beacon:
            self.beacon_detections.append(beacon)
            logger.warning(f"VNS: Beacon pattern detected {src_ip} -> {dst_ip}")
        
        return flow
    
    def _get_service(self, port: int) -> str:
        """Get service name from port"""
        services = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
            53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
            443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
            1433: "MSSQL", 1521: "Oracle", 3306: "MySQL",
            3389: "RDP", 5432: "PostgreSQL", 5985: "WinRM",
            6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
            27017: "MongoDB"
        }
        return services.get(port, f"port-{port}")
    
    # =========================================================================
    # DNS TELEMETRY
    # =========================================================================
    
    def record_dns_query(self, src_ip: str, query_name: str, query_type: str = "A",
                         response_code: str = "NOERROR",
                         response_ips: List[str] = None,
                         response_ttl: int = 0) -> DNSQuery:
        """Record a DNS query"""
        
        query_id = f"dns-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Check for suspicious domains
        threat_indicators = []
        is_suspicious = False
        
        # Check against suspicious TLDs/domains
        for sus_domain in self.suspicious_domains:
            if query_name.endswith(sus_domain):
                threat_indicators.append(f"Suspicious domain: {sus_domain}")
                is_suspicious = True
        
        # Check for canary domains
        for canary in self.canary_domains:
            if canary in query_name:
                threat_indicators.append(f"Canary domain accessed: {canary}")
                is_suspicious = True
        
        # Check for DGA-like patterns
        if self._looks_like_dga(query_name):
            threat_indicators.append("Possible DGA domain")
            is_suspicious = True
        
        # Check for DNS tunneling (long subdomains)
        if len(query_name) > 50:
            labels = query_name.split('.')
            if any(len(l) > 30 for l in labels):
                threat_indicators.append("Possible DNS tunneling")
                is_suspicious = True
        
        query = DNSQuery(
            query_id=query_id,
            timestamp=now,
            src_ip=src_ip,
            query_name=query_name,
            query_type=query_type,
            response_code=response_code,
            response_ips=response_ips or [],
            response_ttl=response_ttl,
            is_suspicious=is_suspicious,
            threat_indicators=threat_indicators
        )
        
        self.dns_queries.append(query)
        self.dns_by_domain[query_name].append(query_id)
        
        if is_suspicious:
            logger.warning(f"VNS: Suspicious DNS query from {src_ip}: {query_name}")
        
        return query
    
    def _looks_like_dga(self, domain: str) -> bool:
        """Check if domain looks like DGA-generated"""
        # Remove TLD
        parts = domain.split('.')
        if len(parts) < 2:
            return False
        
        name = parts[0]
        
        # Check entropy
        if len(name) < 8:
            return False
        
        # Count consonants vs vowels
        vowels = set('aeiou')
        consonants = sum(1 for c in name.lower() if c.isalpha() and c not in vowels)
        total_alpha = sum(1 for c in name if c.isalpha())
        
        if total_alpha == 0:
            return False
        
        consonant_ratio = consonants / total_alpha
        
        # DGA domains tend to have unusual consonant ratios
        if consonant_ratio > 0.8 or consonant_ratio < 0.3:
            return True
        
        # Check for random-looking strings
        if len(set(name)) > len(name) * 0.7 and len(name) > 10:
            return True
        
        return False
    
    # =========================================================================
    # TLS FINGERPRINTING
    # =========================================================================
    
    def record_tls_fingerprint(self, ja3_hash: str, ja3_string: str = None,
                               known_client: str = None) -> TLSFingerprint:
        """Record a TLS fingerprint"""
        
        now = datetime.now(timezone.utc).isoformat()
        
        if ja3_hash in self.tls_fingerprints:
            # Update existing
            fp = self.tls_fingerprints[ja3_hash]
            fp.last_seen = now
            fp.seen_count += 1
            return fp
        
        # Check if malicious
        is_suspicious = ja3_hash in self.malicious_ja3
        threat_score = 90 if is_suspicious else 0
        
        fp = TLSFingerprint(
            fingerprint_id=f"ja3-{ja3_hash[:8]}",
            ja3_hash=ja3_hash,
            ja3_string=ja3_string or "",
            first_seen=now,
            last_seen=now,
            seen_count=1,
            known_client=known_client,
            is_suspicious=is_suspicious,
            threat_score=threat_score
        )
        
        self.tls_fingerprints[ja3_hash] = fp
        
        if is_suspicious:
            logger.warning(f"VNS: Malicious JA3 fingerprint detected: {ja3_hash}")
        
        return fp
    
    # =========================================================================
    # DECEPTION
    # =========================================================================
    
    def add_canary_ip(self, ip: str):
        """Add a canary IP"""
        self.canary_ips.add(ip)
        logger.info(f"VNS: Added canary IP {ip}")
    
    def add_canary_domain(self, domain: str):
        """Add a canary domain"""
        self.canary_domains.add(domain)
        logger.info(f"VNS: Added canary domain {domain}")
    
    def add_canary_port(self, port: int):
        """Add a canary port"""
        self.canary_ports.add(port)
        logger.info(f"VNS: Added canary port {port}")
    
    # =========================================================================
    # QUERIES
    # =========================================================================
    
    def get_flows(self, src_ip: str = None, dst_ip: str = None,
                  direction: FlowDirection = None,
                  suspicious_only: bool = False,
                  limit: int = 100) -> List[Dict]:
        """Query flows with filters"""
        results = []
        
        for flow in reversed(self.flows):
            if src_ip and flow.src_ip != src_ip:
                continue
            if dst_ip and flow.dst_ip != dst_ip:
                continue
            if direction and flow.direction != direction:
                continue
            if suspicious_only and flow.status != FlowStatus.SUSPICIOUS:
                continue
            
            results.append(asdict(flow))
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_dns_queries(self, src_ip: str = None, domain: str = None,
                        suspicious_only: bool = False,
                        limit: int = 100) -> List[Dict]:
        """Query DNS records with filters"""
        results = []
        
        for query in reversed(self.dns_queries):
            if src_ip and query.src_ip != src_ip:
                continue
            if domain and domain not in query.query_name:
                continue
            if suspicious_only and not query.is_suspicious:
                continue
            
            results.append(asdict(query))
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_beacon_detections(self, confirmed_only: bool = False,
                              limit: int = 50) -> List[Dict]:
        """Get beacon detections"""
        results = []
        
        for detection in reversed(self.beacon_detections):
            if confirmed_only and not detection.is_confirmed:
                continue
            
            results.append(asdict(detection))
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_suspicious_fingerprints(self) -> List[Dict]:
        """Get suspicious TLS fingerprints"""
        return [
            asdict(fp) for fp in self.tls_fingerprints.values()
            if fp.is_suspicious
        ]
    
    def get_vns_stats(self) -> Dict:
        """Get VNS statistics"""
        suspicious_flows = sum(1 for f in self.flows if f.status == FlowStatus.SUSPICIOUS)
        suspicious_dns = sum(1 for q in self.dns_queries if q.is_suspicious)
        
        return {
            "total_flows": len(self.flows),
            "suspicious_flows": suspicious_flows,
            "total_dns_queries": len(self.dns_queries),
            "suspicious_dns": suspicious_dns,
            "tls_fingerprints": len(self.tls_fingerprints),
            "malicious_fingerprints": sum(1 for fp in self.tls_fingerprints.values() if fp.is_suspicious),
            "beacon_detections": len(self.beacon_detections),
            "canary_ips": len(self.canary_ips),
            "canary_domains": len(self.canary_domains),
            "canary_ports": len(self.canary_ports),
            "domain_pulse_domains": len(self.domain_pulse_state),
            "edge_mesh_edges": len(self.edge_mesh_state),
        }
    
    def validate_endpoint_telemetry(self, endpoint_ip: str,
                                    endpoint_flows: List[Dict]) -> Dict:
        """
        Validate endpoint telemetry against network truth.
        Returns discrepancies.
        """
        discrepancies = []
        
        # Get VNS flows for this endpoint
        vns_flows = self.get_flows(src_ip=endpoint_ip, limit=1000)
        vns_flow_set = set((f['dst_ip'], f['dst_port']) for f in vns_flows)
        
        # Check endpoint flows against VNS
        for ep_flow in endpoint_flows:
            key = (ep_flow.get('dst_ip'), ep_flow.get('dst_port'))
            if key[0] and key not in vns_flow_set:
                discrepancies.append({
                    "type": "endpoint_only",
                    "description": f"Flow to {key[0]}:{key[1]} seen by endpoint but not VNS",
                    "severity": "medium"
                })
        
        # Check VNS flows not seen by endpoint
        ep_flow_set = set((f.get('dst_ip'), f.get('dst_port')) for f in endpoint_flows)
        for vns_flow in vns_flows:
            key = (vns_flow['dst_ip'], vns_flow['dst_port'])
            if key not in ep_flow_set:
                discrepancies.append({
                    "type": "vns_only",
                    "description": f"Flow to {key[0]}:{key[1]} seen by VNS but not endpoint",
                    "severity": "high"  # Possible endpoint compromise
                })
        
        return {
            "endpoint_ip": endpoint_ip,
            "endpoint_flows_count": len(endpoint_flows),
            "vns_flows_count": len(vns_flows),
            "discrepancies": discrepancies,
            "discrepancy_count": len(discrepancies)
        }


# Global singleton
vns = VirtualNetworkSensor()
