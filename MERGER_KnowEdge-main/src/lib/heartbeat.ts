import { memory, MemoryLayer, MemoryBus } from './memory';
import { nwuPolicyMemory } from './nwuPolicyMemory';
import { assessmentStandards } from './assessmentStandardsMemory';

export type BackendStatus = 'online' | 'offline' | 'checking';

class HeartbeatService {
  private interval: any = null;
  private subscribers: ((status: BackendStatus) => void)[] = [];
  private currentStatus: BackendStatus = 'checking';
  private lastPolicyRefresh: number = 0;
  private readonly POLICY_REFRESH_INTERVAL = 3600000; // 1 hour

  /**
   * Starts periodic heartbeat at a set interval.
   */
  start(intervalMs: number = 30000) {
    if (this.interval) return;
    
    // Initial beat
    this.beat();
    
    const schedule = () => {
      this.interval = setTimeout(async () => {
        await this.beat();
        schedule();
      }, intervalMs);
    };
    schedule();

    // Event-driven update from WebSocket (relayed via MemoryBus)
    MemoryBus.subscribe('session-events' as any, (data: any) => {
      if (data.type === 'SYSTEM_HEALTH') {
        const lastStatus = this.currentStatus;
        this.currentStatus = data.payload.ollama_online ? 'online' : 'offline';
        if (this.currentStatus !== lastStatus) {
            this.notify(this.currentStatus);
        }
        // console.log("[EVENT-HEARTBEAT] Health updated via WebSocket broadcast.");
      }
    });
  }

  /**
   * Single heartbeat logic.
   */
  async beat() {
    // a) Write L1 memory entry for last beat
    memory.write(MemoryLayer.L1, "last_beat", Date.now());

    // b) Check Python backend health silently
    const lastStatus = this.currentStatus;
    try {
      const res = await fetch('/api/health'); // Python health endpoint mapped to /api/health usually in server.ts
      if (res.ok) {
        this.currentStatus = 'online';
      } else {
        this.currentStatus = 'offline';
      }
    } catch (e) {
      this.currentStatus = 'offline';
      // Silently swallow errors in sandbox mode
    }

    // c) Update subscribers if status changed
    if (this.currentStatus !== lastStatus) {
      this.notify(this.currentStatus);
    }

    // d) Prune expired memory entries
    memory.prune();

    // e) Increment heartbeat count in L2
    const currentCount = memory.read(MemoryLayer.L2, "heartbeat_count")?.value || 0;
    memory.write(MemoryLayer.L2, "heartbeat_count", currentCount + 1);

    // f) Refresh NWU Policies and Assessment Standards every hour
    const now = Date.now();
    if (now - this.lastPolicyRefresh > this.POLICY_REFRESH_INTERVAL) {
      nwuPolicyMemory.refreshPolicies();
      assessmentStandards.refreshStandards();
      this.lastPolicyRefresh = now;
      console.debug('[HEARTBEAT] NWU Policies and Assessment Standards refreshed');
    }
  }

  /**
   * Clears the interval.
   */
  stop() {
    if (this.interval) {
      clearTimeout(this.interval);
      this.interval = null;
    }
  }

  onStatusChange(cb: (status: BackendStatus) => void): () => void {
    this.subscribers.push(cb);
    cb(this.currentStatus); // Immediate sync
    return () => {
      this.subscribers = this.subscribers.filter(s => s !== cb);
    };
  }

  private notify(status: BackendStatus) {
    this.subscribers.forEach(s => s(status));
  }

  getStatus(): BackendStatus {
    return this.currentStatus;
  }
}

export const heartbeat = new HeartbeatService();
