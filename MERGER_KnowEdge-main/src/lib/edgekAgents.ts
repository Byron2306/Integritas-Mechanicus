/**
 * EdgeK Agents Framework
 * Core architecture for session-aware task execution and skill crystallization.
 */

import { memory, MemoryLayer, MemoryBus } from './memory';
import { callGemini } from './models/gemini';

export enum AgentRole {
  CONDUCTOR = "CONDUCTOR",
  RESEARCH = "ResearchAgent",
  INTEGRITY = "IntegrityAgent",
  CITATION = "CitationAgent",
  SOCRATIC = "SocraticAgent",
  FORENSIC = "ForensicAgent"
}

export interface StateLedgerEntry {
  agentId: string;
  role: AgentRole;
  timestamp: number;
  finding: string;
  confidence: number;
  metadata?: any;
}

export class StateLedger {
  private static ledger: StateLedgerEntry[] = [];

  static write(entry: StateLedgerEntry) {
    this.ledger.push(entry);
    MemoryBus.publish('agent-findings', entry);
  }

  static read(): StateLedgerEntry[] {
    return [...this.ledger];
  }

  static clear() {
    this.ledger = [];
  }
}

export class AgentBus {
  static publish(event: string, payload: any) {
    MemoryBus.publish('session-events', { type: 'AGENT_EVENT', event, payload });
  }

  static subscribe(handler: (data: any) => void) {
    return MemoryBus.subscribe('session-events', (data) => {
      if (data.type === 'AGENT_EVENT') handler(data);
    });
  }
}

export interface AgentDescriptor {
  role: AgentRole;
  systemPrompt: string;
  toolDeclarations?: any[];
}

export class EdgeKAgent {
  public id: string;
  public role: AgentRole;
  private systemPrompt: string;
  private tools: any[];

  constructor(descriptor: AgentDescriptor) {
    this.id = `agent_${descriptor.role}_${Math.random().toString(36).substring(7)}`;
    this.role = descriptor.role;
    this.systemPrompt = descriptor.systemPrompt;
    this.tools = descriptor.toolDeclarations || [];
  }

  async executeLoop(task: string, context: string): Promise<string> {
    AgentBus.publish('AGENT_START', { id: this.id, role: this.role, task });
    
    try {
      const prompt = `
        System: ${this.systemPrompt}
        Context: ${context}
        Task: ${task}
        
        Execute the task and provide findings. Use tools if available.
      `;

      // Simplified for now - real function calling would involve iterative message passing
      const result = await callGemini(prompt, { 
        model: "gemini-2.0-flash",
        tools: this.tools.length > 0 ? [{ functionDeclarations: this.tools }] : undefined
      });

      const finding = {
        agentId: this.id,
        role: this.role,
        timestamp: Date.now(),
        finding: result,
        confidence: 0.9 // TODO: extract from result
      };

      StateLedger.write(finding);
      AgentBus.publish('AGENT_SUCCESS', { id: this.id, finding: result });
      return result;
    } catch (e) {
      AgentBus.publish('AGENT_ERROR', { id: this.id, error: String(e) });
      throw e;
    }
  }
}

const AGENT_CONFIGS: Record<AgentRole, AgentDescriptor> = {
  [AgentRole.CONDUCTOR]: {
    role: AgentRole.CONDUCTOR,
    systemPrompt: "You are the Agent Swarm Conductor. Orchestrate specialized agents to solve complex tasks."
  },
  [AgentRole.RESEARCH]: {
    role: AgentRole.RESEARCH,
    systemPrompt: "You are the ResearchAgent. Use web research tools to gather data.",
    toolDeclarations: [
      {
        name: "fetchURL",
        description: "Fetches content from a URL via the research backend",
        parameters: {
          type: "OBJECT",
          properties: {
            url: { type: "STRING", description: "The URL to fetch" }
          },
          required: ["url"]
        }
      }
    ]
  },
  [AgentRole.INTEGRITY]: {
    role: AgentRole.INTEGRITY,
    systemPrompt: "You are the IntegrityAgent. Analyze text for AI characteristics and ethical compliance."
  },
  [AgentRole.CITATION]: {
    role: AgentRole.CITATION,
    systemPrompt: "You are the CitationAgent. Verify academic citations and reference formats (APA 7th)."
  },
  [AgentRole.SOCRATIC]: {
    role: AgentRole.SOCRATIC,
    systemPrompt: "You are the SocraticAgent. Challenge assumptions and provide deep pedagogical critique."
  },
  [AgentRole.FORENSIC]: {
    role: AgentRole.FORENSIC,
    systemPrompt: "You are the ForensicAgent. Perform deep pattern analysis and solve complex logic puzzles."
  }
};

export class AgentConductor {
  private agents: Map<string, EdgeKAgent> = new Map();

  spawn(role: AgentRole): string {
    const config = AGENT_CONFIGS[role];
    const agent = new EdgeKAgent(config);
    this.agents.set(agent.id, agent);
    return agent.id;
  }

  kill(id: string) {
    this.agents.delete(id);
  }

  async dispatch(task: string, roles: AgentRole[]): Promise<any[]> {
    const agentIds = roles.map(r => this.spawn(r));
    
    // Recursive loop (max 3)
    let currentTask = task;
    let results: any[] = [];

    for (let i = 0; i < 3; i++) {
      console.log(`[Conductor] Iteration ${i + 1} for task: ${currentTask}`);
      const promises = agentIds.map(id => {
        const agent = this.agents.get(id);
        return agent ? agent.executeLoop(currentTask, JSON.stringify(results)) : Promise.resolve(null);
      });

      const iterationResults = await Promise.allSettled(promises);
      results = iterationResults.map(r => r.status === 'fulfilled' ? r.value : `Error: ${r.reason}`);

      // Self-improvement check
      if (this.isTaskComplete(results)) break;
      currentTask = `The previous results were ${JSON.stringify(results)}. Some aspects are missing or failed. Refine and complete.`;
    }

    // cleanup
    agentIds.forEach(id => this.kill(id));
    return results;
  }

  private isTaskComplete(results: any[]): boolean {
    // Simple heuristic: if any results contain "SUCCESS" or lack distinctive error strings
    return results.every(r => typeof r === 'string' && !r.startsWith('Error:'));
  }

  broadcast(message: string) {
    AgentBus.publish('BROADCAST', { message });
  }

  recall() {
    return StateLedger.read();
  }
}

export const conductorInstance = new AgentConductor();

export function getAgentManifest() {
  return AGENT_CONFIGS;
}

