import { db } from './firebase';
import { collection, addDoc, serverTimestamp } from 'firebase/firestore';
import { memoryBus } from './MemoryBus';

export interface DecisionEntry {
  id: string;
  kind: string;
  status: string;
  payload: any;
  timestamp: number;
}

export interface AuditEntry {
  timestamp: number;
  action: string;
  detail: any;
}

/**
 * KnowEdge RunController
 * Manages pipeline state, audit trails, and decision ledgers.
 */
class RunController {
  runId: string = 'default';
  phase: string = 'idle';
  progress: number = 0;
  status: 'idle' | 'running' | 'paused' | 'complete' | 'error' = 'idle';
  heartbeat: number = Date.now();
  decisionLedger: DecisionEntry[] = [];
  auditLog: AuditEntry[] = [];

  constructor() {
    this.updateHeartbeat();
  }

  async transitionPhase(newPhase: string, progress: number) {
    this.phase = newPhase;
    this.progress = Math.min(Math.max(progress, 0), 100);
    
    const entry: AuditEntry = {
      timestamp: Date.now(),
      action: 'PHASE_TRANSITION',
      detail: { phase: newPhase, progress: this.progress }
    };
    
    this.auditLog.push(entry);

    // Publish to MemoryBus
    memoryBus.publish('agent-findings', {
      type: 'PHASE_TRANSITION',
      runId: this.runId,
      phase: newPhase,
      progress: this.progress
    });

    // Write to Firestore
    try {
      await addDoc(collection(db, 'audit'), {
        runId: this.runId,
        phase: newPhase,
        progress: this.progress,
        timestamp: serverTimestamp(),
        action: 'PHASE_TRANSITION'
      });
    } catch (err) {
      console.warn("Firestore audit failure:", err);
    }
  }

  async logAction(action: string, detail: object = {}) {
    const entry: AuditEntry = {
      timestamp: Date.now(),
      action,
      detail
    };
    this.auditLog.push(entry);

    try {
      await addDoc(collection(db, 'audit'), {
        runId: this.runId,
        action,
        detail,
        timestamp: serverTimestamp()
      });
    } catch (err) {
      console.warn("Firestore action log failure:", err);
    }
  }

  addDecision(kind: string, status: string, payload: object) {
    const decision: DecisionEntry = {
      id: crypto.randomUUID(),
      kind,
      status,
      payload,
      timestamp: Date.now()
    };
    this.decisionLedger.push(decision);
    
    memoryBus.publish('agent-findings', {
      type: 'NEW_DECISION',
      decision
    });

    return decision;
  }

  updateHeartbeat() {
    this.heartbeat = Date.now();
  }
}

export const runController = new RunController();
