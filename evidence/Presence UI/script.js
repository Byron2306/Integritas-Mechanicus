/**
 * Arda OS — Presence Interface Script
 * ====================================
 *
 * Connected to the Presence Server (localhost:7070):
 *   /api/speak   → Ollama + MandosContext → LLM response
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
};

const form = document.getElementById('directive-form');
const input = document.getElementById('directive-input');
const speakButton = document.getElementById('speak-button');
const boundaryButton = document.getElementById('boundary-button');
const settingsButton = document.getElementById('settings-button');
const micButton = document.getElementById('mic-button');

const presenceRest = document.getElementById('presence-rest');
const presenceCard = presenceRest.closest('.presence-card');

const voiceDot = document.querySelector('.voice-dot');
const stateDot = document.getElementById('state-dot');
const metaState = stateDot?.parentElement;
const voiceStatus = document.getElementById('voice-status');

// ================================================================
// PRESENCE STATE MACHINE
// ================================================================
// CSS-only animation on the still image.
// Speaking: glow pulse + brightness shift.
// Rest: gentle breathing.

let presenceState = 'rest'; // 'rest' | 'speaking'
let currentAudio = null;

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
async function apiSpeak(directive) {
  try {
    const resp = await fetch(`${API_BASE}/api/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: directive, topic: directive.slice(0, 50), session_token: sessionToken }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    serverConnected = true;
    const encId = data.encounter_id || 'none';
    console.log(`[Presence] ${encId} | ${data.source}${data.model ? ' (' + data.model + ')' : ''} | mandos: ${data.mandos_context}`);
    // Update system log with encounter ID
    const logEl = document.getElementById('system-log-body');
    if (logEl) {
      const ts = new Date().toLocaleTimeString();
      logEl.textContent = `[${ts}] ${encId} | ${data.source} | ${data.eval_count || 0} tokens`;
    }
    // Update Constitutional Orchestra
    updateOrchestralState(data);
    return data.response;
  } catch (err) {
    console.warn('[Presence] Server unreachable, using fallback:', err.message);
    serverConnected = false;
    return generateFallbackResponse(directive);
  }
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

  // Try voice
  const audioBlob = await apiVoice(response);

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
    // No voice — simulate speaking duration
    const duration = Math.max(2000, Math.min(response.length * 80, 15000));
    setTimeout(() => setPresenceState('rest'), duration);
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
    }
  });
});

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

// ================================================================
// MICROPHONE INPUT (Web Speech API)
// ================================================================

let recognition = null;
let isListening = false;

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn('[Presence] Web Speech API not available');
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    console.log('[Presence] Heard:', transcript);
    input.value = transcript;
    handleDirective(transcript);
    input.value = '';
  };

  recognition.onerror = (event) => {
    console.warn('[Presence] Speech error:', event.error);
    setMicState(false);
  };

  recognition.onend = () => {
    setMicState(false);
  };
}

function toggleMic() {
  if (!recognition) {
    initSpeechRecognition();
    if (!recognition) {
      showSpeakingText('Speech recognition not available in this browser.');
      return;
    }
  }

  if (isListening) {
    recognition.stop();
    setMicState(false);
  } else {
    recognition.start();
    setMicState(true);
    showSpeakingText('Listening...');
  }
}

function setMicState(listening) {
  isListening = listening;
  if (micButton) {
    micButton.classList.toggle('active', listening);
    micButton.title = listening ? 'Stop listening' : 'Speak directive';
  }
}

if (micButton) {
  micButton.addEventListener('click', toggleMic);
}

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

  panelBody.innerHTML = `
    <p class="lead">System Configuration</p>
    <p>
      <strong>Server:</strong> ${health ? '🟢 Connected' : '🔴 Unreachable'}<br/>
      <strong>Ollama:</strong> ${svc.ollama?.status === 'running' ? '🟢 Running' : '🟡 Offline (fallback active)'}<br/>
      ${svc.ollama?.models?.length ? `<strong>Models:</strong> ${svc.ollama.models.join(', ')}<br/>` : ''}
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

// ================================================================
// UTILITIES
// ================================================================

function escapeHtml(text) {
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}

// ================================================================
// INIT
// ================================================================

// Start background telemetry polling
apiGet('health').then((data) => {
  serverConnected = !!data;
  // Capture principal session token (derived from sealed covenant identity hash)
  if (data?.session_token) {
    sessionToken = data.session_token;
    console.log('[Presence] Principal session token acquired (covenant-bound)');
  }
  if (voiceStatus) {
    const svc = data?.services || {};
    if (svc.elevenlabs === 'configured') {
      voiceStatus.textContent = 'ready';
    } else if (serverConnected) {
      voiceStatus.textContent = 'no voice key';
    } else {
      voiceStatus.textContent = 'offline';
    }
  }
  const ollamaStatus = document.getElementById('ollama-status');
  if (ollamaStatus) {
    ollamaStatus.textContent = data?.services?.ollama?.status === 'running' ? 'connected' : 'offline';
  }

  // Initial UI refresh
  if (data?.polyphonic_state) {
    updateHighFidelityPanels(data.polyphonic_state);
  }

  console.log('[Arda Presence] Server:', serverConnected ? 'connected' : 'offline (fallback mode)');
  console.log('[Arda Presence] Services:', data?.services);
}).catch(() => {
  serverConnected = false;
  if (voiceStatus) voiceStatus.textContent = 'offline';
  console.log('[Arda Presence] Server offline — running in fallback mode');
});

// Periodic polling every 3 seconds for the Sovereign Dashboard
setInterval(async () => {
  if (!serverConnected) return;
  try {
    const data = await apiGet('health');
    if (data && data.polyphonic_state) {
      updateHighFidelityPanels(data.polyphonic_state);
    }
  } catch (err) {
    console.warn('[Presence] Polling failed:', err.message);
  }
}, 3000);

initSpeechRecognition();
