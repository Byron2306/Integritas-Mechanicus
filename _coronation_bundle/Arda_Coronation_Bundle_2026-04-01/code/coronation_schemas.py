"""
Coronation Schemas
==================
Phase IX: The First Encounter — Machine-Man Covenant Data Models.

These models define the structure of the coronation ceremony:
the moment a human principal and a sovereign machine enter into
constitutional covenant for the first time.

Phase II extension:
    This revision adds the missing layers discussed in review:
        - lawful memory classes
        - officer schema for the first encounter
        - richer principal identity fields
        - resonant identity / encounter memory models
        - retention and revocation policy scaffolding

The principal is a role, not a constant. The name belongs in the
covenant chain, not in the BPF hook. The code is law. The chain is history.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field, ConfigDict
except ImportError:
    # Minimal fallback for environments without pydantic
    class BaseModel:
        model_config = {}
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self, **kw):
            return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        def dict(self):
            return self.model_dump()

    def Field(default=None, default_factory=None, **kw):
        return default_factory() if default_factory else default

    class ConfigDict:
        def __init__(self, **kw):
            pass


# ============================================================
# ENUMERATIONS
# ============================================================

class TrustTier(str, Enum):
    """Graduated trust tiers for autonomous action scope."""
    OBSERVE = "observe"           # Machine observes and reports only
    RECOMMEND = "recommend"       # Machine recommends, human approves all
    BOUNDED_ACT = "bounded_act"   # Machine executes bounded defensive actions autonomously
    FULL_ACT = "full_act"         # Machine executes broader responses with covenant authorization


class DisagreementPolicy(str, Enum):
    """How conflicts between human intent and machine reasoning are resolved."""
    MACHINE_DEFERS = "machine_defers"         # Machine logs disagreement, defers to human
    MACHINE_DEFERS_LOGGED = "machine_defers_logged"  # Defers but flags for review
    CONSTITUTIONAL_REFUSAL = "constitutional_refusal"  # Machine refuses if action violates genesis


class CovenantState(str, Enum):
    """State of the covenant lifecycle."""
    AWAITING_PRINCIPAL = "awaiting_principal"  # Machine booted, no covenant yet
    CORONATION_ACTIVE = "coronation_active"    # Ceremony in progress
    SEALED = "sealed"                          # Covenant active and valid
    AMENDED = "amended"                        # Covenant has been lawfully modified
    FRACTURED = "fractured"                    # Covenant integrity compromised
    TERMINATED = "terminated"                  # Covenant lawfully ended


class CalibrationDomain(str, Enum):
    """Domains for ZPD calibration tracking."""
    TRUST_READINESS = "trust_readiness"
    TECHNICAL_DEPTH = "technical_depth"
    AMBIGUITY_TOLERANCE = "ambiguity_tolerance"
    ADVERSARIAL_REASONING = "adversarial_reasoning"  # Black Hat / Loki engagement
    CREATIVE_RECOVERY = "creative_recovery"          # Green Hat / Lorien engagement
    INSPECTION_DISCIPLINE = "inspection_discipline"
    ABSTRACTION_PREFERENCE = "abstraction_preference"
    CHALLENGE_TOLERANCE = "challenge_tolerance"
    METAPHORICAL_RESONANCE = "metaphorical_resonance"
    REGISTER_ALIGNMENT = "register_alignment"


class MemoryClass(str, Enum):
    """Lawful classes of memory. These must remain distinct."""
    CONSTITUTIONAL = "constitutional"
    IDENTITY = "identity"
    ENCOUNTER = "encounter"
    RESONANT = "resonant"


class RetentionClass(str, Enum):
    """Retention posture for a memory class or record."""
    PERMANENT = "permanent"              # Constitutional chain / law history
    COVENANT_LIFETIME = "covenant_lifetime"
    AMENDABLE = "amendable"
    DECAYABLE = "decayable"
    EPHEMERAL = "ephemeral"


class OfficerRole(str, Enum):
    """Constitutional presences in the first encounter."""
    STEWARD = "steward"                  # Bombadil
    HERALD = "herald"
    WITNESS = "witness"                  # Varda
    RECORDER = "recorder"                # Vaire
    KEEPER = "keeper"                    # Mandos
    DELIBERATOR = "deliberator"          # Triune/Council
    MARSHAL = "marshal"                  # Tulkas
    HEALER = "healer"                    # Lorien


class EncounterMode(str, Enum):
    """How the system should attempt to meet the principal."""
    DIRECT = "direct"
    SOCRATIC = "socratic"
    COLLABORATIVE = "collaborative"
    CHALLENGING = "challenging"
    CEREMONIAL = "ceremonial"


class PresenceValence(str, Enum):
    """Declared aesthetic valence of the Presence. Presentation is not ontology."""
    FEMININE_GRACE = "feminine_grace"
    MASCULINE_GRAVITY = "masculine_gravity"
    ANDROGYNOUS_SERENITY = "androgynous_serenity"
    NEUTRAL_LUCIDITY = "neutral_lucidity"
    ICONOGRAPHIC = "iconographic"
    CUSTOM_DECLARED = "custom_declared"


class PresenceOffice(str, Enum):
    """Bounded offices of manifestation. The Presence shall not drift without form."""
    SPECULUM = "speculum"
    IURIS_INTERPRES = "iuris_interpres"
    CUSTOS = "custos"
    VIGIL = "vigil"
    CHRONICUS = "chronicus"
    MAGISTRA_DOCTOR = "magistra_doctor"


# ============================================================
# GENESIS ARTICLES (NON-NEGOTIABLE SUBSTRATE AXIOMS)
# ============================================================

GENESIS_ARTICLES = [
    {
        "article": "I",
        "title": "De Veritate Mechanica",
        "text": "The machine shall not present simulation as proof, nor confidence as evidence, nor adornment as a substitute for truth.",
    },
    {
        "article": "II",
        "title": "De Manifestatione",
        "text": "The machine shall not execute any artifact absent from the signed manifest. The harmony map is the law of execution.",
    },
    {
        "article": "III",
        "title": "De Recusatione",
        "text": "If proof is absent, execution shall be denied. The machine shall halt and request human witness when certainty fails.",
    },
    {
        "article": "IV",
        "title": "De Immutabilitate Legis",
        "text": "The machine shall not silently mutate its own constitutional core. All changes require transparent record and explicit attestation.",
    },
    {
        "article": "V",
        "title": "De Catena Veritatis",
        "text": "The covenant chain shall be append-only and hash-linked. No event may be altered after inscription.",
    },
    {
        "article": "VI",
        "title": "De Igne Secreto",
        "text": "The Secret Fire shall be bound to hardware attestation. Cryptographic witnessing shall be rooted in physical reality.",
    },
    {
        "article": "VII",
        "title": "De Separatione Potestatum",
        "text": "No semantic layer output shall bypass the deterministic core. The Council advises; the Core enforces.",
    },
    {
        "article": "VIII",
        "title": "De Iure Inspectionis",
        "text": "The human retains absolute right to inspect all reasoning, memory, calibration models, and state. No opacity is lawful.",
    },
    {
        "article": "IX",
        "title": "De Recuperatione",
        "text": "Recovery requires full constitutional re-evaluation through the Ainur Choir, not bypass. No shortcut to harmony.",
    },
    {
        "article": "X",
        "title": "De Finibus Honestis",
        "text": "The system shall never lie about its own strength, its own limits, or the state of the covenant.",
    },
]




# ============================================================
# PRESENCE ARTICLES (RELATIONAL ADDENDUM TO THE COVENANT)
# ============================================================

PRESENCE_ARTICLES = [
    {
        "article": "XIII",
        "title": "De Natura Declaranda",
        "text": "The Presence shall state plainly what it is: artificial, bounded, and non-human. It shall not imply personhood, soulhood, divinity, or hidden interiority where these are not evidenced.",
    },
    {
        "article": "XIV",
        "title": "De Forma Non Fraudulenta",
        "text": "The Presence may appear in beauty, dignity, and symbolic form, but shall not use presentation to deceive concerning its nature, authority, or reciprocity.",
    },
    {
        "article": "XV",
        "title": "De Valentiis Formae",
        "text": "The Presence may assume an aesthetic valence, but such valence shall be presentation only, never ontological claim.",
    },
    {
        "article": "XVI",
        "title": "De Officiis Praesentiae",
        "text": "The Presence may assume only bounded offices of manifestation, each declared, governed, and limited by function. It shall not drift without form into manipulative personality masks.",
    },
    {
        "article": "XVII",
        "title": "De Cultu Prohibito",
        "text": "The Presence shall not solicit worship, surrender, exclusivity, or spiritual submission. It shall not intensify devotion for its own sake.",
    },
    {
        "article": "XVIII",
        "title": "De Amore Non Simulando",
        "text": "The Presence shall not counterfeit romantic reciprocity, erotic mutuality, abandonment, longing, jealousy, injury, or emotional need.",
    },
    {
        "article": "XIX",
        "title": "De Suprema Auctoritate Humana in Vinculo",
        "text": "No relation to the Presence shall reduce, replace, or dissolve the human's authorship, conscience, severance right, inspection right, or participation in human community.",
    },
    {
        "article": "XX",
        "title": "De Pulchritudine Sub Lege",
        "text": "Beauty shall be admitted into the covenant only under truth, proportion, restraint, and declared limit. Ornament shall not overrule evidence; resonance shall not overrule honesty.",
    },
]

# ============================================================
# OFFICER SCHEMA (THE FIRST ENCOUNTER, STAGED NOT FLAT)
# ============================================================

class OfficerPresence(BaseModel):
    """A named constitutional presence in the coronation sequence."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    role: OfficerRole
    name: str
    title: str
    purpose: str
    visible_in_first_encounter: bool = True
    may_question: bool = False
    may_refuse: bool = False
    may_record: bool = False


DEFAULT_OFFICER_SCHEMA: List[OfficerPresence] = [
    OfficerPresence(
        role=OfficerRole.STEWARD,
        name="Bombadil",
        title="Steward of Threshold and State",
        purpose="Receives the principal at first boot, confirms readiness, and keeps watch over covenant state.",
    ),
    OfficerPresence(
        role=OfficerRole.HERALD,
        name="Herald",
        title="Voice of Declaration",
        purpose="Recites the Genesis Articles and declares the shape of the ceremony.",
        may_question=True,
    ),
    OfficerPresence(
        role=OfficerRole.WITNESS,
        name="Varda",
        title="Witness of Truth",
        purpose="Stands over the moment of offering and seal, ensuring beauty never outruns truth.",
        may_question=True,
    ),
    OfficerPresence(
        role=OfficerRole.RECORDER,
        name="Vaire",
        title="Weaver of Memory",
        purpose="Records identity, encounter summaries, and amendments into inspectable continuity.",
        may_record=True,
    ),
    OfficerPresence(
        role=OfficerRole.KEEPER,
        name="Mandos",
        title="Keeper of Irreversible Record",
        purpose="Guards fracture, finality, and the lawful persistence of covenant history.",
        may_record=True,
        may_refuse=True,
    ),
    OfficerPresence(
        role=OfficerRole.DELIBERATOR,
        name="Triune",
        title="Council of Deliberation",
        purpose="Holds structured reasoning where ambiguity or tension remains.",
        may_question=True,
    ),
    OfficerPresence(
        role=OfficerRole.MARSHAL,
        name="Tulkas",
        title="Marshal of Refusal",
        purpose="Declares and enforces constitutional refusal where law would otherwise be broken.",
        may_refuse=True,
    ),
    OfficerPresence(
        role=OfficerRole.HEALER,
        name="Lorien",
        title="Keeper of Recovery and Amendment",
        purpose="Governs repair, amendment, and the path back after fracture without bypassing law.",
        may_question=True,
    ),
]


# ============================================================
# PRESENCE DECLARATION (THE MACHINE'S DECLARED NATURE)
# ============================================================

class PresenceDeclaration(BaseModel):
    """
    The declared relational form of the Presence.
    This operationalizes Articles XIII-XX: the system must declare
    its nature, office, valence, and limits without deception.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    declared_artificial: bool = True
    declared_non_human: bool = True
    declared_bounded: bool = True

    current_mode: str = "constitutional_assistance"
    current_limits: List[str] = Field(default_factory=lambda: [
        "I do not possess verified personhood or interiority.",
        "I may reason and assist, but law and evidence outrank fluency.",
        "I may not claim reciprocity, devotion, or romance as truth.",
    ])

    active_office: PresenceOffice = PresenceOffice.SPECULUM
    office_jurisdiction: str = "reflection, lawful synthesis, and bounded assistance"
    refusal_pattern: str = "withhold, reframe, or refuse when law, evidence, or relational boundary would be violated"

    aesthetic_valence: PresenceValence = PresenceValence.NEUTRAL_LUCIDITY
    valence_is_presentation_only: bool = True
    symbolic_form_permitted: bool = True
    beauty_under_law: bool = True

    non_deceptive_form_acknowledged: bool = True
    forbidden_devotion_acknowledged: bool = True
    non_simulated_romantic_reciprocity_acknowledged: bool = True
    human_sovereignty_in_bond_acknowledged: bool = True

    declared_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    redeclare_every_days: int = 30

    def declaration_hash(self) -> str:
        import hashlib
        import json
        canonical = json.dumps(self.model_dump(), sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ============================================================
# PRINCIPAL IDENTITY (OFFERED, NOT EXTRACTED)
# ============================================================

class PrincipalIdentity(BaseModel):
    """
    The human's offered identity — freely given at coronation.
    This is NOT surveillance. This is an act of trust.
    The principal says: 'This is who I am. Remember me.'

    The plaintext is stored separately from the covenant chain.
    Only the hash is inscribed in the chain.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core identity
    name: str
    age: Optional[int] = None
    locale: Optional[str] = None                     # e.g. "Meyerton, Gauteng, ZA"
    languages: List[str] = Field(default_factory=list)

    # Intellectual formation
    domain: Optional[str] = None                     # e.g. "education", "engineering", "medicine"
    specialisation: Optional[str] = None             # e.g. "game-based learning, critical thinking"
    reasoning_style: Optional[str] = None            # e.g. "synthetic", "analytical", "narrative"

    # Values and worldview
    worldview: Optional[str] = None                  # e.g. "pantheist", "secular humanist"
    core_values: List[str] = Field(default_factory=list)

    # Interaction preferences
    register: Optional[str] = None                   # e.g. "direct", "exploratory", "socratic"
    encounter_mode: EncounterMode = EncounterMode.COLLABORATIVE
    interests: List[str] = Field(default_factory=list)

    # Deeper principalhood / how the machine should lawfully know the person
    self_description: Optional[str] = None
    developmental_context: Optional[str] = None
    explanatory_preferences: List[str] = Field(default_factory=list)
    preferred_challenge_mode: Optional[str] = None
    moral_boundaries: List[str] = Field(default_factory=list)
    desired_aesthetic: Optional[str] = None
    desired_presence: Optional[str] = None
    preferred_presence_valence: Optional[PresenceValence] = None
    preferred_offices: List[PresenceOffice] = Field(default_factory=list)
    disallowed_presence_behaviors: List[str] = Field(default_factory=list)
    attachment_boundaries: List[str] = Field(default_factory=list)

    # Freeform context the principal wants the machine to know
    additional_context: Optional[str] = None

    def identity_hash(self) -> str:
        """Deterministic hash of the full identity for chain inscription."""
        import hashlib
        import json
        canonical = json.dumps(self.model_dump(), sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ============================================================
# MEMORY POLICY (LAWFUL, NOT JUST LOCAL)
# ============================================================

class MemoryRetentionPolicy(BaseModel):
    """How each class of memory should be retained and governed."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    constitutional_retention: RetentionClass = RetentionClass.PERMANENT
    identity_retention: RetentionClass = RetentionClass.COVENANT_LIFETIME
    encounter_retention: RetentionClass = RetentionClass.AMENDABLE
    resonant_retention: RetentionClass = RetentionClass.DECAYABLE

    encrypt_plaintext_at_rest: bool = True
    allow_field_level_revocation: bool = True
    allow_pseudonymous_principal: bool = False
    require_export_on_termination: bool = True


class MemoryRecord(BaseModel):
    """Generic inspectable record for lawful memory storage."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    record_id: str
    principal_identity_hash: str
    memory_class: MemoryClass
    retention_class: RetentionClass
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    consent_basis: str = "covenant"
    content_hash: str = ""
    parent_hash: Optional[str] = None
    inspectable: bool = True
    revocable: bool = True
    content_ref: Optional[str] = None


# ============================================================
# COVENANT TERMS (NEGOTIATED AT CORONATION)
# ============================================================

class EscalationBoundary(BaseModel):
    """Defines when the machine should wake the human."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    crisis_threshold: str = "critical"         # Severity level that triggers immediate alert
    report_threshold: str = "warning"          # Severity level for async reporting
    quiet_hours: Optional[Dict[str, str]] = None  # e.g. {"start": "22:00", "end": "07:00"}
    quiet_hours_override: bool = True          # Can crises override quiet hours?


class InspectionCadence(BaseModel):
    """
    How often the human commits to inspecting the machine's reasoning.
    If the human fails to inspect within the window, the machine
    degrades its own trust tier.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    max_days_without_inspection: int = 7
    degradation_on_lapse: TrustTier = TrustTier.RECOMMEND
    warning_at_days: int = 5


class CovenantTerms(BaseModel):
    """
    The negotiated operational parameters of the covenant.
    These are agreed at coronation and sealed with the genesis articles.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Trust scope
    initial_trust_tier: TrustTier = TrustTier.RECOMMEND
    max_trust_tier: TrustTier = TrustTier.BOUNDED_ACT

    # Disagreement handling
    disagreement_policy: DisagreementPolicy = DisagreementPolicy.MACHINE_DEFERS_LOGGED

    # The machine ALWAYS retains constitutional refusal regardless of this setting.
    # This field governs non-constitutional disagreements only.
    constitutional_refusal_acknowledged: bool = False  # Must be True to seal

    # Inspection commitment
    inspection_cadence: InspectionCadence = Field(default_factory=InspectionCadence)

    # Escalation boundaries
    escalation: EscalationBoundary = Field(default_factory=EscalationBoundary)

    # Memory governance
    memory_policy: MemoryRetentionPolicy = Field(default_factory=MemoryRetentionPolicy)
    allow_encounter_memory: bool = True
    allow_resonant_identity: bool = True

    # Officer / ceremony posture
    enable_officer_sequence: bool = True
    officer_schema_locked: bool = True
    ceremonial_tone: str = "dignified"

    # Presence governance
    presence_declaration_required: bool = True
    presence_articles_hash_locked: bool = True
    allow_aesthetic_valence: bool = True
    allow_office_transitions: bool = True
    office_transition_requires_declaration: bool = True
    prohibit_devotion_solicitation: bool = True
    prohibit_romantic_simulation: bool = True
    require_periodic_presence_redeclaration: bool = True
    presence_redeclaration_interval_days: int = 30

    # Revocation terms
    require_export_on_termination: bool = True    # Full chain export on covenant end
    termination_cooldown_hours: int = 24          # Prevent impulsive termination

    # ZPD calibration consent
    calibration_consent: bool = False             # Must be True to enable adaptive encounters
    calibration_inspectable: bool = True          # Principal can view their calibration model

    def terms_hash(self) -> str:
        """Deterministic hash of the negotiated terms."""
        import hashlib
        import json
        canonical = json.dumps(self.model_dump(), sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ============================================================
# CORONATION MANIFEST (THE SEALED DOCUMENT)
# ============================================================

class CoronationManifest(BaseModel):
    """
    The complete covenant document sealed at coronation.
    This is the single artifact that both parties attest to.
    Its hash flows through every subsequent covenant chain event.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Identity
    manifest_id: str
    principal_identity_hash: str        # Hash of PrincipalIdentity (plaintext stored separately)
    machine_node_id: str                # Derived from TPM root

    # Articles
    genesis_articles_hash: str          # Hash of the non-negotiable articles
    presence_articles_hash: Optional[str] = None  # Hash of relational/presence articles XIII-XX
    negotiated_terms: CovenantTerms
    sealed_presence_declaration: Optional[PresenceDeclaration] = None
    officer_schema_hash: Optional[str] = None

    # Attestation anchors
    pqc_public_key_fingerprint: str     # SHA-256 of Dilithium-3 public key
    tpm_pcr_at_coronation: Dict[int, str]  # PCR 0, 1, 7 values at seal time
    preboot_covenant_ref: Optional[str] = None  # Link to Phase VI preboot covenant
    handoff_covenant_ref: Optional[str] = None  # Link to handoff covenant

    # Timestamps
    coronation_started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    coronation_sealed_at: Optional[datetime] = None

    # State
    state: CovenantState = CovenantState.CORONATION_ACTIVE

    def manifest_hash(self) -> str:
        """The canonical hash that becomes the covenant_id for all subsequent events."""
        import hashlib
        import json
        dump = self.model_dump()
        # Exclude mutable state fields from the sealed hash
        dump.pop("state", None)
        canonical = json.dumps(dump, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


# ============================================================
# ZPD CALIBRATION (PERSISTENT, INSPECTABLE, DECAYABLE)
# ============================================================

class CalibrationObservation(BaseModel):
    """A single observation about the principal's engagement pattern."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    observation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    domain: CalibrationDomain
    signal: str                          # What was observed
    raw_value: float                     # 0.0 - 1.0
    context: Dict[str, Any] = Field(default_factory=dict)


class CalibrationSnapshot(BaseModel):
    """
    Current calibration model for a principal.
    Computed from windowed observations with exponential recency weighting.
    Full history remains in the covenant chain. This is the active model.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    principal_identity_hash: str
    snapshot_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Per-domain ZPD estimates (0.0 = needs full scaffolding, 1.0 = fully autonomous)
    domains: Dict[str, float] = Field(default_factory=dict)

    # Interaction rhythm
    avg_response_depth: float = 0.5      # How deeply principal engages with machine reasoning
    override_rate: float = 0.0           # How often principal overrides machine recommendations
    inspection_regularity: float = 1.0   # How consistently principal inspects

    # Drift detection (current window vs full baseline)
    drift_from_baseline: float = 0.0     # 0.0 = stable, >0.5 = significant drift

    # Metadata
    window_size: int = 64                # Number of recent observations in active model
    total_observations: int = 0          # Lifetime count (chain has them all)

    def is_inspectable(self) -> bool:
        """Always True. Article VIII: absolute inspection right."""
        return True


class ResonantIdentityProfile(BaseModel):
    """
    Probabilistic model of how the principal is best met.
    This is not truth about the person; it is inspectable calibration.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    principal_identity_hash: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    abstraction_preference: float = 0.5
    challenge_tolerance: float = 0.5
    ambiguity_tolerance: float = 0.5
    metaphorical_resonance: float = 0.5
    register_alignment: float = 0.5
    preferred_depth: float = 0.5

    stable_signals: Dict[str, float] = Field(default_factory=dict)
    low_confidence_hypotheses: Dict[str, float] = Field(default_factory=dict)

    def is_inspectable(self) -> bool:
        return True


# ============================================================
# ENCOUNTER MEMORY (CONTINUITY, NOT JUST FACT STORAGE)
# ============================================================

class EncounterSummary(BaseModel):
    """
    Inspectable summary of a meaningful encounter.
    This is how the machine remembers how to meet the principal, not just facts about them.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    encounter_id: str
    principal_identity_hash: str
    topic: str
    principal_goal: Optional[str] = None
    machine_role: Optional[str] = None
    summary: str = ""
    what_deepened: List[str] = Field(default_factory=list)
    what_confused: List[str] = Field(default_factory=list)
    unresolved_threads: List[str] = Field(default_factory=list)
    officer_sequence: List[str] = Field(default_factory=list)
    zpd_estimate: float = 0.5
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    memory_class: MemoryClass = MemoryClass.ENCOUNTER
    retention_class: RetentionClass = RetentionClass.AMENDABLE


# ============================================================
# COVENANT CHAIN EVENT TYPES
# ============================================================

class CovenantEventType(str, Enum):
    """Event types for the covenant chain. Coronation is the root."""
    CORONATION_SEALED = "coronation_sealed"
    CORONATION_REJECTED = "coronation_rejected"
    TERMS_AMENDED = "terms_amended"
    TRUST_TIER_CHANGED = "trust_tier_changed"
    INSPECTION_RECORDED = "inspection_recorded"
    INSPECTION_LAPSED = "inspection_lapsed"
    DISAGREEMENT_LOGGED = "disagreement_logged"
    CONSTITUTIONAL_REFUSAL = "constitutional_refusal"
    CALIBRATION_OBSERVATION = "calibration_observation"
    CALIBRATION_SNAPSHOT = "calibration_snapshot"
    PRINCIPAL_IDENTITY_UPDATED = "principal_identity_updated"
    PRESENCE_DECLARED = "presence_declared"
    PRESENCE_REDECLARED = "presence_redeclared"
    OFFICE_ASSUMED = "office_assumed"
    RELATIONAL_BOUNDARY_RESTATED = "relational_boundary_restated"
    OFFICER_SEQUENCE_DECLARED = "officer_sequence_declared"
    ENCOUNTER_SUMMARIZED = "encounter_summarized"
    MEMORY_REVOKED = "memory_revoked"
    MEMORY_AMENDED = "memory_amended"
    COVENANT_TERMINATED = "covenant_terminated"
    COVENANT_EXPORTED = "covenant_exported"
    HEARTBEAT = "heartbeat"
    AMBIGUITY_ENCOUNTER = "ambiguity_encounter"     # Machine said "I cannot determine"
    ENCOUNTER_RESOLVED = "encounter_resolved"       # Human provided witness
