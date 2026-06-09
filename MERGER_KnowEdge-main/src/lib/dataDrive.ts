import { MemoryBus } from './memory';
import { AgentBus } from './edgekAgents';

export interface DataPayload {
  source: string;
  target: string;
  timestamp: number;
  metadata: any;
}

class DataDriveEngine {
  private status: 'IDLE' | 'ACTIVE' | 'ROUTING' = 'IDLE';
  private currentPayload: DataPayload | null = null;

  init() {
    console.log("[DataDrive] Engine Initialized. Data highways established.");
    this.status = 'ACTIVE';
    MemoryBus.publish('session-events' as any, { type: 'DATADRIVE_STATUS', status: 'ACTIVE' });
  }

  async ingest(sourceArtifact: string, targetArtifact: string) {
    this.status = 'ROUTING';
    this.currentPayload = {
      source: sourceArtifact,
      target: targetArtifact,
      timestamp: Date.now(),
      metadata: { node: 'LOCAL_DATADRIVE_01' }
    };
    
    console.log("[DataDrive] Ingesting multi-artifact stream...");
    await this.route(this.currentPayload);
  }

  private async route(payload: DataPayload) {
    const targets = ['Detection Lab', 'ERTP', 'EdgeK Swarm', 'MEM5 Bus', 'Oxford Lab'];
    
    for (const target of targets) {
      console.log(`[DataDrive] Routing to ${target}...`);
      AgentBus.publish('WS_TELEMETRY', { 
        event: 'DATADRIVE_ROUTING', 
        payload: { target, timestamp: Date.now() } 
      });
      // Block 4: 1s per target routing
      await new Promise(r => setTimeout(r, 1000));
    }

    this.status = 'ACTIVE';
    MemoryBus.publish('session-events' as any, { type: 'DATADRIVE_ROUTING_COMPLETE', payload });
  }

  getStatus() {
    return this.status;
  }
}

export const dataDrive = new DataDriveEngine();
