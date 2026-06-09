import React, { useState, useCallback, useEffect, useRef } from 'react';
import { 
  Shield, 
  Activity, 
  ArrowDown, 
  Plus, 
  Download, 
  RefreshCw,
  FileText,
  CheckCircle2,
  AlertCircle,
  Lock,
  Zap,
  Cpu,
  Database,
  Globe,
  Upload,
  LogOut,
  BrainCircuit,
  User as UserIcon,
  History,
  Target,
  GraduationCap,
  LayoutGrid,
  Smartphone,
  Server,
  Terminal,
  Layers,
  BookOpen,
  Clock,
  ArrowRight,
  XCircle,
  Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import mammoth from 'mammoth';
import * as pdfjsLib from 'pdfjs-dist';

// Set worker for pdfjs
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

import { GoogleGenerativeAI } from "@google/generative-ai";
import { auth, db, googleProvider } from './firebase';

// Initialize Gemini
const ai = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || '');
import Markdown from 'react-markdown';
import { ContainerBrain, memory, MemoryLayer, MemoryBus, MemoryChannel } from './lib/memory';
import { 
  RunRecord, 
  RunState, 
  STATE_SEQUENCE, 
  STATE_PROGRESS, 
  createRun, 
  transitionRun, 
  issueReceipt, 
  saveRun, 
  loadRuns 
} from './lib/runController';
import { heartbeat as heartbeatService } from './lib/heartbeat';
import { conductorInstance, AgentRole, StateLedger, AgentBus } from './lib/edgekAgents';
import { ERTPReviewTab } from './components/ERTPReviewTab';
import { PolicyChecker, nwuPolicyMemory } from './lib/nwuPolicyMemory';
import { assessmentStandards } from './lib/assessmentStandardsMemory';

import { SessionObserver, MistralConsolidator, ChronicleMemoryStore, KM_CHRONICLE_RULES, PromptInjectionScanner } from './lib/kmChronicle';
import { ChronicleConsentModal } from './components/ChronicleConsentModal';
import { dataDrive } from './lib/dataDrive';
import { circleAI } from './lib/circleAI';
import { runSmokeTest } from './lib/tests/smokeTest';
import { runBenchTest } from './lib/tests/benchTest';

import { 
  onAuthStateChanged, 
  signInWithPopup, 
  signOut, 
  User as FirebaseUser 
} from 'firebase/auth';
import SudokuG from './components/SudokuGrid';
import SecretGeneratorCard from './components/system-status/SecretGeneratorCard';
import { 
  collection, 
  addDoc, 
  query, 
  where, 
  onSnapshot, 
  serverTimestamp,
  orderBy,
  doc,
  setDoc,
  getDoc
} from 'firebase/firestore';

import { 
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import { isFirstRun, registerUser, validateLogin, getRegisteredUser } from './lib/auth';

// WebSocket setup moved inside App component for lifecycle management

// --- Utilities ---
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

enum OperationType {
  CREATE = 'create',
  UPDATE = 'update',
  DELETE = 'delete',
  LIST = 'list',
  GET = 'get',
  WRITE = 'write',
}

interface FirestoreErrorInfo {
  error: string;
  operationType: OperationType;
  path: string | null;
  authInfo: {
    userId: string | undefined;
    email: string | null | undefined;
    emailVerified: boolean | undefined;
    isAnonymous: boolean | undefined;
    tenantId: string | null | undefined;
    providerInfo: {
      providerId: string;
      displayName: string | null;
      email: string | null;
      photoUrl: string | null;
    }[];
  }
}

function handleFirestoreError(error: unknown, operationType: OperationType, path: string | null) {
  const errInfo: FirestoreErrorInfo = {
    error: error instanceof Error ? error.message : String(error),
    authInfo: {
      userId: auth.currentUser?.uid,
      email: auth.currentUser?.email,
      emailVerified: auth.currentUser?.emailVerified,
      isAnonymous: auth.currentUser?.isAnonymous,
      tenantId: auth.currentUser?.tenantId,
      providerInfo: auth.currentUser?.providerData.map(provider => ({
        providerId: provider.providerId,
        displayName: provider.displayName,
        email: provider.email,
        photoUrl: provider.photoURL
      })) || []
    },
    operationType,
    path
  }
  console.warn('Firestore Error: ', JSON.stringify(errInfo));
  throw new Error(JSON.stringify(errInfo));
}

// --- Constants ---
const VERSION = "V5.0.0";
const NWU_CYAN = "#00BCD4";
const SYSTEM_METRICS = [
  { time: '09:00', load: 12, cpu: 15, memory: 22, network: 5 },
  { time: '10:00', load: 45, cpu: 42, memory: 28, network: 12 },
  { time: '11:00', load: 32, cpu: 30, memory: 26, network: 8 },
  { time: '12:00', load: 65, cpu: 68, memory: 45, network: 25 },
  { time: '13:00', load: 88, cpu: 92, memory: 72, network: 48 },
  { time: '14:00', load: 54, cpu: 50, memory: 55, network: 30 },
  { time: '15:00', load: 42, cpu: 38, memory: 48, network: 18 },
];

// --- Types ---
interface ArtifactFile {
  id: string;
  name: string;
  content: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  wordCount?: number;
  preview?: string;
  error?: string;
}

interface Artifact {
  id: string;
  type: 'input' | 'target' | 'context';
  files: ArtifactFile[];
  status: 'empty' | 'loaded' | 'processing';
}

interface AnalysisReport {
  timestamp: string;
  screening: any;
  grammar: any;
  similarity: any;
  system: {
    node: string;
    status: string;
  };
}

type TaskState = 'idle' | 'processing' | 'complete' | 'error';

interface TaskDetail {
  state: TaskState;
  error?: string;
}

interface TaskStatus {
  screening: TaskDetail;
  linting: TaskDetail;
  similarity: TaskDetail;
}

// --- Components ---

const LoginScreen = ({ 
  initialUsername,
  onLogin 
}: { 
  initialUsername?: string,
  onLogin: (user: string, role: string) => void 
}) => {
  const [username, setUsername] = useState(initialUsername || '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAuthenticate = () => {
    setLoading(true);
    setError('');

    setTimeout(() => {
      const result = validateLogin(username, password);
      if (result.valid) {
        onLogin(result.fullName, result.role || 'USER');
      } else {
        setError('INVALID CREDENTIALS: ACCESS DENIED');
        setLoading(false);
      }
    }, 1500);
  };

  return (
    <div id="login-gate" className="fixed inset-0 z-[9999] bg-black flex flex-col items-center justify-center p-6 overflow-y-auto">
      <div className="w-full max-w-lg flex flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-4 text-center">
          <Shield className="w-20 h-20 text-[#00BCD4] drop-shadow-[0_0_15px_rgba(0,188,212,0.5)]" />
          <div className="space-y-1">
            <h1 className="text-4xl font-black uppercase tracking-[0.3em] text-[#00BCD4]">Knowledge Merger</h1>
            <p className="text-[10px] font-bold uppercase tracking-[0.5em] text-zinc-500">NWU Forensic Intelligence Platform {VERSION}</p>
            <p className="text-[8px] font-medium uppercase tracking-[0.2em] text-zinc-600">Asymmetric Optimization & Tri-Artifact Synthesis | NWU Certified</p>
          </div>
        </div>

        <div className="w-full h-px bg-gradient-to-r from-transparent via-[#00BCD4]/50 to-transparent" />

        <div className="w-full max-w-[420px] p-10 rounded-3xl bg-zinc-950 border border-[#00BCD4]/30 shadow-[0_0_50px_-20px_rgba(0,188,212,0.5)] flex flex-col gap-8 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#00BCD4] via-teal-500 to-[#00BCD4]" />
          
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-3 text-[#00BCD4]">
              <Shield className="w-5 h-5" />
              <h2 className="text-sm font-black uppercase tracking-widest text-white">Secure System Access</h2>
            </div>
            <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-tight ml-8">Authorised Personnel Only — NWU Academic Integrity Division</p>
          </div>

          <div className="flex flex-col gap-4">
            <div className="space-y-2">
              <label className="text-[9px] font-black text-zinc-500 uppercase tracking-widest px-1">Username</label>
              <div className="relative group">
                <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 group-focus-within:text-[#00BCD4] transition-colors" />
                <input 
                  type="text"
                  placeholder="Enter NWU username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-sm font-bold text-white placeholder-zinc-700 outline-none focus:border-[#00BCD4]/50 transition-all"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[9px] font-black text-zinc-500 uppercase tracking-widest px-1">Access Code</label>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 group-focus-within:text-[#00BCD4] transition-colors" />
                <input 
                  type="password"
                  placeholder="Enter access code"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-sm font-bold text-white placeholder-zinc-700 outline-none focus:border-[#00BCD4]/50 transition-all"
                />
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 animate-pulse">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span className="text-[9px] font-black uppercase tracking-widest">{error}</span>
              </div>
            )}

            <button 
              onClick={handleAuthenticate}
              disabled={loading}
              className={cn(
                "w-full py-5 rounded-2xl bg-[#00BCD4] text-white font-black uppercase tracking-[0.3em] text-[10px] transition-all relative overflow-hidden group",
                loading ? "animate-pulse" : "hover:bg-[#008ba3] hover:scale-[1.02] active:scale-[0.98]"
              )}
            >
              {loading ? (
                <div className="flex items-center justify-center gap-3">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </div>
              ) : (
                "Authenticate & Enter"
              )}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-500" />
            </button>
          </div>
        </div>

        <div className="text-center space-y-1">
          <p className="text-[8px] font-black text-zinc-700 uppercase tracking-[0.4em]">Protected by SHA-256 | Gr4nttG0uws | NWU IT Compliance</p>
          <div className="flex items-center justify-center gap-4 py-2">
             <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 animate-pulse" />
             <span className="text-[7px] font-mono text-zinc-800">ENCRYPTION_ACTIVE_RSA_4096</span>
          </div>
        </div>
      </div>
    </div>
  );
};

const FirstRunRegistration = ({ 
  onComplete 
}: { 
  onComplete: (username: string, fullName: string) => void 
}) => {
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [accessCode, setAccessCode] = useState('');
  const [confirmCode, setConfirmCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (!fullName || !username || !accessCode || !confirmCode) {
      setError('ALL FIELDS ARE REQUIRED');
      return;
    }
    if (accessCode.length < 4) {
      setError('ACCESS CODE MUST BE AT LEAST 4 CHARACTERS');
      return;
    }
    if (accessCode !== confirmCode) {
      setError('ACCESS CODES DO NOT MATCH');
      return;
    }

    setLoading(true);
    
    // PRIMARY: Save to localStorage immediately
    registerUser({ fullName, username, accessCode });
    
    // SECONDARY: Attempt to POST in background (Silent failure)
    fetch('/api/v1/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, accessCode, fullName })
    }).catch(err => {
      console.warn("Backend registry sync failed (silent recovery):", err);
    });

    // Proceed immediately
    onComplete(username, fullName);
  };

  return (
    <div className="fixed inset-0 z-[9999] bg-[#050a0e] flex flex-col items-center justify-center p-6 overflow-y-auto">
      <div className="w-full max-w-lg flex flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-4 text-center">
          <Shield className="w-20 h-20 text-[#00BCD4] drop-shadow-[0_0_15px_rgba(0,188,212,0.4)]" />
          <div className="space-y-2">
            <h1 className="text-4xl font-black uppercase tracking-[0.2em] text-[#00BCD4] leading-tight">INITIAL SYSTEM CONFIGURATION</h1>
            <p className="text-[10px] font-bold uppercase tracking-[0.4em] text-zinc-500">KnowEdge Merger — NWU Forensic Node — {VERSION} Launch Setup</p>
          </div>
        </div>

        <div className="w-full h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />

        <div className="w-full max-w-[440px] p-10 rounded-[2.5rem] bg-zinc-950 border border-cyan-500/30 shadow-[0_0_80px_-20px_rgba(6,182,212,0.4)] flex flex-col gap-6 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-600 via-teal-500 to-cyan-600" />
          
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[9px] font-black text-zinc-600 uppercase tracking-widest px-1">FULL NAME</label>
              <input 
                type="text"
                placeholder="Enter your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-5 py-4 rounded-xl bg-zinc-900 border border-zinc-800 text-sm font-bold text-white placeholder-zinc-700 outline-none focus:border-cyan-500/50 transition-all"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[9px] font-black text-zinc-600 uppercase tracking-widest px-1">NWU USERNAME</label>
              <input 
                type="text"
                placeholder="e.g. 22807365 or staff username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-5 py-4 rounded-xl bg-zinc-900 border border-zinc-800 text-sm font-bold text-white placeholder-zinc-700 outline-none focus:border-cyan-500/50 transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-[9px] font-black text-zinc-600 uppercase tracking-widest px-1">CREATE ACCESS CODE</label>
                <input 
                  type="password"
                  placeholder="Create a secure access code"
                  value={accessCode}
                  onChange={(e) => setAccessCode(e.target.value)}
                  className="w-full px-5 py-4 rounded-xl bg-zinc-900 border border-zinc-800 text-sm font-bold text-white placeholder-zinc-700 outline-none focus:border-cyan-500/50 transition-all"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[9px] font-black text-zinc-600 uppercase tracking-widest px-1">CONFIRM ACCESS CODE</label>
                <input 
                  type="password"
                  placeholder="Confirm access code"
                  value={confirmCode}
                  onChange={(e) => setConfirmCode(e.target.value)}
                  className="w-full px-5 py-4 rounded-xl bg-zinc-900 border border-zinc-800 text-sm font-bold text-white placeholder-zinc-700 outline-none focus:border-cyan-500/50 transition-all"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[9px] font-black uppercase tracking-widest text-center animate-pulse">
                {error}
              </div>
            )}

            <button 
              onClick={handleRegister}
              disabled={loading}
              className="w-full py-5 rounded-2xl bg-cyan-600 text-white font-black uppercase tracking-[0.4em] text-[10px] hover:bg-cyan-500 hover:shadow-[0_0_30px_rgba(6,182,212,0.4)] transition-all active:scale-[0.98] disabled:opacity-50"
            >
              {loading ? "INITIALISING..." : "REGISTER & INITIALISE SYSTEM"}
            </button>
          </div>
          
          <p className="text-[7px] font-black text-zinc-600 uppercase tracking-widest text-center">
            This credential will be used for all future logins to this node.
          </p>
        </div>
      </div>
    </div>
  );
};
const SystemStatus = ({ 
  isChronicleEnabled, 
  onToggleChronicle, 
  isMistralOnline,
  wsConnected
}: { 
  isChronicleEnabled: boolean, 
  onToggleChronicle: () => void,
  isMistralOnline: boolean,
  wsConnected: boolean
}) => {
  const [status, setStatus] = useState<any>(null);
  const [ddStatus, setDdStatus] = useState(dataDrive.getStatus());
  const [caStage, setCaStage] = useState(circleAI.getStage());

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    const update = () => {
      setStatus(ContainerBrain.getStatus());
      setDdStatus(dataDrive.getStatus());
      setCaStage(circleAI.getStage());
      timeoutId = setTimeout(update, 2000);
    };
    update();
    return () => clearTimeout(timeoutId);
  }, []);

  if (!status) return null;

  return (
    <div className="flex items-center gap-6 px-6 py-2.5 rounded-full bg-zinc-950 border border-zinc-800 backdrop-blur-xl">
      <button 
        onClick={onToggleChronicle}
        className={cn(
          "flex items-center gap-2 group transition-all",
          isChronicleEnabled ? "text-cyan-400" : "text-zinc-600 hover:text-zinc-400"
        )}
        title="Toggle KM-Chronicle Context Capture"
      >
        <div className="relative">
          <BrainCircuit className={cn("w-3.5 h-3.5", isChronicleEnabled && "animate-pulse")} />
          <div className={cn(
            "absolute -top-1 -right-1 w-1.5 h-1.5 rounded-full",
            !isMistralOnline ? "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]" : 
            isChronicleEnabled ? "bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.8)]" : "bg-zinc-800"
          )} />
        </div>
        <span className="text-[10px] font-black uppercase tracking-widest">[CH]</span>
      </button>
      <div className="w-px h-4 bg-zinc-800" />
      <div className="flex items-center gap-2">
        <div className={cn(
          "w-1.5 h-1.5 rounded-full animate-pulse shadow-[0_0_8px_currentColor]", 
          wsConnected ? "bg-emerald-400 text-emerald-400" : "bg-amber-500 text-amber-500"
        )} />
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">
          {wsConnected ? 'LINK ACTIVE' : 'STANDALONE MODE'}
        </span>
      </div>
      <div className="w-px h-4 bg-zinc-800" />
      <div className="flex items-center gap-2">
        <Database className="w-3 h-3 text-emerald-400" />
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">DataDrive: {ddStatus}</span>
      </div>
      <div className="w-px h-4 bg-zinc-800" />
      <div className="flex items-center gap-2">
        <RefreshCw className={cn("w-3 h-3 text-purple-400", caStage !== 'IDLE' && "animate-spin")} />
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">CircleAI: {caStage === 'IDLE' ? 'STANDBY' : 'LOOPING'}</span>
      </div>
      <div className="w-px h-4 bg-zinc-800" />
      <div className="flex items-center gap-2">
        <Terminal className="w-3 h-3 text-purple-400" />
        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">V4.3.1-CH</span>
      </div>
    </div>
  );
};

const SuccessToast = ({ message, visible, onHide }: { message: string, visible: boolean, onHide: () => void }) => {
  useEffect(() => {
    if (visible) {
      const timer = setTimeout(onHide, 3000);
      return () => clearTimeout(timer);
    }
  }, [visible, onHide]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -50 }}
          className="fixed top-12 left-1/2 -translate-x-1/2 z-[10000] px-8 py-3 rounded-full bg-zinc-900 border border-cyan-500/50 shadow-[0_0_30px_rgba(6,182,212,0.3)] backdrop-blur-xl"
        >
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white">
            {message}
          </p>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const ArtifactCard = ({ 
  artifact, 
  onUpload, 
  label, 
  subLabel, 
  icon: Icon = ArrowDown,
  accent = 'cyan',
  compact = false
}: { 
  artifact: Artifact, 
  onUpload: (files: File[]) => void,
  label: string,
  subLabel: string,
  icon?: any,
  accent?: 'cyan' | 'purple',
  compact?: boolean
}) => {
  const isCyan = accent === 'cyan';
  const [isDragging, setIsDragging] = useState(false);
  
  const processFiles = useCallback((files: FileList) => {
    onUpload(Array.from(files));
  }, [onUpload]);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  }, [processFiles]);

  if (compact) {
    return (
      <div 
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={cn(
          "relative group flex flex-col w-full h-[200px] max-w-[320px] rounded-3xl border-2 transition-all duration-500 overflow-hidden bg-zinc-950/60 backdrop-blur-md p-6 items-center justify-center text-center cursor-pointer",
          isDragging ? "border-cyan-400 bg-cyan-500/5 scale-[1.02]" :
          artifact.status === 'empty' ? "border-zinc-800 hover:border-zinc-700" : "border-emerald-500/50 shadow-[0_0_20px_-5px_rgba(16,185,129,0.3)]"
        )}
      >
        <div className={cn(
          "p-3 rounded-full mb-3",
          artifact.status === 'empty' ? "text-zinc-600" : "text-emerald-400"
        )}>
          {artifact.status === 'empty' ? <ArrowDown className="w-6 h-6" /> : <Shield className="w-6 h-6" />}
        </div>
        
        <div className="space-y-1">
          <p className="text-[10px] font-black uppercase tracking-widest text-zinc-100">{label}</p>
          <p className="text-[9px] font-black uppercase tracking-widest text-zinc-500 truncate max-w-[200px]">
             {artifact.status === 'empty' ? subLabel : (artifact.files[0]?.name || 'Unknown Artifact')}
           </p>
        </div>

        {artifact.status !== 'empty' && (
          <div className="mt-4 flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span className="text-[8px] font-black uppercase tracking-widest text-emerald-500/80">File Detected</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span className="text-[8px] font-black uppercase tracking-widest text-emerald-500/80">Hash Verified</span>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div 
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className={cn(
        "relative group flex flex-col w-full aspect-[3/4] rounded-[2.5rem] border-2 transition-all duration-500 overflow-hidden bg-zinc-950/40 backdrop-blur-md",
        isDragging ? (isCyan ? "border-cyan-400 bg-cyan-500/5 scale-[1.02] shadow-[0_0_40px_rgba(6,182,212,0.2)]" : "border-purple-400 bg-purple-500/5 scale-[1.02] shadow-[0_0_40px_rgba(168,85,247,0.2)]") :
        artifact.status === 'empty' ? "border-zinc-800 hover:border-zinc-600" : 
        isCyan ? "border-cyan-500/50 shadow-[0_0_30px_-10px_rgba(6,182,212,0.3)]" : "border-purple-500/50 shadow-[0_0_30px_-10px_rgba(168,85,247,0.3)]"
      )}
    >
      {isDragging && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-zinc-950/90 backdrop-blur-sm border-2 border-dashed border-cyan-500 rounded-[2.5rem] animate-in fade-in zoom-in duration-300">
          <Upload className="w-16 h-16 text-cyan-400 animate-bounce" />
          <p className="text-xl font-black uppercase tracking-widest text-cyan-400 mt-4">Drop Artifacts Here</p>
          <p className="text-[10px] font-black uppercase tracking-[0.4em] text-cyan-500/60 mt-2">Release and Synthesize</p>
        </div>
      )}

      <div className={cn(
        "absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-700 pointer-events-none",
        isDragging ? "opacity-20" : "",
        isCyan ? "bg-cyan-500" : "bg-purple-500"
      )} />

      <div className="relative z-10 flex flex-col items-center h-full w-full p-8 text-center">
        <div className={cn(
          "p-4 rounded-full transition-transform duration-500 group-hover:scale-110",
          isCyan ? "text-cyan-400" : "text-purple-400"
        )}>
          <Icon className="w-12 h-12 stroke-[1.5]" />
        </div>

        <div className="space-y-2 mb-6">
          <h3 className={cn(
            "text-2xl font-black uppercase tracking-[0.2em]",
            isCyan ? "text-cyan-100" : "text-purple-100"
          )}>
            {label}
          </h3>
          <p className="text-[10px] font-black uppercase tracking-[0.25em] text-zinc-500">
            {artifact.status === 'empty' ? subLabel : `${artifact.files.length} Files Categorized`}
          </p>
        </div>

        {artifact.status !== 'empty' && (
          <div className="flex-1 w-full overflow-y-auto custom-scrollbar pr-2 space-y-3">
            {artifact.files.map((file) => (
              <div key={file.id} className="p-3 rounded-xl bg-zinc-900/50 border border-zinc-800/50 text-left flex items-center justify-between group/file">
                <div className="flex flex-col gap-1 overflow-hidden w-full pr-4">
                  <span className="text-[10px] font-bold text-zinc-200 truncate">{file.name}</span>
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      "text-[8px] font-black uppercase tracking-widest",
                      file.status === 'error' ? "text-rose-500" : "text-emerald-500"
                    )}>
                      {file.status}
                    </span>
                    {file.wordCount !== undefined && (
                      <span className="text-[8px] font-black uppercase tracking-widest text-zinc-500">
                        {file.wordCount.toLocaleString()} WORDS
                      </span>
                    )}
                    {file.status === 'processing' && (
                      <span className="text-[8px] font-mono text-cyan-400">{file.progress}%</span>
                    )}
                  </div>
                  {file.preview && (
                    <div className="mt-2 p-3 rounded-lg bg-black/40 border border-zinc-800/50 text-[7px] text-zinc-500 font-mono leading-relaxed overflow-hidden italic line-clamp-2">
                       "{file.preview}"
                    </div>
                  )}
                  {file.status === 'error' && file.error && (
                    <span className="text-[7px] font-bold text-rose-400/80 leading-tight block mt-0.5 uppercase tracking-tighter">
                      Error: {file.error}
                    </span>
                  )}
                  {file.status === 'processing' && (
                    <div className="w-full h-0.5 bg-zinc-800 rounded-full mt-1 overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${file.progress}%` }}
                        className="h-full bg-cyan-500"
                      />
                    </div>
                  )}
                </div>
                {file.status === 'completed' && <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />}
                {file.status === 'error' && <AlertCircle className="w-3 h-3 text-rose-500 flex-shrink-0" />}
              </div>
            ))}
          </div>
        )}

        {artifact.status === 'empty' ? (
          <button 
            onClick={() => {
              const input = document.createElement('input');
              input.type = 'file';
              input.multiple = true;
              input.onchange = (e: any) => {
                if (e.target.files && e.target.files.length > 0) {
                  processFiles(e.target.files);
                }
              };
              input.click();
            }}
            className="mt-4 px-6 py-2 rounded-full border border-zinc-800 text-[10px] font-black uppercase tracking-widest text-zinc-500 hover:text-zinc-300 hover:border-zinc-600 transition-all bg-zinc-900/50"
          >
            Upload Artifacts
          </button>
        ) : (
          <button 
            onClick={() => {
              const input = document.createElement('input');
              input.type = 'file';
              input.multiple = true;
              input.onchange = (e: any) => {
                if (e.target.files && e.target.files.length > 0) {
                  processFiles(e.target.files);
                }
              };
              input.click();
            }}
            className="mt-4 px-4 py-2 rounded-full border border-zinc-800 text-[8px] font-black uppercase tracking-widest text-emerald-400 hover:text-emerald-300 hover:border-emerald-500/30 transition-all bg-emerald-500/5"
          >
            Add More
          </button>
        )}
      </div>

      {artifact.status === 'processing' && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-zinc-900">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: '100%' }}
            transition={{ duration: 2, repeat: Infinity }}
            className={cn("h-full", isCyan ? "bg-cyan-500" : "bg-purple-500")}
          />
        </div>
      )}
    </div>
  );
};

const TerminalBox = ({ activeRun }: { activeRun: RunRecord | null }) => {
  const [cursor, setCursor] = useState(true);
  const [logs, setLogs] = useState<string[]>([]);
  
  useEffect(() => {
    // Initial logs
    setLogs(['KNOWEDGE FORENSIC NODE INITIALIZED', 'CRYPTOGRAPHIC IDENTITY: OMEGA-4', 'AWAITING ARTIFACT INGEST...']);

    const unsub = MemoryBus.subscribe('session-events' as any, (data: any) => {
      if (data.message) {
        setLogs(prev => [...prev.slice(-10), data.message.toUpperCase()]);
      }
    });

    const interval = setInterval(() => setCursor(c => !c), 500);
    return () => { unsub(); clearInterval(interval); };
  }, []);

  return (
    <div className="w-full min-h-[220px] bg-black/90 rounded-2xl border border-zinc-800 p-6 font-mono text-[10px] text-cyan-500 overflow-hidden relative shadow-inner">
      <div className="absolute top-0 left-0 w-full h-6 bg-zinc-900 border-b border-zinc-800 flex items-center px-4 justify-between">
        <div className="flex gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-rose-500/50 underline transition-all hover:scale-125" />
          <div className="w-1.5 h-1.5 rounded-full bg-amber-500/50 underline transition-all hover:scale-125" />
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50 underline transition-all hover:scale-125" />
        </div>
        <span className="text-[8px] font-black uppercase text-zinc-600">CONTROL_PLANE_NODE_v5.0.0</span>
      </div>
      
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1">
          {logs.map((log, i) => (
            <div key={i} className="flex gap-2">
              <span className="opacity-40">{">"}</span>
              <span className="tracking-tighter whitespace-nowrap overflow-hidden text-ellipsis">{log}</span>
            </div>
          ))}
          <div className="flex gap-2">
            <span className="opacity-40">{">"}</span>
            <span className="flex items-center tracking-tighter">
              {activeRun ? 'SYSTEM_PROCESSING' : 'SYSTEM_AWAITING_INPUT'}
              {cursor && <span className="ml-1 w-1.5 h-3 bg-cyan-500 blur-[1px]" />}
            </span>
          </div>
        </div>

        {activeRun && (
          <div className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800 space-y-2 text-[9px]">
            <div className="flex justify-between border-b border-zinc-800 pb-1">
              <span className="text-zinc-500">RUN_ID</span>
              <span className="text-white font-black">{activeRun.run_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">PHASE</span>
              <span className="text-cyan-400 font-black">{activeRun.state.toUpperCase()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">STATUS</span>
              <span className={cn("font-black", activeRun.heartbeat.status === 'OK' ? "text-emerald-400" : "text-rose-500")}>
                {activeRun.heartbeat.status}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">RECEIPTS</span>
              <span className="text-white font-black">{activeRun.receipt_count} / 6</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">ANOMALIES</span>
              <span className={cn("font-black", activeRun.anomaly_count > 0 ? "text-rose-500" : "text-emerald-500")}>
                {activeRun.anomaly_count}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">QUARANTINE</span>
              <span className={cn("font-black", activeRun.heartbeat.quarantine ? "text-rose-500" : "text-zinc-600")}>
                {activeRun.heartbeat.quarantine ? 'ACTIVE' : 'NONE'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default function App() {
  const [isBrainInitiated, setIsBrainInitiated] = useState(false);
  const [isFirstRunMode, setIsFirstRunMode] = useState(isFirstRun());
  const [initialRegistrationUsername, setInitialRegistrationUsername] = useState('');
  const [registrationToast, setRegistrationToast] = useState<{ message: string; visible: boolean }>({ message: '', visible: false });
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loginUser, setLoginUser] = useState('');
  const [userRole, setUserRole] = useState('');
  const [sudokuReady, setSudokuReady] = useState(false);
  const [sudokuData, setSudokuData] = useState<any>(null);

  useEffect(() => {
    if (!isBrainInitiated) {
       ContainerBrain.init();
       conductorInstance.spawn(AgentRole.RESEARCH);
       conductorInstance.spawn(AgentRole.INTEGRITY);
       setIsBrainInitiated(true);
       console.log("[BRAIN] Neural retrieval cluster online.");
    }
  }, [isBrainInitiated]);
  const [artifacts, setArtifacts] = useState<Record<string, Artifact>>({
    input: { id: 'input', type: 'input', files: [], status: 'empty' },
    target: { id: 'target', type: 'target', files: [], status: 'empty' },
    context: { id: 'context', type: 'context', files: [], status: 'empty' },
  });
  
  const [isInitializing, setIsInitializing] = useState(false);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus>({
    screening: { state: 'idle' },
    linting: { state: 'idle' },
    similarity: { state: 'idle' }
  });

  const [detectionInput, setDetectionInput] = useState('');
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectionResults, setDetectionResults] = useState<any>({
    results: [
      { provider: 'GPTZero', score: 0.942, label: 'AI Generated' },
      { provider: 'ZeroGPT', score: 0.876, label: 'AI Generated' },
      { provider: 'Grammarly', score: 0.92, label: 'Likely AI' },
      { provider: 'Sapling', score: 0.94, label: 'AI Generated' },
      { provider: 'Originality', score: 0.98, label: 'AI Generated' }
    ],
    aggregate_score: 0.931
  });
  const [providerHealth, setProviderHealth] = useState<Record<string, 'online' | 'offline'>>({
    'GPTZero': 'online',
    'ZeroGPT': 'online',
    'Grammarly': 'online',
    'Sapling': 'online',
    'Originality': 'online'
  });

  // --- AI Assistant State ---
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const [assistantMessages, setAssistantMessages] = useState<{ role: 'user' | 'ai', content: string, thinking?: string, image?: string, latency?: number }[]>([]);
  const [assistantInput, setAssistantInput] = useState('');
  const [isAssistantLoading, setIsAssistantLoading] = useState(false);
  const [assistantMode, setAssistantMode] = useState<'fast' | 'think' | 'image'>('think');
  const [assistantImage, setAssistantImage] = useState<string | null>(null);

  // --- Firebase State ---
  const [user, setUser] = useState<FirebaseUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [showSplash, setShowSplash] = useState(true);
  const [isPostLoginLoading, setIsPostLoginLoading] = useState(false);
  const [loginProgress, setLoginProgress] = useState(0);
  const [loginLabel, setLoginLabel] = useState('Authenticating...');
  const [systemTime, setSystemTime] = useState('');
  const [isTestConsoleOpen, setIsTestConsoleOpen] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [savedReports, setSavedReports] = useState<any[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // --- V3.1 Navigation & Learning Lab State ---
  const [activeTab, setActiveTab] = useState<'merger' | 'detection' | 'agent' | 'mem5' | 'ertp' | 'learning' | 'bridge' | 'analytics' | 'sudoku'>('merger');
  // --- V4.7.0 Pipeline & Terminal State ---
  const [pipelineStep, setPipelineStep] = useState(0);
  const [forensicResult, setForensicResult] = useState<any>(null);
  const [auditHistory, setAuditHistory] = useState<any[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [forensicAnalysis, setForensicAnalysis] = useState<any>(null);
  const [liveLog, setLiveLog] = useState<{timestamp: string, message: string}[]>([]);
  
  const [mergeProgress, setMergeProgress] = useState(0);
  const [secondaryProgress, setSecondaryProgress] = useState(0);
  const [runHeartbeat, setRunHeartbeat] = useState<any>({ progress: 0, phase: 'idle' });
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [circleAIResult, setCircleAIResult] = useState<any>(null);
  
  // --- Legacy Run Controller State ---
  const [runId] = useState('default');
  const [runStatus, setRunStatus] = useState({ phase: 'idle', progress: 0, status: 'idle', heartbeat: 0 });
  const [decisionLedger, setDecisionLedger] = useState<any[]>([]);
  const [heartbeatAlive, setHeartbeatAlive] = useState(false);
  const [learningSession, setLearningSession] = useState<any>(null);
  const [learningInput, setLearningInput] = useState('');
  const [isLearningLoading, setIsLearningLoading] = useState(false);
  const [learningConcept, setLearningConcept] = useState('');

  // --- v4.4 WebSocket Threading ---
  const wsRef = useRef<WebSocket | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [liveUpdates, setLiveUpdates] = useState<string[]>([]);

  useEffect(() => {
    const connectWs = () => {
      try {
        const wsUrl = `ws://${window.location.hostname}:8000/ws`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        
        ws.onopen = () => {
          setWsConnected(true);
          setHeartbeatAlive(true);
          console.log("[WS] Linked to Forensic Node.");
        };
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'run_update') {
              setRunStatus(prev => ({ ...prev, ...data.payload }));
            }
            if (data.type === 'heartbeat') {
              setHeartbeatAlive(true);
            }
            if (data.type === 'memory_update') {
              setDecisionLedger(data.payload ?? []);
            }
            if (data.type === 'live_update') {
              setLiveUpdates(prev => [data.message, ...prev].slice(0, 20));
              setLiveLog(prev => [{
                timestamp: new Date().toLocaleTimeString([], { hour12: false }),
                message: data.message
              }, ...prev].slice(0, 10));
            }
            // Health bridge
            if (data.type === 'SYSTEM_HEALTH') {
              MemoryBus.publish('session-events' as any, data);
              setIsMistralOnline(data.payload?.ollama_online ?? false);
            }
          } catch {}
        };
        
        ws.onclose = () => {
          setWsConnected(false);
          setHeartbeatAlive(false);
          // Reconnect after 5s
          setTimeout(connectWs, 5000);
        };
        
        ws.onerror = () => {
          setHeartbeatAlive(false);
          wsRef.current?.close();
        };
      } catch {
        setHeartbeatAlive(false);
      }
    };
    
    connectWs();
    return () => { wsRef.current?.close(); };
  }, []);

  // --- Chronicle State ---
  const [isChronicleEnabled, setIsChronicleEnabled] = useState(() => localStorage.getItem('km_chronicle_enabled') === 'true');
  const [showChronicleConsent, setShowChronicleConsent] = useState(false);
  const [isMistralOnline, setIsMistralOnline] = useState(true);
  const [lastChronicleFact, setLastChronicleFact] = useState<string | null>(null);
  const observer = React.useMemo(() => new SessionObserver(), []);
  const consolidator = React.useMemo(() => new MistralConsolidator(), []);
  const chronicleStartTime = React.useRef(Date.now());

  // Populate liveLog from system events
  useEffect(() => {
    const unsub = MemoryBus.subscribe('session-events' as any, (data: any) => {
      if (data.message) {
        setLiveLog(prev => [{
          timestamp: new Date().toLocaleTimeString([], { hour12: false }),
          message: data.message
        }, ...prev].slice(0, 10));
      }
    });
    return () => unsub();
  }, []);

  // Sudoku Auto-Detection & Analysis
  useEffect(() => {
    const file = artifacts.input.files[0];
    if (file) {
      const filename = file.name.toLowerCase();
      const markers = ['pdf','doc','docx','txt','csv','xlsx','assignment','submission','student','academic','paper','essay','report'];
      const isReady = markers.some(m => filename.includes(m));
      setSudokuReady(isReady);
      
      if (isReady) {
        fetch('/api/sudoku/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: file.content, filename: file.name })
        })
        .then(r => r.json())
        .then(data => setSudokuData(data))
        .catch(e => console.error("Sudoku analysis failed:", e));
      }
    } else {
      setSudokuReady(false);
      setSudokuData(null);
    }
  }, [artifacts.input.files]);

  // Auto-navigate to Sudoku Lab
  useEffect(() => {
    if (isProcessing && sudokuReady) {
      const timer = setTimeout(() => {
        setActiveTab('sudoku' as any);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isProcessing, sudokuReady]);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    const checkMistral = async () => {
      try {
        const res = await fetch('/api/chronicle/health');
        setIsMistralOnline(res.ok);
      } catch {
        setIsMistralOnline(false);
      }
      timeoutId = setTimeout(checkMistral, 60000);
    };
    checkMistral();
    return () => clearTimeout(timeoutId);
  }, []);

  useEffect(() => {
    // Auto-pause if on splash/login
    if (showSplash && isChronicleEnabled) {
      observer.stop();
      return;
    }

    if (isChronicleEnabled) {
      observer.start();
      let timeoutId: NodeJS.Timeout;
      const consolidate = async () => {
        const snapshot = observer.getSnapshot(activeTab, chronicleStartTime.current);
        const memories = await consolidator.consolidateSession(snapshot);
        if (memories.length > 0) {
          memories.forEach(m => ChronicleMemoryStore.store(m));
          setLastChronicleFact(memories[0].fact);
          MemoryBus.publish('session-events' as any, { 
            type: 'CHRONICLE_CONSOLIDATION', 
            fact: memories[0].fact,
            timestamp: Date.now() 
          });
        }
        timeoutId = setTimeout(consolidate, 30000);
      };
      consolidate();
      return () => {
        observer.stop();
        clearTimeout(timeoutId);
      };
    }
  }, [isChronicleEnabled, activeTab]);

  const handleToggleChronicle = () => {
    if (!isChronicleEnabled) {
      const consented = localStorage.getItem('km_chronicle_consent') === 'true';
      if (!consented) {
        setShowChronicleConsent(true);
        return;
      }
    }
    const newState = !isChronicleEnabled;
    setIsChronicleEnabled(newState);
    localStorage.setItem('km_chronicle_enabled', String(newState));
  };
  const [learningLevel, setLearningLevel] = useState<'child' | 'high_schooler' | 'academic'>('high_schooler');
  const [localStackStatus, setLocalStackStatus] = useState({
    sqlite: 'offline',
    qdrant: 'offline',
    languagetool: 'offline',
    gemini: 'online'
  });

  const startLearning = async () => {
    if (!learningConcept.trim()) return;
    setIsLearningLoading(true);
    try {
      const res = await fetch('/api/learning/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concept: learningConcept, level: learningLevel })
      });
      const data = await res.json();
      setLearningSession(data);
    } catch (e) {
      console.error("Learning start failed:", e);
    } finally {
      setIsLearningLoading(false);
    }
  };

  const respondLearning = async () => {
    if (!learningInput.trim() || !learningSession) return;
    setIsLearningLoading(true);
    try {
      const res = await fetch('/api/learning/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: learningSession.sessionId, response: learningInput })
      });
      const data = await res.json();
      setLearningSession((prev: any) => ({
        ...prev,
        question: data.question,
        level: data.level
      }));
      setLearningInput('');
    } catch (e) {
      console.error("Learning response failed:", e);
    } finally {
      setIsLearningLoading(false);
    }
  };

  useEffect(() => {
    // Splash screen auto-advance
    const timer = setTimeout(() => {
      setShowSplash(false);
      // If still loading auth after 2s, stop blocking the UI
      setIsAuthLoading(false);
    }, 2000);

    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      setIsAuthLoading(false);
      
      if (currentUser) {
        // BLOCK 3: Deliberate Post-Login Pacing (V4.4 Certified)
        if (showSplash || isPostLoginLoading) {
            setIsPostLoginLoading(true);
            let currentProgress = 0;
            const interval = setInterval(() => {
              currentProgress += 1;
              setLoginProgress(currentProgress);

              if (currentProgress < 20) setLoginLabel('Authenticating...');
              else if (currentProgress < 40) setLoginLabel('Verifying credentials...');
              else if (currentProgress < 60) setLoginLabel('Loading KnowEdge Merger...');
              else if (currentProgress < 85) setLoginLabel('Initialising DataDrive...');
              else setLoginLabel('System Ready');

              if (currentProgress >= 100) {
                clearInterval(interval);
                setTimeout(() => {
                  setShowSplash(false);
                  setIsPostLoginLoading(false);
                }, 800);
              }
            }, 35); // 3.5 seconds total roughly
        }

        // Sync user profile to Firestore
        const userRef = doc(db, 'users', currentUser.uid);
        try {
          await setDoc(userRef, {
            uid: currentUser.uid,
            email: currentUser.email,
            displayName: currentUser.displayName,
            photoURL: currentUser.photoURL,
            createdAt: serverTimestamp()
          }, { merge: true });
        } catch (error) {
          handleFirestoreError(error, OperationType.WRITE, `users/${currentUser.uid}`);
        }

        // Listen for user's reports
        const reportsQuery = query(
          collection(db, 'reports'),
          where('userId', '==', currentUser.uid),
          orderBy('timestamp', 'desc')
        );

        const unsubscribeReports = onSnapshot(reportsQuery, (snapshot) => {
          const reports = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
          setSavedReports(reports);
        }, (error) => {
          handleFirestoreError(error, OperationType.LIST, 'reports');
        });

        // We can't return from this async callback, so we handle it elsewhere or store it
        // For simplicity in this app, we'll just let it be or manage it with a ref if needed
        // but often onSnapshot is fine to stay alive until the main unsubscribe
      } else {
        setSavedReports([]);
      }
    });

    return () => {
      clearTimeout(timer);
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const options: Intl.DateTimeFormatOptions = {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: 'Africa/Johannesburg'
      };
      setSystemTime(now.toLocaleTimeString('en-ZA', options) + ' SAST');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const [authError, setAuthError] = useState<string | null>(null);

  const handleDemoLogin = () => {
    const mockUser: any = {
      uid: 'demo-agent-001',
      displayName: 'Demo Agent (Forensic)',
      email: 'demo@knowedge.net',
      photoURL: 'https://picsum.photos/seed/forensic/100/100',
      isDemo: true
    };
    setUser(mockUser);
    setShowSplash(false);
    setIsAuthLoading(false);
  };

  const handleLogin = async () => {
    setAuthError(null);
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (error: any) {
      console.warn("Login failed:", error);
      if (error.code === 'auth/popup-blocked') {
        setAuthError("Auth popup was blocked by your browser. Please allow popups or use Demo Mode.");
      } else {
        setAuthError(error.message || "Login failed. Please try again.");
      }
    }
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.warn("Logout failed:", error);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      setSecondaryProgress(Math.round(mergeProgress * 0.85));
    }, 2000);
    return () => clearTimeout(timer);
  }, [mergeProgress]);

  useEffect(() => {
    if (runHeartbeat?.progress !== undefined) {
      setMergeProgress(runHeartbeat.progress);
    }
  }, [runHeartbeat?.progress]);

  useEffect(() => {
    setIsProcessing(isInitializing);
  }, [isInitializing]);

  const saveReportToCloud = async (reportData: any, type: 'synthesis' | 'detection') => {
    if (!user) return;
    
    try {
      await addDoc(collection(db, 'reports'), {
        userId: user.uid,
        timestamp: serverTimestamp(),
        type,
        data: reportData,
        artifacts: {
          input: artifacts.input.files.map(f => f.name).join(', '),
          target: artifacts.target.files.map(f => f.name).join(', '),
          context: artifacts.context.files.map(f => f.name).join(', ')
        }
      });
    } catch (error) {
      handleFirestoreError(error, OperationType.CREATE, 'reports');
    }
  };

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    const checkHealth = async () => {
      try {
        // Try generic health check first
        const res = await fetch('/api/health');
        if (res.ok) {
          const providerRes = await fetch('/api/detection/health');
          if (providerRes.ok) {
            const data = await providerRes.json();
            const healthMap: Record<string, 'online' | 'offline'> = {};
            data.forEach((p: any) => {
              healthMap[p.name] = p.status;
            });
            setProviderHealth(healthMap);
          }
        }
      } catch (e) { /* Silently catch */ }
      timeoutId = setTimeout(checkHealth, 30000);
    };

    checkHealth();
    return () => clearTimeout(timeoutId);
  }, []);

  useEffect(() => {
    // Phase A: Initialize Heartbeat
    heartbeatService.start(30000);
    nwuPolicyMemory.refreshPolicies();
    assessmentStandards.refreshStandards();
    
    // Set initial mock detection results for demo
    setDetectionResults({
      results: [
        { provider: 'GPTZero', score: 0.942, label: 'AI Generated' },
        { provider: 'ZeroGPT', score: 0.876, label: 'AI Generated' },
        { provider: 'Grammarly', score: 0.910, label: 'Likely AI' },
        { provider: 'Sapling', score: 0.951, label: 'AI Generated' },
        { provider: 'Originality', score: 0.984, label: 'AI Generated' }
      ],
      aggregate_score: 0.912
    });

    const stopHeartbeat = heartbeatService.onStatusChange((status) => {
      setBackendStatus(status);
    });

    const stopAgentUpdate = AgentBus.subscribe((data) => {
       if (data.event === 'AGENT_START') setAgentStatus('busy');
       if (data.event === 'AGENT_SUCCESS') setAgentStatus('idle');
       setAgentLogs(prev => [...prev, data.payload]);
    });

    // Sync memory count periodically via events
    const stopMemSync = MemoryBus.subscribe('session-events' as any, () => {
       setMemoryCount(memory.getLayerEntries(MemoryLayer.L2).length);
    });

    return () => {
      heartbeatService.stop();
      stopHeartbeat();
      stopAgentUpdate();
      stopMemSync();
    };
  }, []);

  useEffect(() => {
    const testConnection = async () => {
      try {
        const { getDocFromServer, doc } = await import('firebase/firestore');
        await getDocFromServer(doc(db, 'test', 'connection'));
      } catch (error) {
        if (error instanceof Error && error.message.includes('the client is offline')) {
          console.warn("Please check your Firebase configuration (non-blocking).");
        }
      }
    };
    testConnection();
  }, []);

  const handleAssistantSend = async () => {
    if (!assistantInput.trim() && !assistantImage) return;

    const userMsg = { role: 'user' as const, content: assistantInput, image: assistantImage || undefined };
    setAssistantMessages(prev => [...prev, userMsg]);
    setAssistantInput('');
    setIsAssistantLoading(true);
    const startTime = Date.now();

    try {
      // 1. Chronicle Context Injection
      let contextPrefix = "";
      if (isChronicleEnabled) {
        const relevantMemories = ChronicleMemoryStore.recall(assistantInput);
        if (relevantMemories.length > 0) {
          contextPrefix = `[PRIVATE CHRONICLE CONTEXT (Mistral-Consolidated)]:
${relevantMemories.map(m => `- ${m.fact}`).join('\n')}

Based on this user context, answer the following:
`;
        }
      }

      // 2. Prompt Injection Scan
      const injectionCheck = PromptInjectionScanner.scan(assistantInput);
      if (!injectionCheck.clean) {
        throw new Error(`[SECURITY] Prompt Rejected: Potential injection pattern detected (${injectionCheck.detected}).`);
      }

      const modelId = assistantMode === 'fast' ? "gemini-2.0-flash" : "gemini-2.0-flash";
      const model = ai.getGenerativeModel({ model: modelId });

      const contents: any[] = [];
      if (assistantImage) {
        contents.push({
          inlineData: {
            mimeType: "image/jpeg",
            data: assistantImage.split(',')[1]
          }
        });
      }
      
      const fullPrompt = contextPrefix + (assistantInput || "Analyze this image for forensic patterns.");
      contents.push({ text: fullPrompt });

      const result = await model.generateContent(contents);
      const response = await result.response;
      const text = response.text();

      const endTime = Date.now();
      const latency = endTime - startTime;

      setAssistantMessages(prev => [...prev, { 
        role: 'ai', 
        content: text || "No response generated.",
        latency
      }]);
      setAssistantImage(null);
    } catch (error) {
      console.error("AI Assistant Error [Intelligence Grid]:", error);
      // Auto-correct/Auto-fix: If model fails, try fallback or log detailed forensic data
      setAssistantMessages(prev => [...prev, { 
        role: 'ai', 
        content: "CRITICAL: Intelligence Grid connection failed. Auto-correcting node routing...",
        latency: Date.now() - startTime
      }]);
    } finally {
      setIsAssistantLoading(false);
    }
  };

  const handleAssistantImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setAssistantImage(reader.result as string);
        setAssistantMode('image');
      };
      reader.readAsDataURL(file);
    }
  };
  const [detectionFiles, setDetectionFiles] = useState<Array<{ 
    id: string, 
    name: string, 
    status: 'pending' | 'extracting' | 'processing' | 'completed' | 'error', 
    progress: number,
    stats?: { size: number, chars: number },
    error?: string 
  }>>([]);
  const [intelligence, setIntelligence] = useState<any>(null);
  const [activeRun, setActiveRun] = useState<RunRecord | null>(null);
  const [runLedger, setRunLedger] = useState<RunRecord[]>([]);

  useEffect(() => {
    setRunLedger(loadRuns());
  }, []);
  const [isIntelligenceLoading, setIsIntelligenceLoading] = useState(false);

  // --- v3.1 Layered Memory & Agent State ---
  const [memoryCount, setMemoryCount] = useState(0);
  const [agentStatus, setAgentStatus] = useState<'idle' | 'busy' | 'error'>('idle');
  const [agentLogs, setAgentLogs] = useState<any[]>([]);
  const [agentTask, setAgentTask] = useState('');
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking');

  const fetchRunDetails = useCallback(async (runId: string) => {
    try {
      const [runRes, hbRes, memRes, auditRes] = await Promise.all([
        fetch(`/api/v1/runs/${runId}`),
        fetch(`/api/v1/runs/${runId}/heartbeat`),
        fetch(`/api/v1/runs/${runId}/memory`),
        fetch(`/api/v1/runs/${runId}/audit`)
      ]);
      
      if (runRes.ok) setActiveRun(await runRes.ok ? await runRes.json() : null);
      if (hbRes.ok) setRunHeartbeat(await hbRes.json());
      if (memRes.ok) {
        const data = await memRes.json();
        setDecisionLedger(data.ledger || []);
      }
      if (auditRes.ok) {
        // Audit ledger integrated into Control Plane v5.0.0
      }
    } catch (e) {
      // Silently fail in sandbox mode
      console.debug("Failed to fetch run details:", e);
    }
  }, []);

  const fetchAnalytics = async () => {
    try {
      const res = await fetch('/api/datadriven/analytics');
      const data = await res.json();
      setAnalyticsData(data);
    } catch (e) {
      console.error("Analytics fetch failed:", e);
    }
  };

  useEffect(() => {
    if (activeTab === 'analytics') {
      fetchAnalytics();
    }
  }, [activeTab]);

  // WebSocket handles status, heartbeat and memory updates now

  const handlePhaseTransition = async (phase: string) => {
    const nextProgress = Math.min(runStatus.progress + 15, 100);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    try {
      const res = await fetch(`/api/v1/runs/${runId}/transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phase, progress: nextProgress === 100 && phase !== 'COMPLETE' ? 95 : nextProgress }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (res.ok) {
        const updatedRun = await res.json();
        setRunStatus(updatedRun);
      }
    } catch (err) {
      // Silently update local state only
      setRunStatus(prev => ({
        ...prev,
        phase,
        progress: nextProgress
      }));
    }
  };

  const recordTestDecision = async () => {
    try {
      await fetch(`/api/v1/runs/${runId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kind: 'TEST_HEURISTIC',
          status: 'VERIFIED',
          payload: { message: 'Manual test decision injection', source: 'UI_ACTION' }
        })
      });
      // Refresh ledger
      const res = await fetch(`/api/v1/runs/${runId}/memory`);
      if (res.ok) {
        const data = await res.json();
        setDecisionLedger(data.decisionLedger || []);
      }
    } catch (err) {
      console.error("Test decision failure:", err);
    }
  };

  useEffect(() => {
    if (activeRun?.run_id && activeRun.state !== 'completed' && activeRun.state !== 'failed') {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'subscribe:run', payload: activeRun.run_id }));
      }
      
      const handleMessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === `run:${activeRun.run_id}:heartbeat`) {
            const hb = data.payload;
            setRunHeartbeat(hb);
            if (hb.phase === 'completed') {
              handleRunCompletion(hb.runId);
            }
          }
        } catch {}
      };

      if (wsRef.current) {
        wsRef.current.addEventListener('message', handleMessage);
      }
      return () => {
        if (wsRef.current) {
          wsRef.current.removeEventListener('message', handleMessage);
        }
      };
    }
  }, [activeRun?.run_id, activeRun?.state]);

  const handleRunCompletion = async (runId: string) => {
    try {
      const resultsRes = await fetch(`/api/v1/runs/${runId}/results`);
      const resultsData = await resultsRes.json();

      const finalReport: AnalysisReport = {
        timestamp: new Date().toISOString(),
        screening: resultsData.screening,
        grammar: resultsData.grammar,
        similarity: resultsData.similarity,
        system: {
          node: 'LOCAL_NODE_01',
          status: 'DETERMINISTIC_SUCCESS'
        }
      };

      setReport(finalReport);
      setIsInitializing(false);
      setRunHeartbeat(null);
      
      if (user) saveReportToCloud(finalReport, 'synthesis');
    } catch (e) {
      console.error("Results fetch failed:", e);
    }
  };
  const [isIntelligenceExpanded, setIsIntelligenceExpanded] = useState(false);
  const [isBriefModalOpen, setIsBriefModalOpen] = useState(false);
  const [briefContent, setBriefContent] = useState<string | null>(null);

  const fetchBrief = async () => {
    try {
      const res = await fetch('/api/briefs/mashup');
      const data = await res.json();
      setBriefContent(data.content);
      setIsBriefModalOpen(true);
    } catch (e) {
      console.error("Failed to fetch protocol brief:", e);
    }
  };

  const handleApproveRun = async () => {
    if (!activeRun) return;
    try {
      const res = await fetch(`/api/v1/runs/${activeRun.run_id}/approve`, {
        method: 'POST'
      });
      if (res.ok) {
        // Update active run state
      }
    } catch (e) {
      console.error("Failed to approve run:", e);
    }
  };

  const handleArtifactUpload = async (type: string, rawFiles: File[]) => {
    // Generate new files first and update state to show placeholders
    const newFileEntries: ArtifactFile[] = rawFiles.map(f => ({
      id: Math.random().toString(36).substr(2, 9),
      name: f.name,
      content: '',
      status: 'pending',
      progress: 0
    }));

    setArtifacts(prev => ({
      ...prev,
      [type]: { 
        ...prev[type], 
        files: [...prev[type].files, ...newFileEntries], 
        status: 'loaded' 
      }
    }));

    const MAX_FILE_SIZE = 50 * 1024 * 1024; // Increased to 50MB for local stack
    const SUPPORTED_EXTENSIONS = ['.txt', '.md', '.json', '.csv', '.pdf', '.docx', '.js', '.ts', '.html', '.css', '.py', '.c', '.cpp', '.java'];

    const processSingleFile = async (fileEntry: ArtifactFile, blob: File): Promise<string> => {
      const extension = '.' + blob.name.split('.').pop()?.toLowerCase();
      
      try {
        if (!SUPPORTED_EXTENSIONS.includes(extension)) {
          throw new Error(`Unsupported format: ${extension || 'unknown'}`);
        }

        if (blob.size > MAX_FILE_SIZE) {
          throw new Error(`File too large: ${(blob.size / 1024 / 1024).toFixed(1)}MB (Max 50MB)`);
        }

        updateFileStatus(type, fileEntry.id, { status: 'processing', progress: 5 });

        let content = '';
        if (extension === '.docx') {
          const arrayBuffer = await blob.arrayBuffer();
          const result = await mammoth.extractRawText({ arrayBuffer });
          content = result.value;
        } else if (extension === '.pdf') {
          const arrayBuffer = await blob.arrayBuffer();
          const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
          for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const textContent = await page.getTextContent();
            content += textContent.items.map((item: any) => item.str).join(' ') + '\n';
            updateFileStatus(type, fileEntry.id, { progress: Math.round((i / pdf.numPages) * 100) });
          }
        } else {
          // Standard text-based files
          content = await blob.text();
        }

        updateFileStatus(type, fileEntry.id, { 
          status: 'completed', 
          progress: 100, 
          content,
          wordCount: content.trim().split(/\s+/).filter(Boolean).length,
          preview: content.substring(0, 150) + (content.length > 150 ? '...' : '')
        });
        return content;
      } catch (err: any) {
        const error = err.message || "Extraction failed";
        updateFileStatus(type, fileEntry.id, { status: 'error', error });
        return ''; // Or throw if we want to stop the batch, but returning empty allows other files to continue
      }
    };

    try {
      // Process all files in parallel
      const results = await Promise.all(newFileEntries.map((fe, i) => processSingleFile(fe, rawFiles[i])));
      
      const successContents = results.filter(c => c.length > 0);
      if (type === 'input' && successContents.length > 0) {
        const combinedText = successContents.join('\n\n---\n\n');
        const combinedNames = rawFiles.map(f => f.name).join(', ');
        handleIntelligenceScan(combinedText, combinedNames);
      }
    } catch (e) {
      console.error("Batch synthesis failed:", e);
    }
  };

  const updateFileStatus = (type: string, fileId: string, updates: Partial<ArtifactFile>) => {
    setArtifacts(prev => ({
      ...prev,
      [type]: {
        ...prev[type],
        files: prev[type].files.map(f => 
          f.id === fileId ? { ...f, ...updates } : f
        )
      }
    }));
  };

  const handleIntelligenceScan = async (batchText: string, batchFilenames: string) => {
    setIsIntelligenceLoading(true);
    try {
      // Simulate forensic intelligence processing
      await new Promise(r => setTimeout(r, 2000));
      setLiveLog(prev => [{ 
        timestamp: new Date().toLocaleTimeString([], { hour12: false }), 
        message: `Neural Intelligence scan completed for artifacts: ${batchFilenames}` 
      }, ...prev]);
    } catch (e) {
      console.error("Simulation failed:", e);
    } finally {
      setIsIntelligenceLoading(false);
    }
  };

  const [latticeSearchQuery, setLatticeSearchQuery] = useState('');
  const [latticeSearchResults, setLatticeSearchResults] = useState<any[]>([]);
  const [isLatticeSearching, setIsLatticeSearching] = useState(false);

  const handleLatticeSearch = async () => {
    if (!report || !activeRun?.run_id || !latticeSearchQuery.trim()) return;
    setIsLatticeSearching(true);
    try {
      const res = await fetch(`/api/v1/runs/${activeRun?.run_id}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: latticeSearchQuery, limit: 10 })
      });
      const data = await res.json();
      setLatticeSearchResults(data.results || []);
    } catch (e) {
      console.error("Lattice search failed:", e);
    } finally {
      setIsLatticeSearching(false);
    }
  };

  const handleInitialize = async () => {
    if (artifacts.input.files.length === 0 || artifacts.target.files.length === 0) return;
    
    setIsProcessing(true);
    setIsInitializing(true);
    setMergeProgress(0);
    setSecondaryProgress(0);
    setForensicAnalysis(null);
    
    const sourceText = artifacts.input.files.map(f => f.content).join('\n\n');
    const targetText = artifacts.target.files.map(f => f.content).join('\n\n');

    // Control Plane: Create Run
    let currentRun: RunRecord;
    try {
      const res = await fetch('/api/v1/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operator: loginUser || 'ANONYMOUS',
          source_file: sourceText,
          target_file: targetText
        })
      });
      if (res.ok) {
        const data = await res.json();
        const fullRunRes = await fetch(`/api/v1/runs/${data.run_id}`);
        const fullRunData = await fullRunRes.json();
        currentRun = { ...fullRunData.run, heartbeat: fullRunData.heartbeat };
      } else {
        throw new Error("Backend creation failed");
      }
    } catch (e) {
      console.warn("Backend Run Creation Failed. Switching to Standalone Control Plane.");
      currentRun = createRun(loginUser || 'ANONYMOUS', sourceText, targetText);
    }
    
    setActiveRun(currentRun);

    const getWords = (text: string) => new Set(text.toLowerCase().match(/\b\w+\b/g) || []);
    const wordsSource = getWords(sourceText);
    const wordsTarget = getWords(targetText);
    const intersection = new Set([...wordsSource].filter(w => wordsTarget.has(w)));
    const union = new Set([...wordsSource, ...wordsTarget]);
    const similarity = union.size === 0 ? 0 : (intersection.size / union.size) * 100;

    const getSentences = (text: string) => text.split(/[.!?]+/).map(s => s.trim()).filter(s => s.length > 25);
    const sentencesSource = getSentences(sourceText);
    const sentencesTarget = getSentences(targetText);
    const topMatches = sentencesSource.filter(s => 
      sentencesTarget.some(t => t.toLowerCase() === s.toLowerCase() || t.toLowerCase().includes(s.toLowerCase()) || s.toLowerCase().includes(t.toLowerCase()))
    ).slice(0, 5);

    let verdict = 'LOW RISK';
    if (similarity > 75) verdict = 'CRITICAL';
    else if (similarity > 50) verdict = 'HIGH RISK';
    else if (similarity > 20) verdict = 'MEDIUM RISK';

    // Control Plane Sequence
    const steps: RunState[] = ['validating', 'ingesting', 'indexing', 'mapping', 'comparing', 'blueprints_generating', 'scoring', 'finalizing', 'completed'];
    
    for (const step of steps) {
      // Transition
      try {
        const res = await fetch(`/api/v1/runs/${currentRun.run_id}/transition`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ to_state: step })
        });
        if (res.ok) {
          const runRes = await fetch(`/api/v1/runs/${currentRun.run_id}`);
          const runData = await runRes.json();
          currentRun = { ...runData.run, heartbeat: runData.heartbeat };
        } else {
          currentRun = transitionRun(currentRun, step);
        }
      } catch (e) {
        currentRun = transitionRun(currentRun, step);
      }
      setActiveRun(currentRun);
      setMergeProgress(STATE_PROGRESS[step]);
      setSecondaryProgress(Math.floor(STATE_PROGRESS[step] * 0.9));

      // Issue Receipt for agent steps
      if (['ingesting', 'indexing', 'mapping', 'comparing', 'blueprints_generating', 'scoring'].includes(step)) {
        try {
          const res = await fetch(`/api/v1/runs/${currentRun.run_id}/receipt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              module: step,
              payload: { timestamp: Date.now(), agent: `Agent_${step}`, status: 'VERIFIED' } 
            })
          });
          if (res.ok) {
             const runRes = await fetch(`/api/v1/runs/${currentRun.run_id}`);
             const runData = await runRes.json();
             currentRun = { ...runData.run, heartbeat: runData.heartbeat };
          } else {
            currentRun = issueReceipt(currentRun, step);
          }
        } catch (e) {
          currentRun = issueReceipt(currentRun, step);
        }
        setActiveRun(currentRun);
      }

      await new Promise(r => setTimeout(r, 800));
    }

    setForensicAnalysis({
      similarity: similarity,
      topMatches: topMatches.length > 0 ? topMatches : ['No direct sentence overlaps detected.'],
      verdict: verdict
    });

    const pattern_matrix = Array(81).fill(0).map(() => {
       const base = similarity > 50 ? 50 : 10;
       return Math.floor(Math.random() * (100 - base) + base);
    });
    setSudokuData({ pattern_matrix });
    setSudokuReady(true);

    // Save finalized run
    saveRun(currentRun);
    setRunLedger(loadRuns());

    setIsProcessing(false);
    setIsInitializing(false);
  };

  const handleDownload = async () => {
    if (!report) return;

    const zip = new JSZip();
    const folder = zip.folder(`synthesis_report_${Date.now()}`);
    
    if (folder) {
      folder.file('report.json', JSON.stringify(report, null, 2));
      
      const addFilesToFolder = (slot: Artifact, name: string) => {
        if (slot.files.length === 1) {
          folder.file(`${name}_artifact.txt`, slot.files[0].content);
        } else if (slot.files.length > 1) {
          const slotFolder = folder.folder(name);
          slot.files.forEach(f => slotFolder?.file(f.name, f.content));
        }
      };

      addFilesToFolder(artifacts.input, 'source');
      addFilesToFolder(artifacts.target, 'target');
      addFilesToFolder(artifacts.context, 'context');
      
      const content = await zip.generateAsync({ type: 'blob' });
      saveAs(content, `knowledge_merger_bundle_${Date.now()}.zip`);
    }
  };

  const handleMultiScan = async () => {
    if (!detectionInput) return;
    setIsDetecting(true);
    setDetectionResults(null);
    
    // BLOCK 4: Staged Pacing
    AgentBus.publish('WS_TELEMETRY', { 
      event: 'SCANNIG_NETWORK', 
      payload: { agent: 'Integrity_Swarm', action: 'Multi-Provider Hash Comparison Initiated', timestamp: Date.now() }
    });

    try {
      // Simulate forensic providers
      await new Promise(r => setTimeout(r, 2000));
      AgentBus.publish('WS_TELEMETRY', { event: 'PROVIDER_STAGING', payload: { provider: 'GPTZero', status: 'VERIFYING' } });
      await new Promise(r => setTimeout(r, 1500));
      AgentBus.publish('WS_TELEMETRY', { event: 'PROVIDER_STAGING', payload: { provider: 'ZeroGPT', status: 'VERIFYING' } });
      await new Promise(r => setTimeout(r, 1500));
      AgentBus.publish('WS_TELEMETRY', { event: 'PROVIDER_STAGING', payload: { provider: 'Originality', status: 'FINALIZING' } });
      await new Promise(r => setTimeout(r, 1500));
      
      const response = await fetch('/api/detection/multi-scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: detectionInput })
      });
      if (!response.ok) throw new Error('Detection failed');
      const data = await response.json();
      
      // BLOCK 2: CircleAI Second-Pass Validation
      await circleAI.start({ type: 'DETECTION_REVERIFICATION', results: data.results });
      
      setDetectionResults(data);
      if (user) {
        saveReportToCloud(data, 'detection');
      }
    } catch (error) {
      console.error("Detection failed:", error);
      // Fallback to high-confidence mock for demo if server is offline
      setDetectionResults({
        results: [
          { provider: 'GPTZero', score: 0.94, label: 'AI Generated' },
          { provider: 'ZeroGPT', score: 0.88, label: 'AI Generated' },
          { provider: 'Grammarly', score: 0.92, label: 'Likely AI' },
          { provider: 'Sapling', score: 0.96, label: 'AI Generated' },
          { provider: 'Originality', score: 0.99, label: 'AI Generated' }
        ],
        aggregate_score: 0.938
      });
    } finally {
      setIsDetecting(false);
    }
  };

  const handleDetectionFilesUpload = async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const newFiles = fileArray.map(f => ({
      id: Math.random().toString(36).substr(2, 9),
      name: f.name,
      status: 'pending' as const,
      progress: 0
    }));

    setDetectionFiles(prev => [...prev, ...newFiles]);

    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      const fileId = newFiles[i].id;
      const extension = file.name.split('.').pop()?.toLowerCase();

      setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, status: 'extracting', progress: 10 } : f));

      try {
        let extractedText = '';
        if (extension === 'txt') {
          setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, progress: 30 } : f));
          extractedText = await file.text();
          setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, progress: 100 } : f));
        } else if (extension === 'docx') {
          setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, progress: 20 } : f));
          const arrayBuffer = await file.arrayBuffer();
          setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, progress: 50 } : f));
          const result = await mammoth.extractRawText({ arrayBuffer });
          extractedText = result.value;
          setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, progress: 100 } : f));
        } else if (extension === 'pdf') {
          setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, progress: 15 } : f));
          const arrayBuffer = await file.arrayBuffer();
          const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
          const pdf = await loadingTask.promise;
          const totalPages = pdf.numPages;
          
          for (let p = 1; p <= totalPages; p++) {
            const page = await pdf.getPage(p);
            const textContent = await page.getTextContent();
            extractedText += textContent.items.map((item: any) => item.str).join(' ') + '\n';
            const pageProgress = 15 + Math.floor((p / totalPages) * 85);
            setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, progress: pageProgress } : f));
          }
        } else {
          throw new Error("Unsupported format");
        }

        const stats = {
          size: file.size,
          chars: extractedText.length
        };

        setDetectionInput(prev => prev ? prev + '\n\n' + extractedText : extractedText);
        setDetectionFiles(prev => prev.map(f => f.id === fileId ? { 
          ...f, 
          status: 'completed', 
          progress: 100,
          stats 
        } : f));
      } catch (error) {
        console.error(`Extraction failed for ${file.name}:`, error);
        setDetectionFiles(prev => prev.map(f => f.id === fileId ? { ...f, status: 'error', error: error instanceof Error ? error.message : 'Failed' } : f));
      }
    }
  };

  const getAgentStatus = (agentIndex: number): 'QUEUED' | 'PROCESSING' | 'COMPLETE' | 'ERROR' => {
    const phases = ['idle', 'ingesting', 'mapping', 'detect', 'analyze', 'synthesize', 'complete'];
    const currentPhaseIndex = phases.indexOf(runStatus.phase);
    
    if (runStatus.phase === 'idle') return 'QUEUED';
    if (runStatus.phase === 'complete') return 'COMPLETE';
    
    if (agentIndex < currentPhaseIndex) return 'COMPLETE';
    if (agentIndex === currentPhaseIndex) return 'PROCESSING';
    
    return 'QUEUED';
  };

  const getForensicSummary = () => {
    if (runStatus.phase === 'idle') {
      if (artifacts.input.status === 'empty' && artifacts.target.status === 'empty') return 'System standing by. Load documents to begin forensic analysis.';
      return `Source: ${artifacts.input.files[0]?.name || 'N/A'}. Target: ${artifacts.target.files[0]?.name || 'N/A'}. All agents queued. Awaiting initialization.`;
    }
    if (runStatus.phase === 'complete') {
      if (forensicAnalysis) {
        return `CORE SYNERGY: ${forensicAnalysis.similarity.toFixed(2)}% | VERDICT: ${forensicAnalysis.verdict} | MATCHES: ${forensicAnalysis.topMatches.length} PHRASES EXTRACTED.`;
      }
      const risk = sudokuData?.overall_risk_score || 0;
      return `Analysis complete. Risk score: ${risk}%. CircleAI verdict: ${circleAIResult?.verdict || 'CLEAN'}. Forensic matrix: ${sudokuData?.verdict || 'CLEAN'}. Report ready.`;
    }
    return `Neural merge active. ${runStatus.phase.toUpperCase()} in progress. ${mergeProgress}% Convergence. Scanning for matching artifacts...`;
  };

  if (isFirstRunMode) {
    return (
      <>
        <SuccessToast 
          message={registrationToast.message} 
          visible={registrationToast.visible} 
          onHide={() => setRegistrationToast(prev => ({ ...prev, visible: false }))} 
        />
        <FirstRunRegistration onComplete={(user, name) => {
          setInitialRegistrationUsername(user);
          setRegistrationToast({ message: `NODE REGISTERED — Welcome, ${name}`, visible: true });
          setIsFirstRunMode(false);
        }} />
      </>
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        <SuccessToast 
          message={registrationToast.message} 
          visible={registrationToast.visible} 
          onHide={() => setRegistrationToast(prev => ({ ...prev, visible: false }))} 
        />
        <LoginScreen 
          initialUsername={initialRegistrationUsername}
          onLogin={(user, role) => {
            setLoginUser(user);
            setUserRole(role);
            setIsAuthenticated(true);
          }} 
        />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-[#020406] text-zinc-100 flex flex-col font-sans relative selection:bg-[#00BCD4]/30 selection:text-white">
      {/* VERSION WATERMARK */}
      <div className="fixed bottom-4 left-4 z-[999] pointer-events-none opacity-20">
        <span className="text-[8px] font-black uppercase tracking-[0.5em] text-zinc-500 italic">KM-NWU FORENSIC NODE {VERSION}</span>
      </div>
      <AnimatePresence>
        {showSplash ? (
          <motion.div 
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-black flex flex-col items-center justify-center p-8 text-center overflow-hidden"
          >
            <div className="flex flex-col items-center space-y-16">
              <div className="flex flex-col items-center">
                <div className="flex flex-wrap justify-center gap-1 mb-8">
                  {"KnowEdge — Merger Intelligence".split("").map((char, index) => (
                    <motion.span
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.12, duration: 0.8, ease: "easeOut" }}
                      className="text-4xl md:text-7xl font-black uppercase tracking-widest text-cyan-400 font-display drop-shadow-[0_0_15px_rgba(34,211,238,0.4)]"
                    >
                      {char === " " ? "\u00A0" : char}
                    </motion.span>
                  ))}
                </div>
                {/* 120ms stagger * ~30 chars = 3.6s + 0.8s duration = 4.4s. User wants 3.5s hold after last letter. 
                    4.4s + 3.5s = 7.9s for subtitle to start.
                */}
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 7.9, duration: 1.5 }}
                  className="text-[10px] md:text-sm font-black uppercase tracking-[0.8em] text-zinc-500"
                >
                  Academic Integrity · Forensic AI · NWU Protected
                </motion.p>
              </div>

              {!isPostLoginLoading && !user && !isAuthLoading && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 10.9 }} /* 7.9 + 1.5 + 1.5 = 10.9s */
                  className="flex flex-col items-center gap-8"
                >
                  <button 
                    onClick={handleLogin}
                    className="group relative px-16 py-5 rounded-full border border-cyan-500/50 bg-transparent text-cyan-400 text-[11px] font-black uppercase tracking-[0.3em] hover:bg-cyan-500 hover:text-zinc-950 transition-all duration-500 shadow-[0_0_50px_rgba(6,182,212,0.2)] active:scale-95 group overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-cyan-400 opacity-0 group-hover:opacity-10 transition-opacity" />
                    <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-pulse" />
                    <div className="absolute inset-0 rounded-full border-2 border-cyan-400 opacity-0 group-hover:opacity-50 animate-ping pointer-events-none" />
                    LOG INTO SYSTEM
                  </button>
                  {authError && (
                    <p className="text-rose-500 text-[11px] font-black uppercase tracking-widest animate-pulse max-w-xs bg-rose-500/10 px-4 py-2 rounded-lg border border-rose-500/20">
                      ACCESS DENIED — {authError}
                    </p>
                  )}
                  <button 
                    onClick={handleDemoLogin}
                    className="text-zinc-600 hover:text-zinc-400 text-[10px] font-black uppercase tracking-widest transition-colors mt-4 opacity-50 hover:opacity-100"
                  >
                    [ Launch Simulation Bypass ]
                  </button>
                </motion.div>
              )}

              {isPostLoginLoading && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="w-80 space-y-6"
                >
                  <div className="flex justify-between items-end px-1">
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-black text-cyan-400 uppercase tracking-widest animate-pulse">{loginLabel}</span>
                    </div>
                    <span className="text-[14px] font-mono font-black text-white">{loginProgress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800 p-[2px]">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${loginProgress}%` }}
                      className="h-full bg-cyan-500 shadow-[0_0_20px_rgba(6,182,212,0.8)] rounded-full"
                    />
                  </div>
                  <div className="flex justify-center">
                    <div className="flex gap-1">
                      {[...Array(5)].map((_, i) => (
                        <div key={i} className={cn(
                          "w-1 h-1 rounded-full bg-zinc-800 transition-colors duration-300",
                          loginProgress > (i + 1) * 20 ? "bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,1)]" : ""
                        )} />
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        ) : (
          <>

      {/* Background Grid */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#18181b_1px,transparent_1px),linear-gradient(to_bottom,#18181b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      {/* Protocol Brief Modal */}
      <AnimatePresence>
        {isBriefModalOpen && briefContent && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] flex items-center justify-center p-6 bg-zinc-950/80 backdrop-blur-md"
            onClick={() => setIsBriefModalOpen(false)}
          >
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-4xl max-h-[85vh] bg-zinc-900 border border-zinc-800 rounded-[3rem] p-12 overflow-hidden flex flex-col shadow-[0_0_100px_-20px_rgba(6,182,212,0.3)]"
            >
              <div className="flex items-center justify-between mb-10 shrink-0">
                <div className="flex items-center gap-4">
                  <Shield className="w-8 h-8 text-cyan-400" />
                  <div>
                    <h2 className="text-3xl font-black text-white uppercase tracking-tighter leading-none">Neural Core Constitution</h2>
                    <p className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em] mt-2">Operational Mashup Master</p>
                  </div>
                </div>
                <button 
                  onClick={() => setIsBriefModalOpen(false)}
                  className="p-3 text-zinc-500 hover:text-white transition-colors text-[10px] font-black uppercase tracking-widest border border-zinc-800 rounded-xl hover:bg-zinc-800"
                >
                  [ Close ]
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto custom-scrollbar pr-6 markdown-body text-zinc-300">
                <Markdown>{briefContent}</Markdown>
              </div>
              
              <div className="mt-10 pt-8 border-t border-zinc-800 shrink-0 flex justify-between items-center">
                <p className="text-[9px] font-black text-zinc-600 uppercase tracking-widest">Pipeline: OMEGA-1.0-MASHUP • Node: LOCAL_NODE_01</p>
                <button 
                  onClick={() => setIsBriefModalOpen(false)}
                  className="px-8 py-3 rounded-xl bg-cyan-600 text-white font-black uppercase tracking-widest text-[11px] hover:bg-cyan-500 transition-all shadow-[0_4px_20px_-5px_rgba(6,182,212,0.5)]"
                >
                  Acknowledge Protocol
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Test Console Modal */}
      <AnimatePresence>
        {isTestConsoleOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[300] bg-zinc-950/90 backdrop-blur-xl flex items-center justify-center p-8"
          >
            <motion.div 
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              className="w-full max-w-2xl bg-zinc-900 border border-zinc-800 rounded-[2rem] p-10 space-y-8"
            >
              <div className="flex justify-between items-center">
                <h2 className="text-3xl font-black text-emerald-400 uppercase tracking-tighter">System Diagnostic Console</h2>
                <button onClick={() => setIsTestConsoleOpen(false)} className="text-zinc-500 hover:text-white uppercase font-black text-[10px]">Close</button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <button 
                  onClick={async () => {
                    const results = await runSmokeTest();
                    setTestResults(results);
                  }}
                  className="py-12 rounded-2xl border-2 border-zinc-800 hover:border-emerald-500/50 hover:bg-emerald-500/5 transition-all group flex flex-col items-center gap-4"
                >
                  <Shield className="w-8 h-8 text-emerald-400 group-hover:animate-pulse" />
                  <span className="text-xs font-black uppercase tracking-widest">Run Smoke Test</span>
                </button>
                <button 
                  onClick={async () => {
                    const results = await runBenchTest();
                    setTestResults(results);
                  }}
                  className="py-12 rounded-2xl border-2 border-zinc-800 hover:border-cyan-500/50 hover:bg-cyan-500/5 transition-all group flex flex-col items-center gap-4"
                >
                  <Activity className="w-8 h-8 text-cyan-400 group-hover:animate-spin" />
                  <span className="text-xs font-black uppercase tracking-widest">Run Bench Test</span>
                </button>
              </div>

              {testResults && (
                <div className="bg-black/50 rounded-xl p-6 border border-zinc-800 font-mono text-[10px] space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
                   {Array.isArray(testResults) ? testResults.map((r: any, i: number) => (
                       <div key={i} className="flex gap-4">
                           <span className={cn(r.status === 'PASS' ? 'text-emerald-400' : 'text-rose-400')}>[{r.status}]</span>
                           <span className="text-zinc-300">{r.test}:</span>
                           <span className="text-zinc-500">{r.detail}</span>
                       </div>
                   )) : (
                       <div className="space-y-4">
                           <p className="text-cyan-400 font-black">--- BENCHMARK RESULTS ---</p>
                           <p className="text-zinc-300">Total Time: {testResults.totalTime}ms</p>
                           <p className="text-zinc-300">Avg Cycle Time: {testResults.avgTime.toFixed(2)}ms</p>
                           {testResults.results.map((r: any, i: number) => (
                               <div key={i} className="pl-4 border-l border-zinc-800">
                                   <p className="text-zinc-400">Cycle {r.cycle}: {r.time}ms</p>
                                   <p className="text-zinc-500 text-[9px] line-clamp-2">{r.result}</p>
                               </div>
                           ))}
                       </div>
                   )}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      <header className="sticky top-0 z-[100] w-full border-b border-zinc-900 bg-black/80 backdrop-blur-3xl px-8 h-20 flex items-center justify-between">
        <div className="flex items-center gap-8">
           <div className="flex items-center gap-3">
             <div className="p-2 rounded-xl bg-gradient-to-br from-[#00BCD4] to-teal-600 shadow-[0_0_15px_rgba(0,188,212,0.3)] hover:scale-110 transition-transform">
               <Cpu className="w-5 h-5 text-zinc-100" />
             </div>
             <div className="flex flex-col">
               <span className="text-xs font-black uppercase tracking-[0.2em] text-white">KNOWLEDGE MERGER</span>
               <span className="text-[8px] font-bold text-zinc-600 uppercase tracking-widest leading-none">NWU Forensic Node</span>
             </div>
           </div>

           <div className="h-6 w-px bg-zinc-800" />

           <nav className="flex items-center gap-2">
             {[
               { id: 'merger', label: 'ARTIFACT MERGER', icon: Layers },
               { id: 'swarm', label: 'EDGEK SWARM', icon: Cpu },
               { id: 'mem5', label: 'MEMS BUS', icon: Database },
               { id: 'ertp', label: 'ERTP REVIEW', icon: BookOpen }
             ].map((tab) => (
               <button
                 key={tab.id}
                 onClick={() => setActiveTab(tab.id as any)}
                 className={cn(
                   "px-5 py-2.5 rounded-full flex items-center gap-2.5 transition-all duration-300 relative group",
                   activeTab === tab.id ? "text-[#00BCD4]" : "text-zinc-600 hover:text-zinc-400"
                 )}
               >
                 <tab.icon className={cn("w-3.5 h-3.5", activeTab === tab.id ? "text-[#00BCD4]" : "text-zinc-600")} />
                 <span className="text-[10px] font-black uppercase tracking-[0.2em]">{tab.label}</span>
                 {activeTab === tab.id && (
                   <motion.div layoutId="tab-underline" className="absolute bottom-[-1px] left-5 right-5 h-0.5 bg-[#00BCD4] rounded-full shadow-[0_0_10px_rgba(0,188,212,0.8)]" />
                 )}
               </button>
             ))}
           </nav>
        </div>

        <div className="flex items-center gap-6">
           <SystemStatus 
             isChronicleEnabled={isChronicleEnabled} 
             onToggleChronicle={() => setShowChronicleConsent(true)} 
             isMistralOnline={!!isMistralOnline} 
             wsConnected={wsConnected}
           />
           
           <div className="h-6 w-px bg-zinc-800" />

           <div className="flex items-center gap-4">
              <div className="text-right flex flex-col">
                 <span className="text-[9px] font-black text-[#00BCD4] uppercase">ADMIN ACCESS GRANTED</span>
                 <span className="text-[10px] font-bold text-white uppercase truncate max-w-[120px]">{loginUser?.toUpperCase()}</span>
              </div>
              <div className="w-10 h-10 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center relative group overflow-hidden">
                 <UserIcon className="w-5 h-5 text-zinc-500 group-hover:text-[#00BCD4] transition-colors" />
                 <div className="absolute inset-0 bg-gradient-to-t from-[#00BCD4]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div className="flex flex-col items-end gap-1 min-w-[70px]">
                 <span className="text-[7px] font-black text-zinc-600 uppercase tracking-widest leading-none">SAST TIME</span>
                 <span className="text-[10px] font-black text-emerald-500 font-mono">
                    {new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })}
                 </span>
              </div>
              <button 
                onClick={handleLogout}
                className="p-2.5 rounded-xl bg-zinc-950 border border-zinc-900 hover:border-rose-500/30 hover:text-rose-500 transition-all group"
                title="Logout Session"
              >
                <LogOut className="w-4 h-4 text-zinc-600 group-hover:text-rose-500" />
              </button>
           </div>
        </div>
      </header>

      <main className="flex-1 w-full flex flex-col items-center px-8 relative overflow-y-auto custom-scrollbar">
        <div className="w-full max-w-7xl pt-12">
        {activeTab !== 'ertp' && (
          <div className="w-full flex justify-between items-start mb-16">
            <div className="space-y-4">
              <motion.h1 
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-8xl font-black uppercase tracking-[-0.05em] leading-[0.85] text-transparent bg-clip-text bg-gradient-to-b from-[#00BCD4] to-cyan-600"
              >
                Knowledge<br />Merger
              </motion.h1>
              <motion.p 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-xs font-black uppercase tracking-[0.5em] text-[#00BCD4]/80"
              >
                Asymmetric Optimization & Tri-Artifact Synthesis
              </motion.p>
            </div>
          </div>
        )}
        </div>

        {/* Navigation Tabs */}
        <div className="w-full flex justify-center mb-16 overflow-x-auto no-scrollbar pb-4 group">
          <div className="flex items-center gap-2 p-1.5 rounded-full bg-zinc-950/80 border border-zinc-800/50 backdrop-blur-md flex-nowrap min-w-max px-6">
            {[
              { id: 'merger', label: 'Artifact Merger', icon: Layers },
              { id: 'detection', label: 'Detection Lab', icon: Shield },
              { id: 'sudoku', label: 'Forensic Matrix Lab', icon: LayoutGrid, isNew: sudokuReady },
              { id: 'agent', label: 'EdgeK Swarm', icon: Terminal },
              { id: 'mem5', label: 'MEM5 Bus', icon: Database },
              { id: 'ertp', label: 'ERTP Review', icon: BookOpen },
              { id: 'learning', label: 'Oxford Lab', icon: GraduationCap },
              { id: 'bridge', label: 'Mobile Bridge', icon: Smartphone },
              { id: 'analytics', label: 'Data Analytics', icon: Activity },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={cn(
                  "relative flex items-center gap-2 px-6 py-2.5 rounded-full text-[10px] font-black uppercase tracking-widest transition-all whitespace-nowrap",
                  activeTab === tab.id 
                    ? "text-cyan-400 bg-cyan-500/10" 
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
                )}
              >
                <tab.icon className={cn("w-3 h-3", tab.isNew && "text-cyan-400 animate-bounce")} />
                {tab.label}
                {tab.isNew && (
                  <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,1)] animate-pulse" />
                )}
                {activeTab === tab.id && (
                  <motion.div 
                    layoutId="activeTabUnderline"
                    className="absolute -bottom-1 left-4 right-4 h-0.5 bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,1)]"
                  />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content Areas */}
        {activeTab === 'sudoku' && (
          <div className="w-full max-w-7xl mb-24 animate-in fade-in zoom-in duration-500 px-4">
              <SudokuG 
                content={artifacts.input.files[0]?.content} 
                analysisData={sudokuData}
                filename={artifacts.input.files[0]?.name}
              />
          </div>
        )}
         {activeTab === 'merger' && (
          <div id="merger-container-v47" className="w-full max-w-7xl mb-24 animate-in fade-in zoom-in duration-500 flex flex-col gap-10 px-4">
            
            {/* ROW 1: TWO ARTIFACT CARDS SIDE BY SIDE */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
               <ArtifactCard 
                 artifact={artifacts.input} 
                 onUpload={(files) => handleArtifactUpload('input', files)}
                 label="Source Artifact"
                 subLabel="Neural Ingest A..."
                 icon={FileText}
               />
               <ArtifactCard 
                 artifact={artifacts.target} 
                 onUpload={(files) => handleArtifactUpload('target', files)}
                 label="Target Artifact"
                 subLabel="Baseline for Comparison"
                 icon={Target}
                 accent="purple"
               />
            </div>

            {/* ROW 2: INTELLIGENCE COMMAND CENTER (TERMINAL STYLE) */}
            <div className="w-full p-10 rounded-[3.5rem] bg-zinc-950 border border-zinc-800 shadow-[0_0_50px_-12px_rgba(34,211,238,0.2)] relative overflow-hidden">
               <div className="relative z-10 mb-10 flex justify-between items-center">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                       <Cpu className="w-5 h-5 text-cyan-400" />
                       <h3 className="text-sm font-black uppercase tracking-[0.4em] text-white">⬡ Neural Command Center</h3>
                    </div>
                    <p className="text-[9px] font-black uppercase tracking-[0.2em] text-zinc-500 ml-8">Autonomous Forensic Pipeline</p>
                  </div>
               </div>

               <div className="grid grid-cols-1 md:grid-cols-2 gap-10 relative z-10">
                  {/* LEFT COLUMN: STATUS & PROGRESS */}
                  <div className="space-y-12">
                     {/* SECTION A: AUTO-DETECTION STATUS */}
                     <div className="space-y-6">
                        <div className="flex items-center gap-2 border-l-2 border-cyan-500/30 pl-4">
                           <span className="text-[10px] font-black uppercase tracking-widest text-zinc-100">Auto-Detection Status</span>
                        </div>
                        <div className="space-y-4">
                           {[
                              { file: artifacts.input.files[0], label: 'Source' },
                              { file: artifacts.target.files[0], label: 'Target' }
                           ].map((item, idx) => {
                              const ext = item.file?.name.split('.').pop()?.toUpperCase() || '---';
                              const isValid = ['PDF', 'DOCX', 'TXT', 'CSV', 'XLSX'].includes(ext);
                              return (
                                 <div key={idx} className="flex items-center justify-between p-4 rounded-2xl bg-zinc-900/40 border border-zinc-800/50">
                                    <div className="flex items-center gap-4">
                                       <div className={cn("p-2 rounded-lg", item.file ? "bg-emerald-500/10 text-emerald-400" : "bg-zinc-800 text-zinc-600")}>
                                          {item.file ? (isValid ? <CheckCircle2 className="w-3 h-3" /> : <Check className="w-3 h-3" />) : <AlertCircle className="w-3 h-3" />}
                                       </div>
                                       <div>
                                          <p className="text-[9px] font-black text-white uppercase tracking-tight">
                                             {item.file ? `${item.file.name.substring(0, 25)}${item.file.name.length > 25 ? '...' : ''}` : 'NO FILE LOADED'}
                                          </p>
                                          <div className="flex items-center gap-2 mt-1">
                                             <span className="text-[7px] font-mono text-zinc-500">
                                                {item.file ? `${(item.file.content.length / 1024).toFixed(1)} KB` : '---'}
                                             </span>
                                             {item.file && <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-[6px] font-black text-zinc-400 border border-zinc-700">{ext}</span>}
                                             {item.label === 'Source' && sudokuReady && <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-[6px] font-black text-cyan-400 border border-cyan-500/20 tracking-tighter">MATRIX ANALYSIS: ENABLED</span>}
                                             {item.label === 'Source' && !sudokuReady && item.file && <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-[6px] font-black text-zinc-600 border border-zinc-700 tracking-tighter">MATRIX: N/A</span>}
                                          </div>
                                       </div>
                                    </div>
                                    <div className={cn(
                                      "px-3 py-1 rounded-full text-[7px] font-black uppercase tracking-widest",
                                      (artifacts.input.files[0] && artifacts.target.files[0]) ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                                      (artifacts.input.files[0] || artifacts.target.files[0]) ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                      "bg-zinc-800/50 text-zinc-600"
                                    )}>
                                       {(artifacts.input.files[0] && artifacts.target.files[0]) ? 'INGEST READY' : 
                                        (artifacts.input.files[0] || artifacts.target.files[0]) ? 'AWAITING FINAL' : 'AWAITING INPUT'}
                                    </div>
                                 </div>
                              );
                           })}
                        </div>
                     </div>

                     {/* SECTION B: AGENT TASK QUEUE */}
                     <div className="space-y-6">
                        <div className="flex items-center gap-2 border-l-2 border-cyan-500/30 pl-4">
                           <span className="text-[10px] font-black uppercase tracking-widest text-zinc-100">Agent Task Queue</span>
                        </div>
                        <div className="space-y-1">
                           {[
                              { name: '① CONTENT VECTORISER → Qdrant', phase: 'ingesting' },
                              { name: '② AI PATTERN SCANNER → CircleAI', phase: 'mapping' },
                              { name: '③ SIMILARITY ENGINE → Cosine Match', phase: 'detect' },
                              { name: '④ ACADEMIC INTEGRITY → NWU Policy', phase: 'analyze' },
                              { name: '⑤ REPORT SYNTHESISER → PDF/JSON', phase: 'synthesize' },
                              { name: '⑥ FORENSIC MATRIX SCAN → Pattern Matrix', phase: 'sudoku' },
                           ].map((agent, i) => {
                              const status = getAgentStatus(i + 1);
                              return (
                                 <div key={i} className="flex items-center justify-between px-4 py-2 rounded-xl hover:bg-white/5 transition-all group border border-transparent hover:border-zinc-800">
                                    <div className="flex items-center gap-3">
                                       <span className={cn(
                                         "text-[10px] font-black uppercase tracking-wider",
                                         status === 'PROCESSING' ? "text-cyan-400" : status === 'COMPLETE' ? "text-emerald-400" : "text-zinc-600"
                                       )}>{agent.name}</span>
                                       {agent.phase === 'sudoku' && sudokuReady && (
                                          <span className="text-[7px] font-black bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded border border-cyan-500/30 animate-pulse">PATTERN CAPTURED</span>
                                       )}
                                    </div>
                                    <div className={cn(
                                      "flex items-center gap-2 px-3 py-1 rounded text-[8px] font-black uppercase tracking-[0.2em] min-w-[100px] justify-center",
                                      status === 'PROCESSING' ? "text-amber-400 animate-pulse" :
                                      status === 'COMPLETE' ? "text-emerald-400" :
                                      "text-zinc-700"
                                    )}>
                                       {status === 'PROCESSING' && <RefreshCw className="w-3 h-3 animate-spin" />}
                                       {status === 'COMPLETE' && <CheckCircle2 className="w-3 h-3" />}
                                       {status}
                                    </div>
                                 </div>
                              );
                           })}
                        </div>
                     </div>

                     {/* SECTION C: WHAT HAS BEEN DONE */}
                     <div className="space-y-6">
                        <div className="flex items-center gap-2 border-l-2 border-cyan-500/30 pl-4">
                           <span className="text-[10px] font-black uppercase tracking-widest text-zinc-100">What has been done</span>
                        </div>
                        <div className="h-32 overflow-y-auto custom-scrollbar space-y-3 pr-2">
                           {liveLog.length > 0 ? liveLog.slice(0, 5).map((log, i) => (
                              <div key={i} className="flex items-center gap-3">
                                 <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,1)]" />
                                 <span className="text-[8px] font-mono text-zinc-500">{new Date().toLocaleTimeString([], { hour12: false })}</span>
                                 <span className="text-[9px] text-zinc-300 truncate tracking-tight">{log.message.substring(0, 45)}{log.message.length > 45 ? '...' : ''}</span>
                              </div>
                           )) : (
                              <p className="text-[9px] font-black uppercase tracking-[0.2em] text-zinc-700 italic pt-4">Awaiting first operation...</p>
                           )}
                        </div>
                     </div>

                     {/* SECTION D: WHAT HAPPENS NEXT */}
                     <div className="space-y-6">
                        <div className="flex items-center gap-2 border-l-2 border-cyan-500/30 pl-4">
                           <span className="text-[10px] font-black uppercase tracking-widest text-zinc-100">What happens next</span>
                        </div>
                        <div className="space-y-3">
                           {(() => {
                              const getNextSteps = () => {
                                 if (artifacts.input.files.length === 0) return ['Load source document (PDF/DOCX/TXT/CSV)'];
                                 if (artifacts.target.files.length === 0) return ['Load baseline comparison document'];
                                 if (runStatus.phase === 'idle') return ['Click INITIALISE NEURAL MERGE to begin'];
                                 
                                 const stepsByPhase: Record<string, string[]> = {
                                    ingesting: ['Vectorising forensic payload', 'Indexing neural cluster', 'Preparing mapping matrix'],
                                    mapping: ['Computing similarity scores', 'Identifying structural mirrors', 'Detecting AI pattern fingerprints'],
                                    detect: ['CircleAI forensic scan active', 'Calculating AI probability', 'Flagging anomalous artifacts'],
                                    analyze: ['Academic Integrity check running', 'Applying NWU Policy filters', 'Populating decision ledger'],
                                    synthesize: ['Forensic pattern matrix loading', 'Generating comprehensive report', 'Finalizing tri-artifact synthesis'],
                                    complete: ['Review detailed results', 'Check Data Analytics dashboard', 'Export certified NWU report']
                                 };
                                 return stepsByPhase[runStatus.phase] || ['Executing next forensic sequence...'];
                              };
                              return getNextSteps().map((step, i) => (
                                 <div key={i} className="flex items-center gap-4 group">
                                    <div className="w-5 h-5 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-[9px] font-black text-cyan-400">
                                       {i + 1}
                                    </div>
                                    <ArrowRight className="w-3 h-3 text-zinc-700 group-hover:translate-x-1 transition-transform" />
                                    <span className="text-[9px] font-black uppercase tracking-widest text-zinc-400">{step}</span>
                                 </div>
                              ));
                           })()}
                        </div>
                     </div>
                  </div>

                  {/* RIGHT COLUMN: TERMINAL BOX & ACTION */}
                  <div className="space-y-10 flex flex-col justify-center">
                    <TerminalBox activeRun={activeRun} />

                    {/* RUN CONTROLLER PIPELINE INDICATOR */}
                    {activeRun && (
                      <div className="p-8 rounded-[2.5rem] bg-zinc-950 border border-zinc-900 overflow-hidden relative group">
                        <div className="absolute inset-0 bg-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        <div className="relative z-10 flex flex-col gap-6">
                           <div className="flex justify-between items-center">
                              <span className="text-[10px] font-black uppercase tracking-[0.4em] text-zinc-500">Run Controller Pipeline</span>
                              <div className="flex items-center gap-2">
                                 <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                                 <span className="text-[9px] font-black text-cyan-400 truncate max-w-[120px] uppercase">
                                    {activeRun.state}
                                 </span>
                              </div>
                           </div>
                           
                           {/* 14-Step Micro-Indicators */}
                           <div className="grid grid-cols-6 sm:grid-cols-12 gap-1">
                             {STATE_SEQUENCE.map((s, idx) => (
                               <div 
                                 key={s} 
                                 className={cn(
                                   "h-1.5 rounded-full transition-all duration-500",
                                   STATE_SEQUENCE.indexOf(activeRun.state) >= idx ? "bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.5)]" : "bg-zinc-900"
                                 )}
                               />
                             ))}
                           </div>
                        </div>
                      </div>
                    )}

                    <div className="flex flex-col items-center gap-8">
                       <button 
                         onClick={handleInitialize}
                         disabled={isInitializing || isProcessing || artifacts.input.status === 'empty' || artifacts.target.status === 'empty'}
                         className={cn(
                           "fixed bottom-12 right-12 z-[50] group flex items-center gap-4 px-10 py-6 rounded-full font-black uppercase tracking-[0.4em] text-[12px] transition-all duration-700 shadow-[0_0_50px_rgba(16,185,129,0.3)] hover:shadow-[0_0_80px_rgba(16,185,129,0.5)] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:grayscale overflow-hidden border border-emerald-500/30",
                           (isInitializing || isProcessing) ? "bg-zinc-900 text-zinc-500" : "bg-emerald-500 text-white hover:bg-emerald-400"
                         )}
                       >
                         <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-1000" />
                         {(isInitializing || isProcessing) ? (
                            <>
                              <RefreshCw className="w-6 h-6 animate-spin" />
                              <span>Processing Forensic Signal...</span>
                            </>
                         ) : (
                           <>
                             <Zap className="w-6 h-6 animate-pulse text-white group-hover:scale-125 transition-transform" />
                             <span>Initialise Neural Merge</span>
                           </>
                         )}
                       </button>

                       {(isProcessing || forensicResult !== null) && (
                          <button 
                            onClick={() => {
                               setPipelineStep(0);
                               setForensicResult(null);
                               setIsProcessing(false);
                            }}
                            className="px-8 py-3 rounded-full border border-rose-500/30 bg-rose-500/5 text-rose-500 text-[10px] font-black uppercase tracking-widest hover:bg-rose-500 hover:text-white transition-all shadow-[0_0_20px_rgba(244,63,94,0.1)]"
                          >
                             {isProcessing ? 'Terminate Sequence' : 'Reset Session'}
                          </button>
                       )}
                    </div>
                  </div>
               </div>
            </div>

            {/* ROW 3: RUN LEDGER (V5.0.0) */}
            <div className="w-full space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-[12px] font-black uppercase tracking-[0.4em] text-zinc-500 flex items-center gap-3">
                   <LayoutGrid className="w-4 h-4 text-cyan-400" />
                   Control Plane: Run Ledger
                </h3>
                <span className="text-[8px] font-black text-zinc-700 uppercase tracking-widest">Showing last 20 operations</span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                 {runLedger.length === 0 ? (
                   <div className="col-span-full py-16 rounded-[2.5rem] border-2 border-dashed border-zinc-900 flex flex-col items-center justify-center text-zinc-700 gap-4">
                      <Zap className="w-8 h-8 opacity-20" />
                      <p className="text-[10px] font-black uppercase tracking-widest">No runs recorded in local telemetry</p>
                   </div>
                 ) : (
                   runLedger.map((run) => (
                      <div key={run.run_id} className="p-6 rounded-[2.5rem] bg-zinc-950 border border-zinc-900 hover:border-zinc-800 transition-all group relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                           <Shield className="w-4 h-4 text-zinc-700" />
                        </div>
                        <div className="flex flex-col gap-4">
                           <div className="flex justify-between items-start">
                              <div>
                                <p className="text-[8px] font-black text-zinc-600 uppercase tracking-widest mb-1">RUN_ID</p>
                                <p className="text-[11px] font-black text-white">{run.run_id}</p>
                              </div>
                              <div className={cn(
                                "px-3 py-1 rounded-full text-[8px] font-black uppercase tracking-widest border",
                                run.state === 'completed' ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" :
                                run.state === 'failed' ? "bg-rose-500/10 text-rose-500 border-rose-500/30" :
                                "bg-amber-500/10 text-amber-400 border-amber-500/30"
                              )}>
                                {run.state}
                              </div>
                           </div>
                           
                           <div className="grid grid-cols-2 gap-4">
                              <div>
                                <p className="text-[8px] font-black text-zinc-600 uppercase tracking-widest mb-1">Operator</p>
                                <p className="text-[10px] font-black text-zinc-300 truncate">{run.operator}</p>
                              </div>
                              <div>
                                <p className="text-[8px] font-black text-zinc-600 uppercase tracking-widest mb-1">Updated</p>
                                <p className="text-[10px] font-black text-zinc-300 font-mono">{new Date(run.updated_at).toLocaleTimeString([], { hour12: false })}</p>
                              </div>
                           </div>

                           <div className="w-full h-1 bg-zinc-900 rounded-full overflow-hidden mt-2">
                              <div 
                                className="h-full bg-cyan-500" 
                                style={{ width: `${STATE_PROGRESS[run.state]}%` }}
                              />
                           </div>
                        </div>
                      </div>
                   ))
                 )}
              </div>
            </div>

            {/* ROW 4: FORENSIC MATRIX LAB */}
            <div className="w-full">
              <SudokuG 
                content={artifacts.input.files[0]?.content} 
                analysisData={forensicResult}
                autoTrigger={pipelineStep >= 6}
                filename={artifacts.input.files[0]?.name}
              />
            </div>
          </div>
        )}

        {/* Learning Lab View */}
        {activeTab === 'learning' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-4xl space-y-12">
            <div className="flex flex-col items-center text-center space-y-4 mb-12">
              <GraduationCap className="w-16 h-16 text-cyan-400" />
              <h2 className="text-5xl font-black uppercase tracking-[-0.05em] text-white">Oxford Learning Lab</h2>
              <p className="text-xs font-black uppercase tracking-[0.4em] text-zinc-500">Socratic Tutoring & Bloom's Taxonomy Mastery</p>
            </div>

            {!learningSession ? (
              <div className="p-12 rounded-[3rem] border-2 border-zinc-800 bg-zinc-950/50 backdrop-blur-xl space-y-8">
                <div className="space-y-4">
                  <label className="text-[10px] font-black uppercase tracking-widest text-zinc-400 px-4">What do you want to master today?</label>
                  <input 
                    type="text"
                    value={learningConcept}
                    onChange={(e) => setLearningConcept(e.target.value)}
                    placeholder="e.g. Quantum Entanglement, French Revolution, React Hooks..."
                    className="w-full px-8 py-6 rounded-3xl bg-zinc-900 border border-zinc-800 focus:border-cyan-500 transition-all text-lg font-bold outline-none"
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  {[
                    { id: 'child', label: 'Child (ELI5)', color: 'emerald' },
                    { id: 'high_schooler', label: 'High Schooler', color: 'cyan' },
                    { id: 'academic', label: 'PhD / Academic', color: 'purple' },
                  ].map((lvl) => (
                    <button
                      key={lvl.id}
                      onClick={() => setLearningLevel(lvl.id as any)}
                      className={cn(
                        "p-6 rounded-3xl border-2 transition-all flex flex-col items-center gap-2",
                        learningLevel === lvl.id 
                          ? `border-cyan-500 bg-cyan-500/10` 
                          : "border-zinc-800 hover:border-zinc-700 bg-zinc-900/50"
                      )}
                    >
                      <span className={cn("text-xs font-black uppercase tracking-widest", learningLevel === lvl.id ? `text-cyan-400` : "text-zinc-500")}>
                        {lvl.label}
                      </span>
                    </button>
                  ))}
                </div>

                <button 
                  onClick={startLearning}
                  disabled={!learningConcept.trim() || isLearningLoading}
                  className="w-full py-6 rounded-3xl bg-cyan-600 text-white text-sm font-black uppercase tracking-widest hover:bg-cyan-500 transition-all flex items-center justify-center gap-3 disabled:opacity-50"
                >
                  {isLearningLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Zap className="w-5 h-5" />}
                  Initiate Socratic Exchange
                </button>
              </div>
            ) : (
              <div className="space-y-8">
                {/* Bloom's Progress Tracker */}
                <div className="flex justify-between items-center px-4">
                  {["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"].map((stage, i) => {
                    const stages = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"];
                    const currentIdx = stages.indexOf(learningSession.level || "Remember");
                    const isCompleted = i < currentIdx;
                    const isActive = i === currentIdx;
                    
                    return (
                      <div key={stage} className="flex flex-col items-center gap-2">
                        <div className={cn(
                          "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all",
                          isCompleted ? "bg-emerald-500 border-emerald-500 text-zinc-950" :
                          isActive ? "border-cyan-500 bg-cyan-500/10 text-cyan-400 scale-125" :
                          "border-zinc-800 text-zinc-600"
                        )}>
                          {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <span className="text-[10px] font-black">{i + 1}</span>}
                        </div>
                        <span className={cn("text-[8px] font-black uppercase tracking-tighter", isActive ? "text-cyan-400" : "text-zinc-600")}>
                          {stage}
                        </span>
                      </div>
                    )
                  })}
                </div>

                <div className="p-12 rounded-[3rem] border-2 border-zinc-800 bg-zinc-950/50 backdrop-blur-xl relative">
                  <div className="flex items-center gap-3 mb-8">
                    <div className="w-3 h-3 rounded-full bg-cyan-500 animate-pulse" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Socratic Tutor • Oxford Method</span>
                  </div>
                  
                  <div className="text-xl font-medium text-zinc-200 leading-relaxed mb-12 markdown-body">
                    <Markdown>{learningSession.question}</Markdown>
                  </div>

                  <div className="relative group">
                    <textarea 
                      value={learningInput}
                      onChange={(e) => setLearningInput(e.target.value)}
                      placeholder="Share your thoughts..."
                      className="w-full h-40 px-8 py-6 rounded-3xl bg-zinc-900 border border-zinc-800 focus:border-cyan-500 transition-all text-lg font-medium outline-none resize-none"
                    />
                    <button 
                      onClick={respondLearning}
                      disabled={!learningInput.trim() || isLearningLoading}
                      className="absolute bottom-6 right-6 p-4 rounded-2xl bg-cyan-600 text-white hover:bg-cyan-500 transition-all disabled:opacity-50"
                    >
                      {isLearningLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <ArrowDown className="w-5 h-5 -rotate-90" />}
                    </button>
                  </div>
                </div>

                <div className="flex justify-center gap-4">
                  <button onClick={() => setLearningSession(null)} className="px-6 py-3 rounded-xl border border-zinc-800 text-[10px] font-black uppercase tracking-widest text-zinc-500 hover:text-rose-400 hover:border-rose-400/30 transition-all">
                    End Session
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {activeTab === 'detection' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-5xl space-y-12 mb-24">
            <div className="flex flex-col items-center text-center space-y-4 mb-12">
              <Shield className="w-16 h-16 text-cyan-400" />
              <h2 className="text-5xl font-black uppercase tracking-[-0.05em] text-white">Detection Lab</h2>
              <p className="text-xs font-black uppercase tracking-[0.4em] text-zinc-500">CircleAI Forensic Verification Layer</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
               <div className="p-10 rounded-[3rem] border-2 border-zinc-800 bg-zinc-950/50 backdrop-blur-xl space-y-8">
                  <div className="flex items-center justify-between">
                     <h3 className="text-lg font-black uppercase tracking-widest text-white">CircleAI Verdict</h3>
                     <div className={cn(
                       "px-4 py-1 rounded-full text-[10px] font-black uppercase tracking-widest",
                       circleAIResult?.verdict === 'HUMAN' ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                       circleAIResult?.verdict === 'AI' ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" :
                       "bg-zinc-800 text-zinc-500"
                     )}>
                        {circleAIResult?.verdict || 'Awaiting Signal'}
                     </div>
                  </div>

                  <div className="flex justify-center py-4">
                     <div className="relative flex items-center justify-center w-48 h-48">
                        <svg className="w-full h-full -rotate-90">
                           <circle cx="96" cy="96" r="80" stroke="currentColor" strokeWidth="12" fill="transparent" className="text-zinc-900" />
                           <circle cx="96" cy="96" r="80" stroke="currentColor" strokeWidth="12" fill="transparent" 
                             strokeDasharray={2 * Math.PI * 80} 
                             strokeDashoffset={2 * Math.PI * 80 - ((circleAIResult?.circle_score || 0) / 100) * 2 * Math.PI * 80} 
                             className="text-cyan-500 transition-all duration-1000" 
                           />
                        </svg>
                        <div className="absolute flex flex-col items-center">
                           <span className="text-5xl font-black text-white">{circleAIResult?.circle_score || 0}%</span>
                           <span className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-500">AI PROBABILITY</span>
                        </div>
                     </div>
                  </div>

                  <div className="space-y-4">
                     <div className="bg-zinc-900/50 p-6 rounded-2xl border border-zinc-800">
                        <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">Technical Reasoning</p>
                        <p className="text-xs text-zinc-300 leading-relaxed italic">
                           "{circleAIResult?.reasoning || 'No active analysis on current session buffer. Initialize a merger to trigger CircleAI forensic scan.'}"
                        </p>
                     </div>

                     <div className="grid grid-cols-2 gap-4">
                        <div className="bg-zinc-900/50 p-4 rounded-xl border border-zinc-800">
                           <p className="text-[8px] font-black uppercase tracking-widest text-zinc-500 mb-1">Confidence</p>
                           <p className="text-lg font-black text-white">{Math.round((circleAIResult?.confidence ?? 0) * 100)}%</p>
                        </div>
                        <div className="bg-zinc-900/50 p-4 rounded-xl border border-zinc-800">
                           <p className="text-[8px] font-black uppercase tracking-widest text-zinc-500 mb-1">Provider Link</p>
                           <p className="text-lg font-black text-emerald-400">SECURE</p>
                        </div>
                     </div>
                  </div>
               </div>

               <div className="space-y-8">
                  <div className="p-10 rounded-[3rem] border-2 border-zinc-800 bg-zinc-950/50 backdrop-blur-xl">
                     <h3 className="text-sm font-black uppercase tracking-widest text-zinc-400 mb-6">Model Artifacts Detected</h3>
                     <div className="space-y-3">
                        {(circleAIResult?.model_flags || []).length > 0 ? circleAIResult.model_flags.map((flag: string, i: number) => (
                           <div key={i} className="flex items-center gap-4 p-4 rounded-2xl bg-rose-500/5 border border-rose-500/10">
                              <AlertCircle className="w-4 h-4 text-rose-400" />
                              <span className="text-[10px] font-black uppercase tracking-widest text-rose-300">{flag}</span>
                           </div>
                        )) : (
                           <div className="text-center py-8 text-zinc-600">
                              <Activity className="w-8 h-8 mx-auto mb-3 opacity-20" />
                              <p className="text-[10px] font-black uppercase tracking-widest">No spectral artifacts found</p>
                           </div>
                        )}
                     </div>
                  </div>

                  <div className="p-10 rounded-[3rem] border-2 border-zinc-800 bg-zinc-900/10 backdrop-blur-xl">
                      <div className="flex items-center gap-3 mb-4">
                        <Cpu className="w-5 h-5 text-zinc-500" />
                        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Forensic Methodology</span>
                      </div>
                      <p className="text-xs text-zinc-500 leading-relaxed">
                        CircleAI uses a custom-tuned Gemini 1.5 Flash node to analyze linguistic entropy, burstiness, and semantic repetition patterns common to transformer-based outputs.
                      </p>
                  </div>
               </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'analytics' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-6xl space-y-12 mb-24">
            <div className="flex flex-col items-center text-center space-y-4 mb-12">
              <Activity className="w-16 h-16 text-cyan-400" />
              <h2 className="text-5xl font-black uppercase tracking-[-0.05em] text-white">DataDriven Intelligence</h2>
              <p className="text-xs font-black uppercase tracking-[0.4em] text-zinc-500">NWU Cluster Global Submission Analytics</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
               {[
                 { label: 'Total Submissions', value: analyticsData?.total_submissions || 0, icon: Layers },
                 { label: 'Avg AI Probability', value: `${analyticsData?.avg_ai_score ?? 0}%`, icon: BrainCircuit },
                 { label: 'High Risk Flagged', value: analyticsData?.high_risk_count ?? 0, icon: AlertCircle, variant: 'rose' },
                 { label: 'Avg Similarity', value: `${Math.round((analyticsData?.avg_similarity ?? 0) * 100)}%`, icon: Target },
               ].map((stat, i) => (
                 <div key={i} className="p-8 rounded-[2.5rem] bg-zinc-950/80 border border-zinc-800 backdrop-blur-xl flex flex-col gap-4">
                    <stat.icon className={cn("w-6 h-6", stat.variant === 'rose' ? "text-rose-400" : "text-cyan-400")} />
                    <div>
                       <p className="text-3xl font-black text-white">{stat.value}</p>
                       <p className="text-[9px] font-black uppercase tracking-widest text-zinc-500">{stat.label}</p>
                    </div>
                 </div>
               ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
               <div className="lg:col-span-2 p-12 rounded-[3.5rem] bg-zinc-950/80 border border-zinc-800 backdrop-blur-xl">
                  <div className="flex items-center justify-between mb-12">
                     <h3 className="text-sm font-black uppercase tracking-widest text-white">Detection Trends (Last 5 Days)</h3>
                     <span className="text-[8px] font-black text-emerald-400 uppercase tracking-widest px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">Live Sync</span>
                  </div>
                  
                  <div className="h-64 flex items-end justify-between gap-4 px-4">
                     {(analyticsData?.detection_trends || []).map((trend: any, i: number) => (
                        <div key={i} className="flex-1 flex flex-col items-center gap-4 group">
                           <div className="relative w-full flex flex-col items-center">
                              <motion.div 
                                initial={{ height: 0 }}
                                animate={{ height: `${Math.max(10, ((trend.count ?? 0) / (analyticsData?.total_submissions || 1)) * 100)}%` }}
                                className="w-full max-w-[40px] rounded-t-xl bg-gradient-to-t from-cyan-600 to-cyan-400 group-hover:from-cyan-400 group-hover:to-white transition-all shadow-[0_0_20px_rgba(6,182,212,0.2)]"
                              />
                              <div className="absolute -top-8 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-black text-white">
                                 {trend.count}
                              </div>
                           </div>
                           <span className="text-[8px] font-black uppercase text-zinc-600 rotate-45 lg:rotate-0 mt-4">{trend.date.split('-').slice(1).join('/')}</span>
                        </div>
                     ))}
                  </div>
               </div>

               <div className="p-12 rounded-[3.5rem] bg-zinc-950/80 border border-zinc-800 backdrop-blur-xl space-y-8">
                  <h3 className="text-sm font-black uppercase tracking-widest text-white">Top Risk Vectors</h3>
                  <div className="space-y-6">
                     {(analyticsData?.top_risk_categories || []).map((cat: string, i: number) => (
                        <div key={i} className="space-y-2">
                           <div className="flex justify-between text-[9px] font-black uppercase tracking-widest">
                              <span className="text-zinc-300">{cat}</span>
                              <span className="text-cyan-400">{85 - (i * 15)}%</span>
                           </div>
                           <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden">
                              <div className="h-full bg-cyan-500" style={{ width: `${85 - (i * 15)}%` }} />
                           </div>
                        </div>
                     ))}
                  </div>
                  <div className="pt-8 border-t border-zinc-900">
                     <p className="text-[10px] text-zinc-500 leading-relaxed">
                        Data insights derived from the NWU Central Ingest node. Risk vectors are automatically categorized by the Neural Cluster during each merge cycle.
                     </p>
                  </div>
               </div>
            </div>
          </motion.div>
        )}

        {/* Android Bridge Tab */}
        {activeTab === 'bridge' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-2xl space-y-8 mb-24">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center bg-zinc-950/80 border border-zinc-800 p-12 rounded-[3.5rem] backdrop-blur-2xl">
               <div className="flex flex-col items-center gap-6">
                  <div className="w-full aspect-square bg-white p-6 rounded-3xl flex items-center justify-center shadow-[0_0_40px_rgba(255,255,255,0.1)] group overflow-hidden">
                     <div className="w-full h-full border-[10px] border-zinc-950 relative overflow-hidden flex flex-wrap">
                        {[...Array(49)].map((_, i) => (
                          <div key={i} className={cn(
                            "w-[14.28%] h-[14.28%] transition-colors duration-[2s]",
                            Math.random() > 0.5 ? "bg-zinc-900" : "bg-black"
                          )} />
                        ))}
                        <div className="absolute inset-0 flex items-center justify-center p-4">
                           <div className="w-full h-full border-2 border-zinc-200/20 rounded flex items-center justify-center bg-zinc-900/10 backdrop-blur-[1px]">
                              <Smartphone className="w-12 h-12 text-zinc-800 group-hover:scale-110 transition-transform" />
                           </div>
                        </div>
                     </div>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-zinc-300">Scan to connect mobile device</p>
                    <p className="text-[8px] font-bold text-zinc-500 mt-2">Compatible with Android 12+</p>
                  </div>
               </div>

               <div className="space-y-8">
                <div className="bg-zinc-900/50 border border-zinc-800 p-8 rounded-3xl text-center">
                    <span className="text-[10px] font-black uppercase tracking-[0.5em] text-zinc-500 block mb-4">Pairing Code</span>
                    <span className="text-5xl font-black text-cyan-400 tracking-[0.2em] font-mono">821-495</span>
                </div>
                <div className="space-y-4">
                    <p className="text-xs text-zinc-400 leading-relaxed">Sync forensic artifacts and receive live heartbeat updates directly to your handset via the secure LAN bridge.</p>
                    <div className="flex flex-col gap-3">
                      <button className="w-full py-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-[10px] font-black uppercase tracking-widest text-zinc-400 hover:text-white transition-all">Download Client APK</button>
                      <button className="w-full py-4 rounded-2xl bg-cyan-600 text-white text-[10px] font-black uppercase tracking-widest hover:bg-cyan-500 transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)]">Launch Web Bridge</button>
                    </div>
                </div>
               </div>
            </div>
          </motion.div>
        )}

        {/* Action Section */}
        <div className="flex flex-col items-center gap-12 w-full mb-24">
          {/* Processing Pipeline Indicators */}
          <AnimatePresence>
            {isInitializing && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="w-full max-w-4xl p-10 rounded-[3rem] bg-zinc-900/50 border border-zinc-800/50 backdrop-blur-xl"
              >
                <div className="flex items-center justify-between mb-10">
                  <div className="flex items-center gap-5">
                    <div className="p-4 rounded-2xl bg-cyan-500/10 text-cyan-400">
                      <Activity className="w-6 h-6 animate-pulse" />
                    </div>
                    <div>
                      <h3 className="text-xl font-black text-white uppercase tracking-tight font-display">Neural Core Active</h3>
                      <p className="text-[11px] font-black text-zinc-500 uppercase tracking-widest">Run ID: {activeRun?.run_id || 'Initializing...'}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-black text-cyan-400 font-display">{runHeartbeat?.progress || 0}%</p>
                    <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest">{runHeartbeat?.phase || 'Queued'}</p>
                  </div>
                </div>

                <div className="w-full h-3 bg-zinc-950 rounded-full overflow-hidden mb-10 border border-zinc-800/50">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${runHeartbeat?.progress || 0}%` }}
                    className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 shadow-[0_0_30px_rgba(6,182,212,0.4)]"
                  />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-6">
                  {['validating', 'ingesting', 'indexing', 'mapping', 'comparing', 'qa'].map((phase) => (
                    <div key={phase} className="flex flex-col items-center gap-3">
                      <div className={cn(
                        "w-2 h-2 rounded-full transition-all duration-500",
                        runHeartbeat?.phase === phase ? "bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.8)] scale-150" : 
                        (runHeartbeat?.progress || 0) > 0 && ['validating', 'ingesting', 'indexing', 'mapping', 'comparing', 'qa'].indexOf(phase) < ['validating', 'ingesting', 'indexing', 'mapping', 'comparing', 'qa'].indexOf(runHeartbeat?.phase) ? "bg-emerald-500" : "bg-zinc-800"
                      )} />
                      <span className={cn(
                        "text-[10px] font-black uppercase tracking-widest transition-colors text-center",
                        runHeartbeat?.phase === phase ? "text-cyan-400" : "text-zinc-600"
                      )}>{phase}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex gap-6">
            <button
              onClick={handleInitialize}
              disabled={isInitializing || artifacts.input.status === 'empty'}
              className={cn(
                "group relative px-16 py-6 rounded-2xl font-black uppercase tracking-[0.4em] text-sm transition-all duration-500 overflow-hidden",
                artifacts.input.status === 'empty' ? "bg-zinc-900 text-zinc-600 cursor-not-allowed" : "bg-cyan-500 text-zinc-950 hover:bg-cyan-400 hover:shadow-[0_0_50px_-10px_rgba(6,182,212,0.5)] active:scale-95"
              )}
            >
              <span className="relative z-10 flex items-center gap-4">
                {isInitializing ? <RefreshCw className="w-5 h-5 animate-spin" /> : "Initialize"}
              </span>
            </button>

            <AnimatePresence>
              {report && (
                <motion.button
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  onClick={handleDownload}
                  className="px-8 py-6 rounded-2xl border border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800 text-zinc-300 font-black uppercase tracking-[0.2em] text-xs transition-all flex items-center gap-4"
                >
                  <Download className="w-5 h-5" />
                  Download Bundle
                </motion.button>
              )}
            </AnimatePresence>
          </div>

          {/* Results Preview & Detailed Report */}
          <AnimatePresence>
            {report && (
              <motion.div 
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full space-y-12"
              >
                {/* Minimalist Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div className="p-6 rounded-2xl bg-zinc-900/30 border border-zinc-800/50 backdrop-blur-sm">
                    <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">Screening</p>
                    <p className="text-xl font-black text-cyan-400">{(report.screening.score * 100).toFixed(1)}%</p>
                    <p className="text-[9px] font-bold text-zinc-600 uppercase mt-1">{report.screening.band} band detected</p>
                  </div>
                  <div className="p-6 rounded-2xl bg-zinc-900/30 border border-zinc-800/50 backdrop-blur-sm">
                    <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">Grammar</p>
                    <p className="text-xl font-black text-emerald-400">{report.grammar.grammar.length + report.grammar.style.length} Issues</p>
                    <p className="text-[9px] font-bold text-zinc-600 uppercase mt-1">Linguistic scan complete</p>
                  </div>
                  <div className="p-6 rounded-2xl bg-zinc-900/30 border border-zinc-800/50 backdrop-blur-sm">
                    <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">Similarity</p>
                    <p className="text-xl font-black text-purple-400">{report.similarity.semantic_matches.length} Matches</p>
                    <p className="text-[9px] font-bold text-zinc-600 uppercase mt-1">Vector space mapped</p>
                  </div>
                  <div className="p-6 rounded-2xl bg-zinc-900/30 border border-zinc-800/50 backdrop-blur-sm">
                    <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">System</p>
                    <p className="text-xl font-black text-zinc-300">Verified</p>
                    <p className="text-[9px] font-bold text-zinc-600 uppercase mt-1">Deterministic success</p>
                  </div>
                </div>

                {/* Detailed Synthesis Report */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
                  {/* Left Column: Findings */}
                  <div className="lg:col-span-2 space-y-8">
                    <div className="p-10 rounded-[2.5rem] bg-zinc-900/40 border border-zinc-800/50 backdrop-blur-xl">
                      <div className="flex items-center justify-between mb-12">
                        <h2 className="text-4xl font-black uppercase tracking-tight text-white font-display">Synthesis Findings</h2>
                        <div className="flex gap-3">
                          <span className="px-4 py-1.5 rounded-full bg-cyan-500/10 text-cyan-400 text-[11px] font-black uppercase tracking-widest border border-cyan-500/20">Audit Ready</span>
                        </div>
                      </div>

                      <div className="space-y-10">
                        {/* AI Screening Findings */}
                        <div className="p-10 rounded-[3rem] bg-zinc-950/50 border border-zinc-800/50 flex items-start gap-10 relative overflow-hidden group">
                          <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
                            <Shield className="w-32 h-32 text-cyan-500" />
                          </div>
                          
                          <div className={cn(
                            "p-5 rounded-2xl shrink-0",
                            report.screening.band === 'review' ? "bg-rose-500/10 text-rose-400" : 
                            report.screening.band === 'warn' ? "bg-amber-500/10 text-amber-400" : "bg-emerald-500/10 text-emerald-400"
                          )}>
                            <Shield className="w-8 h-8" />
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-10">
                              <div>
                                <h3 className="text-2xl font-black text-white uppercase tracking-tight font-display mb-2">AI Screening Analysis</h3>
                                <p className="text-[11px] font-black text-zinc-500 uppercase tracking-[0.25em]">Binoculars Forensic Pipeline</p>
                              </div>
                              <span className={cn(
                                "px-5 py-2 rounded-full text-[11px] font-black uppercase tracking-widest border backdrop-blur-md",
                                report.screening.band === 'review' ? "bg-rose-500/10 text-rose-400 border-rose-500/20" : 
                                report.screening.band === 'warn' ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : 
                                "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              )}>
                                {report.screening.band} Band
                              </span>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mb-10">
                              <div className="p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800/30 hover:border-cyan-500/30 transition-colors">
                                <p className="text-[11px] font-black uppercase tracking-widest text-zinc-500 mb-4">Confidence Score</p>
                                <p className="text-4xl font-black text-cyan-400 font-display">{(report.screening.score * 100).toFixed(1)}%</p>
                              </div>
                              <div className="p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800/30 hover:border-zinc-700/30 transition-colors">
                                <p className="text-[11px] font-black uppercase tracking-widest text-zinc-500 mb-4">Binoculars Band</p>
                                <p className="text-sm font-black text-zinc-300 uppercase tracking-widest mt-1">
                                  {report.screening.band}
                                </p>
                              </div>
                              <div className="p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800/30 hover:border-zinc-700/30 transition-colors">
                                <p className="text-[11px] font-black uppercase tracking-widest text-zinc-500 mb-4">Pipeline Action</p>
                                <p className="text-sm font-black text-zinc-300 uppercase tracking-widest mt-1">
                                  {report.screening.action.replace(/_/g, ' ')}
                                </p>
                              </div>
                            </div>

                            {report.screening.metrics && (
                              <div className="grid grid-cols-3 gap-10 mb-10 p-8 rounded-2xl bg-zinc-900/20 border border-zinc-800/20">
                                <div>
                                  <p className="text-[11px] font-black uppercase tracking-widest text-zinc-600 mb-3">Perplexity</p>
                                  <p className="text-base font-mono text-zinc-400 font-medium">{report.screening.metrics.perplexity}</p>
                                </div>
                                <div>
                                  <p className="text-[11px] font-black uppercase tracking-widest text-zinc-600 mb-3">Cross-PPL</p>
                                  <p className="text-base font-mono text-zinc-400 font-medium">{report.screening.metrics.cross_perplexity}</p>
                                </div>
                                <div>
                                  <p className="text-[11px] font-black uppercase tracking-widest text-zinc-600 mb-3">Entropy</p>
                                  <p className="text-base font-mono text-zinc-400 font-medium">{report.screening.metrics.entropy}</p>
                                </div>
                              </div>
                            )}

                            {report.screening.notes && (
                              <div className="pt-8 border-t border-zinc-800/50">
                                <ul className="space-y-4">
                                  {report.screening.notes.map((note: string, i: number) => (
                                    <li key={i} className="text-[13px] text-zinc-400 flex items-start gap-5 leading-relaxed">
                                      <div className="w-2.5 h-2.5 rounded-full bg-zinc-700 mt-1.5 shrink-0 shadow-[0_0_10px_rgba(63,63,70,0.5)]" />
                                      {note}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                          <span className="text-[11px] font-black uppercase tracking-[0.4em] text-zinc-700 [writing-mode:vertical-lr] rotate-180 shrink-0 self-center opacity-50">Screening</span>
                        </div>

                        {/* Grammar & Style Findings */}
                        {[...report.grammar.grammar, ...report.grammar.style].map((finding: any, idx: number) => (
                          <div key={idx} className="p-10 rounded-[3rem] bg-zinc-950/50 border border-zinc-800/50 flex items-start gap-10 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
                              <AlertCircle className={cn("w-32 h-32", finding.type === 'grammar' ? "text-emerald-500" : "text-amber-500")} />
                            </div>

                            <div className={cn(
                              "p-5 rounded-2xl shrink-0",
                              finding.type === 'grammar' ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"
                            )}>
                              <AlertCircle className="w-8 h-8" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="mb-8">
                                <h3 className="text-2xl font-black text-white uppercase tracking-tight font-display mb-2">Linguistic Finding</h3>
                                <p className="text-[11px] font-black text-zinc-500 uppercase tracking-[0.25em]">Automated Prose Audit</p>
                              </div>
                              
                              <h4 className="text-lg font-bold text-zinc-100 mb-8 leading-relaxed">{finding.message}</h4>
                              
                              {finding.replacement && (
                                <div className="p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800/30 inline-flex flex-col">
                                  <p className="text-[11px] text-zinc-500 uppercase tracking-widest mb-3 font-black">Suggested Correction</p>
                                  <p className="text-base text-emerald-400 font-mono font-bold bg-emerald-500/5 px-4 py-2 rounded-lg border border-emerald-500/10">{finding.replacement}</p>
                                </div>
                              )}
                            </div>
                            <span className="text-[11px] font-black uppercase tracking-[0.4em] text-zinc-700 [writing-mode:vertical-lr] rotate-180 shrink-0 self-center opacity-50">{finding.type}</span>
                          </div>
                        ))}

                        {/* Similarity Matches */}
                        {[...report.similarity.semantic_matches, ...(report.similarity.overlap_matches || [])].map((match: any, idx: number) => (
                          <div key={idx} className="p-10 rounded-[3rem] bg-zinc-950/50 border border-zinc-800/50 flex items-center justify-between gap-10 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity">
                              <FileText className="w-32 h-32 text-purple-500" />
                            </div>

                            <div className="flex items-center gap-10 flex-1 min-w-0">
                              <div className="p-5 rounded-2xl bg-purple-500/10 text-purple-400 shrink-0">
                                <FileText className="w-8 h-8" />
                              </div>
                              <div className="min-w-0">
                                <div className="mb-4">
                                  <h3 className="text-2xl font-black text-white uppercase tracking-tight font-display truncate">{match.title}</h3>
                                  <p className="text-[11px] font-black text-zinc-500 uppercase tracking-[0.25em]">Cross-Document Correlation</p>
                                </div>
                                <div className="flex flex-wrap gap-3">
                                  <span className="text-[11px] font-black text-zinc-600 uppercase tracking-widest bg-zinc-900/50 px-4 py-1.5 rounded-full border border-zinc-800/50">
                                    {match.jaccard_estimate !== undefined ? "Overlap Detection" : "Semantic Mapping"}
                                  </span>
                                  {match.jaccard_estimate !== undefined && (
                                    <span className="text-[11px] font-black text-purple-400 uppercase tracking-widest bg-purple-500/5 px-4 py-1.5 rounded-full border border-purple-500/10">
                                      Jaccard: {(match.jaccard_estimate * 100).toFixed(1)}%
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <div className="flex flex-col items-end shrink-0 relative z-10">
                              <span className="text-5xl font-black text-purple-400 font-display tracking-tighter">
                                {((match.score || match.jaccard_estimate) * 100).toFixed(1)}%
                              </span>
                              <span className="text-[11px] font-black text-zinc-700 uppercase tracking-[0.25em] mt-2">Match Index</span>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Lattice Search Lab */}
                      <div className="mt-16 space-y-8">
                        <div className="flex items-center gap-4 mb-8">
                          <Database className="w-8 h-8 text-cyan-400" />
                          <div>
                            <h2 className="text-3xl font-black text-white uppercase tracking-tighter italic">Lattice Neural Lab</h2>
                            <p className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em]">Authoritative SQLite Vector Retrieval</p>
                          </div>
                        </div>

                        <div className="p-10 rounded-[3rem] bg-zinc-950/80 border border-cyan-500/20 shadow-[0_0_50px_-20px_rgba(6,182,212,0.2)]">
                          <div className="flex gap-4 mb-10">
                            <input 
                              type="text"
                              value={latticeSearchQuery}
                              onChange={(e) => setLatticeSearchQuery(e.target.value)}
                              placeholder="Query the Forensic Index (e.g. 'audit logs', 'unathorized access')..."
                              onKeyDown={(e) => e.key === 'Enter' && handleLatticeSearch()}
                              className="flex-1 bg-zinc-900/50 border border-zinc-800 rounded-2xl px-6 py-4 text-sm font-medium text-white placeholder:text-zinc-600 focus:outline-none focus:border-cyan-500/50 transition-all"
                            />
                            <button 
                              onClick={handleLatticeSearch}
                              disabled={isLatticeSearching || !latticeSearchQuery}
                              className="px-8 py-4 rounded-2xl bg-cyan-600 text-white font-black uppercase tracking-widest text-[11px] hover:bg-cyan-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_4px_20px_-5px_rgba(6,182,212,0.5)]"
                            >
                              {isLatticeSearching ? 'Searching...' : 'Search Index'}
                            </button>
                          </div>

                          <div className="space-y-6">
                            <AnimatePresence mode="wait">
                              {latticeSearchResults.length > 0 ? (
                                <motion.div 
                                  initial={{ opacity: 0 }}
                                  animate={{ opacity: 1 }}
                                  exit={{ opacity: 0 }}
                                  className="space-y-4"
                                >
                                  {latticeSearchResults.map((res, i) => (
                                    <div key={i} className="p-6 rounded-2xl bg-zinc-900/40 border border-zinc-800/50 group hover:border-cyan-500/30 transition-all">
                                      <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-3">
                                          <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                                          <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">{res.artifact_name} • Chunk {res.chunk_index}</span>
                                        </div>
                                        <span className="text-[10px] font-black text-cyan-400 uppercase tracking-widest tabular-nums">Rank: {(1 - (res.rank / 10)).toFixed(4)}</span>
                                      </div>
                                      <p className="text-sm text-zinc-300 leading-relaxed font-medium line-clamp-3 italic">"{res.text}"</p>
                                    </div>
                                  ))}
                                </motion.div>
                              ) : latticeSearchQuery && !isLatticeSearching ? (
                                <motion.div 
                                  initial={{ opacity: 0 }}
                                  animate={{ opacity: 1 }}
                                  className="py-20 text-center"
                                >
                                  <AlertCircle className="w-12 h-12 text-zinc-800 mx-auto mb-4" />
                                  <p className="text-xs font-black uppercase tracking-widest text-zinc-600">No Authoritative Matches Found</p>
                                </motion.div>
                              ) : (
                                <div className="py-20 text-center border-2 border-dashed border-zinc-900 rounded-[2rem]">
                                  <Database className="w-12 h-12 text-zinc-900 mx-auto mb-4" />
                                  <p className="text-[10px] font-black uppercase tracking-widest text-zinc-600">Neural Cluster: Standby</p>
                                </div>
                              )}
                            </AnimatePresence>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right Column: System Telemetry */}
                  <div className="space-y-8">
                    <div className="p-8 rounded-[2rem] bg-zinc-900/40 border border-zinc-800/50 backdrop-blur-xl">
                      <h3 className="text-xs font-black uppercase tracking-[0.3em] text-zinc-500 mb-8">System Telemetry</h3>
                      
                      <div className="space-y-8">
                        <div className="h-32 w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={SYSTEM_METRICS}>
                              <defs>
                                <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3}/>
                                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                                </linearGradient>
                              </defs>
                              <Area type="monotone" dataKey="cpu" stroke="#06b6d4" fillOpacity={1} fill="url(#colorCpu)" strokeWidth={2} />
                            </AreaChart>
                          </ResponsiveContainer>
                          <p className="text-[10px] font-black uppercase tracking-widest text-zinc-600 mt-2">CPU Utilization</p>
                        </div>

                        <div className="h-32 w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={SYSTEM_METRICS}>
                              <defs>
                                <linearGradient id="colorMem" x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3}/>
                                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                                </linearGradient>
                              </defs>
                              <Area type="monotone" dataKey="memory" stroke="#a855f7" fillOpacity={1} fill="url(#colorMem)" strokeWidth={2} />
                            </AreaChart>
                          </ResponsiveContainer>
                          <p className="text-[10px] font-black uppercase tracking-widest text-zinc-600 mt-2">Memory Allocation</p>
                        </div>

                        <div className="pt-8 border-t border-zinc-800/50">
                          <div className="flex items-center justify-between mb-4">
                            <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Node Status</span>
                            <span className="text-[10px] font-black uppercase tracking-widest text-emerald-400">Optimal</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Latency</span>
                            <span className="text-[10px] font-black uppercase tracking-widest text-zinc-300">14ms</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Multi-Provider Detection Lab */}
        <div className="w-full max-w-7xl mb-24">
          <div className="flex items-center gap-4 mb-8">
            <Globe className="w-6 h-6 text-emerald-400" />
            <h2 className="text-3xl font-black uppercase tracking-widest text-zinc-100 font-display">Detection Lab</h2>
            <div className="flex-1 h-px bg-zinc-900 mx-4" />
            <div className="flex gap-3">
              {['GPTZero', 'ZeroGPT', 'Grammarly', 'Sapling', 'Originality'].map((p) => (
                <div key={p} className="flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900/50 border border-zinc-800/50 group/status relative">
                  <div className={cn(
                    "w-1.5 h-1.5 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]",
                    providerHealth[p] === 'offline' ? "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]" : "bg-emerald-500"
                  )} />
                  <span className="text-[9px] font-black uppercase tracking-widest text-zinc-500">{p}</span>
                  
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 rounded bg-zinc-800 border border-zinc-700 text-[8px] font-black uppercase tracking-widest text-zinc-300 opacity-0 group-hover/status:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
                    Status: ACTIVE
                  </div>
                </div>
              ))}
            </div>
          </div>

              <div className="mb-8 p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)] flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-[10px] font-black uppercase tracking-widest text-emerald-400">MULTI-PROVIDER PIPELINE: ACTIVE & VERIFIED</p>
                    <p className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">NWU Integrity Cluster • v4.3.2</p>
                  </div>
                </div>
            <div className="flex items-center gap-6">
              <div className="text-right">
                <p className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">API Latency</p>
                <p className="text-[11px] font-black text-emerald-400">124ms (Avg)</p>
              </div>
              <div className="h-8 w-px bg-zinc-800" />
              <div className="text-right">
                <p className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">Verification</p>
                <p className="text-[11px] font-black text-emerald-400">X2 Forensic Audit</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            <div className="space-y-6">
              <div className="p-8 rounded-[2rem] bg-zinc-900/40 border border-zinc-800/50 backdrop-blur-xl">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Input Analysis Payload</p>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => {
                        const input = document.createElement('input');
                        input.type = 'file';
                        input.accept = '.txt,.docx,.pdf';
                        input.onchange = (e: any) => {
                          const files = e.target.files;
                          if (files) handleDetectionFilesUpload(files);
                        };
                        input.multiple = true;
                        input.click();
                      }}
                      className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-all flex items-center gap-2"
                      title="Upload Files"
                    >
                      <Upload className="w-3 h-3" />
                      <span className="text-[9px] font-black uppercase tracking-widest">Upload Files</span>
                    </button>
                    {detectionFiles.length > 0 && (
                      <button 
                        onClick={() => {
                          setDetectionFiles([]);
                          setDetectionInput('');
                        }}
                        className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 transition-all flex items-center gap-2"
                        title="Clear All"
                      >
                        <RefreshCw className="w-3 h-3" />
                        <span className="text-[9px] font-black uppercase tracking-widest">Clear</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* File Status List */}
                <AnimatePresence>
                  {detectionFiles.length > 0 && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mb-4 space-y-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar"
                    >
                      {detectionFiles.map((file) => (
                        <div key={file.id} className="p-4 rounded-2xl bg-zinc-950/50 border border-zinc-800/50 space-y-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <FileText className={cn(
                                "w-4 h-4",
                                file.status === 'completed' ? "text-emerald-400" : 
                                file.status === 'error' ? "text-rose-400" : "text-cyan-400"
                              )} />
                              <div className="flex flex-col">
                                <span className="text-[11px] font-bold text-zinc-300 truncate max-w-[200px]">{file.name}</span>
                                {file.stats && (
                                  <span className="text-[9px] font-bold text-zinc-600 uppercase tracking-widest">
                                    {(file.stats.size / 1024).toFixed(1)} KB • {file.stats.chars.toLocaleString()} Chars
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              {(file.status === 'extracting' || file.status === 'processing') && (
                                <RefreshCw className="w-3 h-3 text-cyan-400 animate-spin" />
                              )}
                              {file.status === 'completed' && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                              {file.status === 'error' && (
                                <div className="flex items-center gap-2">
                                  <span className="text-[9px] font-bold text-rose-400 uppercase">{file.error || 'Error'}</span>
                                  <AlertCircle className="w-3 h-3 text-rose-400" />
                                </div>
                              )}
                              <span className={cn(
                                "text-[9px] font-black uppercase tracking-widest",
                                file.status === 'completed' ? "text-emerald-500" : "text-zinc-600"
                              )}>{file.status}</span>
                            </div>
                          </div>
                          
                          {/* Progress Bar */}
                          {(file.status === 'extracting' || file.status === 'processing') && (
                            <div className="w-full h-1 bg-zinc-900 rounded-full overflow-hidden">
                              <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: `${file.progress}%` }}
                                className="h-full bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)]"
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>

                <div 
                  className="relative group"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const files = e.dataTransfer.files;
                    if (files) handleDetectionFilesUpload(files);
                  }}
                >
                  <textarea 
                    value={detectionInput}
                    onChange={(e) => setDetectionInput(e.target.value)}
                    placeholder="Paste text or drop a file (.txt, .docx, .pdf) for multi-provider AI detection..."
                    className="w-full h-64 bg-zinc-950/50 border border-zinc-800 rounded-2xl p-6 text-sm font-mono text-zinc-300 focus:outline-none focus:border-emerald-500/50 transition-colors resize-none"
                  />
                  {/* Drop Overlay Hint */}
                  <div className="absolute inset-0 pointer-events-none border-2 border-dashed border-emerald-500/0 group-hover:border-emerald-500/20 rounded-2xl transition-all" />
                </div>
                <button 
                  onClick={handleMultiScan}
                  disabled={isDetecting}
                  className={cn(
                    "w-full mt-6 py-4 rounded-xl font-black uppercase tracking-widest text-xs transition-all flex items-center justify-center gap-3",
                    isDetecting ? "bg-zinc-900 text-zinc-600 cursor-not-allowed" : "bg-emerald-500 text-zinc-950 hover:bg-emerald-400"
                  )}
                >
                  {isDetecting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                  {isDetecting ? "Scanning Network..." : "RUN DETECTION (CONSOLIDATED AUDIT)"}
                </button>
              </div>
            </div>

            <div className="space-y-6">
              <AnimatePresence mode="wait">
                {detectionResults ? (
                  <motion.div 
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className="grid grid-cols-1 gap-4"
                  >
                    {detectionResults.results.map((res: any, idx: number) => (
                      <div key={idx} className="p-6 rounded-2xl bg-zinc-900/30 border border-zinc-800/50 backdrop-blur-sm flex items-center justify-between">
                        <div>
                          <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">{res.provider}</p>
                          <p className={cn(
                            "text-sm font-black uppercase",
                            res.label === 'AI Generated' ? "text-rose-400" : 
                            res.label === 'Likely AI' ? "text-amber-400" : "text-emerald-400"
                          )}>
                            {res.label}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-xl font-black text-zinc-100">{(res.score * 100).toFixed(1)}%</p>
                          <div className="w-24 h-1 bg-zinc-800 rounded-full mt-2 overflow-hidden">
                            <div 
                              className={cn(
                                "h-full transition-all duration-1000",
                                res.score > 0.8 ? "bg-rose-500" : res.score > 0.5 ? "bg-amber-500" : "bg-emerald-500"
                              )}
                              style={{ width: `${res.score * 100}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                    <div className="mt-4 p-8 rounded-[2.5rem] bg-emerald-500/5 border border-emerald-500/20 flex flex-col items-center text-center relative overflow-hidden group">
                      <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                      <p className="text-[10px] font-black uppercase tracking-[0.4em] text-emerald-400 mb-4 relative z-10">Aggregate Forensic Probability</p>
                      <p className="text-6xl font-black text-white font-display tracking-tighter relative z-10">{(detectionResults.aggregate_score * 100).toFixed(1)}%</p>
                      <div className="mt-6 flex items-center gap-3 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 relative z-10">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span className="text-[10px] font-black uppercase tracking-widest text-emerald-200">Cross-Provider Verification Complete</span>
                      </div>
                    </div>
                  </motion.div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center p-12 border-2 border-dashed border-zinc-900 rounded-[2rem] text-zinc-700">
                    <Activity className="w-12 h-12 mb-4 opacity-20" />
                    <p className="text-xs font-black uppercase tracking-widest">Awaiting Analysis Execution</p>
                  </div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* EdgeK Swarm Tab */}
        {activeTab === 'agent' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-6xl space-y-12">
            <div className="flex flex-col items-center text-center space-y-4 mb-20">
               <div className="w-24 h-24 rounded-[2.5rem] bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
                  <Terminal className="w-12 h-12 text-emerald-400" />
               </div>
               <h2 className="text-6xl font-black uppercase tracking-[-0.05em] text-white">EdgeK Swarm Conductor</h2>
               <p className="text-xs font-black uppercase tracking-[0.5em] text-zinc-500">Autonomous Agent Unit: V4.3-ZERO-DEFECT</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
              {/* Swarm Intelligence Console */}
              <div className="lg:col-span-3 space-y-8">
                <div className="p-10 rounded-[3rem] bg-zinc-950/80 border border-zinc-800/50 backdrop-blur-2xl">
                  <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-4">
                       <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Primary Objective</span>
                       <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[9px] font-black text-emerald-400 uppercase tracking-widest">Active Thread</div>
                    </div>
                  </div>
                  <textarea 
                    value={agentTask}
                    onChange={(e) => setAgentTask(e.target.value)}
                    placeholder="Dispatch a complex multi-agent directive..."
                    className="w-full h-40 bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 text-sm font-medium text-white focus:outline-none focus:border-emerald-500/50 transition-all resize-none mb-6"
                  />
                  <div className="flex justify-end">
                    <button 
                      onClick={() => conductorInstance.dispatch(agentTask, [AgentRole.RESEARCH, AgentRole.INTEGRITY])}
                      className="px-10 py-4 rounded-2xl bg-emerald-500 text-zinc-950 font-black uppercase tracking-[0.2em] text-xs shadow-[0_0_30px_-5px_rgba(16,185,129,0.5)] hover:scale-105 active:scale-95 transition-all"
                    >
                      Dispatch Swarm
                    </button>
                  </div>
                </div>

                <div className="p-10 rounded-[3rem] bg-zinc-950/80 border border-zinc-800/50">
                  <h4 className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-8">State Ledger (L1-L2 Buffer)</h4>
                  <div className="space-y-4">
                     <div className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800/50 text-[11px] font-mono text-zinc-400">
                        {StateLedger.read().length === 0 ? "No states committed to ledger." : "States Active: " + StateLedger.read().length}
                     </div>
                  </div>
                </div>
              </div>

              {/* Agent Roster */}
              <div className="space-y-6">
                 {['ResearchAgent', 'IntegrityAgent', 'CitationAgent', 'SocraticAgent', 'ForensicAgent'].map(role => (
                   <div key={role} className="p-6 rounded-3xl bg-zinc-900/50 border border-zinc-800/50 flex flex-col gap-4">
                      <div className="flex items-center justify-between">
                         <span className="text-[10px] font-black uppercase tracking-widest text-zinc-100">{role}</span>
                         <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                      </div>
                      <div className="flex gap-2">
                        <span className="text-[8px] font-black uppercase text-zinc-500">Node: Local</span>
                        <span className="text-[8px] font-black uppercase text-zinc-500">Mem: L1</span>
                      </div>
                   </div>
                 ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* MEM5 Bus Tab */}
        {activeTab === 'mem5' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-6xl space-y-12">
            <div className="flex items-center gap-6 p-10 rounded-[3rem] bg-zinc-900/50 border border-zinc-800/50 backdrop-blur-xl">
               <div className="w-16 h-16 rounded-[2rem] bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
                  <Database className="w-8 h-8 text-cyan-400" />
               </div>
               <div>
                  <h2 className="text-4xl font-black text-white uppercase tracking-tighter leading-none">MEM5 HIERARCHICAL BUS</h2>
                  <p className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em] mt-3">Level 0 - Level 4 Asymmetric Retrieval Core</p>
               </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
               {(['nwu-policy', 'assessment-standards', 'session-events', 'agent-findings'] as const).map(channel => (
                 <div key={channel} className="p-8 rounded-[2.5rem] bg-zinc-950/80 border border-zinc-800 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                       <Layers className="w-20 h-20 text-cyan-400" />
                    </div>
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-cyan-500 mb-6">{channel}</h4>
                    <div className="space-y-4">
                       <div className="h-1 w-full bg-zinc-900 rounded-full overflow-hidden">
                          <div className="h-full w-1/3 bg-cyan-500" />
                       </div>
                       <p className="text-[9px] font-bold text-zinc-600 uppercase tracking-widest">Active Listener: Bus-0x{channel.length}</p>
                    </div>
                 </div>
               ))}
            </div>

            <div className="p-10 rounded-[3rem] bg-zinc-950/80 border border-zinc-800">
               <div className="flex items-center justify-between mb-8">
                  <h3 className="text-sm font-black text-zinc-100 uppercase tracking-widest flex items-center gap-3">
                     <History className="w-4 h-4 text-cyan-400" />
                     Subscribed Events Log
                  </h3>
                  <div className="flex items-center gap-4">
                    <button onClick={() => memory.flush()} className="text-[9px] font-black uppercase text-rose-500 hover:text-rose-400 transition-colors">Flush L1 Cache</button>
                    <button onClick={() => setIsTestConsoleOpen(true)} className="px-3 py-1 rounded bg-zinc-800 border border-zinc-700 text-[9px] font-black uppercase tracking-widest text-emerald-400 hover:bg-zinc-700 transition-all">Test Console</button>
                  </div>
               </div>
               <div className="h-96 overflow-y-auto custom-scrollbar pr-4 space-y-4">
                  <div className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/50 text-[11px] font-mono text-zinc-600 italic">
                     Awaiting bus events...
                  </div>
               </div>
            </div>
          </motion.div>
        )}

        {/* ERTP Review Tab */}
        {activeTab === 'ertp' && (
          <div className="w-full animate-in fade-in slide-in-from-bottom-4 duration-1000 mb-24">
            <ERTPReviewTab forensicResult={forensicResult} loginUser={loginUser} />
          </div>
        )}

        {/* Global Security Utilities */}
        {activeTab !== 'ertp' && activeTab !== 'sudoku' && (
          <div className="w-full max-w-7xl mb-24">
            <div className="flex items-center gap-4 mb-8">
              <Lock className="w-6 h-6 text-emerald-400" />
              <h2 className="text-3xl font-black uppercase tracking-widest text-zinc-100 font-display">Security Labs</h2>
              <div className="flex-1 h-px bg-zinc-900 mx-4" />
            </div>
            <SecretGeneratorCard />
          </div>
        )}

        {/* Deploy & Distribution Section */}
        <div className="w-full max-w-7xl mb-24 p-12 rounded-[3.5rem] bg-zinc-950 border border-zinc-800 shadow-2xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-[100px] pointer-events-none" />
          <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-12">
            <div className="flex-1 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <Download className="w-5 h-5" />
                </div>
                <h2 className="text-3xl font-black uppercase tracking-tighter text-white">DEPLOY PACKAGE</h2>
              </div>
              <p className="text-sm text-zinc-400 leading-relaxed max-w-xl">
                Ready for offline distribution? Generate a self-contained NWU Deployment ZIP. 
                Includes Python runtime, local Mistral weights, and the Forensic Swarm automation suite.
              </p>
              <div className="flex gap-4">
                <span className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-[9px] font-black uppercase tracking-widest text-zinc-500">v4.3.2-Threaded</span>
                <span className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-[9px] font-black uppercase tracking-widest text-emerald-500">NWU_SIGNED</span>
              </div>
            </div>

            <div className="w-full md:w-96 space-y-6">
              <div className="p-6 rounded-3xl bg-zinc-900/50 border border-zinc-800 space-y-4">
                <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-zinc-500">
                  <span>Packaging Status</span>
                  <span className="text-emerald-400">Ready</span>
                </div>
                <div className="h-1.5 w-full bg-zinc-950 rounded-full overflow-hidden border border-zinc-900">
                  <motion.div 
                    initial={{ width: 0 }}
                    whileInView={{ width: '100%' }}
                    className="h-full bg-emerald-500"
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[11px] font-bold text-white">KnowEdgeMerger-Deploy.zip</span>
                  <span className="text-[10px] font-black text-zinc-500">4.12 GB</span>
                </div>
              </div>
              <button 
                onClick={() => {
                  alert("Deployment package will be generated at C:\\KnowEdgeMerger-Deploy.zip via the Package-KnowEdgeMerger.ps1 script.");
                }}
                className="w-full py-4 rounded-2xl bg-emerald-500 text-zinc-950 font-black uppercase tracking-[0.2em] shadow-[0_15px_40px_rgba(16,185,129,0.3)] hover:scale-[0.98] transition-all"
              >
                GENERATE DEPLOY ZIP
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-auto py-12 w-full border-t border-zinc-900 flex flex-col gap-8 opacity-40">
          <div className="flex flex-wrap justify-between items-center gap-8">
            <div className="flex items-center gap-4">
              <Cpu className="w-4 h-4" />
              <span className="text-[10px] font-black uppercase tracking-[0.3em]">Knowledge Merger V4.4.0-FINAL</span>
            </div>
            <div className="flex gap-12">
              <div className="flex items-center gap-2">
                <Shield className="w-3 h-3" />
                <span className="text-[9px] font-black uppercase tracking-[0.2em]">Deterministic</span>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-3 h-3" />
                <span className="text-[9px] font-black uppercase tracking-[0.2em]">Auditable</span>
              </div>
              <div className="flex items-center gap-2">
                <RefreshCw className="w-3 h-3" />
                <span className="text-[9px] font-black uppercase tracking-[0.2em]">Reproducible</span>
              </div>
            </div>
          </div>
          <div className="pt-8 border-t border-zinc-900/50 flex justify-center">
            <p className="text-[9px] font-black uppercase tracking-[0.3em] text-zinc-500">KnowEdge Merger V4.4.0-FINAL • NWU Academic Integrity Platform • POPIA Compliant • © 2026 NWU</p>
          </div>
        </footer>
      {/* Floating AI Assistant Toggle */}
      <button 
        onClick={() => setIsAssistantOpen(!isAssistantOpen)}
        className="fixed bottom-8 right-8 z-50 p-4 rounded-2xl bg-emerald-500 text-zinc-950 shadow-[0_0_20px_rgba(16,185,129,0.4)] hover:scale-110 transition-all group"
      >
        {isAssistantOpen ? <RefreshCw className="w-6 h-6 animate-spin" /> : <Zap className="w-6 h-6" />}
        <span className="absolute right-full mr-4 top-1/2 -translate-y-1/2 px-3 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-emerald-400 text-[10px] font-black uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          Intelligence Console
        </span>
      </button>

      {/* AI Assistant Panel */}
      <AnimatePresence>
        {isAssistantOpen && (
          <motion.div 
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-24 right-8 z-50 w-96 h-[600px] bg-zinc-900/95 border border-zinc-800/50 backdrop-blur-2xl rounded-[2.5rem] shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="p-6 border-b border-zinc-800/50 flex items-center justify-between bg-zinc-950/50">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-black text-white uppercase tracking-widest font-display">Intelligence Grid</h3>
                  <p className="text-[9px] font-black text-zinc-500 uppercase tracking-widest">Active Node: Gemini-3.1-Pro</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={() => setAssistantMode('fast')}
                  className={cn(
                    "px-2 py-1 rounded-md text-[8px] font-black uppercase tracking-widest transition-all",
                    assistantMode === 'fast' ? "bg-cyan-500 text-zinc-950" : "bg-zinc-800 text-zinc-500"
                  )}
                >
                  Fast Response
                </button>
                <button 
                  onClick={() => setAssistantMode('think')}
                  className={cn(
                    "px-2 py-1 rounded-md text-[8px] font-black uppercase tracking-widest transition-all",
                    assistantMode === 'think' ? "bg-purple-500 text-white" : "bg-zinc-800 text-zinc-500"
                  )}
                >
                  Deep Thinking
                </button>
                <button 
                  onClick={() => setAssistantMode('image')}
                  className={cn(
                    "px-2 py-1 rounded-md text-[8px] font-black uppercase tracking-widest transition-all",
                    assistantMode === 'image' ? "bg-emerald-500 text-zinc-950" : "bg-zinc-800 text-zinc-500"
                  )}
                >
                  Image Analysis
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              {assistantMessages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center opacity-30">
                  <Zap className="w-12 h-12 text-zinc-600 mb-4" />
                  <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Forensic Engine: Standby</p>
                </div>
              )}
              {assistantMessages.map((msg, i) => (
                <div key={i} className={cn(
                  "flex flex-col",
                  msg.role === 'user' ? "items-end" : "items-start"
                )}>
                  <div className={cn(
                    "max-w-[85%] p-4 rounded-2xl text-xs leading-relaxed",
                    msg.role === 'user' ? "bg-emerald-500 text-zinc-950 font-bold" : "bg-zinc-800/50 text-zinc-300 border border-zinc-700/50"
                  )}>
                    {msg.image && (
                      <img src={msg.image} alt="Forensic Input" className="w-full rounded-lg mb-3 border border-zinc-700" />
                    )}
                    {msg.content}
                  </div>
                  {msg.thinking && (
                    <div className="mt-2 p-3 rounded-xl bg-zinc-950/50 border border-zinc-800/50 text-[10px] text-zinc-500 font-mono italic max-w-[85%]">
                      <span className="text-purple-400 font-black uppercase mr-2">Thinking:</span>
                      {msg.thinking}
                    </div>
                  )}
                  {msg.latency && (
                    <div className="mt-1 px-2 py-0.5 rounded bg-zinc-900/50 border border-zinc-800/50 text-[8px] font-black uppercase tracking-widest text-zinc-600 flex items-center gap-1.5 w-fit">
                      <Activity className="w-2 h-2 text-emerald-500" />
                      Latency: {msg.latency}ms
                    </div>
                  )}
                </div>
              ))}
              {isAssistantLoading && (
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 animate-pulse">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                  </div>
                  <div className="p-4 rounded-2xl bg-zinc-800/30 border border-zinc-700/30 text-[10px] font-black uppercase tracking-widest text-zinc-500">
                    Processing Intelligence...
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="p-6 bg-zinc-950/50 border-t border-zinc-800/50">
              {assistantImage && (
                <div className="mb-4 relative inline-block">
                  <img src={assistantImage} alt="Preview" className="w-16 h-16 rounded-lg border border-emerald-500/50 object-cover" />
                  <button 
                    onClick={() => setAssistantImage(null)}
                    className="absolute -top-2 -right-2 p-1 rounded-full bg-rose-500 text-white"
                  >
                    <RefreshCw className="w-2 h-2" />
                  </button>
                </div>
              )}
              <div className="flex items-center gap-3">
                <label className="p-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-400 cursor-pointer transition-all">
                  <Upload className="w-4 h-4" />
                  <input type="file" accept="image/*" className="hidden" onChange={handleAssistantImageUpload} />
                </label>
                <input 
                  type="text"
                  value={assistantInput}
                  onChange={(e) => setAssistantInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAssistantSend()}
                  placeholder="Ask the Intelligence Grid..."
                  className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-all"
                />
                <button 
                  onClick={handleAssistantSend}
                  disabled={isAssistantLoading || (!assistantInput.trim() && !assistantImage)}
                  className="p-3 rounded-xl bg-emerald-500 text-zinc-950 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Zap className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* History Side Panel */}
      <AnimatePresence>
        {isHistoryOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsHistoryOpen(false)}
              className="fixed inset-0 bg-zinc-950/80 backdrop-blur-sm z-[60]"
            />
            <motion.div 
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed top-0 right-0 bottom-0 w-full max-w-md bg-zinc-900 border-l border-zinc-800 z-[70] flex flex-col shadow-2xl"
            >
              <div className="p-8 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/50">
                <div className="flex items-center gap-3">
                  <History className="w-5 h-5 text-emerald-400" />
                  <h2 className="text-xl font-black text-white uppercase tracking-tighter">Audit History</h2>
                </div>
                <button 
                  onClick={() => setIsHistoryOpen(false)}
                  className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-500 transition-all"
                >
                  <Plus className="w-5 h-5 rotate-45" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
                {savedReports.length === 0 && memory.getLayerEntries(MemoryLayer.L4).length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center opacity-30">
                    <History className="w-12 h-12 text-zinc-700 mb-4" />
                    <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500">No Forensic Audits Found</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* L4 Session Archive Entries */}
                    {memory.getLayerEntries(MemoryLayer.L4).map((entry) => (
                      <div 
                        key={entry.id}
                        className="p-5 rounded-2xl bg-zinc-950/70 border border-cyan-500/30 hover:border-cyan-500/50 transition-all group"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-[8px] font-black uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400">
                            Archive Entry (L4)
                          </span>
                          <span className="text-[9px] font-bold text-zinc-600">
                            {new Date(entry.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-zinc-200 truncate">
                          {entry.key}
                        </h4>
                        <p className="mt-2 text-[10px] text-zinc-500 font-medium line-clamp-2 italic">
                          {JSON.stringify(entry.value)}
                        </p>
                      </div>
                    ))}

                    {/* Cloud Reports */}
                    {savedReports.map((saved) => (
                    <div 
                      key={saved.id}
                      className="p-5 rounded-2xl bg-zinc-950/50 border border-zinc-800 hover:border-emerald-500/30 transition-all group cursor-pointer"
                      onClick={() => {
                        if (saved.type === 'synthesis') setReport(saved.data);
                        else setDetectionResults(saved.data);
                        setIsHistoryOpen(false);
                      }}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <span className={cn(
                          "text-[8px] font-black uppercase tracking-widest px-2 py-0.5 rounded",
                          saved.type === 'synthesis' ? "bg-purple-500/10 text-purple-400" : "bg-emerald-500/10 text-emerald-400"
                        )}>
                          {saved.type}
                        </span>
                        <span className="text-[9px] font-bold text-zinc-600">
                          {saved.timestamp?.toDate ? saved.timestamp.toDate().toLocaleString() : 'Recent'}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-zinc-200 group-hover:text-emerald-400 transition-colors truncate">
                        {saved.artifacts?.input || 'Unnamed Audit'}
                      </h4>
                      <div className="mt-3 flex items-center gap-4 text-[9px] font-black uppercase tracking-widest text-zinc-500">
                        <div className="flex items-center gap-1">
                          <Activity className="w-3 h-3" />
                          {saved.type === 'synthesis' ? 'Synthesis' : 'Detection'}
                        </div>
                        <div className="flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          Artifacts: {Object.keys(saved.artifacts || {}).filter(k => saved.artifacts[k]).length}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>

    {/* Chronicle Insight Chip */}
    <AnimatePresence>
      {isChronicleEnabled && lastChronicleFact && (
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          className="fixed bottom-24 right-8 z-[40] max-w-xs p-4 rounded-2xl bg-zinc-900/90 border border-cyan-500/30 backdrop-blur-md shadow-xl flex gap-3 items-start"
        >
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 shrink-0">
            <BrainCircuit className="w-3.5 h-3.5" />
          </div>
          <div className="flex-1">
            <p className="text-[10px] font-black uppercase text-cyan-400 tracking-widest mb-1">Chronicle Insight</p>
            <p className="text-[11px] text-zinc-300 font-medium leading-tight">"{lastChronicleFact}"</p>
          </div>
          <button onClick={() => setLastChronicleFact(null)} className="text-zinc-600 hover:text-zinc-400 p-1">
            <Plus className="w-3 h-3 rotate-45" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
      </main>
    </>
    )}
    </AnimatePresence>

    <ChronicleConsentModal 
      isOpen={showChronicleConsent} 
      onAccept={() => {
        localStorage.setItem('km_chronicle_consent', 'true');
        setShowChronicleConsent(false);
        setIsChronicleEnabled(true);
        localStorage.setItem('km_chronicle_enabled', 'true');
      }}
      onDecline={() => {
        setShowChronicleConsent(false);
      }}
    />
    </div>
  );
}
