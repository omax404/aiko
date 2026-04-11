import { motion, AnimatePresence } from 'framer-motion';
import { 
  Settings, 
  Key, 
  Cpu, 
  X,
  ShieldCheck,
  Zap,
  Globe,
  Palette,
  Wind,
  Image as ImageIcon
} from 'lucide-react';
import { clsx } from 'clsx';
import { useNeuralStore } from '../store/useNeuralStore';
import { useState } from 'react';

export function SettingsModal({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
  const { 
    apiConfig, updateApiConfig, 
    themeColor, setThemeColor,
    dynamicsIntensity, showAnimatedAssets, updateSettings
  } = useNeuralStore();
  const [localKey, setLocalKey] = useState(apiConfig.apiKey || "");
  const [localBaseUrl, setLocalBaseUrl] = useState(apiConfig.baseUrl || "");

  const handleSave = async () => {
    updateApiConfig({ apiKey: localKey, baseUrl: localBaseUrl });
    
    // Sync to backend config.json
    try {
      await fetch('http://localhost:8080/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          LLM_URL: apiConfig.provider === 'Ollama' ? 'http://127.0.0.1:11434/api/chat' : (localBaseUrl || apiConfig.baseUrl),
          LLM_BASE_URL: localBaseUrl || apiConfig.baseUrl,
          MODEL_NAME: apiConfig.model,
          DEEPSEEK_API_KEY: localKey || apiConfig.apiKey,
          PROVIDER: apiConfig.provider,
          TTS_PROVIDER: apiConfig.ttsProvider,
          TTS_ENABLED: apiConfig.ttsEnabled
        })
      });
    } catch (e) {
      console.error("Backend sync failed", e);
    }
    
    onClose();
  };

  const themes = [
    { name: 'Amber', color: '#d4956a' },
    { name: 'Emerald', color: '#10b981' },
    { name: 'Azure', color: '#3b82f6' },
    { name: 'Rose', color: '#f43f5e' },
    { name: 'Violet', color: '#8b5cf6' },
    { name: 'Gold', color: '#fbbf24' },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/80 backdrop-blur-md">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="w-full max-w-xl bg-[var(--bg-elevated)] border border-[var(--b2)] rounded-[32px] overflow-hidden shadow-2xl relative"
          >
            {/* Header Area */}
            <div className="p-8 border-b border-[var(--b1)] bg-gradient-to-br from-[var(--acc)]/5 to-transparent">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                   <div className="w-11 h-11 rounded-2xl bg-[var(--acc)]/10 flex items-center justify-center border border-[var(--acc)]/20 shadow-lg shadow-[var(--acc)]/10">
                     <Settings size={20} className="text-[var(--acc)]" />
                   </div>
                   <div>
                     <h2 className="text-xl font-bold tracking-tight text-[var(--t1)] brand-text uppercase">System Configuration</h2>
                     <p className="text-[10px] text-[var(--t3)] uppercase tracking-widest font-bold mt-1">Refining Identity // Node_Sync_Active</p>
                   </div>
                </div>
                <button 
                  title="Close Configuration"
                  onClick={onClose} 
                  className="p-2.5 rounded-xl hover:bg-white/5 text-[var(--t3)] hover:text-white transition-all"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Scrollable Form Content */}
            <div className="p-8 flex flex-col gap-8 max-h-[60vh] overflow-y-auto custom-scrollbar">
              
              {/* Visual Identity / Theme */}
              <div className="flex flex-col gap-3">
                 <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--acc)]/70 ml-1">Visual Identity (Accent Palette)</label>
                 <div className="flex flex-wrap gap-3 p-4 rounded-2xl bg-[var(--bg-input)] border border-[var(--b1)]">
                    {themes.map((t) => (
                      <button
                        key={t.name}
                        onClick={() => setThemeColor(t.color)}
                        className={clsx(
                          "group relative w-12 h-12 rounded-xl transition-all flex items-center justify-center",
                          themeColor === t.color ? "ring-2 ring-white/20 scale-110" : "hover:scale-105"
                        )}
                        style={{ background: t.color }}
                        title={t.name}
                      >
                        {themeColor === t.color && (
                          <div className="w-2 h-2 bg-white rounded-full shadow-lg" />
                        )}
                        <div className="absolute -bottom-6 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap text-[8px] font-bold uppercase tracking-widest text-[var(--t3)]">
                          {t.name}
                        </div>
                      </button>
                    ))}
                    <div className="ml-auto flex items-center gap-3 pr-2">
                       <Palette size={16} className="text-[var(--t4)]" />
                       <span className="text-[9px] font-bold text-[var(--t4)] uppercase tracking-widest">Global Sync</span>
                    </div>
                 </div>
              </div>

              {/* UI Dynamics */}
              <div className="flex flex-col gap-6 p-6 rounded-2xl bg-[var(--bg-input)] border border-[var(--b1)]">
                 <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                       <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--acc)]/70 flex items-center gap-2">
                          <Wind size={12} /> Dynamics Intensity
                       </label>
                       <span className="text-[10px] font-mono text-[var(--t3)] font-bold">{dynamicsIntensity}%</span>
                    </div>
                    <input 
                       title="Dynamics Intensity"
                       type="range" 
                       min="0" max="100" 
                       value={dynamicsIntensity}
                       onChange={(e) => updateSettings({ dynamicsIntensity: parseInt(e.target.value) })}
                       className="w-full accent-[var(--acc)] h-1.5 bg-white/5 rounded-full appearance-none cursor-pointer"
                       placeholder="Slide to adjust intensity"
                    />
                    <p className="text-[9px] text-[var(--t4)] font-bold uppercase tracking-tight">Controls motion speed, blur intensity, and transition fluidity.</p>
                 </div>

                 <div className="h-px bg-white/5 w-full" />

                 <div className="flex items-center justify-between">
                    <div className="flex flex-col gap-1">
                       <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--t2)] flex items-center gap-2">
                          <ImageIcon size={12} className="text-[var(--acc)]" /> Animated Assets
                       </label>
                       <p className="text-[9px] text-[var(--t4)] font-bold uppercase">Enable animated icons and GIF support.</p>
                    </div>
                    <button 
                       title="Toggle Animated Assets"
                       onClick={() => updateSettings({ showAnimatedAssets: !showAnimatedAssets })}
                       className={clsx(
                         "w-12 h-6 rounded-full transition-all relative border",
                         showAnimatedAssets ? "bg-[var(--acc)] border-[var(--acc)]/40" : "bg-white/5 border-white/10"
                       )}
                    >
                       <motion.div 
                         animate={{ x: showAnimatedAssets ? 26 : 4 }}
                         className="absolute top-1 w-4 h-4 rounded-full bg-white shadow-lg"
                       />
                    </button>
                 </div>
              </div>

              {/* Provider Selection (Strictly Ollama) */}
              <div className="flex flex-col gap-3">
                 <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--acc)]/70 ml-1">Core Brain Provider</label>
                  <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
                    {['Ollama'].map((p) => (
                      <button
                        key={p}
                        onClick={() => {
                          updateApiConfig({ provider: p });
                          setLocalBaseUrl('http://localhost:11434/v1');
                        }}
                        className={clsx(
                          "px-4 py-3.5 rounded-2xl border text-[11px] font-bold uppercase tracking-widest flex items-center gap-3 transition-all",
                          apiConfig.provider === p 
                            ? "bg-[var(--acc)]/10 border-[var(--acc)]/50 text-white shadow-lg shadow-[var(--acc)]/10" 
                            : "bg-[var(--bg-input)] border-[var(--b1)] text-[var(--t3)] hover:bg-[var(--bg-hover)]"
                        )}
                      >
                         <Globe size={14} className={apiConfig.provider === p ? "text-[var(--acc)]" : "text-[var(--t4)]"} />
                         <span className="truncate">{p}</span>
                         {apiConfig.provider === p && <ShieldCheck size={12} className="ml-auto text-[var(--acc)] shrink-0" />}
                      </button>
                    ))}
                  </div>
              </div>
              {apiConfig.provider === 'Custom' && (
                <div className="flex flex-col gap-3">
                    <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--acc)]/70 ml-1">API Engine Interface (Base URL)</label>
                    <div className="relative group">
                       <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                          <Globe size={16} className="text-[var(--t4)] group-focus-within:text-[var(--acc)] transition-colors" />
                       </div>
                       <input 
                          type="text"
                          value={localBaseUrl}
                          onChange={(e) => setLocalBaseUrl(e.target.value)}
                          className="w-full pl-12 pr-4 py-3.5 bg-[var(--bg-input)] border border-[var(--b1)] rounded-2xl text-[13px] text-[var(--t1)] placeholder-[var(--t4)] focus:border-[var(--acc)]/30 transition-all outline-none"
                          placeholder="http://localhost:11434/v1"
                       />
                    </div>
                    <p className="text-[9px] text-[var(--t4)] font-bold uppercase tracking-tight ml-2">Override the default endpoint for specialized local/cloud nodes.</p>
                </div>
              )}

              {/* Voice Engine Selection */}
              <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between px-1">
                    <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--acc)]/70">Voice Synthesis Engine</label>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] text-[var(--t4)] font-bold uppercase tracking-widest">Active</span>
                      <button 
                        title="Toggle Neural Voice"
                        onClick={() => updateApiConfig({ ttsEnabled: !apiConfig.ttsEnabled })}
                        className={clsx(
                          "w-8 h-4 rounded-full transition-all relative border",
                          apiConfig.ttsEnabled ? "bg-[var(--acc)] border-[var(--acc)]/40" : "bg-white/5 border-white/10"
                        )}
                      >
                         <motion.div 
                           animate={{ x: apiConfig.ttsEnabled ? 16 : 4 }}
                           className="absolute top-0.5 w-2.5 h-2.5 rounded-full bg-white shadow-lg"
                         />
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {['Pocket', 'Gemini'].map((v) => (
                      <button
                        key={v}
                        onClick={() => updateApiConfig({ ttsProvider: v as any })}
                        className={clsx(
                          "px-4 py-3.5 rounded-2xl border text-[11px] font-bold uppercase tracking-widest flex items-center gap-3 transition-all",
                          apiConfig.ttsProvider === v 
                            ? "bg-[var(--acc)]/10 border-[var(--acc)]/50 text-white shadow-lg shadow-[var(--acc)]/10" 
                            : "bg-[var(--bg-input)] border-[var(--b1)] text-[var(--t3)] hover:bg-[var(--bg-hover)]"
                        )}
                      >
                         <Wind size={14} className={apiConfig.ttsProvider === v ? "text-[var(--acc)]" : "text-[var(--t4)]"} />
                         <span className="truncate">{v === 'Pocket' ? 'Pocket TTS (Local)' : 'Gemini Live (Cloud)'}</span>
                         {apiConfig.ttsProvider === v && <ShieldCheck size={12} className="ml-auto text-[var(--acc)] shrink-0" />}
                      </button>
                    ))}
                  </div>
                  <p className="text-[9px] text-[var(--t4)] font-bold uppercase tracking-tight ml-2">
                    {apiConfig.ttsProvider === 'Pocket' 
                      ? 'Uses high-speed local inference with Kokoro/StyleTTS2.' 
                      : 'Uses Google Cloud for premium high-fidelity voice.'}
                  </p>
              </div>

              {/* Model Select */}
              <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between px-1">
                    <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--acc)]/70">Neural Model</label>
                    <span className="text-[9px] text-[var(--t4)] font-mono font-bold">ID: {apiConfig.model}</span>
                  </div>
                  <div className="relative group">
                     <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                        <Cpu size={16} className="text-[var(--t4)] group-focus-within:text-[var(--acc)] transition-colors" />
                     </div>
                     <input 
                        type="text"
                        value={apiConfig.model}
                        onChange={(e) => updateApiConfig({ model: e.target.value })}
                        className="w-full pl-12 pr-4 py-3.5 bg-[var(--bg-input)] border border-[var(--b1)] rounded-2xl text-[13px] text-[var(--t1)] placeholder-[var(--t4)] focus:border-[var(--acc)]/30 transition-all outline-none font-medium"
                        placeholder="gpt-4o, gemini-pro, etc..."
                     />
                  </div>
              </div>

              {/* API Key Input */}
              <div className="flex flex-col gap-3">
                  <label className="text-[10px] uppercase tracking-[0.2em] font-bold text-[var(--acc)]/70 ml-1">Access Token (Encrypted)</label>
                  <div className="relative group">
                     <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                        <Key size={16} className="text-[var(--t4)] group-focus-within:text-[var(--acc)] transition-colors" />
                     </div>
                     <input 
                        type="password"
                        value={localKey}
                        onChange={(e) => setLocalKey(e.target.value)}
                        className="w-full pl-12 pr-4 py-3.5 bg-[var(--bg-input)] border border-[var(--b1)] rounded-2xl text-[13px] text-[var(--t1)] placeholder-[var(--t4)] focus:border-[var(--acc)]/30 transition-all outline-none"
                        placeholder="sk-neural-..."
                     />
                  </div>
                  <p className="text-[10px] text-[var(--t4)] font-bold italic px-2 uppercase tracking-tight">Keys are stored locally only. Secure transmission to Neural Hub.</p>
              </div>

            </div>

            {/* Footer Area */}
            <div className="p-8 border-t border-[var(--b1)] flex gap-4 bg-black/20">
              <button 
                onClick={onClose}
                className="flex-1 py-4 rounded-2xl bg-white/[0.03] border border-white/5 text-[10px] font-bold text-[var(--t3)] tracking-[0.2em] hover:bg-white/5 hover:text-white transition-all uppercase"
              >
                Discard
              </button>
              <button 
                onClick={handleSave}
                className="flex-[2] py-4 rounded-2xl bg-gradient-to-br from-[var(--acc)] to-[var(--acc)]/80 text-white text-[10px] font-bold tracking-[0.2em] shadow-xl shadow-[var(--acc)]/20 hover:scale-[1.01] active:scale-[0.98] transition-all uppercase flex items-center justify-center gap-3 border border-white/10"
              >
                <Zap size={14} className="animate-pulse" />
                Apply Changes
              </button>
            </div>

          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
