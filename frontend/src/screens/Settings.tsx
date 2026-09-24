import React, { useState } from "react";
import { FactBanner } from "../components/ui/FactBanner";
import { Badge } from "../components/ui/Badge";
import { Lock, Bell, Check, Save } from "lucide-react";

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrl] = useState<string>("http://127.0.0.1:8000/api/v1");
  const [webhookUrl, setWebhookUrl] = useState<string>("https://discord.com/api/webhooks/mock");
  const [soundAlerts, setSoundAlerts] = useState<boolean>(true);
  const [saved, setSaved] = useState<boolean>(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Terminal Configuration & Environmental Guardrails"
        subtitle="Live trading mode is structurally locked behind Phase 19 approval tokens. Paper simulation adapter is active by default."
      />

      <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-4 font-mono text-xs max-w-2xl">
        <h4 className="font-bold text-slate-100 uppercase tracking-wider pb-2 border-b border-[#222938]">
          Execution Environment
        </h4>

        {/* Paper Mode Toggle (Locked) */}
        <div className="flex items-center justify-between p-3 rounded bg-[#0B0E14] border border-[#222938]">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-100">Paper Trading Simulation</span>
              <Badge state="CONNECTED">ACTIVE</Badge>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Zero capital risk. Fills simulated against realistic tick order book model.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-500 flex items-center gap-1 font-mono">
              <Lock size={12} className="text-amber-400" />
              LIVE LOCKED
            </span>
          </div>
        </div>

        {/* Backend API Endpoint */}
        <div className="space-y-1">
          <label className="block text-slate-400">FastAPI Backend Endpoint:</label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full px-3 py-2 rounded bg-[#0B0E14] border border-[#222938] text-slate-100"
          />
        </div>

        {/* Notification Webhooks */}
        <div className="space-y-1">
          <label className="block text-slate-400 flex items-center gap-1.5">
            <Bell size={13} className="text-amber-400" />
            Emergency Stop Alert Webhook (Discord / Telegram):
          </label>
          <input
            type="text"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            className="w-full px-3 py-2 rounded bg-[#0B0E14] border border-[#222938] text-slate-100"
          />
          <span className="text-[10px] text-slate-500">
            Fires immediately when Independent Position Watcher executes an emergency hard stop or 15:15 IST square-off.
          </span>
        </div>

        {/* Sound Notifications */}
        <div className="flex items-center gap-2 pt-2">
          <input
            type="checkbox"
            id="sound-alert"
            checked={soundAlerts}
            onChange={(e) => setSoundAlerts(e.target.checked)}
            className="rounded border-[#222938] bg-[#0B0E14] text-sky-600 focus:ring-0 cursor-pointer"
          />
          <label htmlFor="sound-alert" className="text-slate-300 cursor-pointer select-none">
            Enable audible telemetry alerts on Watcher intervention & candidate discovery
          </label>
        </div>

        <div className="pt-3 border-t border-[#222938] flex justify-end">
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-white font-mono text-xs font-bold transition-all shadow-md"
          >
            {saved ? <Check size={14} /> : <Save size={14} />}
            {saved ? "PREFERENCES SAVED" : "SAVE PREFERENCES"}
          </button>
        </div>
      </div>
    </div>
  );
};
