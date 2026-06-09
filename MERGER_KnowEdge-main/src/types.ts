export type UserRole = 'Admin' | 'User' | 'Viewer';

export interface UserProfile {
  uid: string;
  email: string;
  displayName: string;
  role: UserRole;
  createdAt: any;
}

export interface Architecture {
  id: string;
  name: string;
  content: string;
  uploadedAt: any;
  uid: string;
  isValid?: boolean;
  validationError?: string;
  hash: string;
  vector?: number[];
  metadata?: Record<string, any>;
  version?: number;
  lastModified?: string;
}

export interface ArchitectureVersion {
  id: string;
  archId: string;
  content: string;
  version: number;
  createdAt: any;
  uid: string;
  hash: string;
  changeSummary?: string;
}

export interface Run {
  id: string;
  uid: string;
  archAId?: string;
  archBId?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'REGRESSION_BLOCK';
  currentPhase: number;
  progress: number;
  startedAt?: any;
  completedAt?: any;
}

export interface Telemetry {
  id: string;
  runId: string;
  phaseId: string;
  message: string;
  timestamp: any;
  agentId: string;
  lane?: 'explore' | 'commit';
}

export interface Receipt {
  id: string;
  runId: string;
  provider: string;
  endpoint: string;
  timestamp: any;
  hash: string;
  status: 'verified' | 'unverified' | 'conflicted';
}

export interface Handshake {
  id: string;
  uid: string;
  timestamp: any;
  status: 'online' | 'degraded' | 'offline';
  latency: number;
  echo: boolean;
}

export interface Artifact {
  id: string;
  runId: string;
  type: string;
  content: string;
  hash: string;
  vector?: number[];
}
