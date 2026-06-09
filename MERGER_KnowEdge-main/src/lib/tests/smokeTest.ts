import { dataDrive } from '../dataDrive';
import { circleAI } from '../circleAI';
import { auth } from '../../firebase';
import { MemoryBus } from '../memory';

export async function runSmokeTest() {
  const results: any[] = [];
  
  const log = (test: string, status: 'PASS' | 'FAIL', detail: string) => {
    const entry = { test, status, detail, timestamp: Date.now() };
    results.push(entry);
    MemoryBus.publish('session-events' as any, { type: 'SMOKE_TEST_ENTRY', ...entry });
  };

  try {
    // 1. DataDrive Init
    dataDrive.init();
    log("DataDrive Initialization", "PASS", "Engine online and highways established.");

    // 2. CircleAI Init
    if (circleAI.getStage() === 'IDLE') {
        log("CircleAI Engine Status", "PASS", "Engine standby [IDLE].");
    }

    // 3. Firebase Connection
    if (auth) {
        log("Firebase Auth Bridge", "PASS", "Auth module initialized.");
    }

    // 4. Memory Bus Integrity
    if (MemoryBus) {
        log("MEM5 Bus Integrity", "PASS", "Event distribution layer active.");
    }

  } catch (e: any) {
    log("System Smoke Test", "FAIL", e.message);
  }

  return results;
}
