import { motion } from "framer-motion";
import { Check, PencilLine, X } from "lucide-react";

/**
 * The three-button review group, used identically for the post and for
 * the image. Keeping it one component means the two halves can never
 * drift apart visually, which matters — a reviewer scanning quickly
 * should not have to relearn the controls halfway down the panel.
 *
 * status: "pending" | "approved" | "rejected"
 */

const STATUS_STYLE = {
  approved: {
    color: "#35E0D8",
    label: "Approved",
  },
  rejected: {
    color: "#F2536D",
    label: "Rejected",
  },
  pending: {
    color: "#7E8AA0",
    label: "Awaiting review",
  },
};

function Btn({ onClick, disabled, children, tone = "neutral", active }) {
  const tones = {
    approve: active
      ? "border-signal/60 bg-signal/20 text-signal"
      : "border-signal/30 bg-signal/[0.07] text-signal hover:bg-signal/15",
    edit: "border-violet/35 bg-violet/[0.08] text-violet hover:bg-violet/20",
    reject: active
      ? "border-[#F2536D]/60 bg-[#F2536D]/20 text-[#F2536D]"
      : "border-[#F2536D]/25 bg-[#F2536D]/[0.06] text-[#F2536D]/90 hover:bg-[#F2536D]/15",
    neutral: "border-white/12 bg-white/[0.04] text-chalk/80 hover:bg-white/[0.09]",
  };
  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={disabled}
      whileHover={disabled ? {} : { scale: 1.03 }}
      whileTap={disabled ? {} : { scale: 0.97 }}
      className={`flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-2 font-display text-[12px] transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${tones[tone]}`}
    >
      {children}
    </motion.button>
  );
}

export default function ReviewControls({
  label,
  status = "pending",
  busy = false,
  disabled = false,
  editing = false,
  onApprove,
  onEdit,
  onReject,
  approveText = "Approve",
  editText = "Review or Edit",
  rejectText = "Reject",
}) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.pending;

  return (
    <div
      className="rounded-xl border p-3 transition-colors"
      style={{
        borderColor: status === "pending" ? "rgba(255,255,255,0.09)" : `${s.color}35`,
        background: status === "pending" ? "rgba(255,255,255,0.02)" : `${s.color}0A`,
      }}
    >
      <div className="mb-2.5 flex items-center justify-between">
        <p className="eyebrow">{label}</p>
        <span
          className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider"
          style={{ color: s.color }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: s.color }}
          />
          {s.label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-1.5">
        <Btn
          tone="approve"
          onClick={onApprove}
          disabled={disabled || busy}
          active={status === "approved"}
        >
          <Check size={13} /> {approveText}
        </Btn>
        <Btn tone="edit" onClick={onEdit} disabled={disabled || busy} active={editing}>
          <PencilLine size={13} /> {editText}
        </Btn>
        <Btn
          tone="reject"
          onClick={onReject}
          disabled={disabled || busy}
          active={status === "rejected"}
        >
          <X size={13} /> {rejectText}
        </Btn>
      </div>
    </div>
  );
}
