import { MemoryBus } from './memory';

export type RunState = 
  | 'created' | 'validating' | 'ingesting' | 'indexing' | 'mapping'
  | 'comparing' | 'blueprints_generating' | 'scoring' | 'qa'
  | 'auditing' | 'finalizing' | 'completed' | 'failed' | 'rolled_back' | 'quarantined';

export const STATE_SEQUENCE: RunState[] = [
  'created', 'validating', 'ingesting', 'indexing', 'mapping',
  'comparing', 'blueprints_generating', 'scoring', 'qa',
  'auditing', 'finalizing', 'completed'
];

export const STATE_PROGRESS: Record<RunState, number> = {
  created: 0, validating: 8, ingesting: 16, indexing: 24, mapping: 32,
  comparing: 40, blueprints_generating: 50, scoring: 62, qa: 72,
  auditing: 82, finalizing: 92, completed: 100,
  failed: 0, rolled_back: 0, quarantined: 0
};

export interface HeartbeatRecord {
  run_id: string;
  phase: string;
  status: 'OK' | 'RED';
  progress_pct: number;
  last_checkpoint: string;
  last_module: string;
  warning_count: number;
  anomaly_count: number;
  receipt_count: number;
  memory_checksum: string;
  artifact_hash: string;
  retry_count: number;
  quarantine: boolean;
  last_exception: string | null;
  updated_at_utc: string;
}

export interface RunRecord {
  run_id: string;
  state: RunState;
  operator: string;
  source_file: string;
  target_file: string;
  receipt_count: number;
  anomaly_count: number;
  warning_count: number;
  created_at: number;
  updated_at: number;
  heartbeat: HeartbeatRecord;
}

export function generateRunId(): string {
  const d = new Date();
  const date = d.toISOString().slice(0, 10).replace(/-/g, '');
  const rand = Math.random().toString(36).substring(2, 6).toUpperCase();
  return `RUN-${date}-${rand}`;
}

export function createRun(operator: string, sourceFile: string, targetFile: string): RunRecord {
  const runId = generateRunId();
  const now = Date.now();
  const run: RunRecord = {
    run_id: runId,
    state: 'created',
    operator,
    source_file: sourceFile,
    target_file: targetFile,
    receipt_count: 0,
    anomaly_count: 0,
    warning_count: 0,
    created_at: now,
    updated_at: now,
    heartbeat: {
      run_id: runId,
      phase: 'created',
      status: 'OK',
      progress_pct: 0,
      last_checkpoint: 'INIT',
      last_module: 'SYSTEM',
      warning_count: 0,
      anomaly_count: 0,
      receipt_count: 0,
      memory_checksum: 'NONE',
      artifact_hash: 'NONE',
      retry_count: 0,
      quarantine: false,
      last_exception: null,
      updated_at_utc: new Date().toISOString()
    }
  };
  saveRun(run);
  MemoryBus.publish('session-events' as any, { message: `RUN CREATED: ${runId}` });
  return run;
}

export function transitionRun(run: RunRecord, toState: RunState): RunRecord {
  const currentIndex = STATE_SEQUENCE.indexOf(run.state);
  const targetIndex = STATE_SEQUENCE.indexOf(toState);
  
  // Allow transitions to failure states or forward transitions
  if (toState !== 'failed' && toState !== 'rolled_back' && toState !== 'quarantined') {
    if (targetIndex <= currentIndex && currentIndex !== -1) {
      console.warn(`Invalid transition: ${run.state} -> ${toState}`);
    }
  }

  const updated: RunRecord = {
    ...run,
    state: toState,
    updated_at: Date.now(),
    heartbeat: {
      ...run.heartbeat,
      phase: toState,
      progress_pct: STATE_PROGRESS[toState],
      updated_at_utc: new Date().toISOString()
    }
  };
  
  saveRun(updated);
  MemoryBus.publish('session-events' as any, { message: `TRANSITION: ${run.state} -> ${toState}` });
  return updated;
}

export function issueReceipt(run: RunRecord, module: string): RunRecord {
  const updated: RunRecord = {
    ...run,
    receipt_count: run.receipt_count + 1,
    heartbeat: {
      ...run.heartbeat,
      receipt_count: run.heartbeat.receipt_count + 1,
      last_module: module,
      updated_at_utc: new Date().toISOString()
    }
  };
  saveRun(updated);
  MemoryBus.publish('session-events' as any, { message: `RECEIPT ISSUED: ${module}` });
  return updated;
}

export function rollbackRun(run: RunRecord): RunRecord {
  return transitionRun(run, 'rolled_back');
}

export function quarantineRun(run: RunRecord, reason: string): RunRecord {
  const updated = transitionRun(run, 'quarantined');
  updated.heartbeat.quarantine = true;
  updated.heartbeat.last_exception = reason;
  saveRun(updated);
  return updated;
}

export function saveRun(run: RunRecord): void {
  const runs = loadRuns();
  const existingIndex = runs.findIndex(r => r.run_id === run.run_id);
  if (existingIndex > -1) {
    runs[existingIndex] = run;
  } else {
    runs.unshift(run);
  }
  localStorage.setItem('km_runs_v5', JSON.stringify(runs.slice(0, 20)));
}

export function loadRuns(): RunRecord[] {
  const data = localStorage.getItem('km_runs_v5');
  if (!data) return [];
  try {
    return JSON.parse(data);
  } catch {
    return [];
  }
}
