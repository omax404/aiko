import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { emit } from '@tauri-apps/api/event';
import { Sidebar } from './components/Sidebar';
import { ChatBubble } from './components/ChatBubble';
import { InputDock } from './components/InputDock';
import { SettingsModal } from './components/SettingsModal';
import { SkeletonLoader } from './components/SkeletonLoader';
import { RotatingOrbital } from './components/AnimatedIcons';
import { ProjectIntelligence } from './components/ProjectIntelligence';
import { Live2DAvatar } from './components/Live2DAvatar';
import { OnboardingWizard } from './components/OnboardingWizard';
import { useNeuralStore } from './store/useNeuralStore';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import {
  PanelLeft,
  ChevronLeft,
  ChevronRight,
  Activity,
  Settings,
  Zap,
  ExternalLink
} from 'lucide-react';
import { Window, getCurrentWindow } from '@tauri-apps/api/window';

/* ── Custom Titlebar ─────────────────────────────────────── */
function TitleBar({ sessionLabel, showAnimatedAssets, onSettings, onProject, onToggleSidebar }: {
  sessionLabel: string;
  showAnimatedAssets: boolean;
  onSettings: () => void;
  onProject: () => void;
  onToggleSidebar: () => void;
}) {
  // Use Tauri API — native, 100% reliable
  const isTauri = !!(window as any).__TAURI__;
  const minimize = () => isTauri ? getCurrentWindow().minimize().catch(console.error) : console.log("Minimize");
  const maximize = () => isTauri ? getCurrentWindow().toggleMaximize().catch(console.error) : console.log("Maximize");
  const close = () => isTauri ? getCurrentWindow().close().catch(console.error) : window.close();

  // Every interactive element MUST have WebkitAppRegion: 'no-drag' directly on it
  const noDrag: React.CSSProperties = { WebkitAppRegion: 'no-drag' } as React.CSSProperties;

  const iconBtn = (onClick: () => void, title: string, children: React.ReactNode): React.ReactNode => (
    <button onClick={onClick} title={title} style={{
      ...noDrag,
      width: 38, height: 48, background: 'transparent', border: 'none',
      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: 'rgba(255,255,255,0.35)', transition: 'background 100ms, color 100ms', flexShrink: 0,
    }}
      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; e.currentTarget.style.color = 'rgba(255,255,255,0.8)'; }}
      onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'rgba(255,255,255,0.35)'; }}>
      {children}
    </button>
  );

  const winBtn = (onClick: () => void, title: string, children: React.ReactNode, isClose = false): React.ReactNode => (
    <button onClick={onClick} title={title} style={{
      ...noDrag,
      width: 46, height: 48, background: 'transparent', border: 'none',
      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: 'rgba(255,255,255,0.35)', transition: 'background 100ms, color 100ms', flexShrink: 0,
    }}
      onMouseEnter={e => {
        e.currentTarget.style.background = isClose ? '#c42b1c' : 'rgba(255,255,255,0.08)';
        e.currentTarget.style.color = isClose ? '#fff' : 'rgba(255,255,255,0.9)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'transparent';
        e.currentTarget.style.color = 'rgba(255,255,255,0.35)';
      }}>
      {children}
    </button>
  );

  return (
    <div
      data-tauri-drag-region
      style={{
        height: 48, background: '#0e0d0c', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        flexShrink: 0, borderBottom: '1px solid rgba(255,255,255,0.04)',
        userSelect: 'none', WebkitAppRegion: 'drag',
      } as React.CSSProperties}
    >
      {/* Left: App icon buttons — all explicitly no-drag */}
      <div style={{ display: 'flex', alignItems: 'center', ...noDrag }}>
        {iconBtn(onToggleSidebar, 'Toggle Sidebar', <PanelLeft size={16} />)}
        <div style={{ display: 'flex', gap: 0 }}>
          {iconBtn(() => { }, 'Back', <ChevronLeft size={18} style={{ opacity: 0.3 }} />)}
          {iconBtn(() => { }, 'Forward', <ChevronRight size={18} style={{ opacity: 0.3 }} />)}
        </div>
      </div>

      {/* Center: drag region only — no buttons */}
      <div data-tauri-drag-region style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 10, pointerEvents: 'none',
      }}>
        {showAnimatedAssets ? <RotatingOrbital /> : <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'rgba(255,255,255,0.08)' }} />}
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.15)', fontWeight: 500, letterSpacing: 1.5 }}>
          AIKO — {sessionLabel}
        </span>
      </div>

      {/* Right: action icons + window controls — all explicitly no-drag */}
      <div style={{ display: 'flex', alignItems: 'center', ...noDrag }}>
        {iconBtn(onProject, 'Project', <Activity size={14} />)}
        {iconBtn(onSettings, 'Settings', <Settings size={14} />)}
        <span style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.06)', margin: '0 6px', flexShrink: 0 }} />
        {winBtn(minimize, 'Minimize',
          <svg width="11" height="1.5" viewBox="0 0 11 1.5"><rect width="11" height="1.5" rx="0.75" fill="currentColor" /></svg>
        )}
        {winBtn(maximize, 'Maximize',
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><rect x=".75" y=".75" width="8.5" height="8.5" rx="1.5" stroke="currentColor" strokeWidth="1.2" /></svg>
        )}
        {winBtn(close, 'Close',
          <svg width="10" height="10" viewBox="0 0 10 10"><line x1="1.5" y1="1.5" x2="8.5" y2="8.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /><line x1="8.5" y1="1.5" x2="1.5" y2="8.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>,
          true
        )}
      </div>
    </div>
  );
}

/* ── Right Dashboard (with Live2D inside) ────────────────── */
function DashboardStats({ 
  bridgeStatus, isThinking, isTalking, currentEmotion,
  avatarScale, setAvatarScale, amplitude
}: {
  bridgeStatus: any; isThinking: boolean; isTalking: boolean; currentEmotion: string;
  avatarScale: number; setAvatarScale: (s: number) => void; amplitude: number;
}) {
  const { apiConfig } = useNeuralStore();
  return (
    <div className="w-[320px] min-w-[320px] h-full flex flex-col bg-[var(--bg-sidebar)] border-l border-[var(--b1)] overflow-hidden">
      {/* Live2D Avatar — scaled up */}
      <div className="flex-1 flex items-center justify-center bg-black/30 relative overflow-hidden min-h-0">
        <Live2DAvatar
          modelUrl="/live2d/vivian/vivian.model3.json"
          isThinking={isThinking}
          isTalking={isTalking}
          emotion={currentEmotion}
          width={320}
          height={600}
          scale={avatarScale}
          amplitude={amplitude}
        />
        {/* Online dot */}
        <div className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,1)]" />
      </div>

      {/* Stats — bottom section */}
      <div className="px-3.5 pb-4 pt-3.5 flex flex-col gap-2.5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="text-[9px] font-bold text-[rgba(212,149,106,0.4)] tracking-[2px] uppercase">
            System Core
          </div>
          <div className="flex gap-0.5 items-center">
            {[0.4, 0.7, 1.0, 0.6].map((h, i) => (
              <div key={i} className="w-0.5 bg-[var(--acc)]" style={{ height: 10 * h, opacity: 0.5 + h * 0.5 }} />
            ))}
          </div>
        </div>

        {/* Mascot Mode Toggle */}
        <button
          onClick={async () => {
             try {
               const mascot = new Window('mascot');
               await mascot.show();
               await getCurrentWindow().hide();
             } catch (e) { console.error("Could not switch to mascot", e); }
          }}
          className="bg-[rgba(212,149,106,0.03)] border border-[var(--acc)] rounded-lg p-2.5 px-3 flex items-center justify-between hover:bg-[var(--acc)] hover:text-black transition-all group w-full text-left cursor-pointer"
        >
          <span className="text-[10px] uppercase font-bold tracking-widest text-[var(--acc)] group-hover:text-black">Mascot Mode</span>
          <ExternalLink size={14} className="text-[var(--acc)] group-hover:text-black" />
        </button>

        {/* Avatar Scale Slider */}
        <div className="bg-[rgba(212,149,106,0.03)] border border-[rgba(212,149,106,0.1)] rounded-lg p-2.5 px-3 flex flex-col gap-1.5">
          <div className="flex justify-between items-center">
            <span className="text-[8px] text-[rgba(212,149,106,0.6)] font-semibold uppercase">Avatar Scale</span>
            <span className="text-[9px] text-[var(--acc)] font-bold font-mono">{(avatarScale * 100).toFixed(0)}%</span>
          </div>
          <input 
            type="range"
            min="0.5"
            max="2.0"
            step="0.05"
            value={avatarScale}
            onChange={(e) => setAvatarScale(parseFloat(e.target.value))}
            className="w-full h-1 bg-[rgba(212,149,106,0.1)] rounded-lg appearance-none cursor-pointer accent-green-500"
            title="Adjust Avatar Scale"
          />
        </div>

        {/* Active Model */}
        <div className="bg-[rgba(212,149,106,0.03)] border border-[rgba(212,149,106,0.1)] rounded-lg p-2.5 px-3 flex flex-col gap-1.5">
          <div className="text-[8px] text-[rgba(212,149,106,0.6)] font-semibold uppercase">Active Model</div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            <span className="text-[9px] text-white font-bold font-mono uppercase truncate">{apiConfig.model}</span>
          </div>
          <div className="text-[7px] text-slate-500 font-bold tracking-widest uppercase">
            {apiConfig.provider} // Active
          </div>
        </div>

        {/* Sync Bridge */}
        <div className="bg-[rgba(212,149,106,0.03)] border border-[rgba(212,149,106,0.1)] rounded-lg p-2.5 px-3 flex flex-col gap-1.5">
          <div className="text-[8px] text-[rgba(212,149,106,0.6)] font-semibold uppercase">Sync Bridge</div>
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${bridgeStatus.status === 'connected' ? 'bg-green-500 shadow-[0_0_6px_#22c55e]' : 'bg-red-500'}`} />
            <span className="text-[9px] text-white font-bold font-mono uppercase">{bridgeStatus.status}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Welcome Screen ──────────────────────────────────────── */
export function WelcomeScreen({ onRecall }: { onRecall: () => void }) {
  const { dynamicsIntensity } = useNeuralStore();
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: (100 - dynamicsIntensity) / 100 + 0.2 }}
      className="flex-1 flex flex-col items-center justify-center text-center p-12 gap-8"
    >
      <div className="max-w-md">
        <div className="w-16 h-16 rounded-2xl bg-amber-600/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-8">
          <Zap size={32} className="text-amber-400" />
        </div>
        <h1 className="text-2xl font-bold text-white uppercase brand-text tracking-widest">Aiko</h1>
        <p className="text-[13px] text-slate-500 mt-3 leading-relaxed font-light px-4">
          Your neural companion is ready.
        </p>
      </div>
      <button onClick={onRecall}
        className="px-8 py-3 rounded-xl bg-white/[0.03] border border-white/10 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:bg-white/5 hover:text-white transition-all">
        View History
      </button>
    </motion.div>
  );
}

/* ── Main App ────────────────────────────────────────────── */
function App() {
  const {
    messages, streamingContent, connect, activeSessionId, sessions,
    isThinking, triggerPurge, loadSessions, fetchBridgeStatus,
    bridgeStatus, currentEmotion, isSidebarOpen, toggleSidebar, themeColor,
    dynamicsIntensity, showAnimatedAssets, isTalking, avatarScale, setAvatarScale,
    amplitude, apiConfig
  } = useNeuralStore();

  const maskUnclosedLatex = (text: string) => {
    // Count occurrences of $$
    const blockMathParts = text.split('$$');
    if (blockMathParts.length % 2 === 0) {
      // Unclosed block math
      blockMathParts[blockMathParts.length - 1] = ' \\dots $$';
      return blockMathParts.join('$$');
    }
    
    // Count occurrences of $
    // Slightly naive, but works for masking
    const inlineMathParts = text.split(/(?<!\\)\$/);
    if (inlineMathParts.length % 2 === 0) {
      inlineMathParts[inlineMathParts.length - 1] = ' \\dots $';
      return inlineMathParts.join('$');
    }
    return text;
  };

  const activeSession = sessions.find(s => s.id === activeSessionId);
  const sessionLabel = activeSession?.title || 'New Session';
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isProjectOpen, setIsProjectOpen] = useState(false);
  const [isPurgeConfirmOpen, setIsPurgeConfirmOpen] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    emit('app-ready').catch(() => { });
    // Inject accent color on mount
    document.documentElement.style.setProperty('--acc', themeColor);
    document.documentElement.style.setProperty('--acc-soft', `${themeColor}1f`);
    document.documentElement.style.setProperty('--acc-glow', `${themeColor}40`);

    try { connect('http://127.0.0.1:8080'); } catch (e) { }
    fetchBridgeStatus();
    loadSessions();
    const t = setInterval(() => fetchBridgeStatus(), 30000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <div style={{
      width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column',
      overflow: 'hidden', background: 'var(--bg-base)', color: 'var(--t1)'
    }}>

      {/* ONE titlebar — session name + action icons + window controls */}
      <TitleBar
        sessionLabel={sessionLabel}
        showAnimatedAssets={showAnimatedAssets}
        onSettings={() => setIsSettingsOpen(true)}
        onProject={() => setIsProjectOpen(true)}
        onToggleSidebar={toggleSidebar}
      />

      {/* Onboarding Overlay */}
      {(!apiConfig.apiKey && apiConfig.provider !== 'Ollama') && (
        <div className="absolute inset-0 z-[100]">
          <OnboardingWizard />
        </div>
      )}

      {/* Body row */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* Left sidebar — animated collapse */}
        <AnimatePresence initial={false}>
          {isSidebarOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{
                type: 'spring',
                damping: 20 + (dynamicsIntensity / 10),
                stiffness: 100 + (dynamicsIntensity / 2)
              }}
              style={{ overflow: 'hidden', flexShrink: 0 }}
            >
              <Sidebar onOpenSettings={() => setIsSettingsOpen(true)} onOpenProject={() => setIsProjectOpen(true)} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chat area */}
        <main style={{
          flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative',
          background: 'var(--bg-base)'
        }}>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto custom-scrollbar" style={{ padding: '24px 24px 0' }}>
            <div style={{ maxWidth: 680, margin: '0 auto', display: 'flex', flexDirection: 'column', paddingBottom: 160 }}>
              {messages.length === 0 ? (
                <WelcomeScreen onRecall={loadSessions} />
              ) : (
                <>
                  <AnimatePresence mode="popLayout" initial={false}>
                    {messages.map((msg: any, i: number) => (
                      <ChatBubble
                        key={(msg.id || msg.timestamp || 'msg') + '-' + i}
                        id={msg.id} role={msg.role} content={msg.content}
                        emotion={msg.emotion} timestamp={msg.timestamp}
                      />
                    ))}
                  </AnimatePresence>

                  {/* Streaming bubble */}
                  <AnimatePresence>
                    {streamingContent && (
                      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                        className="flex w-full mb-12">
                        <div className="flex gap-6 max-w-[85%]">
                          <div className="w-9 h-9 rounded-xl bg-amber-600/10 border border-amber-500/30 flex items-center justify-center flex-shrink-0 mt-1">
                            <Zap size={16} className="text-amber-400 animate-pulse" />
                          </div>
                          <div className="flex flex-col gap-1">
                            <span className="text-[10px] font-bold uppercase tracking-widest text-amber-500 px-1">Aiko</span>
                            <div className="text-[15px] leading-[1.8] text-[var(--t1)] selectable markdown-content">
                              <ReactMarkdown 
                                remarkPlugins={[remarkGfm, remarkMath]}
                                rehypePlugins={[[rehypeKatex, { throwOnError: false }]]}
                              >
                                {maskUnclosedLatex(streamingContent)}
                              </ReactMarkdown>
                              <span className="inline-block w-0.5 h-4 bg-amber-400 ml-0.5 animate-pulse align-middle" />
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Thinking Loader — Advanced Neural Style */}
                  <AnimatePresence>
                    {isThinking && !streamingContent && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, transition: { duration: 0.2 } }}
                        className="flex items-start gap-6 px-1 py-6 w-full"
                      >
                        <div className="w-9 h-9 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <NeuralNode />
                        </div>
                        <div className="flex flex-col gap-2.5 flex-1">
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500/60">Neural_Synthesis</span>
                            <ThinkingDots />
                          </div>
                          <SkeletonLoader />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  <div ref={chatEndRef} className="h-4" />
                </>
              )}
            </div>
          </div>

          {/* Input bar — floating at bottom */}
          <div className="absolute bottom-0 left-0 w-full z-10" style={{
            padding: '0 0 16px 0',
            background: 'var(--bg-base)',
          }}>
            <InputDock onOpenProject={() => setIsProjectOpen(true)} />
          </div>
        </main>

        {/* Right panel — Live2D + stats */}
        <DashboardStats
          bridgeStatus={bridgeStatus}
          isThinking={isThinking}
          isTalking={isTalking}
          currentEmotion={currentEmotion}
          avatarScale={avatarScale}
          setAvatarScale={setAvatarScale}
          amplitude={amplitude}
        />
      </div>

      {/* Modals */}
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      <ProjectIntelligence isOpen={isProjectOpen} onClose={() => setIsProjectOpen(false)} />

      {isPurgeConfirmOpen && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md">
          <div className="glass-pane rounded-[32px] p-10 max-w-sm w-full mx-4 text-center">
            <div className="text-3xl mb-4">🧪</div>
            <h2 className="text-sm font-bold text-white uppercase tracking-[0.3em] mb-4">Initialize Purge?</h2>
            <p className="text-[12px] text-slate-500 leading-relaxed mb-8">Reset current session state.</p>
            <div className="flex gap-4">
              <button onClick={() => setIsPurgeConfirmOpen(false)}
                className="flex-1 py-3.5 rounded-2xl bg-white/[0.03] border border-white/5 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:bg-white/5">
                Cancel
              </button>
              <button onClick={async () => { setIsPurgeConfirmOpen(false); await triggerPurge(); }}
                className="flex-1 py-3.5 rounded-2xl bg-red-600/20 border border-red-500/30 text-[10px] font-bold text-white uppercase tracking-widest hover:bg-red-600 transition-all">
                Proceed
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function NeuralNode() {
  return (
    <div className="relative w-6 h-6">
      <div className="absolute inset-0 bg-amber-500/20 blur-[6px] rounded-full animate-pulse" />
      <div className="relative w-full h-full rounded-full border border-amber-500/40 flex items-center justify-center">
        <div className="w-1.5 h-1.5 bg-amber-500 rounded-full" />
      </div>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex gap-1">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          animate={{ scale: [1, 1.5, 1], opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
          className="w-1 h-1 rounded-full bg-amber-500"
        />
      ))}
    </div>
  );
}

export default App;
