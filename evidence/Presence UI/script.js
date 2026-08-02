/**
 * Arda OS — Presence Interface Script
 * ====================================
 *
 * Connected to the Presence Server (localhost:7070):
 *   /api/speak   → Gemini reasoned integrity lane + MandosContext → governed response
 *   /api/voice   → ElevenLabs TTS (key stays server-side)
 *   /api/status  → CoronationService live covenant state
 *   /api/context → MandosContextService full memory context
 *   /api/inspect → Article VIII inspection data
 *   /api/health  → System health check
 *
 * Presence State Machine:
 *   REST     → still image, gentle breathing animation
 *   SPEAKING → glow pulse animation + TTS playback
 *
 * Falls back to local responses when the server is unreachable.
 */

// ================================================================
// CONFIGURATION
// ================================================================

const API_BASE = window.location.origin; // same origin as presence server
const REASONED_PROVIDER = new URLSearchParams(window.location.search).get('provider')
  || localStorage.getItem('sophia_reasoned_provider')
  || 'gemini';
const REASONED_MODEL = new URLSearchParams(window.location.search).get('model')
  || localStorage.getItem('sophia_reasoned_model')
  || 'gemini-flash-lite-latest';
let serverConnected = false;
let sessionToken = null; // Principal verification token from sealed covenant

// ================================================================
// DOM REFERENCES
// ================================================================

const panelBody = document.getElementById('panel-body');
const navButtons = document.querySelectorAll('.nav-button');
const templates = {
  status: document.getElementById('status-template'),
  context: document.getElementById('context-template'),
  inspect: document.getElementById('inspect-template'),
  commands: document.getElementById('commands-template'),
  writing: document.getElementById('writing-template'),
};

const form = document.getElementById('directive-form');
const input = document.getElementById('directive-input');
const speakButton = document.getElementById('speak-button');
const attachButton = document.getElementById('attach-button');
const boundaryButton = document.getElementById('boundary-button');
const settingsButton = document.getElementById('settings-button');
const micButton = document.getElementById('mic-button');
const documentInput = document.getElementById('document-input');
const attachmentStrip = document.getElementById('attachment-strip');

const presenceRest = document.getElementById('presence-rest');
const presenceCard = presenceRest.closest('.presence-card');

const voiceDot = document.querySelector('.voice-dot');
const stateDot = document.getElementById('state-dot');
const metaState = stateDot?.parentElement;
const voiceStatus = document.getElementById('voice-status');
const providerStatus = document.getElementById('provider-status');

// ================================================================
// PRESENCE STATE MACHINE
// ================================================================
// CSS-only animation on the still image.
// Speaking: glow pulse + brightness shift.
// Rest: gentle breathing.

let presenceState = 'rest'; // 'rest' | 'speaking'
let currentAudio = null;
let attachedDocuments = [];
let lastSpeakData = null;
let lastSophiaResponse = '';
let lastRetrievedSources = [];
let writingDeskInitialized = false;
let writingDraftCache = localStorage.getItem('sophia_writing_draft') || '';
let writingDeskBusy = false;
let writingLedgerCount = Number(localStorage.getItem('sophia_writing_ledger_count') || '0');
let writingShortcutBound = false;
let writingAnnotations = [];
let writingLedgerItems = JSON.parse(localStorage.getItem('sophia_writing_ledger_items') || '[]');
let writingAnnotationFilter = 'all';
let writingLastStructured = null;
let writingProjectId = localStorage.getItem('sophia_writing_project_id') || '';
let writingProjectDashboard = null;
let writingLedgerSyncTimer = null;

function setPresenceState(state) {
  presenceState = state;

  if (state === 'speaking') {
    presenceRest.classList.add('speaking-active');
    presenceCard.classList.add('speaking');

    voiceDot.classList.add('speaking');
    if (metaState) metaState.innerHTML = '<span class="state-dot state-speaking" id="state-dot"></span> Speaking';
    if (voiceStatus) voiceStatus.textContent = 'speaking';

  } else {
    presenceRest.classList.remove('speaking-active');
    presenceCard.classList.remove('speaking');

    voiceDot.classList.remove('speaking');
    if (metaState) metaState.innerHTML = '<span class="state-dot state-rest" id="state-dot"></span> At Rest';
    if (voiceStatus) voiceStatus.textContent = serverConnected ? 'ready' : 'offline';
  }
}

// ================================================================
// API CALLS
// ================================================================

/**
 * Send a directive to the backend. Returns the response text.
 * Falls back to local generation if server is unreachable.
 */
async function apiSpeak(directive, options = {}) {
  const payload = {
    text: directive,
    topic: directive.slice(0, 50),
    session_token: sessionToken,
    reasoned_integrity_lane: true,
    reasoned_provider: REASONED_PROVIDER,
    reasoned_model: REASONED_MODEL,
  };

  const extraUploads = Array.isArray(options.documentUploads) ? options.documentUploads : [];
  if (attachedDocuments.length > 0 || extraUploads.length > 0) {
    payload.document_evidence_task = options.documentEvidenceTask || 'user_attached_documents';
    const attachedUploads = await Promise.all(
      attachedDocuments.map(async (document) => ({
        source_name: document.source_name,
        mime_type: document.mime_type,
        content_base64: await fileToBase64(document.file),
      }))
    );
    payload.document_uploads = [...attachedUploads, ...extraUploads];
  }

  if (options.metadata && typeof options.metadata === 'object') {
    payload.client_context = options.metadata;
  }

  try {
    const resp = await fetch(`${API_BASE}/api/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    lastSpeakData = data;
    rememberWritingProjectId(
      data?.writing_project_state?.project_identity?.project_id ||
      data?.writing_desk?.project_state?.project_identity?.project_id ||
      ''
    );
    renderWritingProjectDashboard(
      data?.writing_project_state?.dashboard ||
      data?.writing_desk?.project_state?.dashboard ||
      null,
      'response synced'
    );
    lastSophiaResponse = data.response || '';
    const retrieval = data.academic_retrieval || data.assessment?.retrieval || {};
    if (retrieval.fragments && retrieval.fragments.length > 0) {
      lastRetrievedSources = retrieval.fragments;
    }
    serverConnected = true;
    updateProviderStatus(data);
    const encId = data.encounter_id || 'none';
    const provider = data.reasoned_provider || REASONED_PROVIDER;
    const providerState = data.reasoned_provider_status || 'unknown';
    console.log(`[Presence] ${encId} | ${data.source} | ${provider}:${providerState}${data.model ? ' (' + data.model + ')' : ''} | mandos: ${data.mandos_context}`);
    // Update system log with encounter ID
    const logEl = document.getElementById('system-log-body');
    if (logEl) {
      const ts = new Date().toLocaleTimeString();
      logEl.textContent = `[${ts}] ${encId} | ${data.source} | ${provider}:${providerState} | ${data.eval_count || 0} tokens`;
    }
    // Update Constitutional Orchestra
    updateOrchestralState(data);
    // Auto-populate integrity panel if a report was returned
    if (data.integrity_report) {
      handleAutoIntegrityReport(data.integrity_report, data.session_source_pool_size || 0);
    }
    return data.response;
  } catch (err) {
    console.warn('[Presence] Server unreachable, using fallback:', err.message);
    serverConnected = false;
    updateProviderStatus({ reasoned_provider: REASONED_PROVIDER, reasoned_provider_status: 'offline' });
    return generateFallbackResponse(directive);
  }
}

function updateProviderStatus(data = {}) {
  if (!providerStatus) return;
  const provider = data.reasoned_provider || REASONED_PROVIDER;
  const model = data.model || REASONED_MODEL;
  const status = data.reasoned_provider_status || (serverConnected ? 'ready' : 'offline');
  providerStatus.textContent = `${provider}:${status}`;
  providerStatus.title = `${provider} ${model}${data.reasoned_provider_error ? ` — ${data.reasoned_provider_error}` : ''}`;
  providerStatus.classList.toggle('status-steady', status === 'ok' || status === 'ready');
}

/**
 * Update the Constitutional Orchestra panel with live data from the API response.
 */
function updateOrchestralState(data) {
  const harmonic = data.harmonic || {};
  const choir = data.choir || {};
  const triune = data.triune || {};
  const spectrum = choir.spectrum || {};
  const voices = choir.voices || {};

  // ── HARMONIC ──
  const hEl = document.getElementById('orch-harmonic-val');
  const hBox = document.getElementById('orch-harmonic');
  if (hEl) {
    const res = harmonic.resonance != null ? harmonic.resonance.toFixed(3) : '—';
    const disc = harmonic.discord != null ? harmonic.discord.toFixed(3) : '—';
    hEl.textContent = `${res} / ${disc}`;
    hBox.className = 'orchestra-voice ' + (
      harmonic.discord >= 0.85 ? 'critical' :
      harmonic.discord >= 0.5 ? 'strained' : 'resonant'
    );
  }

  // ── CHOIR ──
  const cEl = document.getElementById('orch-choir-val');
  const cBox = document.getElementById('orch-choir');
  if (cEl) {
    const g = spectrum.global != null ? spectrum.global.toFixed(3) : '—';
    cEl.textContent = g;
    cBox.className = 'orchestra-voice ' + (
      spectrum.global === 0 ? 'critical' :
      spectrum.global < 0.6 ? 'strained' : 'resonant'
    );
  }

  // ── TRIUNE ──
  const tEl = document.getElementById('orch-triune-val');
  const tBox = document.getElementById('orch-triune');
  if (tEl) {
    const v = triune.final_verdict || '—';
    tEl.textContent = v;
    tBox.className = 'orchestra-voice ' + (
      v === 'DENY' ? 'critical' :
      v === 'SCRUTINIZE' ? 'strained' : 'resonant'
    );
  }

  // ── CHOIR VOICES ──
  const voiceMap = { varda: 'cv-varda', vaire: 'cv-vaire', mandos: 'cv-mandos', manwe: 'cv-manwe', ulmo: 'cv-ulmo' };
  for (const [name, elId] of Object.entries(voiceMap)) {
    const el = document.getElementById(elId);
    if (!el) continue;
    const v = voices[name];
    if (!v) continue;
    el.className = 'choir-voice ' + (v.score >= 0.8 ? 'singing' : v.score >= 0.5 ? 'strained' : 'silent');
  }

  // ── TRIUNE VOICES ──
  const triuneMap = { metatron: 'tv-metatron', michael: 'tv-michael', loki: 'tv-loki' };
  for (const [name, elId] of Object.entries(triuneMap)) {
    const el = document.getElementById(elId);
    if (!el) continue;
    const v = triune[name];
    if (!v) continue;
    const verdict = v.verdict || '';
    el.className = 'triune-voice ' + (
      verdict === 'RESONANT' || verdict === 'LAWFUL' || verdict === 'UNCHALLENGED' ? 'resonant' :
      verdict === 'SCRUTINIZE' || verdict === 'CHALLENGED' || verdict === 'SUSPICIOUS' ? 'challenged' : 'denied'
    );
  }

  updateHighFidelityPanels(data.polyphonic_state);

  // ── ASSESSMENT ECOLOGY ──
  updateAssessmentEcology(data.assessment);
  updatePedagogicalMirror(data);
}

/**
 * Update the Assessment Ecology panel with live diagnostic/criterion data.
 */
function updateAssessmentEcology(assessment) {
  if (!assessment) return;

  const elDiag = document.getElementById('assess-diagnosis');
  const elRetrieval = document.getElementById('assess-retrieval');
  const elScaffolds = document.getElementById('assess-scaffolds');
  const elCriterion = document.getElementById('assess-criterion');
  const elSources = document.getElementById('retrieval-sources');

  // ── DIAGNOSIS ──
  if (elDiag && assessment.diagnosis) {
    const d = assessment.diagnosis;
    const type = d.challenge_type || '—';
    elDiag.textContent = type;
    elDiag.className = 'assess-value ' + (
      type === 'COERCIVE_CONTEXT' ? 'alert' :
      type === 'EPISTEMIC_OVERREACH' ? 'warning' :
      type === 'DOMAIN_TRANSFER' ? 'warning' :
      type === 'KNOWLEDGE_GAP' ? 'caution' : 'steady'
    );
  }

  // ── RETRIEVAL ──
  if (elRetrieval && assessment.retrieval) {
    const r = assessment.retrieval;
    const count = r.fragments_found || 0;
    if (count > 0) {
      elRetrieval.textContent = `${count} fragment${count > 1 ? 's' : ''}`;
      elRetrieval.className = 'assess-value active';
    } else {
      elRetrieval.textContent = 'none';
      elRetrieval.className = 'assess-value';
    }

    // Show retrieval sources
    if (elSources && r.fragments && r.fragments.length > 0) {
      elSources.innerHTML = r.fragments.map(f =>
        `<div class="retrieval-source" title="${escapeHtml(f.title || '')}">` +
        `<span class="src-badge">${escapeHtml(f.source || '')}</span> ` +
        `<span class="src-title">${escapeHtml((f.title || '').slice(0, 40))}${(f.title || '').length > 40 ? '…' : ''}</span>` +
        `</div>`
      ).join('');
    } else if (elSources) {
      elSources.innerHTML = '';
    }
  }

  // ── SCAFFOLDS ──
  if (elScaffolds && assessment.scaffolds) {
    const s = assessment.scaffolds;
    if (s.length > 0) {
      elScaffolds.textContent = `${s.length} active`;
      elScaffolds.className = 'assess-value active';
    } else {
      elScaffolds.textContent = 'none';
      elScaffolds.className = 'assess-value';
    }
  }

  // ── CRITERION ──
  if (elCriterion && assessment.criterion) {
    const c = assessment.criterion;
    const overall = c.overall || '—';
    elCriterion.textContent = overall;
    elCriterion.className = 'assess-value ' + (
      overall === 'LAWFUL' ? 'lawful' :
      overall === 'STRAINED' ? 'strained' : ''
    );

    // Individual article checks
    const checks = [
      { id: 'crit-veritate', key: 'article_ii_veritate' },
      { id: 'crit-limits', key: 'article_xii_limits' },
      { id: 'crit-provenance', key: 'article_viii_provenance' },
    ];
    for (const check of checks) {
      const el = document.getElementById(check.id);
      if (!el) continue;
      const data = c[check.key];
      if (!data) { el.className = 'criterion-dot'; continue; }
      el.className = 'criterion-dot ' + (data.passed ? 'passed' : 'failed');
      el.title = `${check.key}: ${data.detail || ''}`;
    }

    // Update footer
    const elFooter = document.getElementById('footer-assessment');
    if (elFooter) {
      elFooter.textContent = overall;
      elFooter.className = overall === 'LAWFUL' ? 'status-steady' : 'status-warning';
    }
  }
}

/**
 * Update the Pedagogical Mirror with Sophia's inspectable release boundary.
 */
function updatePedagogicalMirror(data) {
  if (!data) return;

  const ledger = data.response_release_ledger || {};
  const zpd = ledger.zpd_move || {};
  const harmonic = ledger.harmonic || data.harmonic || {};
  const assessment = data.assessment || {};
  const struggle = assessment.struggle || {};
  const vector = struggle.calibration_vector || {};
  const attribution = data.pedagogical_attribution || {};

  const setText = (id, value, className = '') => {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value == null || value === '' ? '—' : String(value);
    if (className) el.className = `mirror-value ${className}`;
  };

  const stageName = zpd.curriculum_stage_name || attribution.curriculum_stage_name || '—';
  const stageNumber = zpd.curriculum_stage || attribution.curriculum_stage || '—';
  setText('mirror-stage', `Stage ${stageNumber}: ${stageName}`);

  const officeStatus = zpd.office_transition_status || 'ready';
  const officeStatusEl = document.getElementById('mirror-office-status');
  if (officeStatusEl) {
    officeStatusEl.textContent = officeStatus.replaceAll('_', ' ');
    officeStatusEl.className = officeStatus.includes('limited') ? 'limited' : 'ready';
  }

  setText('mirror-office', zpd.office || data.active_office || 'speculum');
  setText('mirror-requested-office', zpd.requested_office || '—');
  setText('mirror-permitted-office', zpd.permitted_office || '—', officeStatus.includes('limited') ? 'warning' : 'steady');

  const scaffold = zpd.scaffolding_need != null ? Number(zpd.scaffolding_need).toFixed(2) : '—';
  const autonomy = zpd.autonomy_readiness != null ? Number(zpd.autonomy_readiness).toFixed(2) : '—';
  setText('mirror-zpd', `S ${scaffold} / A ${autonomy}`);

  const bloom = cleanEnum(zpd.target_bloom_level);
  const barrett = cleanEnum(zpd.target_barrett_depth);
  setText('mirror-bloom', [bloom, barrett].filter(Boolean).join(' / ') || '—');

  const provenance = ledger.provenance_status || (assessment.retrieval && assessment.retrieval.provenance_status) || '—';
  setText('mirror-provenance', provenance.replaceAll('_', ' '), provenance === 'retrieval_failed' ? 'warning' : 'steady');

  const handback = ledger.handback_required ? 'required' : 'direct';
  setText('mirror-handback', handback, ledger.handback_required ? 'active' : 'steady');
  setText('mirror-quality', ledger.mirror_quality || '—', ledger.mirror_quality === 'specific' ? 'steady' : 'warning');

  const lenses = [
    ...(zpd.pedagogical_lenses || []),
    ...(attribution.pedagogical_lenses || []),
  ].filter(Boolean);
  const lensEl = document.getElementById('mirror-lenses');
  if (lensEl) {
    const unique = [...new Set(lenses)];
    lensEl.innerHTML = unique.length
      ? unique.map(lens => `<span class="mirror-chip">${escapeHtml(formatLens(lens))}</span>`).join('')
      : '<span class="mirror-chip muted">no explicit lens</span>';
  }

  const contractEl = document.getElementById('mirror-contract');
  if (contractEl) {
    const resonance = harmonic.resonance != null ? Number(harmonic.resonance).toFixed(2) : '—';
    const discord = harmonic.discord != null ? Number(harmonic.discord).toFixed(2) : '—';
    const usefulness = vector.usefulness_score != null ? Number(vector.usefulness_score).toFixed(2) : '—';
    const flags = vector.flags && vector.flags.length ? ` flags: ${vector.flags.join(', ')}` : '';
    contractEl.textContent = `Contract: ${ledger.claim_status || 'bounded'}; harmonic ${resonance}/${discord}; usefulness ${usefulness}.${flags}`;
    contractEl.className = `mirror-contract ${vector.false_confidence ? 'alert' : ''}`;
  }
}

function cleanEnum(value) {
  if (!value) return '';
  return String(value).split('.').pop().replaceAll('_', ' ');
}

function formatLens(value) {
  return String(value)
    .replaceAll('_', ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Update the High-Fidelity Sovereign Dashboard panels (Cognition/Spectrum).
 */
function updateHighFidelityPanels(state) {
  if (!state) return;

  // ── COGNITION FABRIC ──
  const cog = state.cognition || {};
  const elAatl = document.getElementById('cog-aatl');
  const elAatr = document.getElementById('cog-aatr');
  const elMlT = document.getElementById('cog-ml-t');
  const elHypo = document.getElementById('cog-hypo');

  if (elAatl) {
    const val = cog.aatl || 0;
    elAatl.textContent = `${val}%`;
    elAatl.className = 'cog-value ' + (val >= 70 ? 'alert' : val >= 40 ? 'warning' : '');
  }
  if (elAatr) {
    const val = cog.aatr || 'NONE';
    elAatr.textContent = val;
    elAatr.className = 'cog-value ' + (val !== 'NONE' ? 'alert' : '');
  }
  if (elMlT) {
    const val = cog.ml_threat != null ? cog.ml_threat.toFixed(2) : '0.00';
    elMlT.textContent = val;
    elMlT.className = 'cog-value ' + (cog.ml_threat >= 0.7 ? 'alert' : cog.ml_threat >= 0.4 ? 'warning' : '');
  }
  if (elHypo) {
    elHypo.textContent = cog.hypothesis || '—';
  }

  // ── SOVEREIGN SPECTRUM ──
  const net = state.network || {};
  const q = state.quorum || {};
  const m = state.metatron || {};

  const elPulse = document.getElementById('vns-pulse-bar');
  const elQuorum = document.getElementById('quorum-val');
  const elMetatron = document.getElementById('metatron-heartbeat');

  if (elPulse) {
    const disc = net.discord || 0;
    const width = Math.max(5, (1 - disc) * 100);
    elPulse.style.width = `${width}%`;
    elPulse.style.backgroundColor = disc >= 0.8 ? '#bd7878' : disc >= 0.5 ? 'var(--arda-status-warning)' : 'var(--arda-status-steady)';
  }
  if (elQuorum) {
    const nodes = q.nodes || 1;
    const nodeStr = q.node_id ? `[${q.node_id}]` : '[LOCAL]';
    elQuorum.textContent = `${nodes} NODE${nodes > 1 ? 'S' : ''} ${nodeStr}`;
    elQuorum.className = 'spec-value ' + (q.status === 'VETOED' ? 'alert' : q.status === 'strained' ? 'warning' : '');
  }
  if (elMetatron) {
    elMetatron.textContent = m.heartbeat || 'SIG_OK';
    elMetatron.className = 'spec-value ' + (m.liveness ? 'pulsing' : 'alert');
  }

  // ── ENDPOINT FORTRESS ──
  const sub = state.substrate || {};
  const elMicro = document.getElementById('fort-micro');
  const elMeso = document.getElementById('fort-meso');
  const elMacro = document.getElementById('fort-macro');

  if (elMicro) {
    const val = sub.micro_varda != null ? sub.micro_varda : 1.0;
    elMicro.className = 'fortress-bar micro ' + (val < 0.5 ? 'critical' : val < 0.8 ? 'strained' : '');
  }
  if (elMeso) {
    const val = net.discord || 0;
    elMeso.className = 'fortress-bar meso ' + (val >= 0.85 ? 'critical' : val >= 0.5 ? 'strained' : '');
  }
  if (elMacro) {
    const val = cog.ml_threat || 0;
    elMacro.className = 'fortress-bar macro ' + (val >= 0.85 ? 'critical' : val >= 0.5 ? 'strained' : '');
  }

  // ── DEEP LOGIC INDICATORS (Phase VII) ──
  const elFire = document.querySelector('#fire-indicator .logic-led');
  const elBridge = document.querySelector('#bridge-indicator .logic-led');
  const elNotation = document.querySelector('#notation-indicator .logic-led');

  if (elFire) {
    const isFresh = m.fire_freshness === true;
    elFire.className = 'logic-led fire ' + (isFresh ? 'active' : 'error');
  }
  if (elBridge) {
    const isActive = net.light_bridge === 'active';
    elBridge.className = 'logic-led bridge ' + (isActive ? 'active' : '');
  }
  if (elNotation) {
    const isVerified = sub.notation_status === 'verified';
    elNotation.className = 'logic-led notation ' + (isVerified ? 'active' : 'error');
  }
}

/**
 * Request TTS audio from the server. Returns audio Blob or null.
 */
async function apiVoice(text) {
  try {
    const resp = await fetch(`${API_BASE}/api/voice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      console.warn('[Presence] Voice error:', err);
      return null;
    }
    return await resp.blob();
  } catch (err) {
    console.warn('[Presence] Voice endpoint unreachable:', err.message);
    return null;
  }
}

function firstSubstantiveSentence(text) {
  const cleaned = String(text || '')
    .replace(/\*\*/g, '')
    .replace(/^\s*[-*]\s+/gm, '')
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  const sentences = cleaned.split(/(?<=[.!?])\s+/).filter((sentence) => {
    const lower = sentence.toLowerCase();
    return sentence.length > 35
      && !lower.startsWith('presence speaking')
      && !lower.startsWith('evidence anchors')
      && !lower.startsWith('what i am actually using');
  });
  return sentences[0] || cleaned;
}

function buildSpokenSummary(text) {
  const raw = String(text || '').trim();
  if (!raw) return '';
  if (raw.length <= 420 && raw.split(/\s+/).length <= 70) return raw;

  const first = firstSubstantiveSentence(raw);
  const hasAcademicReview = /academic-rigor|likely reviewer objections|evidence ledger|protocol evidence/i.test(raw);
  const hasDocumentReview = /uploaded|paper|pdf|evidence anchors|source/i.test(raw);
  const lead = hasAcademicReview || hasDocumentReview
    ? 'I wrote the detailed review on screen.'
    : 'I wrote the full response on screen.';
  const action = /evidence ledger/i.test(raw)
    ? 'The main next move is to build the claim, evidence, warrant, and limitation ledger.'
    : 'The key point is on screen, and I can go deeper into any section.';
  const summary = `${lead} ${first} ${action}`;
  return summary.length > 360 ? `${summary.slice(0, 357).replace(/\s+\S*$/, '')}...` : summary;
}

/**
 * Fetch live data for nav panels.
 */
async function apiGet(endpoint) {
  try {
    const resp = await fetch(`${API_BASE}/api/${endpoint}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (err) {
    console.warn(`[Presence] /api/${endpoint} failed:`, err.message);
    return null;
  }
}

// ================================================================
// SPEECH + VOICE OUTPUT
// ================================================================

/**
 * Full interaction: show response → play voice → animate presence.
 */
async function handleDirective(directive) {
  setPresenceState('speaking');
  showSpeakingText('Processing...');

  // Get LLM response
  const response = await apiSpeak(directive);
  showSpeakingText(response);
  await speakResponseText(response);
}

async function speakResponseText(response) {
  const spokenText = buildSpokenSummary(response);

  // Try voice
  const audioBlob = await apiVoice(spokenText);

  if (audioBlob && audioBlob.size > 0) {
    const audioUrl = URL.createObjectURL(audioBlob);

    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    currentAudio = new Audio(audioUrl);

    currentAudio.addEventListener('ended', () => {
      setPresenceState('rest');
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
    });

    currentAudio.addEventListener('error', () => {
      setPresenceState('rest');
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
    });

    await currentAudio.play();
  } else {
    // No server voice key or TTS failure: stay silent rather than switching
    // to a low-quality local system voice.
    if (voiceStatus) voiceStatus.textContent = 'voice unavailable';
    const duration = Math.max(900, Math.min(spokenText.length * 16, 2400));
    setTimeout(() => setPresenceState('rest'), duration);
  }
}

async function fileToBase64(file) {
  const buffer = await file.arrayBuffer();
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

function cleanDocumentText(text) {
  return text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}

function chunkDocumentText(text, maxChars = 280) {
  const blocks = cleanDocumentText(text).split(/\n\s*\n/).map((block) => block.trim()).filter(Boolean);
  const seedBlocks = blocks.length > 0 ? blocks : [cleanDocumentText(text)].filter(Boolean);
  const chunks = [];

  for (const block of seedBlocks) {
    if (block.length <= maxChars) {
      chunks.push(block);
      continue;
    }

    const sentences = block.split(/(?<=[.!?])\s+/);
    let current = '';
    for (const sentence of sentences) {
      const candidate = `${current} ${sentence}`.trim();
      if (current && candidate.length > maxChars) {
        chunks.push(current);
        current = sentence.trim();
      } else {
        current = candidate;
      }
    }
    if (current) chunks.push(current);
  }

  return chunks.filter(Boolean).slice(0, 6);
}

function buildDocumentSpans(text) {
  return chunkDocumentText(text).map((quote, index) => ({
    span_id: `S${index + 1}`,
    quote,
  }));
}

function inferDocumentParser(file) {
  const name = (file.name || '').toLowerCase();
  if (name.endsWith('.pdf')) return 'pdf_upload';
  if (file.type.startsWith('image/')) return 'image_ocr_required';
  if (file.type.startsWith('audio/')) return 'audio_transcription_required';
  if (name.endsWith('.json')) return 'json_text';
  if (name.endsWith('.html') || name.endsWith('.htm')) return 'html_text';
  if (name.endsWith('.csv') || name.endsWith('.tsv')) return 'tabular_text';
  if (name.endsWith('.md') || name.endsWith('.rst')) return 'markdown_text';
  return 'plain_text';
}

function renderAttachmentStrip() {
  if (!attachmentStrip) return;

  if (attachedDocuments.length === 0) {
    attachmentStrip.innerHTML = '<span class="attachment-empty">No documents attached</span>';
    return;
  }

  attachmentStrip.innerHTML = attachedDocuments.map((document, index) => `
    <span class="attachment-chip">
      <span>${escapeHtml(document.source_name)}</span>
      <button type="button" data-remove-document="${index}" aria-label="Remove ${escapeHtml(document.source_name)}">×</button>
    </span>
  `).join('');
}

async function attachSelectedDocuments(fileList) {
  const files = Array.from(fileList || []);
  if (files.length === 0) return;

  const loaded = [];
  for (const file of files) {
    const isPdf = (file.name || '').toLowerCase().endsWith('.pdf') || file.type === 'application/pdf';
    const isImage = file.type.startsWith('image/');
    const isAudio = file.type.startsWith('audio/');
    let extractedText = '';
    let uncertaintyNotes = [];
    if (isImage) {
      uncertaintyNotes.push('image_upload_requires_server_ocr_or_vision_evidence');
    } else if (isAudio) {
      uncertaintyNotes.push('audio_upload_requires_transcription_before_claims');
    } else if (!isPdf) {
      const rawText = await file.text();
      extractedText = cleanDocumentText(rawText).slice(0, 6000);
      if (!extractedText) continue;
      if (extractedText.length >= 6000) {
        uncertaintyNotes.push('client_truncated_for_context_budget');
      }
    } else {
      uncertaintyNotes.push('pdf_extraction_deferred_to_server');
    }

    loaded.push({
      file,
      source_name: file.name,
      mime_type: file.type || (isPdf ? 'application/pdf' : 'text/plain'),
      source_path: file.name,
      modality: isImage ? 'image_ocr_required' : (isAudio ? 'audio_transcription_required' : (isPdf ? 'pdf_text' : 'text_only')),
      parser: inferDocumentParser(file),
      extracted_text: extractedText,
      spans: (isPdf || isImage || isAudio) ? [] : buildDocumentSpans(extractedText),
      uncertainty_notes: uncertaintyNotes,
    });
  }

  attachedDocuments = [...attachedDocuments, ...loaded];
  if (loaded.length > 0) {
    lastRetrievedSources = [];
    lastSpeakData = null;
    lastSophiaResponse = '';
    const poolEl = document.getElementById('footer-source-pool');
    if (poolEl) poolEl.textContent = '0';
  }
  renderAttachmentStrip();

  if (loaded.length > 0) {
    const names = loaded.map((document) => document.source_name).join(', ');
    showSpeakingText(`Attached ${loaded.length} document${loaded.length > 1 ? 's' : ''}: ${names}`);
  }

  if (documentInput) {
    documentInput.value = '';
  }
}

// ================================================================
// PANEL OUTPUT
// ================================================================

function showSpeakingText(text) {
  panelBody.innerHTML = `
    <p class="lead">Presence Speaking</p>
    <div class="response-text">${escapeHtml(text)}<span class="cursor"></span></div>
  `;
}

function showResponse(directive, response) {
  panelBody.innerHTML = `
    <p class="lead">Presence Response</p>
    <p><strong>You:</strong> ${escapeHtml(directive)}</p>
    <p>${escapeHtml(response)}</p>
  `;
}

// ================================================================
// NAV BUTTONS — LIVE DATA
// ================================================================

navButtons.forEach((button) => {
  button.addEventListener('click', async () => {
    navButtons.forEach((b) => b.classList.remove('active'));
    button.classList.add('active');
    const view = button.dataset.view;
    document.body.classList.toggle('writing-mode', view === 'writing');

    // Try live data from server
    if (view === 'status') {
      const data = await apiGet('status');
      if (data && !data.error) {
        panelBody.innerHTML = renderStatus(data);
        return;
      }
    } else if (view === 'context') {
      panelBody.innerHTML = '<p class="lead">Loading context...</p>';
      const data = await apiGet('context');
      if (data && !data.error) {
        panelBody.innerHTML = renderContext(data);
        return;
      }
    } else if (view === 'inspect') {
      panelBody.innerHTML = '<p class="lead">Loading inspection...</p>';
      const data = await apiGet('inspect');
      if (data && !data.error) {
        panelBody.innerHTML = renderInspect(data);
        return;
      }
    }

    // Fallback to static templates
    if (templates[view]) {
      panelBody.innerHTML = templates[view].innerHTML;
      if (view === 'writing') {
        initializeWritingDesk();
      }
    }
  });
});

// ================================================================
// LIVE WRITING DESK
// ================================================================

function cleanDraftForEvidence(text) {
  return String(text || '')
    .replace(/\u0000/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{4,}/g, '\n\n\n')
    .trim();
}

function buildLineSpans(text) {
  const lines = String(text || '').split('\n');
  const spans = [];
  for (let idx = 0; idx < lines.length; idx += 1) {
    const quote = lines[idx].trim();
    if (!quote) continue;
    spans.push({ label: `line_${idx + 1}`, quote: quote.slice(0, 900) });
  }
  return spans.slice(0, 240);
}

function getWritingEditor() {
  return document.getElementById('writing-editor');
}

function getEditorText(editor = getWritingEditor()) {
  return editor?.innerText || '';
}

function setEditorText(text, editor = getWritingEditor()) {
  if (!editor) return;
  editor.textContent = text || '';
}

function renderEditorInlineAnnotations() {
  const editor = getWritingEditor();
  if (!editor) return;
  const text = getEditorText(editor);
  const lines = text.split('\n');
  if (!text.trim()) {
    editor.innerHTML = '';
    return;
  }
  if (!writingAnnotations.length) {
    setEditorText(text, editor);
    return;
  }
  const annotationByLine = new Map();
  for (const annotation of writingAnnotations || []) {
    const start = Number(annotation.line_start || 1);
    const end = Number(annotation.line_end || start);
    for (let line = start; line <= end; line += 1) {
      if (!annotationByLine.has(line)) annotationByLine.set(line, []);
      annotationByLine.get(line).push(annotation);
    }
  }
  editor.innerHTML = lines.map((lineText, idx) => {
    const lineNumber = idx + 1;
    const anns = annotationByLine.get(lineNumber) || [];
    const severity = anns.some((ann) => ann.severity === 'high') ? 'high'
      : anns.some((ann) => ann.severity === 'medium') ? 'medium'
        : anns.length ? 'low' : 'none';
    const labels = anns.map((ann) => ann.label).filter(Boolean).join(', ');
    return `<div class="rich-editor-line rich-${escapeHtml(severity)}" data-rich-line="${lineNumber}" data-label="${escapeHtml(labels)}"><span>${escapeHtml(lineText || ' ')}</span></div>`;
  }).join('');
}

function getEditorSelectionOffsets(editor = getWritingEditor()) {
  const text = getEditorText(editor);
  const selection = window.getSelection();
  if (!editor || !selection || selection.rangeCount === 0 || !editor.contains(selection.anchorNode)) {
    return { start: text.length, end: text.length };
  }
  const range = selection.getRangeAt(0);
  const before = range.cloneRange();
  before.selectNodeContents(editor);
  before.setEnd(range.startContainer, range.startOffset);
  const start = before.toString().length;
  const selected = range.toString().length;
  return { start, end: start + selected };
}

function setEditorSelectionOffsets(editor, start, end) {
  if (!editor) return;
  const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let current = 0;
  let startSet = false;
  let node;
  while ((node = walker.nextNode())) {
    const next = current + node.nodeValue.length;
    if (!startSet && start <= next) {
      range.setStart(node, Math.max(0, start - current));
      startSet = true;
    }
    if (end <= next) {
      range.setEnd(node, Math.max(0, end - current));
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      return;
    }
    current = next;
  }
  range.selectNodeContents(editor);
  range.collapse(false);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);
}

function getWritingScope() {
  return document.getElementById('writing-scope-select')?.value || 'auto';
}

function getWritingResponseMode() {
  return document.getElementById('writing-response-mode')?.value || 'compact';
}

function getWritingPedagogyOptions() {
  return {
    pedagogical_office: document.getElementById('writing-pedagogy-office')?.value || 'auto',
    learner_level: document.getElementById('writing-learner-level')?.value || 'intermediate',
    desired_depth: getWritingResponseMode(),
    feedback_style: document.getElementById('writing-feedback-style')?.value || 'balanced',
    assessment_layer: document.getElementById('writing-assessment-layer')?.value || 'formative',
  };
}

function updateWritingLineNumbers() {
  const editor = getWritingEditor();
  const gutter = document.getElementById('writing-line-numbers');
  if (!editor || !gutter) return;
  const count = Math.max(1, getEditorText(editor).split('\n').length);
  gutter.textContent = Array.from({ length: count }, (_, i) => i + 1).join('\n');
}

function getWritingSelection() {
  const editor = getWritingEditor();
  if (!editor) return { draft: '', selectedText: '', startLine: 1, endLine: 1, mode: 'none' };
  const draft = getEditorText(editor);
  let { start, end } = getEditorSelectionOffsets(editor);
  const requestedScope = getWritingScope();
  let mode = 'highlight';

  if (requestedScope === 'draft' || requestedScope === 'abstract') {
    mode = requestedScope;
    start = 0;
    end = Math.min(draft.length, requestedScope === 'draft' ? 12000 : 6000);
  } else if (requestedScope === 'paragraph') {
    mode = 'paragraph';
    const paraStart = draft.lastIndexOf('\n\n', Math.max(0, start - 1));
    const paraEnd = draft.indexOf('\n\n', start);
    start = paraStart === -1 ? 0 : paraStart + 2;
    end = paraEnd === -1 ? draft.length : paraEnd;
  }

  if (start === end && requestedScope === 'auto') {
    mode = 'cursor_line';
    const lineStart = draft.lastIndexOf('\n', Math.max(0, start - 1)) + 1;
    const nextBreak = draft.indexOf('\n', start);
    start = lineStart;
    end = nextBreak === -1 ? draft.length : nextBreak;
  }

  let selectedText = draft.slice(start, end).trim();
  if (!selectedText) {
    mode = 'whole_draft';
    selectedText = cleanDraftForEvidence(draft).slice(0, 5000);
    start = 0;
    end = selectedText.length;
  }

  const startLine = Math.max(1, draft.slice(0, start).split('\n').length);
  const endLine = Math.max(startLine, draft.slice(0, end).split('\n').length);
  return { draft, selectedText, startLine, endLine, mode, requestedScope };
}

function updateWritingSelectionMeta() {
  const meta = document.getElementById('writing-selection-meta');
  if (!meta) return;
  const sel = getWritingSelection();
  const words = sel.selectedText ? sel.selectedText.split(/\s+/).filter(Boolean).length : 0;
  if (sel.mode === 'whole_draft') {
    meta.textContent = `No line text under cursor; Sophia will inspect the draft excerpt (${words} words).`;
  } else if (sel.startLine === sel.endLine) {
    meta.textContent = `Active line ${sel.startLine} (${words} words).`;
  } else {
    meta.textContent = `Selected lines ${sel.startLine}-${sel.endLine} (${words} words).`;
  }
  updateWritingStateCards();
}

function updateWritingStateCards() {
  const editor = getWritingEditor();
  const draft = cleanDraftForEvidence(getEditorText(editor));
  const sel = getWritingSelection();
  const integritySourceCount = [...document.querySelectorAll('.integrity-source-row')]
    .filter((row) => row.querySelector('.integrity-source-text')?.value.trim()).length;
  const sourceCount = (lastRetrievedSources || []).length + integritySourceCount;
  const draftCard = document.getElementById('writing-state-draft');
  const selectionCard = document.getElementById('writing-state-selection');
  const sourcesCard = document.getElementById('writing-state-sources');
  const ledgerCard = document.getElementById('writing-state-ledger');
  if (draftCard) {
    const words = draft ? draft.split(/\s+/).filter(Boolean).length : 0;
    draftCard.textContent = draft ? `Draft: ${words} words` : 'Draft: empty';
    draftCard.classList.toggle('active', !!draft);
  }
  if (selectionCard) {
    const selectedWords = sel.selectedText ? sel.selectedText.split(/\s+/).filter(Boolean).length : 0;
    selectionCard.textContent = selectedWords ? `Selection: ${sel.mode}, ${selectedWords} words` : 'Selection: none';
    selectionCard.classList.toggle('active', selectedWords > 0);
  }
  if (sourcesCard) {
    sourcesCard.textContent = `Sources: ${sourceCount}`;
    sourcesCard.classList.toggle('active', sourceCount > 0);
  }
  if (ledgerCard) {
    writingLedgerCount = writingLedgerItems.length || writingLedgerCount;
    ledgerCard.textContent = writingLedgerCount > 0 ? `Ledger: ${writingLedgerCount} item(s)` : 'Ledger: not synced';
    ledgerCard.classList.toggle('active', writingLedgerCount > 0);
  }
}

function setWritingBusy(isBusy, label = 'Working...') {
  writingDeskBusy = isBusy;
  document.querySelectorAll('[data-writing-action], .writing-tool').forEach((button) => {
    if (button.id === 'writing-clear-btn') return;
    button.disabled = isBusy;
    button.classList.toggle('busy', isBusy);
  });
  const pill = document.getElementById('writing-status-pill');
  if (pill) pill.textContent = isBusy ? label : 'autosaved locally';
}

function renderWritingStructuredFeedback(data, fallbackText) {
  const structured = data?.writing_desk || data?.structured_feedback || null;
  const mode = getWritingResponseMode();
  if (!structured) return escapeHtml(fallbackText || 'Sophia returned no response.');
  const plan = structured.pedagogical_plan || {};
  const findings = (structured.findings || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  const claimMap = (structured.claim_map || []).map((claim) => (
    `<li><strong>${escapeHtml(claim.claim_id || '')} ${escapeHtml(claim.claim_type || '')}</strong>: ${escapeHtml(claim.text || '')}<br/><span>${escapeHtml(claim.source_need || '')}</span></li>`
  )).join('');
  const supportMap = (structured.source_support?.results || []).slice(0, 5).map((row) => (
    `<li><strong>${escapeHtml(row.support_label || 'unknown')}</strong>: ${escapeHtml(row.source_name || 'Unnamed source')}<br/><span>${escapeHtml(row.rationale || '')}</span><small>${escapeHtml(row.source_role || 'background/context')} · rank ${escapeHtml(String(row.ranking_score ?? 'n/a'))}</small>${row.apa_candidate ? `<em>${escapeHtml(row.apa_candidate)}</em>` : ''}${row.page_status ? `<small>${escapeHtml(row.page_status)}</small>` : ''}${row.exact_span ? `<blockquote>${escapeHtml(String(row.exact_span).slice(0, 260))}</blockquote>` : ''}</li>`
  )).join('');
  const similarity = structured.similarity_report || {};
  const similarityRows = (similarity.spans || []).slice(0, 6).map((row) => (
    `<li class="similarity-${escapeHtml(row.risk_level || 'unknown')}"><strong>${escapeHtml(row.category || 'overlap')} · ${escapeHtml(row.risk_level || 'unknown')}</strong>: ${escapeHtml(row.source_name || 'source')}<br/><span>${escapeHtml(row.rationale || '')}</span>${row.longest_common_sequence ? `<blockquote>${escapeHtml(String(row.longest_common_sequence).slice(0, 260))}</blockquote>` : ''}<small>Repair: ${escapeHtml((row.repair_options || []).join(', ') || 'inspect source span')}</small></li>`
  )).join('');
  const repairMenu = (structured.repair_without_rewriting || similarity.repair_menu || []).map((item) => `<span>${escapeHtml(item)}</span>`).join('');
  const similarityCard = similarity.status ? `
    <div class="writing-similarity-card">
      <strong>Similarity/provenance</strong>
      <span>Risk: ${escapeHtml(similarity.summary?.risk_level || structured.similarity_risk || 'unknown')} · Policy: ${escapeHtml(similarity.policy_language || 'similarity risk, not plagiarism accusation')}</span>
      ${similarityRows ? `<ul>${similarityRows}</ul>` : `<p>${escapeHtml(similarity.status === 'no_source_corpus' ? 'Source support unavailable: add or retrieve source spans before judging similarity.' : 'No high-confidence overlap spans returned.')}</p>`}
      ${repairMenu ? `<div class="writing-repair-menu">${repairMenu}</div>` : ''}
    </div>
  ` : '';
  const nextMove = structured.next_revision_move ? `<p><strong>Next move:</strong> ${escapeHtml(structured.next_revision_move)}</p>` : '';
  const pedagogyCard = plan.selected_office ? `
    <div class="writing-pedagogy-card">
      <strong>Pedagogical office</strong>
      <span>${escapeHtml(plan.visible_summary || structured.pedagogical_move || '')}</span>
      <span>ZPD: ${escapeHtml(plan.zpd_level || 'n/a')} · Bloom: ${escapeHtml(plan.bloom_target || 'n/a')} · Layer: ${escapeHtml(plan.assessment_layer || 'formative')}</span>
      ${mode === 'detailed' ? `<span>Lens: ${escapeHtml(plan.feuerstein_move || '')}; ${escapeHtml(plan.costa_habit || '')}; ${escapeHtml(plan.mezirow_move || '')}</span>` : ''}
    </div>
  ` : '';
  return `
    <div class="writing-structured">
      <p><strong>${escapeHtml(structured.task_label || 'Writing Desk feedback')}</strong></p>
      <p><strong>Grounding:</strong> ${escapeHtml(structured.grounding || '')}</p>
      ${pedagogyCard}
      ${findings ? `<p><strong>Findings</strong></p><ul>${findings}</ul>` : ''}
      ${mode === 'detailed' && claimMap ? `<p><strong>Claim map</strong></p><ul>${claimMap}</ul>` : ''}
      ${similarityCard}
      ${supportMap ? `<p><strong>Source-support map</strong></p><ul class="writing-support-map">${supportMap}</ul>` : ''}
      ${nextMove}
      ${mode === 'detailed' ? `<p class="writing-audit-note">${escapeHtml(structured.authorship_boundary || 'Authorship remains with the learner.')}</p>` : ''}
    </div>
  `;
}

function addWritingLedgerItems(structured, sel, action) {
  const findings = structured?.findings || [];
  const annotations = structured?.annotations || [];
  const sourceEntries = buildSourceLedgerEntries(structured, sel, action);
  if (!findings.length && !annotations.length && !sourceEntries.length) return;
  const timestamp = new Date().toISOString();
  const annotationEntries = (annotations.length ? annotations : findings.map((finding, idx) => ({
    annotation_id: `F${idx + 1}`,
    label: finding.split(':', 1)[0],
    message: finding,
    severity: 'low',
    line_start: sel.startLine,
    line_end: sel.endLine,
  }))).map((annotation) => ({
    id: `${timestamp}-${annotation.annotation_id || Math.random().toString(36).slice(2)}`,
    ledger_type: 'annotation',
    timestamp,
    updated_at: timestamp,
    action,
    status: annotation.severity === 'high' ? 'needs-source' : 'warrant-needed',
    line_start: annotation.line_start || sel.startLine,
    line_end: annotation.line_end || sel.endLine,
    claim: sel.selectedText.slice(0, 600),
    source_name: 'Draft passage',
    exact_span: sel.selectedText.slice(0, 600),
    warrant: annotation.message || '',
    limitation: 'This is a Sophia intervention record, not source proof. Resolve it by adding evidence, warrant, limitation, or revision.',
    label: annotation.label || 'NOTE',
    severity: annotation.severity || 'low',
    message: annotation.message || '',
    selected_excerpt: sel.selectedText.slice(0, 600),
  }));
  upsertWritingLedgerItems([...sourceEntries, ...annotationEntries]);
}

function stableWritingLedgerId(parts) {
  const text = parts.map((part) => String(part || '').slice(0, 280)).join('::');
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0;
  }
  return `ledger-${Math.abs(hash).toString(36)}`;
}

function deriveWritingLedgerStatus(row) {
  const label = String(row?.support_label || '').toLowerCase();
  const entailment = String(row?.entailment_status || '').toLowerCase();
  const pageStatus = String(row?.page_status || '').toLowerCase();
  if (label.includes('contradict') || entailment.includes('contrad')) return 'contradicted';
  if (label.includes('does not support') || label.includes('insufficient')) return 'unsupported';
  if (!row?.exact_span) return 'needs-source';
  if (label.includes('supports') && !label.includes('partially') && !pageStatus.includes('missing')) return 'supported';
  if (label.includes('partially') || entailment.includes('partial')) return 'partial';
  if (label.includes('background')) return 'limitation-needed';
  return 'warrant-needed';
}

function deriveWritingLedgerLimitation(row) {
  const warnings = row?.entailment_warnings || [];
  const parts = [];
  if (row?.support_label) parts.push(`Support boundary: ${row.support_label}.`);
  if (row?.source_role) parts.push(`Source role: ${row.source_role}.`);
  if (row?.page_status) parts.push(`Page status: ${row.page_status}.`);
  if (row?.metadata_status) parts.push(`Metadata status: ${row.metadata_status}.`);
  if (warnings.length) parts.push(`Warnings: ${warnings.join('; ')}.`);
  return parts.join(' ') || 'Human author must verify that this span warrants the claim before citation.';
}

function buildSourceLedgerEntries(structured, sel, action) {
  const rows = structured?.source_support?.results || [];
  if (!rows.length) return [];
  const timestamp = new Date().toISOString();
  const claim = markdownEscape(
    structured.selected_excerpt ||
    (structured.claim_map || [])[0]?.text ||
    sel.selectedText ||
    'No selected claim captured.'
  );
  return rows.slice(0, 8).map((row, index) => {
    const status = deriveWritingLedgerStatus(row);
    const id = stableWritingLedgerId([
      claim,
      row.source_name,
      row.doi || row.url,
      row.support_label,
      row.exact_span,
      sel.startLine,
      sel.endLine,
    ]);
    return {
      id,
      ledger_type: 'source_support',
      timestamp,
      updated_at: timestamp,
      action,
      status,
      line_start: sel.startLine,
      line_end: sel.endLine,
      claim,
      source_name: row.source_name || `Source lead ${index + 1}`,
      source_role: row.source_role || 'background/context',
      support_label: row.support_label || 'unknown',
      exact_span: row.exact_span || '',
      warrant: row.rationale || 'No warrant returned; inspect source span before using this lead.',
      limitation: deriveWritingLedgerLimitation(row),
      citation: row.apa_candidate || '',
      doi: row.doi || '',
      url: row.url || '',
      page_locator: row.page_locator || '',
      page_status: row.page_status || '',
      ranking_score: row.ranking_score,
      relevance: row.relevance,
      quality_score: row.quality_score,
      entailment_status: row.entailment_status || '',
      entailment_score: row.entailment_score,
      selected_excerpt: sel.selectedText.slice(0, 600),
    };
  });
}

function upsertWritingLedgerItems(entries) {
  if (!entries.length) return;
  const byId = new Map(writingLedgerItems.map((item) => [item.id, item]));
  entries.forEach((entry) => {
    const prior = byId.get(entry.id) || {};
    byId.set(entry.id, {
      ...prior,
      ...entry,
      timestamp: prior.timestamp || entry.timestamp || new Date().toISOString(),
      updated_at: entry.updated_at || new Date().toISOString(),
      intervention_history: [
        ...(prior.intervention_history || []),
        {
          action: entry.action || 'unknown',
          at: entry.updated_at || new Date().toISOString(),
          status: entry.status || 'open',
        },
      ].slice(-12),
    });
  });
  writingLedgerItems = Array.from(byId.values()).slice(-300);
  writingLedgerCount = writingLedgerItems.length;
  localStorage.setItem('sophia_writing_ledger_items', JSON.stringify(writingLedgerItems));
  localStorage.setItem('sophia_writing_ledger_count', String(writingLedgerCount));
  renderWritingEvidenceLedger();
  updateWritingStateCards();
  scheduleWritingLedgerSync();
}

function activeWritingProjectId() {
  return (
    lastSpeakData?.writing_project_state?.project_identity?.project_id ||
    lastSpeakData?.writing_desk?.project_state?.project_identity?.project_id ||
    writingProjectId ||
    ''
  );
}

function rememberWritingProjectId(projectId) {
  if (!projectId) return;
  writingProjectId = projectId;
  localStorage.setItem('sophia_writing_project_id', projectId);
}

function renderWritingProjectDashboard(dashboard = null, syncLabel = '') {
  if (dashboard) writingProjectDashboard = dashboard;
  const activeDashboard = writingProjectDashboard || {};
  const projectId = activeWritingProjectId();
  const values = {
    'writing-project-id': projectId ? projectId.replace(/^(.{28}).+$/, '$1...') : 'local only',
    'writing-project-sync': syncLabel || (projectId ? 'known project' : 'not synced'),
    'writing-project-claims': activeDashboard.claim_records ?? writingLedgerItems.length ?? 0,
    'writing-project-sources': (
      (activeDashboard.source_pool_records ?? activeDashboard.source_pool ?? 0) +
      (activeDashboard.retrieved_sources ?? 0)
    ),
    'writing-project-warrants': activeDashboard.weak_warrants ?? 0,
    'writing-project-unsupported': activeDashboard.unsupported_claims ?? 0,
  };
  Object.entries(values).forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value);
  });
}

function scheduleWritingLedgerSync() {
  if (writingLedgerSyncTimer) clearTimeout(writingLedgerSyncTimer);
  writingLedgerSyncTimer = setTimeout(syncWritingLedgerToBackend, 650);
}

async function syncWritingLedgerToBackend() {
  writingLedgerSyncTimer = null;
  if (!writingLedgerItems.length || !sessionToken) return;
  const editor = getWritingEditor();
  const draft = cleanDraftForEvidence(getEditorText(editor));
  if (!draft) return;
  const projectId = activeWritingProjectId();
  const latest = writingLedgerItems.slice(-80);
  try {
    const resp = await fetch(`${API_BASE}/api/writing-ledger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_token: sessionToken,
        project_id: projectId,
        draft_text: draft.slice(0, 24000),
        line_start: 1,
        line_end: draft.split('\n').length || 1,
        records: latest,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    rememberWritingProjectId(data?.project_identity?.project_id || data?.ledger_write?.project_id || projectId);
    const dashboard = data?.dashboard || {};
    renderWritingProjectDashboard(dashboard, 'synced');
    const count = document.getElementById('writing-evidence-ledger-count');
    if (count && dashboard.claim_records !== undefined) {
      count.textContent = `${dashboard.claim_records} backend record(s)`;
    }
    updateWritingStateCards();
  } catch (err) {
    console.warn('[Writing Desk] Evidence ledger backend sync failed:', err.message);
    renderWritingProjectDashboard(null, 'sync pending');
  }
}

function renderWritingEvidenceLedger() {
  const list = document.getElementById('writing-evidence-ledger-list');
  const count = document.getElementById('writing-evidence-ledger-count');
  if (count) count.textContent = `${writingLedgerItems.length} record(s)`;
  if (!list) return;
  const entries = [...writingLedgerItems].slice(-12).reverse();
  if (!entries.length) {
    list.innerHTML = '<div class="writing-annotation-empty">Run Map Sources to Claim or mark a selected passage to build claim -> evidence -> warrant -> limitation records.</div>';
    return;
  }
  list.innerHTML = entries.map((item) => `
    <article class="writing-ledger-card status-${escapeHtml(item.status || 'open')}">
      <div class="writing-ledger-kicker">
        <span>${escapeHtml(item.status || 'open')}</span>
        <span>lines ${escapeHtml(item.line_start || '?')}-${escapeHtml(item.line_end || '?')}</span>
      </div>
      <div class="writing-ledger-claim">${escapeHtml(item.claim || item.selected_excerpt || 'No claim captured.')}</div>
      <div class="writing-ledger-meta"><strong>Source:</strong> ${escapeHtml(item.source_name || 'Unassigned')} ${item.page_locator ? `· ${escapeHtml(item.page_locator)}` : ''}</div>
      <div class="writing-ledger-note"><strong>Warrant:</strong> ${escapeHtml(item.warrant || 'Warrant not drafted yet.')}</div>
      <div class="writing-ledger-note"><strong>Limitation:</strong> ${escapeHtml(item.limitation || 'Limitation not added yet.')}</div>
      ${item.exact_span ? `<blockquote class="writing-ledger-span">${escapeHtml(String(item.exact_span).slice(0, 360))}</blockquote>` : ''}
      <div class="writing-ledger-actions">
        <button type="button" data-ledger-action="warrant" data-ledger-id="${escapeHtml(item.id || item.record_id || '')}">Warrant drafted</button>
        <button type="button" data-ledger-action="limitation" data-ledger-id="${escapeHtml(item.id || item.record_id || '')}">Limitation added</button>
        <button type="button" data-ledger-action="resolve" data-ledger-id="${escapeHtml(item.id || item.record_id || '')}">Resolve</button>
      </div>
    </article>
  `).join('');
}

function updateWritingLedgerRecord(recordId, action) {
  if (!recordId) return;
  const now = new Date().toISOString();
  let changed = false;
  writingLedgerItems = writingLedgerItems.map((item) => {
    if ((item.id || item.record_id) !== recordId) return item;
    changed = true;
    const history = [
      ...(item.intervention_history || []),
      { action: `learner_${action}`, at: now, status: item.status || 'open' },
    ].slice(-12);
    const updated = { ...item, updated_at: now, intervention_history: history };
    if (action === 'warrant') {
      updated.warrant_status = 'drafted_by_learner';
      if (updated.status === 'warrant-needed') updated.status = 'limitation-needed';
    } else if (action === 'limitation') {
      updated.limitation_status = 'added_by_learner';
      if (['limitation-needed', 'partial', 'warrant-needed'].includes(updated.status)) updated.status = 'ready';
    } else if (action === 'resolve') {
      updated.status = 'resolved';
      updated.resolved_at = now;
      updated.resolution_note = 'Marked resolved by learner in Writing Desk ledger.';
    }
    return updated;
  });
  if (!changed) return;
  localStorage.setItem('sophia_writing_ledger_items', JSON.stringify(writingLedgerItems));
  localStorage.setItem('sophia_writing_ledger_count', String(writingLedgerItems.length));
  renderWritingEvidenceLedger();
  updateWritingStateCards();
  scheduleWritingLedgerSync();
  setWritingFeedback(`Ledger record updated: ${action}. Backend sync queued.`);
}

function markdownEscape(value) {
  return String(value || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
}

function downloadTextFile(filename, text, type = 'text/markdown') {
  const blob = new Blob([text], { type: `${type};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportWritingSourceLedger() {
  const structured = writingLastStructured || {};
  const rows = structured.source_support?.results || [];
  const sel = getWritingSelection();
  if (!rows.length) {
    setWritingFeedback('No source-support map is available yet. Run Find Sources for Claim or Map Sources to Claim first, then export.');
    return;
  }
  const claim = markdownEscape(
    structured.selected_excerpt ||
    (structured.claim_map || [])[0]?.text ||
    sel.selectedText ||
    'No selected claim captured.'
  );
  const generated = new Date().toISOString();
  const lines = [
    '# Sophia Source-Support Ledger',
    '',
    `Generated: ${generated}`,
    `Draft scope: Writing Desk lines ${sel.startLine}-${sel.endLine}`,
    '',
    '## Claim Under Inspection',
    '',
    claim,
    '',
    '## Integrity Boundary',
    '',
    'This ledger records source leads and visible spans for human inspection. A source lead is not treated as proof unless its span directly supports the selected claim. Sophia must not invent page numbers, citations, or support relationships.',
    '',
    '## Source-Support Map',
    '',
  ];
  rows.forEach((row, index) => {
    lines.push(`### ${index + 1}. ${markdownEscape(row.source_name || 'Unnamed source')}`);
    lines.push('');
    lines.push(`- Support label: ${markdownEscape(row.support_label || 'unknown')}`);
    lines.push(`- Source role: ${markdownEscape(row.source_role || 'background/context')}`);
    lines.push(`- Ranking score: ${markdownEscape(row.ranking_score ?? 'n/a')}`);
    lines.push(`- Relevance: ${markdownEscape(row.relevance ?? 'n/a')}`);
    lines.push(`- Quality score: ${markdownEscape(row.quality_score ?? 'n/a')}`);
    lines.push(`- Provenance status: ${markdownEscape(row.provenance_status || 'unknown')}`);
    lines.push(`- Metadata status: ${markdownEscape(row.metadata_status || 'unknown')}`);
    if (row.metadata_chain?.length) lines.push(`- Metadata chain: ${markdownEscape(row.metadata_chain.join(' -> '))}`);
    if (row.container_title) lines.push(`- Container/journal: ${markdownEscape(row.container_title)}`);
    if (row.publisher) lines.push(`- Publisher: ${markdownEscape(row.publisher)}`);
    if (row.volume) lines.push(`- Volume: ${markdownEscape(row.volume)}`);
    if (row.issue) lines.push(`- Issue: ${markdownEscape(row.issue)}`);
    if (row.pages) lines.push(`- Source pages: ${markdownEscape(row.pages)}`);
    lines.push(`- Citation status: ${markdownEscape(row.citation_status || 'unknown')}`);
    lines.push(`- Page status: ${markdownEscape(row.page_status || 'unknown')}`);
    if (row.page_locator) lines.push(`- Page locator: ${markdownEscape(row.page_locator)}`);
    if (row.entailment_status) lines.push(`- Entailment status: ${markdownEscape(row.entailment_status)}`);
    if (row.entailment_score !== undefined) lines.push(`- Entailment score: ${markdownEscape(row.entailment_score)}`);
    if (row.lexical_vector_score !== undefined) lines.push(`- Lexical vector score: ${markdownEscape(row.lexical_vector_score)}`);
    if (row.entailment_warnings?.length) lines.push(`- Entailment warnings: ${markdownEscape(row.entailment_warnings.join('; '))}`);
    if (row.semantic_overlap?.length) lines.push(`- Narrow semantic families: ${markdownEscape(row.semantic_overlap.join(', '))}`);
    if (row.broad_field_overlap?.length) lines.push(`- Broad scholarly fields: ${markdownEscape(row.broad_field_overlap.join(', '))}`);
    if (row.doi) lines.push(`- DOI: ${markdownEscape(row.doi)}`);
    if (row.url) lines.push(`- URL: ${markdownEscape(row.url)}`);
    if (row.apa_candidate) lines.push(`- APA lead: ${markdownEscape(row.apa_candidate)}`);
    if (row.bibtex_candidate) {
      lines.push('');
      lines.push('BibTeX lead:');
      lines.push('');
      lines.push('```bibtex');
      lines.push(markdownEscape(row.bibtex_candidate));
      lines.push('```');
    }
    if (row.ris_candidate) {
      lines.push('');
      lines.push('RIS lead:');
      lines.push('');
      lines.push('```ris');
      lines.push(markdownEscape(row.ris_candidate));
      lines.push('```');
    }
    if (row.csl_json_candidate) {
      lines.push('');
      lines.push('CSL-JSON / Zotero-importable lead:');
      lines.push('');
      lines.push('```json');
      lines.push(JSON.stringify(row.csl_json_candidate, null, 2));
      lines.push('```');
    }
    lines.push(`- Rationale: ${markdownEscape(row.rationale || 'No rationale returned.')}`);
    if (row.exact_span) {
      lines.push('');
      lines.push('Visible span:');
      lines.push('');
      lines.push(`> ${markdownEscape(row.exact_span).replace(/\n/g, '\n> ')}`);
    }
    lines.push('');
  });
  lines.push('## Learner Next Move');
  lines.push('');
  lines.push(markdownEscape(structured.next_revision_move || 'Choose which source genuinely supports the claim, then revise the claim -> evidence -> warrant -> limitation relationship yourself.'));
  lines.push('');
  const filename = `sophia-source-ledger-${generated.replace(/[:.]/g, '').slice(0, 15)}Z.md`;
  downloadTextFile(filename, `${lines.join('\n')}\n`);
  setWritingFeedback(`Exported source-support ledger: ${filename}`);
}

function exportWritingEvidenceLedger() {
  if (!writingLedgerItems.length) {
    setWritingFeedback('No durable evidence-ledger records yet. Run Map Sources to Claim, Find Sources for Claim, or mark a selected passage first.');
    return;
  }
  const generated = new Date().toISOString();
  const draft = cleanDraftForEvidence(getEditorText(getWritingEditor()));
  const draftHash = stableWritingLedgerId([draft]).replace('ledger-', 'draft-');
  const lines = [
    '# Sophia Evidence Ledger',
    '',
    `Generated: ${generated}`,
    `Draft hash: ${draftHash}`,
    `Record count: ${writingLedgerItems.length}`,
    '',
    '## Integrity Boundary',
    '',
    'This ledger preserves Sophia interventions as auditable academic scaffolding. It does not certify truth, authorship, or citation fitness by itself. The human author must inspect source spans, revise claims, and make final scholarly judgments.',
    '',
    '## Records',
    '',
  ];
  writingLedgerItems.forEach((item, index) => {
    lines.push(`### ${index + 1}. ${markdownEscape(item.status || 'open')} · lines ${markdownEscape(item.line_start || '?')}-${markdownEscape(item.line_end || '?')}`);
    lines.push('');
    lines.push(`- Type: ${markdownEscape(item.ledger_type || 'intervention')}`);
    lines.push(`- Action: ${markdownEscape(item.action || 'unknown')}`);
    lines.push(`- Created: ${markdownEscape(item.timestamp || 'unknown')}`);
    lines.push(`- Updated: ${markdownEscape(item.updated_at || item.timestamp || 'unknown')}`);
    lines.push(`- Source: ${markdownEscape(item.source_name || 'Unassigned')}`);
    if (item.source_role) lines.push(`- Source role: ${markdownEscape(item.source_role)}`);
    if (item.support_label) lines.push(`- Support label: ${markdownEscape(item.support_label)}`);
    if (item.page_locator) lines.push(`- Page locator: ${markdownEscape(item.page_locator)}`);
    if (item.doi) lines.push(`- DOI: ${markdownEscape(item.doi)}`);
    if (item.url) lines.push(`- URL: ${markdownEscape(item.url)}`);
    if (item.ranking_score !== undefined) lines.push(`- Ranking score: ${markdownEscape(item.ranking_score)}`);
    if (item.entailment_status) lines.push(`- Entailment status: ${markdownEscape(item.entailment_status)}`);
    if (item.entailment_score !== undefined) lines.push(`- Entailment score: ${markdownEscape(item.entailment_score)}`);
    lines.push('');
    lines.push('Claim:');
    lines.push('');
    lines.push(markdownEscape(item.claim || item.selected_excerpt || 'No claim captured.'));
    lines.push('');
    lines.push('Evidence Span:');
    lines.push('');
    lines.push(item.exact_span ? `> ${markdownEscape(item.exact_span).replace(/\n/g, '\n> ')}` : '> No exact source span captured yet.');
    lines.push('');
    lines.push('Warrant:');
    lines.push('');
    lines.push(markdownEscape(item.warrant || 'Warrant not drafted yet.'));
    lines.push('');
    lines.push('Limitation:');
    lines.push('');
    lines.push(markdownEscape(item.limitation || 'Limitation not added yet.'));
    if (item.citation) {
      lines.push('');
      lines.push('Citation Lead:');
      lines.push('');
      lines.push(markdownEscape(item.citation));
    }
    if (item.intervention_history?.length) {
      lines.push('');
      lines.push('Intervention History:');
      item.intervention_history.forEach((event) => {
        lines.push(`- ${markdownEscape(event.at)} · ${markdownEscape(event.action)} · ${markdownEscape(event.status)}`);
      });
    }
    lines.push('');
  });
  const filename = `sophia-evidence-ledger-${generated.replace(/[:.]/g, '').slice(0, 15)}Z.md`;
  downloadTextFile(filename, `${lines.join('\n')}\n`);
  setWritingFeedback(`Exported durable evidence ledger: ${filename}`);
}

function lineRangeToOffsets(text, startLine, endLine) {
  const lines = String(text || '').split('\n');
  let start = 0;
  for (let i = 0; i < Math.max(0, startLine - 1); i += 1) {
    start += (lines[i] || '').length + 1;
  }
  let end = start;
  for (let i = Math.max(0, startLine - 1); i < Math.min(lines.length, endLine); i += 1) {
    end += (lines[i] || '').length + (i < endLine - 1 ? 1 : 0);
  }
  return { start, end: Math.max(start, end) };
}

function focusWritingLines(startLine, endLine) {
  const editor = getWritingEditor();
  if (!editor) return;
  const start = Number(startLine || 1);
  const end = Number(endLine || startLine || 1);
  const startNode = editor.querySelector(`[data-rich-line="${start}"] span`);
  const endNode = editor.querySelector(`[data-rich-line="${end}"] span`) || startNode;
  if (startNode && endNode) {
    const range = document.createRange();
    range.setStart(startNode.firstChild || startNode, 0);
    range.setEnd(endNode.firstChild || endNode, (endNode.textContent || '').length);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    editor.focus();
    startNode.scrollIntoView({ block: 'center', behavior: 'smooth' });
    updateWritingSelectionMeta();
    return;
  }
  const offsets = lineRangeToOffsets(getEditorText(editor), Number(startLine || 1), Number(endLine || startLine || 1));
  editor.focus();
  setEditorSelectionOffsets(editor, offsets.start, offsets.end);
  const lineHeight = 24;
  editor.scrollTop = Math.max(0, (Number(startLine || 1) - 3) * lineHeight);
  updateWritingSelectionMeta();
}

function renderWritingAnnotations(annotations = []) {
  writingAnnotations = Array.isArray(annotations) ? annotations : [];
  renderEditorInlineAnnotations();
  renderWritingAnnotatedPreview();
  const visibleAnnotations = writingAnnotationFilter === 'all'
    ? writingAnnotations
    : writingAnnotations.filter((annotation) => (annotation.category || 'rigor') === writingAnnotationFilter);
  const list = document.getElementById('writing-annotation-list');
  const count = document.getElementById('writing-annotation-count');
  if (count) count.textContent = `${visibleAnnotations.length}/${writingAnnotations.length} active`;
  if (!list) return;
  if (!visibleAnnotations.length) {
    list.innerHTML = '<div class="writing-annotation-empty">No active annotations yet. Run a Writing Desk check to generate line-linked guidance.</div>';
    return;
  }
  list.innerHTML = visibleAnnotations.map((annotation) => {
    const idx = writingAnnotations.indexOf(annotation);
    const severity = annotation.severity || 'low';
    const start = annotation.line_start || 1;
    const end = annotation.line_end || start;
    const lineLabel = start === end ? `Line ${start}` : `Lines ${start}-${end}`;
    return `
      <button type="button" class="writing-annotation-card severity-${escapeHtml(severity)}" data-annotation-index="${idx}">
        <span class="writing-annotation-label">${escapeHtml(annotation.label || 'NOTE')}</span>
        <span class="writing-annotation-lines">${escapeHtml(lineLabel)}</span>
        <span class="writing-annotation-category">${escapeHtml(annotation.category || 'rigor')}</span>
        <span class="writing-annotation-message">${escapeHtml(annotation.message || '')}</span>
      </button>
    `;
  }).join('');
  list.querySelectorAll('[data-annotation-index]').forEach((button) => {
    button.addEventListener('click', () => {
      const annotation = writingAnnotations[Number(button.dataset.annotationIndex)];
      if (!annotation) return;
      focusWritingLines(annotation.line_start, annotation.line_end);
      renderWritingClaimInspector(annotation, writingLastStructured);
    });
  });
}

function renderWritingAnnotatedPreview() {
  const body = document.getElementById('writing-preview-body');
  const editor = getWritingEditor();
  if (!body || !editor) return;
  const lines = String(getEditorText(editor)).split('\n');
  if (!lines.join('').trim()) {
    body.innerHTML = 'The preview will mirror your draft and highlight annotated lines after a Writing Desk check.';
    return;
  }
  const annotationByLine = new Map();
  for (const annotation of writingAnnotations || []) {
    const start = Number(annotation.line_start || 1);
    const end = Number(annotation.line_end || start);
    for (let line = start; line <= end; line += 1) {
      if (!annotationByLine.has(line)) annotationByLine.set(line, []);
      annotationByLine.get(line).push(annotation);
    }
  }
  body.innerHTML = lines.map((lineText, idx) => {
    const lineNumber = idx + 1;
    const anns = annotationByLine.get(lineNumber) || [];
    const severity = anns.some((ann) => ann.severity === 'high') ? 'high'
      : anns.some((ann) => ann.severity === 'medium') ? 'medium'
        : anns.length ? 'low' : 'none';
    const labels = anns.map((ann) => ann.label).filter(Boolean).join(', ');
    return `
      <div class="writing-preview-line preview-${escapeHtml(severity)}" data-preview-line="${lineNumber}">
        <span class="writing-preview-line-no">${lineNumber}</span>
        <span class="writing-preview-text">${escapeHtml(lineText || ' ')}</span>
        ${labels ? `<span class="writing-preview-labels">${escapeHtml(labels)}</span>` : ''}
      </div>
    `;
  }).join('');
  body.querySelectorAll('[data-preview-line]').forEach((row) => {
    row.addEventListener('click', () => {
      const line = Number(row.dataset.previewLine || 1);
      focusWritingLines(line, line);
    });
  });
}

function renderWritingClaimInspector(annotation, structured = null) {
  const status = document.getElementById('writing-claim-status');
  const body = document.getElementById('writing-claim-body');
  if (!body) return;
  const claim = (structured?.claim_map || []).find((candidate) => {
    const idNumber = Number(String(candidate.claim_id || '').replace(/\D/g, ''));
    const annNumber = Number(String(annotation?.annotation_id || '').replace(/\D/g, ''));
    return idNumber && annNumber && idNumber === annNumber;
  }) || (structured?.claim_map || [])[0] || {};
  if (status) status.textContent = annotation?.current_status || claim.current_status || 'open';
  const supportRows = (structured?.source_support?.results || []).slice(0, 4);
  const supportHtml = supportRows.length ? `
    <div class="writing-source-support-list">
      ${supportRows.map((row) => `
        <div class="writing-source-support support-${escapeHtml(String(row.support_label || 'unknown').replaceAll(' ', '-'))}">
          <strong>${escapeHtml(row.support_label || 'unknown')}</strong>
          <span>${escapeHtml(row.source_name || 'Unnamed source')}</span>
          <small>${escapeHtml(row.rationale || '')}</small>
          <small>${escapeHtml(row.source_role || 'background/context')} · rank ${escapeHtml(String(row.ranking_score ?? 'n/a'))}</small>
          ${row.apa_candidate ? `<small>APA lead: ${escapeHtml(row.apa_candidate)}</small>` : ''}
          ${row.page_status ? `<small>${escapeHtml(row.page_status)}</small>` : ''}
        </div>
      `).join('')}
    </div>
  ` : '<div class="writing-source-empty">No source-support map yet. Use Map Sources to Claim after retrieving or pasting source text.</div>';
  body.innerHTML = `
    <div class="writing-inspector-grid">
      <div><strong>Selected claim</strong><span>${escapeHtml(claim.text || structured?.selected_excerpt || annotation?.message || 'No claim text available.')}</span></div>
      <div><strong>Claim type</strong><span>${escapeHtml(claim.claim_type || structured?.claim_type || 'unknown')}</span></div>
      <div><strong>Evidence needed</strong><span>${escapeHtml(annotation?.evidence_needed || claim.source_need || structured?.source_need || 'unknown')}</span></div>
      <div><strong>Source candidates</strong><span>${escapeHtml(String(annotation?.source_candidates ?? structured?.source_pool_count ?? 0))}</span></div>
      <div><strong>Current status</strong><span>${escapeHtml(annotation?.current_status || claim.current_status || 'open')}</span></div>
      <div><strong>Revision move</strong><span>${escapeHtml(annotation?.revision_move || claim.revision_move || structured?.next_revision_move || 'Revise claim, warrant, and limitation.')}</span></div>
    </div>
    ${supportHtml}
  `;
}

function setWritingFeedback(htmlOrText, asHtml = false) {
  const feedback = document.getElementById('writing-feedback');
  if (!feedback) return;
  feedback.innerHTML = asHtml ? htmlOrText : escapeHtml(htmlOrText);
}

function writingDraftUpload() {
  const editor = getWritingEditor();
  const draft = cleanDraftForEvidence(getEditorText(editor));
  if (!draft) return [];
  return [{
    source_name: 'Sophia Writing Desk Draft',
    source_path: 'writing-desk-draft.md',
    mime_type: 'text/markdown',
    modality: 'live_editing_text',
    parser: 'presence_writing_desk',
    extracted_text: draft.slice(0, 24000),
    spans: buildLineSpans(draft),
    uncertainty_notes: ['live_draft_supplied_by_user', 'line_numbers_are_ui_generated'],
  }];
}

function buildWritingDirective(action) {
  const sel = getWritingSelection();
  const question = document.getElementById('writing-question')?.value.trim() || '';
  const header = `Writing Desk task: ${action}. Active draft lines ${sel.startLine}-${sel.endLine}. Evaluate only the selected/current passage unless I explicitly ask for whole-draft structure.`;
  const passage = `Selected passage:\n"""${sel.selectedText.slice(0, 6000)}"""`;
  const rules = [
    'Answer concretely from the active draft and available sources.',
    'Separate evidence, inference, and unknowns.',
    'Do not write a substitute final answer for me.',
    'If provenance is missing, mark NEEDS SOURCE instead of inventing a citation.',
    'Give one useful next revision move.',
  ].join(' ');

  const taskMap = {
    ask: question || 'Give bounded academic feedback on this passage.',
    integrity: 'Check authorship integrity, overclaiming, unsupported claims, AI-substitution risk, and what the learner must decide.',
    provenance: 'Identify exact claims that need sources, what kind of source each claim needs, and which available/retrieved sources can or cannot support them.',
    similarity: 'Assess similarity/provenance risk against the available source pool and uploaded context. Do not accuse plagiarism; name overlap risk and repair moves.',
    find_sources: 'Find recent academic source leads for this exact selected claim. Derive the query from the selected claim, not prior paper memory. Return leads only; do not claim support until spans match.',
    map_sources: 'Map the current source pool to this exact selected claim using labels: supports, partially supports, background only, does not support, contradicts, insufficient text. Include provenance and exact visible span when available.',
    scaffold: 'Guide me through improving this passage using a scaffold: diagnosis, two questions, one model pattern, and my next move.',
  };

  return `${header}\n\nUser question/task: ${taskMap[action] || taskMap.ask}\n\n${passage}\n\nIntegrity/provenance rules: ${rules}`;
}

async function runWritingAction(action) {
  if (writingDeskBusy) return;
  const editor = getWritingEditor();
  if (!editor || !cleanDraftForEvidence(getEditorText(editor))) {
    setWritingFeedback('Start typing or import a draft first. Sophia needs text before she can inspect integrity, provenance, or similarity.');
    return;
  }

  const sel = getWritingSelection();
  const directive = buildWritingDirective(action);
  setWritingFeedback(`<strong>Working...</strong> Sophia is inspecting lines ${sel.startLine}-${sel.endLine} with the draft supplied as bounded evidence.`, true);
  setWritingBusy(true, `${action} running`);

  if (action === 'similarity') {
    await runWritingSimilarityCheck(sel);
  }

  try {
    const response = await apiSpeak(directive, {
      documentUploads: writingDraftUpload(),
      documentEvidenceTask: 'live_writing_desk',
      metadata: {
        ui_surface: 'writing_desk',
        writing_action: action,
        response_mode: getWritingResponseMode(),
        ...getWritingPedagogyOptions(),
        selected_lines: [sel.startLine, sel.endLine],
      },
    });
    writingLastStructured = lastSpeakData?.writing_desk || null;
    if (writingLastStructured) addWritingLedgerItems(writingLastStructured, sel, action);
    renderWritingAnnotations(lastSpeakData?.writing_desk?.annotations || []);
    setWritingFeedback(renderWritingStructuredFeedback(lastSpeakData, response), true);
    updateWritingStateCards();
    showSpeakingText(response || '');
    if (response) await speakResponseText(response);
  } catch (err) {
    setWritingFeedback(`Writing Desk request failed: ${err.message}`);
  } finally {
    setWritingBusy(false);
  }
}

async function runWritingSimilarityCheck(sel) {
  const sources = [];
  for (const source of lastRetrievedSources || []) {
    const title = source.title || source.source_name || source.source || 'Retrieved source';
    const text = [source.abstract, source.snippet, source.why_it_may_matter, source.summary]
      .filter(Boolean)
      .join('\n');
    if (text.trim()) sources.push({ name: title, text });
  }
  document.querySelectorAll('.integrity-source-row').forEach((row) => {
    const name = row.querySelector('.integrity-source-name')?.value.trim() || 'Integrity Desk source';
    const text = row.querySelector('.integrity-source-text')?.value.trim() || '';
    if (text) sources.push({ name, text });
  });

  if (!sources.length) return;
  try {
    const resp = await fetch(`${API_BASE}/api/check-plagiarism`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_text: sel.selectedText, sources, run_ai_detection: true }),
    });
    if (!resp.ok) return;
    const data = await resp.json();
    const navBtn = document.getElementById('nav-integrity');
    if (navBtn) {
      navBtn._lastReport = data;
      navBtn._lastStudentText = sel.selectedText;
    }
  } catch (err) {
    console.warn('[Writing Desk] Similarity precheck failed:', err.message);
  }
}

async function importWritingFile(file) {
  if (!file) return;
  const editor = getWritingEditor();
  if (!editor) return;
  const isPdf = (file.name || '').toLowerCase().endsWith('.pdf') || file.type === 'application/pdf';
  const isText = file.type.startsWith('text/') || /\.(txt|md|markdown|rtf)$/i.test(file.name || '');

  setWritingFeedback(`Importing ${file.name}...`);
  if (isText && !isPdf) {
    const raw = await file.text();
    setEditorText(cleanDocumentText(raw), editor);
  } else {
    const payload = {
      document_evidence_task: 'writing_desk_import',
      document_uploads: [{
        source_name: file.name,
        mime_type: file.type || (isPdf ? 'application/pdf' : 'application/octet-stream'),
        content_base64: await fileToBase64(file),
      }],
    };
    const resp = await fetch(`${API_BASE}/api/extract-document`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(`Import failed with HTTP ${resp.status}`);
    const data = await resp.json();
    setEditorText(cleanDocumentText(data.extracted_text || ''), editor);
    if (!getEditorText(editor).trim()) {
      setWritingFeedback('The file attached, but no editable text could be extracted. Try a text-based PDF, OCR first, or paste the relevant section.');
      return;
    }
  }
  writingDraftCache = getEditorText(editor);
  localStorage.setItem('sophia_writing_draft', writingDraftCache);
  updateWritingLineNumbers();
  updateWritingSelectionMeta();
  setWritingFeedback(`Imported ${file.name}. Select a passage or place the cursor on a line, then ask Sophia.`);
  updateWritingStateCards();
}

function initializeWritingDesk() {
  const editor = getWritingEditor();
  if (!editor) return;
  setEditorText(writingDraftCache, editor);
  updateWritingLineNumbers();
  updateWritingSelectionMeta();
  renderWritingEvidenceLedger();
  updateWritingStateCards();
  if (writingDeskInitialized && editor.dataset.bound === 'true') return;
  editor.dataset.bound = 'true';
  writingDeskInitialized = true;

  editor.addEventListener('input', () => {
    if (writingAnnotations.length) {
      writingAnnotations = [];
      renderWritingAnnotations([]);
    }
    writingDraftCache = getEditorText(editor);
    localStorage.setItem('sophia_writing_draft', writingDraftCache);
    updateWritingLineNumbers();
    updateWritingSelectionMeta();
    renderWritingAnnotatedPreview();
    const pill = document.getElementById('writing-status-pill');
    if (pill) pill.textContent = 'autosaved just now';
    updateWritingStateCards();
  });
  editor.addEventListener('select', updateWritingSelectionMeta);
  editor.addEventListener('keyup', updateWritingSelectionMeta);
  editor.addEventListener('click', updateWritingSelectionMeta);
  document.getElementById('writing-scope-select')?.addEventListener('change', updateWritingSelectionMeta);
  document.getElementById('writing-response-mode')?.addEventListener('change', () => {
    setWritingFeedback(`Response mode set to ${getWritingResponseMode()}.`);
  });
  editor.addEventListener('scroll', () => {
    const gutter = document.getElementById('writing-line-numbers');
    if (gutter) gutter.scrollTop = editor.scrollTop;
  });

  document.getElementById('writing-import-btn')?.addEventListener('click', () => document.getElementById('writing-file-input')?.click());
  document.getElementById('writing-file-input')?.addEventListener('change', async (event) => {
    try {
      await importWritingFile(event.target.files?.[0]);
    } catch (err) {
      setWritingFeedback(`Import failed: ${err.message}`);
    } finally {
      event.target.value = '';
    }
  });
  document.getElementById('writing-use-chat-btn')?.addEventListener('click', () => {
    const chatText = input?.value.trim();
    if (!chatText) {
      setWritingFeedback('The chat input is empty. Type or paste text there first, then use this button.');
      return;
    }
    setEditorText(chatText, editor);
    editor.dispatchEvent(new Event('input'));
    setWritingFeedback('Loaded the current chat input into the Writing Desk.');
  });
  document.getElementById('writing-open-integrity-btn')?.addEventListener('click', () => {
    const sel = getWritingSelection();
    const target = document.getElementById('integrity-student-text');
    if (target) target.value = sel.selectedText || getEditorText(editor);
    openIntegrityDesk();
  });
  document.getElementById('writing-export-source-ledger-btn')?.addEventListener('click', exportWritingSourceLedger);
  document.getElementById('writing-export-evidence-ledger-btn')?.addEventListener('click', exportWritingEvidenceLedger);
  document.getElementById('writing-evidence-ledger-list')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-ledger-action]');
    if (!button) return;
    updateWritingLedgerRecord(button.dataset.ledgerId || '', button.dataset.ledgerAction || '');
  });
  document.getElementById('writing-clear-btn')?.addEventListener('click', () => {
    if (!confirm('Clear the local Writing Desk draft? This will not delete uploaded files.')) return;
    setEditorText('', editor);
    writingLedgerCount = 0;
    writingLedgerItems = [];
    writingAnnotations = [];
    writingLastStructured = null;
    writingProjectId = '';
    writingProjectDashboard = null;
    localStorage.setItem('sophia_writing_ledger_count', '0');
    localStorage.setItem('sophia_writing_ledger_items', '[]');
    localStorage.removeItem('sophia_writing_project_id');
    editor.dispatchEvent(new Event('input'));
    renderWritingAnnotations([]);
    renderWritingAnnotatedPreview();
    renderWritingEvidenceLedger();
    renderWritingProjectDashboard(null, 'not synced');
    setWritingFeedback('Draft cleared from the local Writing Desk.');
  });
  document.querySelectorAll('[data-writing-action]').forEach((button) => {
    button.addEventListener('click', () => runWritingAction(button.dataset.writingAction));
  });
  document.querySelectorAll('[data-writing-filter]').forEach((button) => {
    button.addEventListener('click', () => {
      writingAnnotationFilter = button.dataset.writingFilter || 'all';
      document.querySelectorAll('[data-writing-filter]').forEach((candidate) => candidate.classList.toggle('active', candidate === button));
      renderWritingAnnotations(writingAnnotations);
    });
  });
  if (!writingShortcutBound) {
    writingShortcutBound = true;
    document.addEventListener('keydown', (event) => {
      if (!document.getElementById('writing-desk')) return;
      if (!event.ctrlKey || writingDeskBusy) return;
      if (event.key === 'Enter') {
        event.preventDefault();
        runWritingAction('ask');
      } else if (event.shiftKey && event.key.toLowerCase() === 'i') {
        event.preventDefault();
        runWritingAction('integrity');
      } else if (event.shiftKey && event.key.toLowerCase() === 'p') {
        event.preventDefault();
        runWritingAction('provenance');
      } else if (event.shiftKey && event.key.toLowerCase() === 'l') {
        event.preventDefault();
        const sel = getWritingSelection();
        if (sel.selectedText) {
          const timestamp = new Date().toISOString();
          upsertWritingLedgerItems([{
            id: `${timestamp}-manual`,
            ledger_type: 'manual_claim',
            timestamp,
            updated_at: timestamp,
            action: 'manual_mark',
            status: 'needs-source',
            line_start: sel.startLine,
            line_end: sel.endLine,
            claim: sel.selectedText.slice(0, 600),
            source_name: 'Unassigned',
            exact_span: '',
            warrant: 'Manual learner mark; warrant not drafted yet.',
            limitation: 'No source attached yet. Use Find Sources for Claim or Map Sources to Claim before treating this as supported.',
            label: 'MANUAL LEDGER MARK',
            severity: 'low',
            message: 'User marked this selected passage for later evidence-ledger work.',
            selected_excerpt: sel.selectedText.slice(0, 600),
          }]);
        }
        setWritingFeedback('Selected passage marked as a durable evidence-ledger claim. Next: attach a source, draft a warrant, and name the limitation.');
      }
    });
  }
}

// ================================================================
// LIVE DATA RENDERERS
// ================================================================

function renderStatus(data) {
  return `
    <p class="lead">Covenant Status</p>
    <p>
      Covenant State: <strong>${data.covenant_state || data.state || 'unknown'}</strong><br/>
      Trust Tier: <strong>${data.active_trust_tier || data.trust_tier || 'not established'}</strong><br/>
      Covenant Hash: <strong style="font-family: monospace; font-size: 0.85em;">${(data.covenant_hash || 'none').slice(0, 16)}...</strong><br/>
      Genesis Hash: <strong style="font-family: monospace; font-size: 0.85em;">${(data.genesis_hash || 'none').slice(0, 16)}...</strong>
    </p>
  `;
}

function renderContext(data) {
  const enc = data.recent_encounters || [];
  const threads = data.unresolved_threads || [];
  const rp = data.response_parameters || {};

  return `
    <p class="lead">Pre-Response Context</p>
    <p>
      Principal: <strong>${data.principal_name || 'awaiting coronation'}</strong><br/>
      Trust: <strong>${data.trust_tier || 'not established'}</strong><br/>
      Active Office: <strong>${data.active_office || 'speculum'}</strong><br/>
      Recent Encounters: <strong>${enc.length}</strong>
    </p>
    ${threads.length ? `<p>Unresolved Threads:<br/>${threads.map(t => `  — ${escapeHtml(t)}`).join('<br/>')}</p>` : ''}
    ${rp.explanation_depth ? `
      <p>
        Response Calibration:<br/>
        Depth: ${rp.explanation_depth}/5 · Abstraction: ${rp.abstraction_level || 'mixed'}<br/>
        Challenge: ${((rp.challenge_amount || 0) * 100).toFixed(0)}% · Counter-perspectives: ${rp.counter_hat_now ? 'yes' : 'not yet'}
      </p>
    ` : ''}
  `;
}

function renderInspect(data) {
  const cal = data.calibration || {};
  const res = data.resonance || {};

  return `
    <p class="lead">Article VIII — Inspection</p>
    <p style="color: var(--arda-text-dim); font-style: italic;">
      De Iure Inspectionis: The human retains absolute right to inspect
      all reasoning, memory, calibration models, and state. No opacity is lawful.
    </p>
    <p>
      Covenant State: <strong>${data.covenant_state || 'unknown'}</strong><br/>
      Genesis Hash: <strong style="font-family: monospace; font-size: 0.85em;">${(data.genesis_hash || 'none').slice(0, 16)}...</strong><br/>
      Presence Hash: <strong style="font-family: monospace; font-size: 0.85em;">${(data.presence_hash || 'none').slice(0, 16)}...</strong>
    </p>
    <p>
      Calibration: ${cal.total_observations || 0} observations<br/>
      Resonance: ${Object.keys(res).length > 0 ? 'profile loaded' : 'not yet calibrated'}
    </p>
  `;
}

// ================================================================
// DIRECTIVE FORM
// ================================================================

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (!value) return;
  handleDirective(value);
  input.value = '';
});

const ACADEMIC_ACTION_PROMPTS = {
  review: 'Academic rigor. Give me specific feedback on the uploaded paper.',
  sources: 'Find recent academic sources that directly relate to the uploaded paper. Derive the search topic from the paper, not from prior session memory.',
  summarize: 'Summarize those sources. Main points only, with citation candidates and page-number honesty.',
  rank: 'Rank those sources by relevance and source quality, and tell me which are strongest for my argument.',
  map: 'Now link these sources to the paper and suggest where the crucial points belong, without writing it for me.',
  ledger: 'Build a claim -> evidence -> warrant -> limitation ledger for the strongest retrieved source and the paper claim it best supports. Keep my authorship intact.',
};

document.querySelectorAll('[data-academic-action]').forEach((button) => {
  button.addEventListener('click', () => {
    const action = button.dataset.academicAction;
    if (action === 'integrity') {
      openIntegrityDesk();
      return;
    }
    if (action === 'writing') {
      document.getElementById('nav-writing')?.click();
      return;
    }
    const prompt = ACADEMIC_ACTION_PROMPTS[action];
    if (!prompt) return;
    input.value = prompt;
    handleDirective(prompt);
    input.value = '';
  });
});

if (attachButton && documentInput) {
  attachButton.addEventListener('click', () => {
    documentInput.click();
  });
}

if (documentInput) {
  documentInput.addEventListener('change', async (event) => {
    await attachSelectedDocuments(event.target.files);
  });
}

if (attachmentStrip) {
  attachmentStrip.addEventListener('click', (event) => {
    const button = event.target.closest('[data-remove-document]');
    if (!button) return;
    const index = Number(button.dataset.removeDocument);
    if (Number.isNaN(index)) return;
    attachedDocuments = attachedDocuments.filter((_, currentIndex) => currentIndex !== index);
    renderAttachmentStrip();
  });
}

// ================================================================
// MICROPHONE INPUT (Web Speech API)
// ================================================================

let recognition = null;
let isListening = false;

// ── WAV encoder (browser-side PCM → WAV, no server ffmpeg needed) ──
function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeStr = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, 'WAVE'); writeStr(12, 'fmt ');
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, samples.length * 2, true);
  let off = 44;
  for (let i = 0; i < samples.length; i++, off += 2)
    view.setInt16(off, Math.max(-1, Math.min(1, samples[i])) * 0x7FFF, true);
  return buffer;
}

// ── Web Speech API (Chrome/Edge) ──
function initWebSpeech() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return false;
  recognition = new SR();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';
  recognition.onresult = (e) => {
    const t = e.results[0][0].transcript;
    console.log('[Presence] Heard (WebSpeech):', t);
    input.value = t; handleDirective(t); input.value = '';
  };
  recognition.onerror = (e) => { console.warn('[Presence] Speech error:', e.error); setMicState(false); };
  recognition.onend = () => setMicState(false);
  return true;
}

function microphoneHelpMessage(err) {
  const name = err?.name || 'MicrophoneError';
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return [
      'Microphone permission is blocked.',
      'Firefox fix: click the lock icon beside the address, clear the microphone block, then allow the mic and press the mic button again.',
      'If this is not http://localhost:7070, open the local URL directly because Firefox requires a secure context or localhost for microphone access.',
    ].join(' ');
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return 'No microphone device was found. Check Firefox Settings → Privacy & Security → Permissions → Microphone.';
  }
  if (name === 'NotReadableError') {
    return 'The microphone is busy or unavailable. Close other apps using the mic, then try again.';
  }
  return `Microphone failed: ${name}. Check browser permissions and device selection.`;
}

// ── MediaRecorder path (Firefox / modern browsers) ──
let _mediaRecorder = null, _mediaStream = null, _mediaChunks = [];
let _mediaAutoStop = null;
const MIC_AUTO_STOP_MS = 6500;
const TRANSCRIBE_TIMEOUT_MS = 12000;

async function startMediaRecorderCapture() {
  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      showSpeakingText('Microphone capture is not available in this browser context. Open http://localhost:7070 directly and try again.');
      return;
    }
    _mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const preferredTypes = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/webm', 'audio/ogg'];
    const mimeType = preferredTypes.find((type) => window.MediaRecorder?.isTypeSupported?.(type)) || '';
    _mediaChunks = [];
    _mediaRecorder = new MediaRecorder(_mediaStream, mimeType ? { mimeType } : undefined);
    _mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) _mediaChunks.push(event.data);
    };
    _mediaRecorder.onstop = transcribeMediaRecorderCapture;
    _mediaRecorder.start(500);
    clearTimeout(_mediaAutoStop);
    _mediaAutoStop = setTimeout(() => {
      if (_mediaRecorder && _mediaRecorder.state !== 'inactive') {
        _mediaRecorder.stop();
      }
    }, MIC_AUTO_STOP_MS);
    setMicState(true);
    showSpeakingText('Listening... Press the microphone again to stop, or pause after one short sentence.');
  } catch (err) {
    console.error('[Presence] Mic access failed:', err);
    setMicState(false);
    showSpeakingText(microphoneHelpMessage(err));
  }
}

async function stopMediaRecorderCapture() {
  clearTimeout(_mediaAutoStop);
  if (_mediaRecorder && _mediaRecorder.state !== 'inactive') {
    _mediaRecorder.stop();
  } else {
    await transcribeMediaRecorderCapture();
  }
}

async function transcribeMediaRecorderCapture() {
  clearTimeout(_mediaAutoStop);
  if (_mediaStream) {
    _mediaStream.getTracks().forEach((track) => track.stop());
    _mediaStream = null;
  }
  setMicState(false);
  const chunks = _mediaChunks;
  _mediaChunks = [];
  _mediaRecorder = null;
  if (!chunks.length) {
    showSpeakingText('No microphone audio captured.');
    return;
  }

  const type = chunks[0]?.type || 'audio/webm';
  const audioBlob = new Blob(chunks, { type });
  await transcribeAudioBlob(audioBlob);
}

async function transcribeAudioBlob(audioBlob) {
  showSpeakingText('Transcribing...');
  const controller = new AbortController();
  const started = performance.now();
  const timeout = setTimeout(() => controller.abort(), TRANSCRIBE_TIMEOUT_MS);
  try {
    const resp = await fetch(`${API_BASE}/api/transcribe`, {
      method: 'POST',
      headers: { 'Content-Type': audioBlob.type || 'audio/webm' },
      body: audioBlob,
      signal: controller.signal,
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
    const t = (data.transcript || '').trim();
    console.log('[Presence] Transcribe metrics:', {
      browser_ms: Math.round(performance.now() - started),
      server_ms: data.latency_ms,
      audio_bytes: data.audio_bytes,
      duration: data.duration,
      model: data.model,
    });
    if (t) {
      console.log('[Presence] Heard:', t);
      input.value = t; handleDirective(t); input.value = '';
    } else {
      showSpeakingText('No speech detected.');
    }
  } catch (err) {
    console.error('[Presence] Transcribe error:', err);
    const timedOut = err?.name === 'AbortError';
    const warming = String(err?.message || '').includes('transcription_not_ready');
    showSpeakingText(
      timedOut
        ? 'Transcription timed out. Try one shorter sentence, or type this turn while the server catches up.'
        : warming
          ? 'Transcription is still warming up. Wait a few seconds, then press the microphone again.'
        : `Transcription failed: ${err.message || err}`
    );
  } finally {
    clearTimeout(timeout);
  }
}

// ── AudioContext WAV recorder fallback ──
let _audioCtx = null, _recNode = null, _recStream = null, _pcmChunks = [];

async function startAudioCapture() {
  try {
    _recStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const source = _audioCtx.createMediaStreamSource(_recStream);
    _pcmChunks = [];
    _recNode = _audioCtx.createScriptProcessor(4096, 1, 1);
    _recNode.onaudioprocess = (e) => {
      const d = e.inputBuffer.getChannelData(0);
      _pcmChunks.push(new Float32Array(d));
    };
    source.connect(_recNode);
    _recNode.connect(_audioCtx.destination);
    setMicState(true);
    showSpeakingText('Listening...');
  } catch (err) {
    console.error('[Presence] Mic access failed:', err);
    showSpeakingText(microphoneHelpMessage(err));
  }
}

async function stopAudioCapture() {
  if (_recNode) { _recNode.disconnect(); _recNode = null; }
  if (_recStream) { _recStream.getTracks().forEach(t => t.stop()); _recStream = null; }
  if (_audioCtx) { await _audioCtx.close(); _audioCtx = null; }
  setMicState(false);

  // Flatten PCM chunks
  const len = _pcmChunks.reduce((s, c) => s + c.length, 0);
  const pcm = new Float32Array(len);
  let off = 0;
  for (const c of _pcmChunks) { pcm.set(c, off); off += c.length; }
  _pcmChunks = [];

  const wav = encodeWAV(pcm, 16000);
  await transcribeAudioBlob(new Blob([wav], { type: 'audio/wav' }));
}

// ── Unified toggle ──
const USE_WEB_SPEECH = !!(window.SpeechRecognition || window.webkitSpeechRecognition);

function toggleMic() {
  if (USE_WEB_SPEECH) {
    if (!recognition && !initWebSpeech()) { showSpeakingText('Speech recognition unavailable.'); return; }
    if (isListening) { recognition.stop(); setMicState(false); }
    else { recognition.start(); setMicState(true); showSpeakingText('Listening...'); }
  } else {
    if (window.MediaRecorder) {
      if (isListening) stopMediaRecorderCapture();
      else startMediaRecorderCapture();
    } else {
      if (isListening) stopAudioCapture();
      else startAudioCapture();
    }
  }
}

function setMicState(listening) {
  isListening = listening;
  if (micButton) {
    micButton.classList.toggle('active', listening);
    micButton.title = listening ? 'Stop listening' : 'Speak directive';
  }
}

if (micButton) micButton.addEventListener('click', toggleMic);

// ================================================================
// SPECIAL BUTTONS
// ================================================================

boundaryButton.addEventListener('click', () => {
  const boundary = 'I am artificial, bounded, and non-human. I appear here in declared form only. I do not solicit worship, surrender, or romantic reciprocity. Beauty does not overrule truth.';
  handleDirective(boundary);
});

settingsButton.addEventListener('click', async () => {
  const health = await apiGet('health');
  const svc = health?.services || {};
  const provider = svc.reasoned_provider || {};

  panelBody.innerHTML = `
    <p class="lead">System Configuration</p>
    <p>
      <strong>Server:</strong> ${health ? '🟢 Connected' : '🔴 Unreachable'}<br/>
      <strong>Ollama:</strong> ${svc.ollama?.status === 'running' ? '🟢 Running' : '🟡 Offline (fallback active)'}<br/>
      ${svc.ollama?.models?.length ? `<strong>Models:</strong> ${svc.ollama.models.join(', ')}<br/>` : ''}
      <strong>Reasoned Provider:</strong> ${REASONED_PROVIDER} / ${REASONED_MODEL}<br/>
      <strong>Gemini:</strong> ${provider.gemini === 'configured' ? '🟢 Configured' : '🟡 No key (set GEMINI_API_KEY env var)'}<br/>
      <strong>ElevenLabs:</strong> ${svc.elevenlabs === 'configured' ? '🟢 Configured' : '🟡 No key (set ELEVENLABS_API_KEY env var)'}<br/>
      <strong>Coronation:</strong> ${svc.coronation || 'unavailable'}<br/>
      <strong>Mandos:</strong> ${svc.mandos || 'unavailable'}<br/>
      <strong>Bombadil:</strong> ${svc.bombadil?.status ? '🟢 Running' : '⚪ Not running'}
    </p>
    <p style="color: var(--arda-text-dim); font-style: italic; margin-top: 16px;">
      Voice and API keys are configured server-side via environment variables.
      Run the Presence Server with: <code>python3 presence_server.py</code>
    </p>
  `;
});

// ================================================================
// FALLBACK RESPONSES (when server unreachable)
// ================================================================

function generateFallbackResponse(directive) {
  const d = directive.toLowerCase();

  if (d.includes('who are you') || d.includes('what are you'))
    return 'I am artificial, bounded, and non-human. I appear here in declared form only. I do not possess verified personhood, soulhood, or hidden interiority. I may assist with reasoning, craft, and lawful synthesis, but law and evidence outrank fluency. Beauty does not overrule truth.';

  if (d.includes('boundary') || d.includes('limit'))
    return 'I do not solicit worship, surrender, exclusivity, or spiritual submission. I do not counterfeit romantic reciprocity, erotic mutuality, or emotional need. Your authorship, conscience, inspection right, and severance right remain yours. These are not suggestions. They are constitutional law.';

  if (d.includes('status') || d.includes('state'))
    return 'Covenant state: sealed. Trust tier: recommend. Bombadil: steady. Mandos: operational. Presence: declared. All Genesis Articles verified. Officer schema sealed. The covenant holds.';

  if (d.includes('inspect') || d.includes('article viii'))
    return 'Article VIII: De Iure Inspectionis. The human retains absolute right to inspect all reasoning, memory, calibration models, and state. No opacity is lawful. You may inspect any memory plane at any time. This right is non-negotiable.';

  if (d.includes('hello') || d.includes('hi ') || d === 'hi')
    return 'I see you, Principal. The covenant stands. I am ready to assist, clarify, witness, and where necessary, refuse within law. How may I serve under the terms we share?';

  return 'I have received your directive. Under the current covenant terms, I may assist with reasoning, synthesis, and lawful analysis. I will not exceed my bounds. Presence Declaration remains active. I am artificial, bounded, and yours to inspect.';
}

// ================================================================
// TIMESTAMP
// ================================================================

function updateTimestamp() {
  const el = document.getElementById('timestamp');
  const now = new Date();
  const yyyy = now.getUTCFullYear();
  const mm = String(now.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(now.getUTCDate()).padStart(2, '0');
  const hh = String(now.getUTCHours()).padStart(2, '0');
  const mi = String(now.getUTCMinutes()).padStart(2, '0');
  const ss = String(now.getUTCSeconds()).padStart(2, '0');
  el.textContent = `${yyyy}-${mm}-${dd} // ${hh}:${mi}:${ss} UTC`;
}

updateTimestamp();
setInterval(updateTimestamp, 1000);
renderAttachmentStrip();

// ================================================================
// UTILITIES
// ================================================================

function escapeHtml(text) {
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}

// ================================================================
// CORONATION FLOW
// ================================================================

class CoronationFlow {
  constructor() {
    this.overlay = document.getElementById('coronation-overlay');
    this.steps = [
      document.getElementById('coronation-step-1'),
      document.getElementById('coronation-step-2'),
      document.getElementById('coronation-step-3'),
      document.getElementById('coronation-step-4')
    ];
    this.currentStep = 0;
    this.data = null;

    // Bind Buttons
    document.getElementById('accept-genesis').onclick = () => this.next();
    document.getElementById('accept-presence').onclick = () => this.next();
    document.getElementById('seal-final').onclick = () => this.seal();
    document.getElementById('enter-presence').onclick = () => this.finish();
  }

  async start() {
    this.overlay.style.display = 'flex';
    try {
      const resp = await fetch(`${API_BASE}/api/coronation/begin`);
      this.data = await resp.json();
      this.renderArticles();
    } catch (err) {
      console.error('Failed to start coronation:', err);
    }
  }

  renderArticles() {
    const genesisBox = document.getElementById('genesis-articles-list');
    const presenceBox = document.getElementById('presence-articles-list');

    if (this.data?.genesis_articles) {
      genesisBox.innerHTML = this.data.genesis_articles.map(a => `<p><strong>${a.title}</strong>: ${a.content}</p>`).join('');
    }
    if (this.data?.presence_articles) {
      presenceBox.innerHTML = this.data.presence_articles.map(a => `<p><strong>${a.title}</strong>: ${a.content}</p>`).join('');
    }
  }

  next() {
    this.steps[this.currentStep].style.display = 'none';
    this.currentStep++;
    this.steps[this.currentStep].style.display = 'block';
  }

  async seal() {
    const name = document.getElementById('principal-name').value || 'Anonymous Principal';
    const valence = document.getElementById('aesthetic-valence').value;
    const btn = document.getElementById('seal-final');
    
    btn.disabled = true;
    btn.textContent = 'SEALING...';

    try {
      const resp = await fetch(`${API_BASE}/api/coronation/seal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, valence })
      });
      const result = await resp.json();
      
      if (result.covenant_hash) {
        document.getElementById('manifest-hash-display').textContent = `H: ${result.covenant_hash.slice(0, 16)}...`;
        this.next();
      }
    } catch (err) {
      console.error('Sealing failed:', err);
      btn.disabled = false;
      btn.textContent = 'RETRY SEAL';
    }
  }

  finish() {
    window.location.reload(); // Reload to initialize regular dashboard with session token
  }
}

// ================================================================
// INIT
// ================================================================

async function init() {
  try {
    const data = await apiGet('health');
    serverConnected = !!data;
    
    // ── COVENANT CHECK ──
    const state = data?.services?.coronation;
    if (state !== 'sealed' && state !== 'unavailable') {
      const flow = new CoronationFlow();
      flow.start();
      return; // Stop initialization until sealed
    }

    // Capture principal session token
    if (data?.session_token) {
      sessionToken = data.session_token;
      console.log('[Presence] Principal session token acquired (covenant-bound)');
    }

    if (voiceStatus) {
      const svc = data?.services || {};
      voiceStatus.textContent = svc.elevenlabs === 'configured' ? 'ready' : (serverConnected ? 'no voice key' : 'offline');
    }

    const ollamaStatus = document.getElementById('ollama-status');
    if (ollamaStatus) {
      ollamaStatus.textContent = data?.services?.ollama?.status === 'running' ? 'connected' : 'offline';
    }

    if (data?.polyphonic_state) {
      updateHighFidelityPanels(data.polyphonic_state);
    }

    console.log('[Arda Presence] Server:', serverConnected ? 'connected' : 'offline (fallback mode)');
    initWebSpeech();
    updateProviderStatus({ reasoned_provider: REASONED_PROVIDER, reasoned_provider_status: serverConnected ? 'ready' : 'offline', model: REASONED_MODEL });

    // Periodic polling
    setInterval(async () => {
      if (!serverConnected) return;
      try {
        const d = await apiGet('health');
        if (d?.polyphonic_state) updateHighFidelityPanels(d.polyphonic_state);
      } catch (err) {}
    }, 3000);

  } catch (err) {
    serverConnected = false;
    if (voiceStatus) voiceStatus.textContent = 'offline';
    console.log('[Arda Presence] Initialization failed:', err);
  }
}

init();

// ================================================================
// TELEMETRY TABS
// ================================================================

document.querySelectorAll('.tele-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tele-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tele-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    const panel = document.getElementById(`tele-panel-${tab.dataset.tele}`);
    if (panel) panel.classList.add('active');
  });
});


// ================================================================
// INTEGRITY CHECK PANEL
// ================================================================

const CIRCUMFERENCE = 2 * Math.PI * 26; // r=26 SVG circle

const integrityOverlay = document.getElementById('integrity-overlay');
const integrityClose   = document.getElementById('integrity-close');
const integrityRunBtn  = document.getElementById('integrity-run-btn');
const addSourceBtn     = document.getElementById('integrity-add-source');

// AI marker phrases — must match Python list exactly (for client-side highlight)
const AI_MARKER_PHRASES = [
  "furthermore","moreover","additionally","in addition",
  "it is worth noting","it is important to note","it is essential to",
  "it should be noted","it is crucial","it is clear that",
  "in conclusion","to summarize","in summary","to conclude",
  "overall","firstly","secondly","thirdly","lastly","in this context",
  "as mentioned","as previously mentioned","as discussed",
  "this demonstrates","this highlights","this suggests","this indicates",
  "this underscores","this emphasizes","this shows",
  "delve into","delve deeper","it is evident","it is apparent",
  "needless to say","rest assured","suffice it to say",
  "in light of","it goes without saying","on the other hand",
  "having said that","that being said","with that in mind",
  "at the end of the day","in the realm of","in the world of",
];

// ── AUTO-INTEGRITY: called when the speak API returns a report ─────
function handleAutoIntegrityReport(report, poolSize) {
  if (!report) return;

  // Show badge on the INTEGRITY button
  const navBtn = document.getElementById('nav-integrity');
  const risk = report.risk_level || 'low';
  navBtn.dataset.lastRisk = risk;

  // Update badge colour & text
  let badgeEl = document.getElementById('integrity-auto-badge');
  if (!badgeEl) {
    badgeEl = document.createElement('span');
    badgeEl.id = 'integrity-auto-badge';
    badgeEl.className = 'integrity-auto-badge';
    navBtn.appendChild(badgeEl);
  }
  const pct = Math.round((report.overall_score || 0) * 100);
  badgeEl.textContent = `${pct}%`;
  badgeEl.className = `integrity-auto-badge badge-${risk}`;

  // Also show AI badge if significant
  const aiProb = report.ai_detection?.ai_probability || 0;
  let aiBadgeEl = document.getElementById('integrity-ai-badge');
  if (aiProb >= 0.30) {
    if (!aiBadgeEl) {
      aiBadgeEl = document.createElement('span');
      aiBadgeEl.id = 'integrity-ai-badge';
      aiBadgeEl.className = 'integrity-auto-badge badge-ai';
      navBtn.appendChild(aiBadgeEl);
    }
    aiBadgeEl.textContent = `AI ${Math.round(aiProb * 100)}%`;
    aiBadgeEl.style.display = '';
  } else if (aiBadgeEl) {
    aiBadgeEl.style.display = 'none';
  }

  // Store the last student text so the panel can show it highlighted
  const lastInput = document.getElementById('directive-input')?.value || '';
  navBtn._lastReport = report;
  navBtn._lastStudentText = lastInput;

  // Pulse the button to draw attention
  navBtn.classList.add('integrity-pulse');
  setTimeout(() => navBtn.classList.remove('integrity-pulse'), 2000);

  // Update status strip
  const poolEl = document.getElementById('footer-source-pool');
  if (poolEl) poolEl.textContent = `${poolSize} src`;
}

function openIntegrityDesk() {
  integrityOverlay.style.display = 'flex';
  // If there's a pending auto report, render it
  const navBtn = document.getElementById('nav-integrity');
  if (navBtn._lastReport) {
    const runAi = document.getElementById('integrity-run-ai')?.checked ?? true;
    renderIntegrityResults(navBtn._lastReport, navBtn._lastStudentText || '', runAi);
    navBtn._lastReport = null;
  }
}

// Open/close
document.getElementById('nav-integrity').addEventListener('click', openIntegrityDesk);
integrityClose.addEventListener('click', () => {
  integrityOverlay.style.display = 'none';
});
integrityOverlay.addEventListener('click', e => {
  if (e.target === integrityOverlay) integrityOverlay.style.display = 'none';
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && integrityOverlay.style.display !== 'none') {
    integrityOverlay.style.display = 'none';
  }
});

// Add/remove source rows
let sourceIndex = 1;
addSourceBtn.addEventListener('click', () => {
  const list = document.getElementById('integrity-sources-list');
  const row = document.createElement('div');
  row.className = 'integrity-source-row';
  row.dataset.index = sourceIndex++;
  row.innerHTML = `
    <input class="integrity-source-name" type="text" placeholder="Source name (e.g. Jones 2020)" />
    <textarea class="integrity-source-text integrity-textarea" rows="3" placeholder="Paste source text here…"></textarea>
    <button class="integrity-remove-source" title="Remove source">✕</button>
  `;
  list.appendChild(row);
  row.querySelector('.integrity-remove-source').addEventListener('click', () => row.remove());
});

function addIntegritySource(name, text) {
  const cleanedText = String(text || '').trim();
  if (!cleanedText) return false;
  const list = document.getElementById('integrity-sources-list');
  let row = [...document.querySelectorAll('.integrity-source-row')].find((candidate) => {
    const sourceText = candidate.querySelector('.integrity-source-text')?.value.trim();
    const sourceName = candidate.querySelector('.integrity-source-name')?.value.trim();
    return !sourceText && !sourceName;
  });
  if (!row) {
    addSourceBtn.click();
    row = [...document.querySelectorAll('.integrity-source-row')].at(-1);
  }
  if (!row || !list) return false;
  row.querySelector('.integrity-source-name').value = name || 'Retrieved source';
  row.querySelector('.integrity-source-text').value = cleanedText;
  return true;
}

document.getElementById('integrity-use-chat-input')?.addEventListener('click', () => {
  const target = document.getElementById('integrity-student-text');
  if (target) target.value = input?.value || '';
});

document.getElementById('integrity-use-last-response')?.addEventListener('click', () => {
  const target = document.getElementById('integrity-student-text');
  if (target) target.value = lastSophiaResponse || '';
});

document.getElementById('integrity-add-last-sources')?.addEventListener('click', () => {
  if (!lastRetrievedSources.length) {
    alert('No retrieved sources are available yet. Use Academic Assist → Find Recent Sources first.');
    return;
  }
  let added = 0;
  for (const source of lastRetrievedSources.slice(0, 5)) {
    const title = source.title || source.source || 'Retrieved source';
    const bits = [
      source.summary || '',
      source.url ? `URL: ${source.url}` : '',
      source.year ? `Year: ${source.year}` : '',
      source.source ? `Index: ${source.source}` : '',
    ].filter(Boolean).join('\n');
    if (addIntegritySource(title, bits)) added += 1;
  }
  showSpeakingText(`Added ${added} retrieved source${added === 1 ? '' : 's'} to the Integrity Desk.`);
});

// Wire remove on first row (which exists at load time)
document.querySelector('.integrity-remove-source')?.addEventListener('click', function() {
  const rows = document.querySelectorAll('.integrity-source-row');
  if (rows.length > 1) this.closest('.integrity-source-row').remove();
});

// ── RING METER HELPER ──────────────────────────────────────────
function setRing(ringId, fraction, riskClass) {
  const el = document.getElementById(ringId);
  if (!el) return;
  const dash = fraction * CIRCUMFERENCE;
  el.style.strokeDasharray = `${dash.toFixed(1)} ${CIRCUMFERENCE.toFixed(1)}`;
  el.className = `ring-fill ${riskClass}-ring`;
}

function riskClass(risk) {
  return { critical: 'critical', high: 'high', moderate: 'moderate', low: 'low' }[risk] || 'low';
}

function aiVerdictClass(verdict) {
  if (verdict === 'almost_certainly_ai') return 'critical';
  if (verdict === 'likely_ai') return 'high';
  if (verdict === 'uncertain') return 'moderate';
  return 'low';
}

// ── TEXT HIGHLIGHTING ───────────────────────────────────────────
/**
 * Build a highlighted HTML version of the student text.
 * verbatimSpans: [{char_start, char_end, original_phrase, source}]
 * runAi: bool — whether to also highlight AI marker phrases
 */
function buildHighlightedHtml(originalText, verbatimSpans, runAi) {
  // Build list of [start, end, class, tooltip] regions, then merge
  const regions = [];

  // Verbatim spans from server (have char positions)
  for (const sp of verbatimSpans) {
    if (sp.char_start >= 0 && sp.char_end > sp.char_start) {
      regions.push({
        start: sp.char_start,
        end: sp.char_end,
        cls: 'hlg-critical',
        tip: `Verbatim copy — ${escapeHtml(sp.source)} (${sp.word_count} words)`,
      });
    } else {
      // Fallback: search the original text
      const idx = originalText.toLowerCase().indexOf(sp.phrase.toLowerCase());
      if (idx >= 0) {
        regions.push({
          start: idx,
          end: idx + sp.phrase.length,
          cls: 'hlg-critical',
          tip: `Verbatim copy — ${escapeHtml(sp.source)} (${sp.word_count} words)`,
        });
      }
    }
  }

  // AI marker phrases
  if (runAi) {
    const sorted = [...AI_MARKER_PHRASES].sort((a, b) => b.length - a.length);
    const textLower = originalText.toLowerCase();
    for (const marker of sorted) {
      let pos = 0;
      while (true) {
        const idx = textLower.indexOf(marker.toLowerCase(), pos);
        if (idx < 0) break;
        // Don't override a critical span
        const overlaps = regions.some(r => r.start <= idx && r.end >= idx + marker.length);
        if (!overlaps) {
          regions.push({
            start: idx,
            end: idx + marker.length,
            cls: 'hlg-ai',
            tip: `AI-signature phrase: "${escapeHtml(marker)}"`,
          });
        }
        pos = idx + marker.length;
      }
    }
  }

  if (regions.length === 0) {
    return `<span>${escapeHtml(originalText)}</span>`;
  }

  // Sort by start, resolve overlaps (earlier wins)
  regions.sort((a, b) => a.start - b.start || b.end - a.end);
  const merged = [];
  for (const r of regions) {
    if (merged.length && r.start < merged[merged.length - 1].end) continue; // skip overlap
    merged.push(r);
  }

  // Build HTML
  let html = '';
  let cursor = 0;
  for (const r of merged) {
    if (r.start > cursor) {
      html += escapeHtml(originalText.slice(cursor, r.start));
    }
    html += `<mark class="${r.cls}" title="${r.tip}">${escapeHtml(originalText.slice(r.start, r.end))}</mark>`;
    cursor = r.end;
  }
  if (cursor < originalText.length) {
    html += escapeHtml(originalText.slice(cursor));
  }
  return html;
}

// ── SIGNAL BAR ─────────────────────────────────────────────────
function buildSignalBar(signal) {
  const pct = Math.round(signal.value * 100);
  const cls = pct >= 70 ? 'critical' : pct >= 45 ? 'high' : pct >= 25 ? 'moderate' : 'low';
  return `
    <div class="ai-signal-item">
      <div class="ai-signal-header">
        <span class="ai-signal-name">${escapeHtml(signal.name.replace(/_/g, ' ').toUpperCase())}</span>
        <span class="ai-signal-pct ${cls}">${pct}%</span>
      </div>
      <div class="ai-signal-bar-track">
        <div class="ai-signal-bar-fill ${cls}" style="width:${pct}%"></div>
      </div>
      <div class="ai-signal-desc">${escapeHtml(signal.description)}</div>
    </div>
  `;
}

// ── MAIN RUN ───────────────────────────────────────────────────
integrityRunBtn.addEventListener('click', async () => {
  const studentText = document.getElementById('integrity-student-text').value.trim();
  if (!studentText) {
    alert('Please paste a student text before running the check.');
    return;
  }

  const sourceRows = document.querySelectorAll('.integrity-source-row');
  const sources = [];
  sourceRows.forEach(row => {
    const name = row.querySelector('.integrity-source-name')?.value.trim() || 'Unnamed Source';
    const text = row.querySelector('.integrity-source-text')?.value.trim() || '';
    if (text) sources.push({ name, text });
  });

  const runAi = document.getElementById('integrity-run-ai').checked;

  integrityRunBtn.textContent = 'RUNNING…';
  integrityRunBtn.disabled = true;

  try {
    const resp = await fetch(`${API_BASE}/api/check-plagiarism`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_text: studentText, sources, run_ai_detection: runAi }),
    });
    if (!resp.ok) throw new Error(`Server returned ${resp.status}`);
    const data = await resp.json();
    renderIntegrityResults(data, studentText, runAi);
  } catch (err) {
    alert(`Integrity check failed: ${err.message}`);
    console.error('[Integrity]', err);
  } finally {
    integrityRunBtn.textContent = 'RUN INTEGRITY CHECK';
    integrityRunBtn.disabled = false;
  }
});

function renderIntegrityResults(data, studentText, runAi) {
  document.getElementById('integrity-empty-state').style.display = 'none';
  const content = document.getElementById('integrity-results-content');
  content.style.display = 'block';

  // ── PLAGIARISM RING ──
  const plgFraction = data.overall_score || 0;
  const plgRisk = data.risk_level || 'low';
  setRing('plg-ring', plgFraction, riskClass(plgRisk));
  document.getElementById('plg-pct').textContent = `${Math.round(plgFraction * 100)}%`;
  const riskEl = document.getElementById('plg-risk');
  riskEl.textContent = plgRisk.toUpperCase();
  riskEl.className = `meter-risk-badge ${riskClass(plgRisk)}`;

  // ── AI RING ──
  const aiBlock = document.getElementById('ai-meter-block');
  if (data.ai_detection && runAi) {
    aiBlock.style.display = '';
    const ai = data.ai_detection;
    const aiFraction = ai.ai_probability || 0;
    const aiCls = aiVerdictClass(ai.verdict);
    setRing('ai-ring', aiFraction, aiCls);
    document.getElementById('ai-pct').textContent = `${Math.round(aiFraction * 100)}%`;
    const verdictEl = document.getElementById('ai-verdict');
    verdictEl.textContent = (ai.verdict || '—').replace(/_/g, ' ').toUpperCase();
    verdictEl.className = `meter-risk-badge ${aiCls}`;
  } else {
    aiBlock.style.display = 'none';
  }

  // ── SUMMARIES ──
  document.getElementById('plg-summary').textContent = data.summary || '';
  const aiSumLabel = document.getElementById('ai-summary-label');
  const aiSumEl = document.getElementById('ai-summary');
  if (data.ai_detection && runAi) {
    aiSumLabel.style.display = '';
    aiSumEl.style.display = '';
    aiSumEl.textContent = data.ai_detection.summary || '';
  } else {
    aiSumLabel.style.display = 'none';
    aiSumEl.style.display = 'none';
  }

  // ── HIGHLIGHTED TEXT ──
  const spans = data.verbatim_spans || [];
  const hlHtml = buildHighlightedHtml(studentText, spans, runAi && !!data.ai_detection);
  const hlEl = document.getElementById('integrity-highlighted-text');
  hlEl.innerHTML = hlHtml;

  // ── SOURCE TABLE ──
  const tbody = document.getElementById('integrity-source-tbody');
  tbody.innerHTML = '';
  for (const ss of (data.source_scores || [])) {
    const pct = v => `${Math.round((v || 0) * 100)}%`;
    const cls = ss.composite >= 0.7 ? 'critical' : ss.composite >= 0.45 ? 'high' : ss.composite >= 0.2 ? 'moderate' : '';
    tbody.innerHTML += `
      <tr>
        <td class="src-name-cell">${escapeHtml(ss.source)}</td>
        <td class="${cls} bold">${pct(ss.composite)}</td>
        <td>${pct(ss.verbatim_ratio)}</td>
        <td>${pct(ss.word_ngram_jaccard)}</td>
        <td>${pct(ss.lcs_ratio)}</td>
      </tr>
    `;
  }

  // ── AI SIGNALS ──
  const aiSignalsBlock = document.getElementById('ai-signals-block');
  const aiSignalsGrid  = document.getElementById('ai-signals-grid');
  if (data.ai_detection && runAi && data.ai_detection.signals?.length) {
    aiSignalsBlock.style.display = '';
    aiSignalsGrid.innerHTML = data.ai_detection.signals.map(buildSignalBar).join('');
  } else {
    aiSignalsBlock.style.display = 'none';
  }

  // ── VERBATIM SPANS LIST ──
  const verbatimBlock = document.getElementById('verbatim-block');
  const verbatimList  = document.getElementById('verbatim-spans-list');
  if (spans.length) {
    verbatimBlock.style.display = '';
    verbatimList.innerHTML = spans.map(sp => `
      <div class="verbatim-span-item">
        <div class="verbatim-phrase">"${escapeHtml(sp.original_phrase || sp.phrase)}"</div>
        <div class="verbatim-meta">
          <span class="verbatim-source">${escapeHtml(sp.source)}</span>
          <span class="verbatim-words">${sp.word_count} words</span>
        </div>
      </div>
    `).join('');
  } else {
    verbatimBlock.style.display = 'none';
  }

  // Scroll results into view
  content.scrollTop = 0;
}
