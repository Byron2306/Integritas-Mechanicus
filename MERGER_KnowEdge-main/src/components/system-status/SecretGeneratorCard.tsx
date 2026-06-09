import { useMemo, useState } from 'react';

type SecretPreset = {
  label: string;
  length: number;
  alphabet: string;
  hint: string;
};

const PRESETS: SecretPreset[] = [
  {
    label: 'Password (Base64-ish safe)',
    length: 32,
    alphabet: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_',
    hint: 'Good default for DB, Redis, and app secrets.',
  },
  {
    label: 'Access key',
    length: 20,
    alphabet: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',
    hint: 'Good default for object-store access keys.',
  },
  {
    label: 'Secret key',
    length: 40,
    alphabet: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_',
    hint: 'Good default for object-store secret keys.',
  },
  {
    label: 'Hex token',
    length: 64,
    alphabet: '0123456789abcdef',
    hint: 'Good default for fixed-format tokens.',
  },
];

function secureRandomString(length: number, alphabet: string): string {
  const values = new Uint32Array(length);
  window.crypto.getRandomValues(values);

  const chars = [];
  for (let i = 0; i < length; i += 1) {
    chars.push(alphabet[values[i] % alphabet.length]);
  }

  return chars.join('');
}

export default function SecretGeneratorCard() {
  const [presetIndex, setPresetIndex] = useState(0);
  const [secret, setSecret] = useState('');
  const [copied, setCopied] = useState(false);

  const preset = useMemo(() => PRESETS[presetIndex], [presetIndex]);

  const generate = () => {
    const next = secureRandomString(preset.length, preset.alphabet);
    setSecret(next);
    setCopied(false);
  };

  const copySecret = async () => {
    if (!secret) return;
    await navigator.clipboard.writeText(secret);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const clearSecret = () => {
    setSecret('');
    setCopied(false);
  };

  return (
    <section className="rounded-2xl border border-slate-700/70 bg-slate-950/70 p-5 shadow-[0_0_0_1px_rgba(148,163,184,0.08)]">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-200">
            Secret Generator
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Generates secrets locally in the browser using Web Crypto. Nothing is persisted or sent to the server
            unless you choose to paste it elsewhere.
          </p>
        </div>
        <div className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-emerald-300">
          Local only
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[minmax(220px,280px)_1fr]">
        <div className="space-y-3">
          <label className="block text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
            Preset
          </label>
          <select
            value={presetIndex}
            onChange={(e) => setPresetIndex(Number(e.target.value))}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none ring-0"
          >
            {PRESETS.map((item, index) => (
              <option key={item.label} value={index}>
                {item.label}
              </option>
            ))}
          </select>

          <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3 text-xs leading-6 text-slate-400">
            <div><span className="text-slate-300">Length:</span> {preset.length}</div>
            <div className="mt-1"><span className="text-slate-300">Hint:</span> {preset.hint}</div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={generate}
              className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20"
            >
              Generate
            </button>
            <button
              type="button"
              onClick={copySecret}
              disabled={!secret}
              className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              type="button"
              onClick={clearSecret}
              disabled={!secret}
              className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm font-medium text-rose-200 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear
            </button>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
              Generated value
            </label>
          </div>
          <div className="relative group/secret">
            <textarea
              value={secret}
              readOnly
              rows={8}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 font-mono text-sm leading-6 text-emerald-200 outline-none"
              placeholder="Click Generate to create a local secret."
            />
            {secret && (
              <button
                onClick={copySecret}
                className="absolute top-3 right-3 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-black uppercase tracking-widest text-emerald-400 hover:bg-emerald-500/20 transition-all opacity-0 group-hover/secret:opacity-100"
              >
                {copied ? 'Copied' : 'Copy to Clipboard'}
              </button>
            )}
          </div>
          <p className="text-xs leading-6 text-slate-500">
            Safety notes: keep analytics, session replay, and auto-save disabled for this panel. Generate secrets on trusted devices only.
          </p>
        </div>
      </div>
    </section>
  );
}
