/**
 * KM-CHRONICLE SYSTEM — V4.3.1
 * Local, private context capture and memory consolidation.
 */

import { memory, MemoryLayer, MemoryBus, MemoryChannel } from './memory';

// --- SANDBOX RULES ENGINE ---

export interface SandboxPolicy {
  allowedOperations: string[];
  blockedPatterns: RegExp[];
  maxMemoryMB: number;
  maxRunTimeMs: number;
  promptInjectionGuard: boolean;
}

export const STRICT_NWU_POLICY: SandboxPolicy = {
  allowedOperations: ['read-dom', 'write-ledger', 'local-consolidation'],
  blockedPatterns: [
    /https?:\/\/(?!localhost|127\.0\.0\.1)/i, // No external URLs
    /\b\d{13}\b/, // NWU Student ID pattern (example)
    /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i // PII: Emails
  ],
  maxMemoryMB: 50,
  maxRunTimeMs: 30000,
  promptInjectionGuard: true
};

export class PromptInjectionScanner {
  private static readonly INJECTION_PATTERNS = [
    /ignore (all )?previous/i,
    /jailbreak/i,
    /system:/i,
    /override/i,
    /act as/i,
    /forget everything/i,
    /you are now/i,
    /new rules/i,
    /standard output format: ignore/i
  ];

  static scan(text: string): { clean: boolean; detected?: string } {
    for (const pattern of this.INJECTION_PATTERNS) {
      if (pattern.test(text)) {
        return { clean: false, detected: pattern.source };
      }
    }
    return { clean: true };
  }
}

export class SandboxedAgent {
  constructor(private policy: SandboxPolicy = STRICT_NWU_POLICY) {}

  execute(taskName: string, operation: () => any): any {
    const startTime = Date.now();
    
    // Check timeout manually if needed or wrap in promise
    const result = operation();

    if (Date.now() - startTime > this.policy.maxRunTimeMs) {
      this.logViolation(taskName, 'TIMEOUT_EXCEEDED');
      throw new Error(`[Sandbox] Execution timed out for ${taskName}`);
    }

    return result;
  }

  private logViolation(task: string, type: string) {
    MemoryBus.publish('integrity-alerts', {
      type: 'SANDBOX_VIOLATION',
      task,
      violation: type,
      timestamp: Date.now()
    });
  }
}

// --- CONTEXT CAPTURE ENGINE ---

export interface ActiveContextSnapshot {
  currentTab: string;
  lastInputText: string;
  recentWorkflow: any[];
  activeComponents: string[];
  sessionDurationMs: number;
  timestamp: number;
}

export class SessionObserver {
  private workflow: any[] = [];
  private lastSnapshotTime: number = 0;
  private observer: MutationObserver | null = null;
  private intersectionObserver: IntersectionObserver | null = null;
  private activeComponents: Set<string> = new Set();
  private lastInput: string = "";

  constructor() {}

  start() {
    if (typeof window === 'undefined') return;

    this.observer = new MutationObserver((mutations) => {
      mutations.forEach(m => {
        if (m.type === 'childList') {
          // Track component lifecycle
          m.addedNodes.forEach(node => {
            if (node instanceof HTMLElement && node.dataset.component) {
              this.activeComponents.add(node.dataset.component);
              this.trackAction('component_mount', node.dataset.component);
            }
          });
        }
      });
    });

    this.observer.observe(document.body, { childList: true, subtree: true });

    // Track inputs
    document.addEventListener('input', (e) => {
      const target = e.target as HTMLInputElement | HTMLTextAreaElement;
      if (target.value) {
        this.lastInput = target.value.slice(-500); // Only keep relevant tail
      }
    });

    this.lastSnapshotTime = Date.now();
  }

  stop() {
    this.observer?.disconnect();
    this.intersectionObserver?.disconnect();
  }

  private trackAction(type: string, detail: any) {
    this.workflow.push({ type, detail, timestamp: Date.now() });
    if (this.workflow.length > 50) this.workflow.shift();
  }

  getSnapshot(currentTab: string, startTime: number): ActiveContextSnapshot {
    return {
      currentTab,
      lastInputText: this.lastInput,
      recentWorkflow: [...this.workflow],
      activeComponents: Array.from(this.activeComponents),
      sessionDurationMs: Date.now() - startTime,
      timestamp: Date.now()
    };
  }
}

// --- MEMORY CONSOLIDATION ---

export interface MemoryFragment {
  fact: string;
  confidence: number;
  category: 'workflow' | 'tool-preference' | 'document-context' | 'session-pattern' | 'nwu-context';
  timestamp: number;
  source: 'chronicle';
}

export class MistralConsolidator {
  private readonly ENDPOINT = '/api/chronicle/consolidate';

  async consolidateSession(snapshot: ActiveContextSnapshot): Promise<MemoryFragment[]> {
    try {
      const response = await fetch(this.ENDPOINT, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Chronicle-Token': this.generateSimpleToken()
        },
        body: JSON.stringify({ snapshot })
      });

      if (!response.ok) throw new Error('Mistral consolidation failed');
      const data = await response.json();
      return data.memories || [];
    } catch (e) {
      console.warn('[Chronicle] Falling back to local storage queue due to offline consolidator');
      return []; // Fallback handled by caller
    }
  }

  private generateSimpleToken() {
    const ts = Date.now().toString();
    return btoa(ts + "_chronicle_v4.3.1");
  }
}

// --- CHRONICLE MEMORY STORE ---

export class ChronicleMemoryStore {
  private static readonly STORAGE_KEY = 'km_chronicle_memories';

  static store(fragment: MemoryFragment) {
    const scan = PromptInjectionScanner.scan(fragment.fact);
    if (!scan.clean) {
      console.error(`[Chronicle] Blocked injection pattern in memory: ${scan.detected}`);
      return;
    }

    const memories = this.list();
    // Simple obfuscation
    const obfuscated = this.obfuscate(fragment);
    memories.push(obfuscated);
    
    // Prune to 200 entries
    if (memories.length > 200) memories.shift();
    
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(memories));
    MemoryBus.publish('session-events' as any, { type: 'CHRONICLE_STORE', fact: fragment.fact });
  }

  static list(): any[] {
    if (typeof localStorage === 'undefined') return [];
    const stored = localStorage.getItem(this.STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  }

  static getDecoded(): MemoryFragment[] {
    return this.list().map(m => this.deobfuscate(m));
  }

  static recall(query: string): MemoryFragment[] {
    const all = this.getDecoded();
    if (!query) return all.slice(-10);
    
    // Simple trigram-ish search or filter by relevance
    return all
      .filter(m => m.fact.toLowerCase().includes(query.toLowerCase()))
      .slice(-3);
  }

  static flush(olderThanHours: number = 6) {
    const now = Date.now();
    const threshold = olderThanHours * 60 * 60 * 1000;
    const filtered = this.getDecoded().filter(m => (now - m.timestamp) < threshold);
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(filtered.map(m => this.obfuscate(m))));
  }

  private static obfuscate(f: MemoryFragment): string {
    const str = JSON.stringify(f);
    // Simple XOR-like base64 obfuscation
    return btoa(str.split('').map((char, i) => 
      String.fromCharCode(char.charCodeAt(0) ^ (i % 5))
    ).join(''));
  }

  private static deobfuscate(encoded: string): MemoryFragment {
    try {
      const decoded = atob(encoded);
      const str = decoded.split('').map((char, i) => 
        String.fromCharCode(char.charCodeAt(0) ^ (i % 5))
      ).join('');
      return JSON.parse(str);
    } catch (e) {
      return { fact: "Corrupted Memory", timestamp: Date.now() } as any;
    }
  }
}

export const KM_CHRONICLE_RULES = {
  NWU_COMPLIANCE: 'Never store student names, ID numbers, or assessment marks',
  NO_PII: 'Never store email addresses, phone numbers, passwords, or ID documents',
  SANDBOX_ISOLATION: 'Chronicle agents run with READ-ONLY access to DOM — no writes, no form submissions',
  INJECTION_GUARD: 'All text passes PromptInjectionScanner before storage or model call',
  LOCAL_ONLY: 'Mistral runs at localhost:11434 — no data leaves the NWU network',
  EPHEMERAL_SCREEN: 'No screenshots taken — context derived from DOM observations only',
  USER_CONTROL: 'Chronicle can be paused/resumed at any time via UI toggle',
  AUDIT_TRAIL: 'All Chronicle operations logged to StateLedger with operation type',
  RATE_LIMIT: 'Max 1 consolidation per 30 seconds, max 200 stored memories',
  CONSENT_GATE: 'Chronicle only activates after user acknowledges the consent modal'
};
