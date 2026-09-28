import React, { useState } from "react";
import { Send } from "lucide-react";
import { AIOrb } from "./AIOrb";

interface AIAssistantBarProps {
  onSubmit?: (prompt: string) => void;
}

const QUICK_PROMPTS = [
  "Analyze RELIANCE",
  "Show Top Opportunities",
  "Check Risk Status",
  "Explain today's drawdown",
];

/**
 * Fixed bottom-center floating glass dock for the AI trading agent.
 */
export const AIAssistantBar: React.FC<AIAssistantBarProps> = ({ onSubmit }) => {
  const [value, setValue] = useState("");

  const send = (prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed) return;
    onSubmit?.(trimmed);
    setValue("");
  };

  return (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-4 z-30 flex justify-center px-4"
      aria-label="AI trading assistant"
    >
      <div className="glass-panel pointer-events-auto w-full max-w-[860px] rounded-2xl px-4 py-3 shadow-glow-blue">
        <div className="flex items-center gap-3">
          <AIOrb size={34} />

          <div className="min-w-0 flex-1">
            <label htmlFor="ai-assistant-input" className="sr-only">
              Ask your AI trading agent
            </label>
            <input
              id="ai-assistant-input"
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") send(value);
              }}
              placeholder="Ask your AI trading agent anything..."
              className="w-full bg-transparent text-[13px] text-slate-100 placeholder:text-slate-600 focus:outline-none"
            />
          </div>

          <button
            type="button"
            onClick={() => send(value)}
            aria-label="Send to AI agent"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-violet-500 text-space-void shadow-glow-cyan transition-transform hover:scale-105 active:scale-95"
          >
            <Send size={15} aria-hidden="true" />
          </button>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-sky-500/10 pt-2">
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => send(p)}
              className="rounded-full border border-sky-500/20 bg-sky-500/6 px-2.5 py-1 text-[10px] text-slate-400 transition-colors hover:border-neon-cyan/45 hover:text-neon-cyan"
            >
              {p}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setValue("")}
            className="rounded-full border border-sky-500/15 px-2.5 py-1 text-[10px] text-slate-600 transition-colors hover:text-slate-300"
            aria-label="Clear assistant input"
          >
            ...
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIAssistantBar;
