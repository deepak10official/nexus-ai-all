import { motion } from "framer-motion";
import { BadgeCheck, Gavel } from "lucide-react";
import Badge from "../ui/Badge.jsx";

function Metric({ label, value, accent }) {
  return (
    <div className="flex-1 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-center">
      <div className={`font-display text-2xl font-semibold ${accent}`}>{value}</div>
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-zinc-500">
        {label}
      </div>
    </div>
  );
}

export default function Tally({ approve, reject, threshold, passed }) {
  const total = approve + reject;
  const approvalPct = total > 0 ? Math.round((approve / total) * 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass p-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="eyebrow">Tally</span>
        {passed ? (
          <Badge tone="emerald" icon={BadgeCheck}>
            Passed
          </Badge>
        ) : (
          <Badge tone="rose" icon={Gavel}>
            Did not pass
          </Badge>
        )}
      </div>
      <div className="flex gap-2.5">
        <Metric label="Approve" value={approve} accent="text-neon-emerald" />
        <Metric label="Reject" value={reject} accent="text-neon-rose" />
        <Metric
          label="Approval %"
          value={`${approvalPct}%`}
          accent={passed ? "text-neon-emerald" : "text-neon-rose"}
        />
        <Metric
          label="Need"
          value={`≥${Math.round(threshold)}%`}
          accent="text-white"
        />
      </div>
    </motion.div>
  );
}
