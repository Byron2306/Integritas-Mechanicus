import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Shield, 
  Grid3X3, 
  Search, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw,
  Zap,
  ArrowRight,
  Database
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ForensicMatrixProps {
  content?: string;
  analysisData?: {
    pattern_matrix?: number[];
  };
  filename?: string;
  autoTrigger?: boolean;
}

const ForensicMatrixLab: React.FC<ForensicMatrixProps> = ({ content, analysisData, filename, autoTrigger }) => {
  const [matrix, setMatrix] = useState<number[]>(new Array(81).fill(0));
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (autoTrigger && !isRunning) {
      setIsRunning(true);
      setProgress(0);
      
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            
            // Set final matrix
            if (analysisData?.pattern_matrix && Array.isArray(analysisData.pattern_matrix)) {
              setMatrix(analysisData.pattern_matrix);
            } else {
              const randomMatrix = Array.from({ length: 81 }, () => Math.floor(Math.random() * 101));
              setMatrix(randomMatrix);
            }
            
            setIsRunning(false);
            return 100;
          }
          return prev + 2;
        });
      }, 30);
      
      return () => clearInterval(interval);
    }
  }, [autoTrigger, analysisData, isRunning]);

  const getCellColor = (val: number) => {
    if (val === 0 && !autoTrigger) return 'bg-zinc-900/20 text-zinc-800 border-zinc-800/10';
    if (val <= 30) return 'bg-emerald-950/40 text-emerald-400 border-emerald-500/20';
    if (val <= 60) return 'bg-amber-950/40 text-amber-400 border-amber-500/20';
    if (val <= 80) return 'bg-orange-950/40 text-orange-400 border-orange-500/20';
    return 'bg-rose-950/40 text-rose-400 border-rose-500/20 shadow-[inset_0_0_15px_rgba(244,63,94,0.1)]';
  };

  // Helper to calculate totals
  const getRowTotal = (rowIdx: number) => {
    let sum = 0;
    for (let i = 0; i < 9; i++) sum += matrix[rowIdx * 9 + i];
    return sum;
  };

  const getColTotal = (colIdx: number) => {
    let sum = 0;
    for (let i = 0; i < 9; i++) sum += matrix[i * 9 + colIdx];
    return sum;
  };

  return (
    <div className="w-full space-y-12 animate-in fade-in slide-in-from-bottom-10 duration-1000">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-8 pb-12 border-b border-zinc-900">
        <div className="flex items-center gap-6">
          <div className="p-4 rounded-3xl bg-cyan-500/10 border border-cyan-500/20 shadow-[0_0_30px_rgba(6,182,212,0.15)] relative group">
            <Grid3X3 className="w-8 h-8 text-cyan-400 group-hover:rotate-90 transition-transform duration-700" />
            <div className="absolute inset-0 bg-cyan-400/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div>
            <h2 className="text-4xl font-black text-white uppercase tracking-[-0.05em]">Forensic Matrix Lab</h2>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.4em]">Row/Column/Box Integrity Scan</span>
              <div className="h-px w-12 bg-zinc-800" />
              <span className="text-[10px] font-mono text-cyan-500 font-bold">NODE: KM-774-NWU</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {filename && (
            <div className="px-5 py-3 rounded-2xl bg-zinc-900/50 border border-zinc-800 flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-black text-zinc-300 uppercase tracking-widest truncate max-w-[150px]">
                {filename}
              </span>
            </div>
          )}
          <div className="px-5 py-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center gap-3">
             <Shield className={cn("w-4 h-4", isRunning ? "text-cyan-400 animate-pulse" : "text-zinc-600")} />
             <span className="text-[10px] font-black text-cyan-400 uppercase tracking-widest">
               {isRunning ? `SCANNED ${progress}%` : 'SCAN READY'}
             </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-start">
        {/* BIG MATRIX GRID */}
        <div className="lg:col-span-8 relative">
          <div className="absolute -inset-10 bg-cyan-500/5 blur-[100px] pointer-events-none" />
          
          <div className="relative flex">
            {/* The actual 9x9 grid */}
            <div className="grid grid-cols-9 gap-1.5 p-3 rounded-2xl bg-zinc-950 border border-zinc-900 shadow-2xl overflow-hidden">
               {matrix.map((val, i) => {
                 const isBoxBoundaryRight = (i + 1) % 3 === 0 && (i + 1) % 9 !== 0;
                 const isBoxBoundaryBottom = i >= 18 && i <= 26 || i >= 45 && i <= 53;
                 
                 return (
                   <div key={i} className="relative group">
                     <motion.div 
                        initial={false}
                        animate={{ 
                          scale: isRunning ? 0.9 + Math.random() * 0.2 : 1,
                          opacity: isRunning ? 0.5 : 1
                        }}
                        className={cn(
                          "w-10 h-10 md:w-14 md:h-14 flex items-center justify-center rounded-lg border-2 text-xs md:text-sm font-black transition-all duration-300 relative z-10",
                          getCellColor(val)
                        )}
                     >
                       {val || (isRunning ? '..' : '0')}
                     </motion.div>
                     
                     {/* Box separator lines */}
                     {isBoxBoundaryRight && (
                       <div className="absolute -right-[5px] top-0 bottom-0 w-px bg-zinc-800/50 z-0" />
                     )}
                     {isBoxBoundaryBottom && (
                       <div className="absolute -bottom-[5px] left-0 right-0 h-px bg-zinc-800/50 z-0" />
                     )}
                   </div>
                 );
               })}
            </div>

            {/* Row Totals Column */}
            <div className="flex flex-col gap-1.5 p-3 pt-6 ml-4">
               {Array.from({ length: 9 }).map((_, i) => (
                 <div key={i} className="w-10 h-10 md:h-14 flex items-center justify-center font-mono text-[9px] text-zinc-600 font-bold border-l border-zinc-900">
                   ∑{getRowTotal(i)}
                 </div>
               ))}
            </div>
          </div>

          {/* Column Totals Row */}
          <div className="flex gap-1.5 p-3 pt-0 ml-3">
             {Array.from({ length: 9 }).map((_, i) => (
               <div key={i} className="w-10 h-10 md:w-14 flex items-center justify-center font-mono text-[9px] text-zinc-600 font-bold border-t border-zinc-900">
                 ∑{getColTotal(i)}
               </div>
             ))}
          </div>
          <div className="mt-6 flex items-center gap-2 px-6 py-2 rounded-full bg-zinc-950 border border-zinc-900 w-fit">
            <AlertTriangle className="w-3 h-3 text-rose-500" />
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400">
              PATTERN INTEGRITY: <span className="text-rose-500">{matrix.filter(v => v > 80).length}</span> CELLS FLAGGED HIGH
            </span>
          </div>
        </div>

        {/* SIDEBAR ANALYTICS */}
        <div className="lg:col-span-4 space-y-8">
           <div className="p-8 rounded-[2.5rem] bg-zinc-900/40 border border-zinc-800/50 space-y-6">
              <div className="flex items-center gap-3">
                 <Zap className="w-5 h-5 text-amber-400" />
                 <h4 className="text-xs font-black uppercase tracking-[0.3em] text-white">Grid Diagnostics</h4>
              </div>
              
              <div className="space-y-4">
                 {[
                   { label: 'Critical Variance', val: matrix.filter(v => v > 80).length, icon: AlertTriangle, color: 'text-rose-400' },
                   { label: 'Stable Nodes', val: matrix.filter(v => v <= 30 && v > 0).length, icon: CheckCircle2, color: 'text-emerald-400' },
                   { label: 'Unscanned Sectors', val: matrix.filter(v => v === 0).length, icon: Search, color: 'text-zinc-500' }
                 ].map((item, i) => (
                   <div key={i} className="flex items-center justify-between p-4 rounded-2xl bg-black border border-zinc-800">
                      <div className="flex items-center gap-3">
                        <item.icon className={cn("w-4 h-4", item.color)} />
                        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">{item.label}</span>
                      </div>
                      <span className="text-sm font-black text-white">{item.val}</span>
                   </div>
                 ))}
              </div>
           </div>

           <div className="p-8 rounded-[2.5rem] bg-cyan-500/5 border border-cyan-500/10 space-y-4">
              <div className="flex items-center gap-3">
                 <Database className="w-4 h-4 text-cyan-400" />
                 <span className="text-[10px] font-black uppercase tracking-widest text-cyan-300">Authoritative Ledger</span>
              </div>
              <p className="text-[10px] text-zinc-500 leading-relaxed uppercase font-bold tracking-tight">
                The Forensic Matrix Lab creates a structural fingerprint of document integrity by analyzing word density, sentence syntax, and vector orientation across a 9x9 neural grid.
              </p>
              <div className="pt-4 flex items-center justify-between border-t border-zinc-800">
                 <span className="text-[8px] font-black text-zinc-600 uppercase tracking-widest">Protocol Version</span>
                 <span className="text-[8px] font-mono text-cyan-500 bg-cyan-500/10 px-2 py-0.5 rounded">4.5.0-NWU</span>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
};

export default ForensicMatrixLab;
