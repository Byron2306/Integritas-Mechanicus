import { db } from '../firebase';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';

export interface Receipt {
  id: string;
  runId: string;
  kind: 'model_call' | 'ingest' | 'merge' | 'qa';
  actor: string;
  status: 'verified' | 'failed';
  timestamp: any;
}

export class GovernanceEngine {
  static async generateReceipt(runId: string, kind: Receipt['kind'], actor: string): Promise<Receipt> {
    const receipt: Receipt = {
      id: `rcpt_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      runId,
      kind,
      actor,
      status: 'verified',
      timestamp: serverTimestamp(),
    };

    try {
      await setDoc(doc(db, 'receipts', receipt.id), receipt);
    } catch (e) {
      console.error("[GOVERNANCE] Receipt persistence failed:", e);
    }

    return receipt;
  }

  static validateTransition(from: string, to: string): boolean {
    const states = [
      "created", "validating", "ingesting", "indexing", "mapping", 
      "comparing", "blueprints_generating", "scoring", "qa", 
      "auditing", "finalizing", "completed", "failed"
    ];
    const fromIdx = states.indexOf(from);
    const toIdx = states.indexOf(to);
    return toIdx > fromIdx || to === 'failed';
  }
}
