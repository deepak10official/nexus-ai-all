import { motion } from "framer-motion";
import { CheckCircle2, XCircle } from "lucide-react";
import GlassCard from "../ui/GlassCard.jsx";
import Badge from "../ui/Badge.jsx";

/**
 * One ballot. `persona` may be undefined if the backend returns a persona_id
 * the front-end doesn't know — we fall back to the name stamped on the vote.
 */
export default function VoteCard({ vote, persona, index, animate, revealDelay }) {
  const approved = vote.decision === "APPROVE";
  const name = persona?.name ?? vote.persona_name ?? vote.persona_id;
  const emoji = persona?.emoji ?? "🗳️";
  const archetype = persona?.archetype;

  const initial = animate ? { opacity: 0, y: 18, scale: 0.98 } : false;

  return (
    <GlassCard
      glow={approved ? "emerald" : "rose"}
      className="flex h-full flex-col p-4"
      initial={initial}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, delay: animate ? index * revealDelay : 0 }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-lg">{emoji}</span>
            <span className="truncate font-display text-sm font-semibold text-white">
              {name}
            </span>
          </div>
          {archetype ? (
            <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-500">
              {archetype}
            </div>
          ) : null}
        </div>
        {approved ? (
          <Badge tone="emerald" icon={CheckCircle2}>
            Approve
          </Badge>
        ) : (
          <Badge tone="rose" icon={XCircle}>
            Reject
          </Badge>
        )}
      </div>

      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-600">
          <span>Confidence</span>
          <span className="text-zinc-400">{Math.round((vote.confidence ?? 0) * 100)}%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
          <motion.div
            className={`h-full rounded-full ${approved ? "bg-neon-emerald" : "bg-neon-rose"}`}
            initial={{ width: 0 }}
            animate={{ width: `${Math.round((vote.confidence ?? 0) * 100)}%` }}
            transition={{ duration: 0.6, delay: animate ? index * revealDelay + 0.1 : 0 }}
          />
        </div>
      </div>

      <p className="mt-3 flex-1 text-sm leading-relaxed text-zinc-300">
        {vote.reasoning?.trim()}
      </p>

      {vote.suggested_changes && !approved ? (
        <div className="mt-3 rounded-lg border border-white/8 bg-white/[0.03] p-2.5">
          <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-neon-orange/80">
            Wants
          </div>
          <p className="text-xs leading-relaxed text-zinc-400">
            {vote.suggested_changes.trim()}
          </p>
        </div>
      ) : null}
    </GlassCard>
  );
}
