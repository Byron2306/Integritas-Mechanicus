/**
 * KnowEdge MemoryBus
 * Lightweight event bus for internal system communication.
 */
class MemoryBus {
  private static instance: MemoryBus;
  private channels: Map<string, any[]> = new Map();
  private subscribers: Map<string, Function[]> = new Map();

  constructor() {
    if (MemoryBus.instance) return MemoryBus.instance;
    MemoryBus.instance = this;
  }

  publish(channel: string, event: object) {
    const timestamp = Date.now();
    const eventWithMetadata = { ...event, timestamp };
    
    // Store in history
    if (!this.channels.has(channel)) {
      this.channels.set(channel, []);
    }
    this.channels.get(channel)?.push(eventWithMetadata);

    console.log(`[MemoryBus:${channel}]`, eventWithMetadata);

    // Notify subscribers
    const channelSubs = this.subscribers.get(channel) || [];
    channelSubs.forEach(cb => {
      try {
        cb(eventWithMetadata);
      } catch (err) {
        console.error(`MemoryBus error in subscriber for ${channel}:`, err);
      }
    });

    return eventWithMetadata;
  }

  subscribe(channel: string, cb: Function) {
    if (!this.subscribers.has(channel)) {
      this.subscribers.set(channel, []);
    }
    this.subscribers.get(channel)?.push(cb);
    
    // Return unsubscribe function
    return () => {
      const subs = this.subscribers.get(channel) || [];
      this.subscribers.set(channel, subs.filter(s => s !== cb));
    };
  }

  getHistory(channel: string) {
    return this.channels.get(channel) || [];
  }
}

export const memoryBus = new MemoryBus();
