import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Shield, BrainCircuit, EyeOff, Lock, Check, X } from 'lucide-react';
import { KM_CHRONICLE_RULES } from '../lib/kmChronicle';

interface ChronicleConsentModalProps {
  isOpen: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

export const ChronicleConsentModal: React.FC<ChronicleConsentModalProps> = ({ 
  isOpen, 
  onAccept, 
  onDecline 
}) => {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="bg-white dark:bg-slate-900 w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800"
        >
          {/* Header */}
          <div className="p-6 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 flex items-center gap-4">
            <div className="p-3 bg-indigo-100 dark:bg-indigo-900/30 rounded-xl">
              <BrainCircuit className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">KM-Chronicle Integration</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">V4.3.1 Private Context Engine</p>
            </div>
          </div>

          {/* Body */}
          <div className="p-6 space-y-6">
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              KM-Chronicle is a background context engine that learns from your workflow to provide smarter, more personalized AI support without you having to restate your context every time.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex gap-3 items-start">
                <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg shrink-0">
                  <EyeOff className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-slate-900 dark:text-white">Private Capture</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Only observes app DOM elements. No screen recording, no mic, no camera.</p>
                </div>
              </div>

              <div className="flex gap-3 items-start">
                <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg shrink-0">
                  <Lock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-slate-900 dark:text-white">Local Consolidation</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Uses local Mistral via Ollama. Your data never leaves the NWU network.</p>
                </div>
              </div>

              <div className="flex gap-3 items-start">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg shrink-0">
                  <Shield className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-slate-900 dark:text-white">NWU Compliant</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Zero PII storage. All metadata is obfuscated and expires after 6 hours.</p>
                </div>
              </div>

              <div className="flex gap-3 items-start">
                <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg shrink-0">
                  <Check className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-slate-900 dark:text-white">Full Control</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Toggle on/off from the system bar at any time. Data is cleared on exit.</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">Compliance Guard</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 italic">
                "{KM_CHRONICLE_RULES.NWU_COMPLIANCE}"
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="p-6 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row gap-3">
            <button 
              onClick={onAccept}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-semibold transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2"
            >
              <Check className="w-5 h-5" />
              Enable KM-Chronicle
            </button>
            <button 
              onClick={onDecline}
              className="flex-1 bg-white hover:bg-slate-50 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 px-6 py-3 rounded-xl font-semibold border border-slate-200 dark:border-slate-700 transition-all flex items-center justify-center gap-2"
            >
              <X className="w-5 h-5" />
              Keep Disabled
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
