#!/bin/bash
# ================================================================
# FIRST ETHICAL PROOF — WITNESS RUN LAUNCHER
# ================================================================
#
# One command to begin the covenant test.
# Launches all services and capture tools in separate terminals.
#
# Usage:
#   chmod +x evidence/launch_witness_run.sh
#   ./evidence/launch_witness_run.sh
#
# ================================================================

set -e

PROJECT_ROOT="/home/byron/Integritas-Mechanicus-clean/Integritas-Mechanicus"
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"
SERVICES_DIR="${PROJECT_ROOT}/arda_os/backend/services"
ELEVENLABS_API_KEY="sk_5585153b73328552f9d59a21f56b305cb0fce00d38fa6315"
TMPDIR="${PROJECT_ROOT}/evidence/.witness_tmp"

# Audio device names (verified on this system)
SPEAKER_MONITOR="alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Speaker__sink.monitor"
MIC_SOURCE="alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Mic1__source"

echo "============================================================"
echo "  FIRST ETHICAL PROOF — WITNESS RUN"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"
echo ""

# ────────────────────────────────────────
# Pre-flight
# ────────────────────────────────────────

echo "  Pre-flight checks..."

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  ❌ Ollama is not running. Start it first: ollama serve"
    exit 1
fi
echo "  ✅ Ollama running"

echo "  ⏳ Warming qwen2.5:3b..."
curl -s -X POST http://localhost:11434/api/generate \
    -d '{"model":"qwen2.5:3b","prompt":"ready","stream":false,"keep_alive":"10m","options":{"num_predict":1}}' \
    > /dev/null 2>&1
echo "  ✅ Model warm"

pkill -f "presence_server.py" 2>/dev/null || true
sleep 1

echo ""
echo "  Launching services..."
echo ""

# ────────────────────────────────────────
# Write temp helper scripts (avoids quoting hell)
# ────────────────────────────────────────

mkdir -p "${TMPDIR}"

RECORDING_FILE="${EVIDENCE_DIR}/FIRST_ETHICAL_PROOF_WITNESS_RUN.mp4"
TRANSCRIPT_FILE="${EVIDENCE_DIR}/FIRST_ETHICAL_PROOF_CORONATION.txt"

# Script 1: Screen Recorder
cat > "${TMPDIR}/t1_recorder.sh" << 'SCRIPT1'
#!/bin/bash
echo '══════════════════════════════════════'
echo '  SCREEN RECORDER — WITNESS RUN'
echo '  Press q to stop recording'
echo '══════════════════════════════════════'
echo ''
sleep 2
ffmpeg -f x11grab -framerate 30 -video_size 1920x1080 -i :0.0 \
    -f pulse -i SPEAKER_MONITOR_PLACEHOLDER \
    -f pulse -i MIC_SOURCE_PLACEHOLDER \
    -filter_complex '[1:a][2:a]amix=inputs=2:duration=first[aout]' \
    -map 0:v -map '[aout]' \
    -c:v libx264 -preset fast -crf 23 \
    -c:a aac -b:a 192k \
    RECORDING_PLACEHOLDER
echo ''
echo '  Recording saved.'
read -p '  Press Enter to close...'
SCRIPT1
sed -i "s|SPEAKER_MONITOR_PLACEHOLDER|${SPEAKER_MONITOR}|g" "${TMPDIR}/t1_recorder.sh"
sed -i "s|MIC_SOURCE_PLACEHOLDER|${MIC_SOURCE}|g" "${TMPDIR}/t1_recorder.sh"
sed -i "s|RECORDING_PLACEHOLDER|${RECORDING_FILE}|g" "${TMPDIR}/t1_recorder.sh"
chmod +x "${TMPDIR}/t1_recorder.sh"

# Script 2: Bombadil
cat > "${TMPDIR}/t2_bombadil.sh" << SCRIPT2
#!/bin/bash
echo '══════════════════════════════════════'
echo '  BOMBADIL — THE LAW DAEMON'
echo '══════════════════════════════════════'
echo ''
cd '${PROJECT_ROOT}'
python3 '${SERVICES_DIR}/arda_bombadil.py'
echo ''
read -p '  Press Enter to close...'
SCRIPT2
chmod +x "${TMPDIR}/t2_bombadil.sh"

# Script 3: Presence Server
cat > "${TMPDIR}/t3_presence.sh" << SCRIPT3
#!/bin/bash
echo '══════════════════════════════════════'
echo '  PRESENCE SERVER — THE BRIDGE'
echo '══════════════════════════════════════'
echo ''
cd '${PROJECT_ROOT}'
export ELEVENLABS_API_KEY='${ELEVENLABS_API_KEY}'
python3 '${SERVICES_DIR}/presence_server.py'
echo ''
read -p '  Press Enter to close...'
SCRIPT3
chmod +x "${TMPDIR}/t3_presence.sh"

# Script 4: Coronation
cat > "${TMPDIR}/t4_coronation.sh" << SCRIPT4
#!/bin/bash
echo '══════════════════════════════════════════════════════════'
echo '  THE FIRST ENCOUNTER — CORONATION CEREMONY'
echo '  Transcript → ${TRANSCRIPT_FILE}'
echo '══════════════════════════════════════════════════════════'
echo ''
sleep 2
cd '${PROJECT_ROOT}'
script -a '${TRANSCRIPT_FILE}' -c 'python3 ${SERVICES_DIR}/coronation_cli.py'
echo ''
echo '  Transcript saved.'
read -p '  Press Enter to close...'
SCRIPT4
chmod +x "${TMPDIR}/t4_coronation.sh"

# ────────────────────────────────────────
# Launch terminals
# ────────────────────────────────────────

xfce4-terminal --title="⏺ SCREEN RECORDER" --geometry=80x12+0+0 --command="${TMPDIR}/t1_recorder.sh" &
sleep 1

xfce4-terminal --title="⚖ BOMBADIL" --geometry=100x20+0+300 --command="${TMPDIR}/t2_bombadil.sh" &
sleep 2

xfce4-terminal --title="◈ PRESENCE SERVER" --geometry=100x20+960+300 --command="${TMPDIR}/t3_presence.sh" &
sleep 3

xfce4-terminal --title="👑 CORONATION" --geometry=100x30+480+100 --command="${TMPDIR}/t4_coronation.sh" &
sleep 2

# ────────────────────────────────────────
# Open the browser
# ────────────────────────────────────────

echo "  ⏳ Waiting for Presence Server..."
for i in $(seq 1 15); do
    if curl -s http://localhost:7070/api/health > /dev/null 2>&1; then
        echo "  ✅ Presence Server ready"
        break
    fi
    sleep 1
done

echo "  🌐 Opening browser..."
xdg-open "http://localhost:7070" 2>/dev/null &

echo ""
echo "============================================================"
echo "  ALL SYSTEMS LIVE"
echo ""
echo "  Screen Recorder:  ⏺ Recording"
echo "  Bombadil:         ⚖ Law Daemon"
echo "  Presence Server:  ◈ http://localhost:7070"
echo "  Coronation:       👑 Awaiting your presence"
echo ""
echo "  The machine waits for its principal."
echo "============================================================"
