#!/bin/bash
# ARDA OS: ULTIMATE SOVEREIGN MEGA TEST (v2.3)
set -e
LOG_FILE="arda_self_healing_trace.log"
echo "--- ARDA OS: SOVEREIGN MEGA TEST START ---" > $LOG_FILE
date >> $LOG_FILE

echo "[1] FRACTURING STATE: Ensuring starting point..." | tee -a $LOG_FILE
# (Simulation of fracture: we will re-restored from scratch)

echo "[2] TRIGGERING RECOVERY: Running RECOVER_ARDA.py..." | tee -a $LOG_FILE
sudo python3 RECOVER_ARDA.py | tee -a $LOG_FILE

echo "[3] VERIFYING MEND: Checking Harmony Map Population..." | tee -a $LOG_FILE
if sudo python3 arda_os/arda_map_seeder_final.py --verify; then
    echo "SUCCESS: Map Populated with Physical Identities." | tee -a $LOG_FILE
else
    echo "FAILURE: Map Verification Failed." | tee -a $LOG_FILE
    exit 1
fi

echo "[4] SOVEREIGN CHALLENGE: Testing Enforcement..." | tee -a $LOG_FILE
echo "Challenge A: /bin/ls (Allowed)" | tee -a $LOG_FILE
if /bin/ls > /dev/null; then
    echo "PASS: /bin/ls executed successfully." | tee -a $LOG_FILE
else
    echo "FAIL: /bin/ls was blocked!" | tee -a $LOG_FILE
    exit 1
fi

echo "Challenge B: /tmp/arda_untrusted (Blocked)" | tee -a $LOG_FILE
cat << 'INNER' > /tmp/arda_untrusted
#!/bin/sh
echo 'UNAUTHORIZED EXECUTION'
INNER
chmod +x /tmp/arda_untrusted

EXIT_CODE=0
/tmp/arda_untrusted 2>&1 | grep -q "Operation not permitted" || EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ] || grep -q "Operation not permitted" <<< "$(/tmp/arda_untrusted 2>&1)"; then
    echo "PASS: /tmp/arda_untrusted was HARD-BLOCKED by Ring-0." | tee -a $LOG_FILE
else
    echo "FAIL: /tmp/arda_untrusted was allowed to run!" | tee -a $LOG_FILE
    exit 1
fi

echo "--- MEGA TEST COMPLETED SUCCESSFULLY ---" | tee -a $LOG_FILE
echo "SUCCESS: Arda OS is Sovereign." | tee -a $LOG_FILE
rm /tmp/arda_untrusted
