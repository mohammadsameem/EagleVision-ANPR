import React, { useState } from 'react';
import { X, Copy, Check, Server, KeyRound, Terminal, Cpu } from 'lucide-react';

interface SettingsAndCodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab: 'settings' | 'part1_html' | 'part2_python';
  nebiusApiKey: string;
  onChangeNebiusApiKey: (val: string) => void;
  nebiusBaseUrl: string;
  onChangeNebiusBaseUrl: (val: string) => void;
  selectedModel: string;
  onChangeSelectedModel: (val: string) => void;
  backendUrl: string;
  onChangeBackendUrl: (val: string) => void;
  standaloneHtmlCode: string;
  pythonMainCode: string;
  requirementsTxtCode: string;
}

export const SettingsAndCodeModal: React.FC<SettingsAndCodeModalProps> = ({
  isOpen,
  onClose,
  initialTab,
  nebiusApiKey,
  onChangeNebiusApiKey,
  nebiusBaseUrl,
  onChangeNebiusBaseUrl,
  selectedModel,
  onChangeSelectedModel,
  backendUrl,
  onChangeBackendUrl,
  standaloneHtmlCode,
  pythonMainCode,
  requirementsTxtCode,
}) => {
  const [activeTab, setActiveTab] = useState<'settings' | 'part1_html' | 'part2_python'>(
    initialTab
  );
  const [copiedId, setCopiedId] = useState<string | null>(null);

  React.useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  if (!isOpen) return null;

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 font-mono"
    >
      <div className="w-full max-w-4xl max-h-[88vh] flex flex-col bg-[#0c1017] border border-slate-700 rounded-sm shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#080a0f] border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <h2 id="modal-title" className="text-xs font-bold font-display tracking-wider text-slate-100 uppercase">
              EAGLEVISION™ // SYSTEM CONFIG &amp; PYTHON YOLOv8 + NEBIUS BACKEND EXPORT
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 text-slate-400 hover:text-slate-100 rounded transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Bar */}
        <div className="flex items-center gap-2 px-4 py-2 bg-[#080a0f]/80 border-b border-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab('settings')}
            className={`px-3 py-1 text-[11px] font-medium rounded-[2px] transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
              activeTab === 'settings'
                ? 'bg-cyan-500 text-slate-950 font-semibold'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            [ SYSTEM CONFIG // NEBIUS TOKEN FACTORY ]
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('part2_python')}
            className={`px-3 py-1 text-[11px] font-medium rounded-[2px] transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
              activeTab === 'part2_python'
                ? 'bg-cyan-500 text-slate-950 font-semibold'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            [ PYTHON YOLOv8 + BYTETRACK + NEBIUS (main.py) ]
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('part1_html')}
            className={`px-3 py-1 text-[11px] font-medium rounded-[2px] transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
              activeTab === 'part1_html'
                ? 'bg-cyan-500 text-slate-950 font-semibold'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            [ STANDALONE HTML EXPORT ]
          </button>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeTab === 'settings' && (
            <div className="space-y-4 max-w-2xl">
              <div className="p-3 rounded-[2px] bg-[#080a0f] border border-slate-800 text-[11px] text-slate-300 leading-relaxed">
                Configure your live <strong>Nebius Token Factory</strong> credentials and select
                the NVIDIA open-source reasoning model. All requests are logged in real time inside
                the <strong>Nebius API Request / Response Inspector</strong> drawer.
              </div>

              <div>
                <label
                  htmlFor="nebius-key-input"
                  className="block text-[11px] font-semibold text-slate-200 mb-1"
                >
                  <KeyRound className="w-3.5 h-3.5 inline mr-1.5 text-cyan-400" />
                  NEBIUS_API_KEY (Bearer Token)
                </label>
                <input
                  id="nebius-key-input"
                  type="password"
                  value={nebiusApiKey}
                  onChange={(e) => onChangeNebiusApiKey(e.target.value)}
                  placeholder="Enter your Nebius API Key (or leave blank for server-side configuration)"
                  className="w-full px-3 py-1.5 bg-[#080a0f] border border-slate-700 rounded-[2px] text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label
                  htmlFor="nebius-base-url-input"
                  className="block text-[11px] font-semibold text-slate-200 mb-1"
                >
                  <Server className="w-3.5 h-3.5 inline mr-1.5 text-emerald-400" />
                  Nebius Token Factory Base URL
                </label>
                <input
                  id="nebius-base-url-input"
                  type="url"
                  value={nebiusBaseUrl}
                  onChange={(e) => onChangeNebiusBaseUrl(e.target.value)}
                  placeholder="https://api.studio.nebius.ai/v1"
                  className="w-full px-3 py-1.5 bg-[#080a0f] border border-slate-700 rounded-[2px] text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label
                  htmlFor="nvidia-model-select"
                  className="block text-[11px] font-semibold text-slate-200 mb-1"
                >
                  <Cpu className="w-3.5 h-3.5 inline mr-1.5 text-cyan-400" />
                  NVIDIA Open-Source Reasoning Model
                </label>
                <select
                  id="nvidia-model-select"
                  value={selectedModel}
                  onChange={(e) => onChangeSelectedModel(e.target.value)}
                  className="w-full px-3 py-1.5 bg-[#080a0f] border border-slate-700 rounded-[2px] text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-400"
                >
                  <option value="nvidia/Llama-3.1-Nemotron-70B-Instruct">
                    Primary Reasoning &amp; Agent Model: nvidia/Llama-3.1-Nemotron-70B-Instruct
                  </option>
                  <option value="nvidia/Mistral-NeMo-Minitron-8B-Instruct">
                    Fast Edge/Agent Model: nvidia/Mistral-NeMo-Minitron-8B-Instruct
                  </option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="backend-url-input"
                  className="block text-[11px] font-semibold text-slate-200 mb-1"
                >
                  <Server className="w-3.5 h-3.5 inline mr-1.5 text-slate-400" />
                  Local FastAPI YOLOv8 Backend URL (Optional)
                </label>
                <input
                  id="backend-url-input"
                  type="url"
                  value={backendUrl}
                  onChange={(e) => onChangeBackendUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                  className="w-full px-3 py-1.5 bg-[#080a0f] border border-slate-700 rounded-[2px] text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs rounded-[2px] transition-colors cursor-pointer"
                >
                  [ SAVE &amp; APPLY CONFIG ]
                </button>
              </div>
            </div>
          )}

          {activeTab === 'part2_python' && (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-cyan-400">
                    main.py (FastAPI + Ultralytics YOLOv8 + ByteTrack + Nebius OpenAI SDK)
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopy(pythonMainCode, 'main.py')}
                    className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-[2px] text-[11px] cursor-pointer"
                  >
                    {copiedId === 'main.py' ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span>Copied main.py</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy main.py</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 rounded-[2px] bg-[#080a0f] border border-slate-800 text-[10.5px] font-mono text-slate-200 overflow-x-auto max-h-72 leading-relaxed">
                  {pythonMainCode}
                </pre>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-cyan-400">requirements.txt</span>
                  <button
                    type="button"
                    onClick={() => handleCopy(requirementsTxtCode, 'requirements.txt')}
                    className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-[2px] text-[11px] cursor-pointer"
                  >
                    {copiedId === 'requirements.txt' ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span>Copied requirements.txt</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy requirements.txt</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 rounded-[2px] bg-[#080a0f] border border-slate-800 text-[10.5px] font-mono text-emerald-300 overflow-x-auto leading-relaxed">
                  {requirementsTxtCode}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'part1_html' && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-cyan-400">
                  index.html (Standalone Single-File Command Center)
                </span>
                <button
                  type="button"
                  onClick={() => handleCopy(standaloneHtmlCode, 'index.html')}
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-[2px] text-[11px] cursor-pointer"
                >
                  {copiedId === 'index.html' ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span>Copied index.html</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy index.html</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-3 rounded-[2px] bg-[#080a0f] border border-slate-800 text-[10.5px] font-mono text-slate-200 overflow-x-auto max-h-96 leading-relaxed">
                {standaloneHtmlCode}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
