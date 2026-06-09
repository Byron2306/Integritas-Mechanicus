/**
 * KnowEdge Merger Layered Memory System (L0-L4)
 * L0 — Meta Rules: core system constraints loaded at boot
 * L1 — Insight Index: fast-lookup index of session facts  
 * L2 — Global Facts: stable accumulated knowledge (persists to localStorage)
 * L3 — Task Skills/SOPs: reusable workflow definitions
 * L4 — Session Archive: distilled records from completed runs
 */

import { nwuPolicyMemory } from './nwuPolicyMemory';
import { assessmentStandards } from './assessmentStandardsMemory';

export enum MemoryLayer {
  L0 = "L0", // Session/Volatile Meta Rules (boot)
  L1 = "L1", // Insight Index (1hr TTL)
  L2 = "L2", // Global Facts (24hr TTL)
  L3 = "L3", // Task Skills/SOPs (7d TTL)
  L4 = "L4"  // Session Archive (Permanent)
}

export type MemoryChannel = 'nwu-policy' | 'assessment-standards' | 'session-events' | 'agent-findings' | 'integrity-alerts';

export interface MemoryEntry {
  id: string;
  layer: MemoryLayer;
  key: string;
  value: any;
  timestamp: number;
  ttl?: number;
  runId?: string;
  channel?: MemoryChannel;
}

export type MemoryHandler = (data: any) => void;

class MemoryStore {
  private entries: MemoryEntry[] = [];
  private readonly STORAGE_KEY = "km_memory_v4.3";

  constructor() {
    this.hydrate();
    this.prune();
  }

  write(layer: MemoryLayer, key: string, value: any, options?: { ttl?: number; runId?: string; channel?: MemoryChannel }): MemoryEntry {
    const defaultTtbs: Record<MemoryLayer, number | undefined> = {
      [MemoryLayer.L0]: undefined, // Session
      [MemoryLayer.L1]: 3600000,    // 1hr
      [MemoryLayer.L2]: 86400000,   // 24hr
      [MemoryLayer.L3]: 604800000,  // 7d
      [MemoryLayer.L4]: undefined    // Permanent
    };

    const entry: MemoryEntry = {
      id: `mem_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      layer,
      key,
      value,
      timestamp: Date.now(),
      ttl: options?.ttl ?? defaultTtbs[layer],
      runId: options?.runId,
      channel: options?.channel
    };

    this.entries = this.entries.filter(e => !(e.layer === layer && e.key === key));
    this.entries.push(entry);

    if ([MemoryLayer.L2, MemoryLayer.L3, MemoryLayer.L4].includes(layer)) {
      this.persist();
    }

    return entry;
  }

  read(layer: MemoryLayer, key: string): MemoryEntry | null {
    this.prune();
    return this.entries.find(e => e.layer === layer && e.key === key) || null;
  }

  recall(query: string): MemoryEntry[] {
    this.prune();
    if (!query) return this.entries.filter(e => e.layer !== MemoryLayer.L0);
    return IndexRecall.fuzzySearch(query, this.entries.filter(e => e.layer !== MemoryLayer.L0));
  }

  prune() {
    const now = Date.now();
    const beforeLength = this.entries.length;
    this.entries = this.entries.filter(e => !e.ttl || (now - e.timestamp) < e.ttl);
    if (this.entries.length !== beforeLength) {
      this.persist();
    }
  }

  private persist() {
    if (typeof localStorage === 'undefined') return;
    try {
      const persistentEntries = this.entries.filter(e => 
        [MemoryLayer.L2, MemoryLayer.L3, MemoryLayer.L4].includes(e.layer)
      );
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(persistentEntries));
    } catch (e) {
      console.error("[MEMORY] Persistence failed:", e);
    }
  }

  private hydrate() {
    if (typeof localStorage === 'undefined') return;
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as MemoryEntry[];
        const persistent = parsed.filter(e => [MemoryLayer.L2, MemoryLayer.L3, MemoryLayer.L4].includes(e.layer));
        this.entries = [...this.entries.filter(e => ![MemoryLayer.L2, MemoryLayer.L3, MemoryLayer.L4].includes(e.layer)), ...persistent];
      }
    } catch (e) {
      console.error("[MEMORY] Hydration failed:", e);
    }
  }

  getLayerEntries(layer: MemoryLayer): MemoryEntry[] {
    this.prune();
    return this.entries.filter(e => e.layer === layer);
  }

  flush() {
    this.entries = [];
    if (typeof localStorage !== 'undefined') localStorage.removeItem(this.STORAGE_KEY);
  }

  getSystemMemoryStatus() {
    return {
      entriesCount: this.entries.length,
      layers: Object.keys(MemoryLayer).reduce((acc, layer) => {
        acc[layer] = this.entries.filter(e => e.layer === layer).length;
        return acc;
      }, {} as any),
      lastSync: Date.now()
    };
  }
}

export const memory = new MemoryStore();

export class MemoryBus {
  private static subscribers: Map<MemoryChannel, Set<MemoryHandler>> = new Map();
  private static eventHistory: Map<MemoryChannel, any[]> = new Map();

  static subscribe(channel: MemoryChannel, handler: MemoryHandler): () => void {
    if (!this.subscribers.has(channel)) {
      this.subscribers.set(channel, new Set());
    }
    this.subscribers.get(channel)!.add(handler);
    return () => this.subscribers.get(channel)?.delete(handler);
  }

  static publish(channel: MemoryChannel, data: any) {
    if (!this.eventHistory.has(channel)) {
      this.eventHistory.set(channel, []);
    }
    const history = this.eventHistory.get(channel)!;
    history.push({ data, timestamp: Date.now() });
    if (history.length > 100) history.shift();

    this.subscribers.get(channel)?.forEach(handler => {
      try {
        handler(data);
      } catch (e) {
        console.error(`[MemoryBus] Handler error on channel ${channel}:`, e);
      }
    });

    // Also write to L1 for recent context
    memory.write(MemoryLayer.L1, `evt_${channel}_${Date.now()}`, data, { channel, ttl: 3600000 });
  }

  static history(channel: MemoryChannel, n: number = 10): any[] {
    return (this.eventHistory.get(channel) || []).slice(-n);
  }
}

export class IndexRecall {
  static trigramSimilarity(s1: string, s2: string): number {
    const getTrigrams = (str: string) => {
      const s = str.toLowerCase();
      const trigrams = new Set<string>();
      for (let i = 0; i < s.length - 2; i++) {
        trigrams.add(s.substring(i, i + 3));
      }
      return trigrams;
    };

    const t1 = getTrigrams(s1);
    const t2 = getTrigrams(s2);
    if (t1.size === 0 || t2.size === 0) return 0;

    let intersection = 0;
    for (const t of t1) {
      if (t2.has(t)) intersection++;
    }
    return (2 * intersection) / (t1.size + t2.size);
  }

  static fuzzySearch(query: string, entries: MemoryEntry[]): MemoryEntry[] {
    return entries
      .map(entry => {
        const content = `${entry.key} ${JSON.stringify(entry.value)}`;
        const score = this.trigramSimilarity(query, content);
        return { entry, score };
      })
      .filter(item => item.score > 0.1)
      .sort((a, b) => b.score - a.score)
      .map(item => item.entry);
  }
}

export class FrameworkFlask {
  private static flasks: Map<string, any> = new Map();

  static setFlask(name: string, data: any) {
    this.flasks.set(name, data);
    MemoryBus.publish('session-events', { type: 'flask_update', name });
  }

  static getFlask(name: string): any {
    return this.flasks.get(name);
  }

  static listFlasks(): string[] {
    return Array.from(this.flasks.keys());
  }
}

export class ContainerBrain {
  static async init() {
    console.log("[Brain] Initializing ContainerBrain...");
    // Load NWU meta-rules into L0
    const policies = nwuPolicyMemory.getAllPolicies();
    policies.forEach(p => memory.write(MemoryLayer.L0, `policy_${p.id}`, p));
    MemoryBus.publish('nwu-policy', { type: 'INIT', count: policies.length });

    // Load assessment standards into L0
    const standards = assessmentStandards.getMarkingBands();
    memory.write(MemoryLayer.L0, "marking_bands", standards);
    MemoryBus.publish('assessment-standards', { type: 'INIT_BANDS' });

    console.log("[Brain] ContainerBrain online.");
  }

  static getStatus() {
    return {
      memory: memory.getSystemMemoryStatus(),
      flasks: FrameworkFlask.listFlasks(),
      busActive: true
    };
  }
}

