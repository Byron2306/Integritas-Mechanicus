export const PROMPT_FRAMEWORKS = [
  { id: 'TREF', name: 'TREF', description: 'Task, Requirement, Expectation, Format' },
  { id: 'SCET', name: 'SCET', description: 'Situation, Complication, Expectation, Task' },
  { id: 'PECRA', name: 'PECRA', description: 'Purpose, Expectation, Context, Request, Action' },
  { id: 'GRADE', name: 'GRADE', description: 'Goal, Request, Action, Detail, Examples' },
  { id: 'ROSES', name: 'ROSES', description: 'Role, Objective, Scenario, Expected Solution, Steps' },
  { id: 'STAR', name: 'STAR', description: 'Situation, Task, Action, Result' },
  { id: 'SOAR', name: 'SOAR', description: 'Situation, Objective, Action, Result' },
  { id: 'SMART', name: 'SMART', description: 'Specific, Measurable, Achievable, Relevant, Time-bound' },
  { id: 'ERA', name: 'ERA', description: 'Expectation, Role, Action' },
  { id: 'APE', name: 'APE', description: 'Action, Purpose, Expectation' },
  { id: 'TAG', name: 'TAG', description: 'Task, Action, Goal' },
  { id: 'CARE', name: 'CARE', description: 'Context, Action, Result, Example' },
];

export const LEARNING_FRAMEWORKS = [
  { id: '8020', name: 'The 80/20 Shortcut', description: 'Focus on the 20% of content that yields 80% of results. 10 two-hour blocks.' },
  { id: 'onepager', name: 'The One-Pager', description: 'Compress complex topics into a single, high-density reference page.' },
  { id: 'eli12', name: "Teach Me Like I'm New", description: 'Explain using 12-year-old vocabulary, stories, and analogies.' },
  { id: 'ladder', name: 'The Skill Ladder', description: 'Map a topic into 5 clear levels from "Know Nothing" to "Could Teach This".' },
  { id: 'traps', name: 'Beginner Mistakes', description: 'Identify the 5 biggest traps that waste weeks of time.' }
];

export const LEVERAGE_STRATEGIES = [
  { id: 'compress', name: 'Decade Compression', role: 'Time-Leverage Strategist', goal: '10 years of progress in 1 year.' },
  { id: 'asymmetric', name: 'Asymmetric Ops', role: 'Opportunity Detector', goal: '10x-100x returns on small inputs.' },
  { id: 'os_upgrade', name: 'Cognitive OS', role: 'OS Upgrader', goal: 'Rewrite thought patterns for clarity and speed.' },
  { id: 'dream_self', name: 'Dream Version', role: 'Psychological Reprogrammer', goal: 'Destroy limiting identity and install high-version self-image.' }
];

export const PROMPT_TECHNIQUES = [
  "Explain like I'm 5",
  "Visualize the process",
  "Break it into chunks",
  "Find the patterns",
  "Use analogies",
  "Break myths",
  "Relate to real life",
  "Teach it back",
  "Ask the critical 'why'",
  "Simulate or practice",
  "Turn it into a story",
  "Challenge it",
  "Prioritize learning",
  "Find the gaps"
];

export const ENGINE_310_ZD = {
  version: "3.10-ZD",
  gates: ["Truth", "Determinism", "Privacy", "Bounded Loops", "No Evasion"],
  lanes: [
    { id: 'explore', name: 'Explore (Internal)', color: 'blue', description: 'Hypothesis generation and candidate planning.' },
    { id: 'commit', name: 'Commit (Output)', color: 'emerald', description: 'Deliverables with verified claims and receipts.' }
  ],
  modes: [
    { id: 'FAST', name: 'FAST', description: 'Drafting only.' },
    { id: 'STANDARD', name: 'STANDARD', description: 'Factual work with evidence bullets.' },
    { id: 'FORMAL', name: 'FORMAL', description: 'High-stakes reporting with audit notes.' }
  ],
  pipeline: [
    "Intake",
    "Route",
    "Explore",
    "Evidence",
    "Build",
    "QA",
    "Audit"
  ],
  references_pack: {
    trusted_domains: [
      "google.com", "microsoft.com", "aws.amazon.com", "github.com", 
      "stackoverflow.com", "wikipedia.org", "mozilla.org", "w3.org",
      "oracle.com", "ibm.com", "redhat.com"
    ],
    conflict_keywords: ["disputed", "unconfirmed", "contradictory", "conflict", "debate", "controversial"],
    verification_logic: "Domain-based authority check + Title-based conflict detection."
  }
};

export const FAILURE_CATEGORIES = [
  "Parser Failures",
  "Mapping Failures",
  "Comparison Conflicts",
  "Score Anomalies",
  "Export Failures"
];

export const BASELINE_METRICS = [
  { name: "Analysis Accuracy", target: "98%" },
  { name: "Execution Speed", target: "< 60s" },
  { name: "Merge Quality", target: "High" },
  { name: "Trace Completeness", target: "100%" }
];

export const MEMOREDEX_STRUCTURE = [
  { id: 'core', name: 'MemoreDex Core', description: 'Authoritative system knowledge and canonical schemas.' },
  { id: 'analysis', name: 'MemoreDex Analysis', description: 'Analytical results and historical run outputs.' },
  { id: 'lab', name: 'MemoreDex Lab', description: 'Experimental artifacts and learning-based optimizations.' }
];

export const SAMPLE_ARCHITECTURES = {
  OFFLINE_QR_SYSTEM: {
    name: "Offline QR Assignment System",
    description: "Enterprise-grade educational assessment platform with offline-first architecture.",
    components: [
      { name: "Local Backend Server", tech: "Node.js/Python", features: ["AI Assessment", "CSV Handling", "File Storage"] },
      { name: "Mobile Student App", tech: "React Native", features: ["QR Scanning", "Offline Sync Queue", "HTML Report Viewer"], dependencies: ["Local Backend Server"] }
    ],
    constraints: ["Works offline", "Supports 800 concurrent users", "Local standalone server"]
  },
  LEGACY_FORM_SYSTEM: {
    name: "Travel Guard Legacy Schema",
    description: "Complex multi-page document architecture for insurance processing.",
    components: [
      { name: "Form Parser", tech: "OCR/Vision", features: ["Field Extraction", "Section Mapping"] },
      { name: "Benefit Engine", tech: "Rules-based", features: ["Schedule Validation", "Policy Matching"] }
    ],
    constraints: ["High precision required", "Multi-page correlation"]
  }
};

export const SOPHIA_AI_FRAMEWORK = {
  name: "Sophia-AI",
  version: "1.0",
  tagline: "Constitutional Governance and Pedagogical Intelligence",
  layers: [
    { 
      id: 'constitutional', 
      name: 'Constitutional Governance', 
      role: 'Defines normative boundaries and positive duties',
      mechanisms: ['Authorship protection', 'Provenance rules', 'Non-deceptive presence', 'Pedagogical obligations'],
      value: 'Turns safety from an ad hoc filter into an explicit rule framework'
    },
    { 
      id: 'technical', 
      name: 'Technical Enforcement', 
      role: 'Makes rules materially enforceable',
      mechanisms: ['Kernel policy controls', 'Hardware attestation', 'Model orchestration'],
      value: 'Reduces reliance on language-only refusal'
    },
    { 
      id: 'response', 
      name: 'Response Governance', 
      role: 'Reviews each turn before delivery',
      mechanisms: ['Normative review', 'Factual validation', 'Intent interpretation', 'Coherence monitoring'],
      value: 'Improves reliability and defensibility'
    },
    { 
      id: 'pedagogical', 
      name: 'Pedagogical Adaptation', 
      role: 'Calibrates support to learner need',
      mechanisms: ['Learner-state estimation', 'Scaffolding modes', 'Structured reasoning formats'],
      value: 'Improves understanding rather than mere completion'
    },
    { 
      id: 'assessment', 
      name: 'Assessment Ecology', 
      role: 'Evaluates performance and growth over time',
      mechanisms: ['Baseline', 'Diagnostic', 'Formative', 'Criterion', 'Reflective', 'Ipsative'],
      value: 'Distinguishes fluent output from grounded understanding'
    },
    { 
      id: 'readiness', 
      name: 'Readiness Model', 
      role: 'Stages access to advanced capabilities',
      mechanisms: ['Capability gates', 'Longitudinal evaluation', 'Growth thresholds'],
      value: 'Links development to evidence, not aspiration'
    }
  ],
  principles: [
    { name: 'Governance before generation', description: 'Normatively governed before fluent output dominates.' },
    { name: 'Assistance without authorship displacement', description: 'Strengthen human work without taking over the role.' },
    { name: 'Verification before confidence', description: 'Claims must be checked before delivered with certainty.' },
    { name: 'Pedagogy before substitution', description: 'Support reasoning, not merely finish the task.' },
    { name: 'Assessment as system logic', description: 'Built-in diagnosis, correction, and growth.' },
    { name: 'Growth with accountability', description: 'Evidenced over time and tied to standards.' }
  ]
};
