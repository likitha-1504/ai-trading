import React, { useState } from "react";
import { AlertOctagon, AlertTriangle } from "lucide-react";
import { Modal } from "../ui/Modal";

interface KillSwitchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
}

export const KillSwitchModal: React.FC<KillSwitchModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
}) => {
  const [reason, setReason] = useState<string>("Manual operator intervention via dashboard");
  const [confirmed, setConfirmed] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const handleConfirm = async () => {
    if (!confirmed) return;
    setSubmitting(true);
    try {
      await onConfirm(reason);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="EMERGENCY KILL-SWITCH INTERVENTION"
      variant="danger"
    >
      <div className="space-y-4">
        <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/80 text-xs text-rose-200 flex items-start gap-2.5">
          <AlertTriangle size={18} className="text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-rose-300">IMMEDIATE SAFETY ACTION</p>
            <p className="mt-1 text-rose-200/90 leading-relaxed">
              Triggering the Kill-Switch immediately:
            </p>
            <ul className="list-disc list-inside mt-1 space-y-0.5 text-rose-300 font-mono text-[11px]">
              <li>Cancels all open/submitted orders across broker adapters</li>
              <li>Instructs Independent Position Watcher to market-square-off ALL open positions</li>
              <li>Locks system into HALTED mode and revokes execution authority</li>
            </ul>
          </div>
        </div>

        <div>
          <label className="block text-xs font-mono text-slate-300 mb-1">
            Reason for Emergency Halt:
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full px-3 py-2 rounded bg-[#0B0E14] border border-[#222938] text-xs font-mono text-slate-100 focus:outline-none focus:border-rose-500"
            placeholder="Specify reason..."
          />
        </div>

        <div className="flex items-center gap-2 pt-2">
          <input
            type="checkbox"
            id="kill-confirm"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="w-4 h-4 rounded border-[#222938] bg-[#0B0E14] text-rose-600 focus:ring-0 cursor-pointer"
          />
          <label htmlFor="kill-confirm" className="text-xs text-slate-300 cursor-pointer select-none">
            I confirm immediate emergency square-off and system shutdown.
          </label>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#222938]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded text-xs font-mono text-slate-300 hover:bg-[#1C2331] transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!confirmed || submitting}
            onClick={handleConfirm}
            className="flex items-center gap-1.5 px-4 py-2 rounded bg-rose-600 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-mono font-bold text-white shadow-lg transition-all"
          >
            <AlertOctagon size={14} />
            {submitting ? "TRIGGERING..." : "CONFIRM EMERGENCY HALT"}
          </button>
        </div>
      </div>
    </Modal>
  );
};
