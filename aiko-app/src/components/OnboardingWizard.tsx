import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNeuralStore } from '../store/useNeuralStore';
import { Play, Key, User, HardDrive, Cloud, AlertCircle } from 'lucide-react';

export function OnboardingWizard() {
  const [step, setStep] = useState(1);
  const [provider, setProvider] = useState<'Ollama' | 'OpenRouter' | 'DeepSeek' | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  
  const updateApiConfig = useNeuralStore((s) => s.updateApiConfig);
  // Assume hubUrl is known or we post to /api/settings if we can.
  // Actually, since this is a React component, we can use the backend proxy or rely on `updateApiConfig` 
  const hubUrl = (typeof window !== 'undefined' && !!(window as any).__TAURI__) 
      ? 'http://127.0.0.1:8080' 
      : (typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8080');

  const handleComplete = async () => {
    if (!username) { setError("I need to know what to call you!"); return; }
    if (provider !== 'Ollama' && !apiKey) { setError("I need an API key to think!"); return; }
    
    try {
      // 1. Tell backend to update config.json
      const configPatch: any = { username, PROVIDER: provider };
      if (provider === 'OpenRouter') configPatch.API_KEY = apiKey;
      if (provider === 'DeepSeek') configPatch.DEEPSEEK_API_KEY = apiKey;
      if (provider === 'Ollama') configPatch.PROVIDER = 'Ollama';
      
      try {
        await fetch(`${hubUrl}/api/settings`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(configPatch)
        });
      } catch (e) {
        console.warn("Backend not reachable for settings post, relying on UI store for now.");
      }

      // 2. Update local Zustand store
      // We set a dummy key for Ollama to bypass the missing-key block
      updateApiConfig({
        provider: provider || 'OpenRouter',
        apiKey: apiKey || 'local-ollama-bypass',
      });
      
    } catch (e) {
      setError("Failed to save settings. Is the Neural Hub running?");
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center bg-transparent backdrop-blur-md relative z-50 text-white/90">
      <div className="absolute inset-0 pointer-events-none bg-black/60" />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-[500px] max-w-[90vw] p-8 rounded-2xl border border-white/10 bg-black/80 shadow-[0_0_50px_rgba(0,0,0,0.5)] z-10 glass-panel"
      >
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-full bg-white/5 mx-auto flex items-center justify-center mb-4 neon-border glow-accent">
            <Play size={28} className="text-accent ml-1" />
          </div>
          <h2 className="text-3xl font-orbitron font-bold text-transparent bg-clip-text bg-gradient-to-r from-accent to-accent-glow">
            Awaken Aiko
          </h2>
          <p className="text-white/50 mt-2 font-light">System initialization required.</p>
        </div>

        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
              <div className="space-y-4">
                <p className="text-sm text-white/70">How should I generate my thoughts?</p>
                <div 
                  className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center gap-4 ${provider === 'Ollama' ? 'border-accent bg-accent/10 glow-accent' : 'border-white/10 hover:border-white/30 bg-white/5'}`}
                  onClick={() => setProvider('Ollama')}
                >
                  <HardDrive size={24} className={provider === 'Ollama' ? 'text-accent' : 'text-white/40'} />
                  <div>
                    <h3 className="font-semibold text-white/90">Local (Ollama)</h3>
                    <p className="text-xs text-white/50">Runs on your hardware. Private, requires strong GPU.</p>
                  </div>
                </div>
                
                <div 
                  className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center gap-4 ${provider === 'OpenRouter' ? 'border-accent bg-accent/10 glow-accent' : 'border-white/10 hover:border-white/30 bg-white/5'}`}
                  onClick={() => setProvider('OpenRouter')}
                >
                  <Cloud size={24} className={provider === 'OpenRouter' ? 'text-accent' : 'text-white/40'} />
                  <div>
                    <h3 className="font-semibold text-white/90">Cloud (OpenRouter)</h3>
                    <p className="text-xs text-white/50">API access to massive models (Claude, Qwen). Requires Key.</p>
                  </div>
                </div>

                <div 
                  className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center gap-4 ${provider === 'DeepSeek' ? 'border-accent bg-accent/10 glow-accent' : 'border-white/10 hover:border-white/30 bg-white/5'}`}
                  onClick={() => setProvider('DeepSeek')}
                >
                  <Cloud size={24} className={provider === 'DeepSeek' ? 'text-accent' : 'text-white/40'} />
                  <div>
                    <h3 className="font-semibold text-white/90">Cloud (DeepSeek)</h3>
                    <p className="text-xs text-white/50">Direct connection to DeepSeek API. Requires Key.</p>
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-4">
                <button 
                  onClick={() => setStep(2)} 
                  disabled={!provider}
                  className="px-6 py-2 rounded-lg bg-accent text-black font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-[0_0_15px_var(--acc)] transition-all"
                >
                  Next
                </button>
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-white/70 mb-2 font-medium flex items-center gap-2">
                    <User size={16} /> What should I call you?
                  </label>
                  <input 
                    type="text" 
                    value={username}
                    onChange={(e) => { setUsername(e.target.value); setError(''); }}
                    className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-accent transition-colors"
                    placeholder="Master, omax, etc."
                  />
                </div>

                {provider !== 'Ollama' && (
                  <div>
                    <label className="block text-sm text-white/70 mb-2 font-medium flex items-center gap-2">
                      <Key size={16} /> {provider} API Key
                    </label>
                    <input 
                      type="password" 
                      value={apiKey}
                      onChange={(e) => { setApiKey(e.target.value); setError(''); }}
                      className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-accent transition-colors font-mono"
                      placeholder="sk-..."
                    />
                    <p className="text-xs text-white/40 mt-2">Stored securely in your local config.json.</p>
                  </div>
                )}

                {error && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
                    <AlertCircle size={16} /> {error}
                  </div>
                )}
              </div>

              <div className="flex justify-between pt-4">
                <button 
                  onClick={() => setStep(1)} 
                  className="px-6 py-2 rounded-lg border border-white/10 text-white/70 hover:bg-white/5 transition-colors"
                >
                  Back
                </button>
                <button 
                  onClick={handleComplete}
                  className="px-6 py-2 rounded-lg bg-accent text-black font-semibold hover:shadow-[0_0_15px_var(--acc)] transition-all"
                >
                  Complete Setup
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
