import React, { useState } from "react";
import { FactBanner } from "../components/ui/FactBanner";
import { Badge } from "../components/ui/Badge";
import { Save, Check } from "lucide-react";

export const StrategyManagement: React.FC = () => {
  // Strategy A (Momentum Continuation) parameters
  const [momRvol, setMomRvol] = useState<number>(2.0);
  const [momMinSlope, setMomMinSlope] = useState<number>(0.15);
  const [momVwapMaxDev, setMomVwapMaxDev] = useState<number>(2.5);

  // Strategy B (Early-Move Detection) parameters
  const [emCompressionBars, setEmCompressionBars] = useState<number>(10);
  const [emRocThreshold, setEmRocThreshold] = useState<number>(0.8);
  const [emBreakoutMult, setEmBreakoutMult] = useState<number>(1.5);

  const [saved, setSaved] = useState<boolean>(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-4">
      <FactBanner
        type="SYSTEM_FACT"
        title="Deterministic Strategy Engine Parameters"
        subtitle="Both strategies operate on fixed mathematical heuristics. Modifying parameters alters algorithmic candidate generation thresholds."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
        {/* Strategy A: Momentum Continuation */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#222938]">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-100 uppercase tracking-wider">
                Strategy A: Momentum Continuation
              </span>
            </div>
            <Badge state="BUY">ACTIVE</Badge>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>RVOL 10 Threshold:</span>
                <span className="font-bold text-sky-400">{momRvol}x</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="4.0"
                step="0.1"
                value={momRvol}
                onChange={(e) => setMomRvol(Number(e.target.value))}
                className="w-full accent-sky-500"
              />
              <span className="text-[10px] text-slate-500">Requires 10-period relative volume surge</span>
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Min Volume Acceleration Slope:</span>
                <span className="font-bold text-sky-400">{momMinSlope}</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="0.5"
                step="0.05"
                value={momMinSlope}
                onChange={(e) => setMomMinSlope(Number(e.target.value))}
                className="w-full accent-sky-500"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>VWAP Max Deviation:</span>
                <span className="font-bold text-sky-400">{momVwapMaxDev}%</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="5.0"
                step="0.1"
                value={momVwapMaxDev}
                onChange={(e) => setMomVwapMaxDev(Number(e.target.value))}
                className="w-full accent-sky-500"
              />
              <span className="text-[10px] text-slate-500">Rejects overextended setups</span>
            </div>
          </div>
        </div>

        {/* Strategy B: Early-Move Detection */}
        <div className="p-4 rounded-lg bg-[#151A23] border border-[#222938] space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#222938]">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-100 uppercase tracking-wider">
                Strategy B: Early-Move Detection
              </span>
            </div>
            <Badge state="WATCH">ACTIVE</Badge>
          </div>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Volatility Compression Lookback:</span>
                <span className="font-bold text-emerald-400">{emCompressionBars} bars</span>
              </div>
              <input
                type="range"
                min="5"
                max="30"
                step="1"
                value={emCompressionBars}
                onChange={(e) => setEmCompressionBars(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
              <span className="text-[10px] text-slate-500">Detects tight price consolidation coils</span>
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>ROC 5 Threshold:</span>
                <span className="font-bold text-emerald-400">{emRocThreshold}%</span>
              </div>
              <input
                type="range"
                min="0.2"
                max="2.0"
                step="0.1"
                value={emRocThreshold}
                onChange={(e) => setEmRocThreshold(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Breakout Volume Multiplier:</span>
                <span className="font-bold text-emerald-400">{emBreakoutMult}x</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="3.0"
                step="0.1"
                value={emBreakoutMult}
                onChange={(e) => setEmBreakoutMult(Number(e.target.value))}
                className="w-full accent-emerald-500"
              />
              <span className="text-[10px] text-slate-500">Confirms coil expansion</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <button
          onClick={handleSave}
          className="flex items-center gap-1.5 px-4 py-2 rounded bg-sky-600 hover:bg-sky-500 text-white font-mono text-xs font-bold transition-all shadow-md"
        >
          {saved ? <Check size={14} /> : <Save size={14} />}
          {saved ? "CONFIG SAVED TO REPO" : "SAVE STRATEGY PARAMETERS"}
        </button>
      </div>
    </div>
  );
};
