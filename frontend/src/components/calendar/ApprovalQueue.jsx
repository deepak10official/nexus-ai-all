import { AnimatePresence, motion } from "framer-motion";
import { Check, X, CalendarPlus, Clock } from "lucide-react";

const PLATFORM_DOT = {
  instagram: "#E1306C",
  facebook: "#1877F2",
};

export default function ApprovalQueue({
  queue,
  onApprove,
  onReject,
  onSchedule,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.07] px-4 py-3">
        <div className="flex items-center gap-2">
          <Clock size={13} className="text-saffron" />
          <h3 className="font-display text-sm font-bold text-chalk">
            Approval Queue
          </h3>
        </div>
        {queue.length > 0 && (
          <span className="grid h-5 min-w-[20px] place-items-center rounded-full bg-saffron/20 px-1.5 font-mono text-[10px] font-bold text-saffron">
            {queue.length}
          </span>
        )}
      </div>

      {/* Queue items */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        <AnimatePresence mode="popLayout">
          {queue.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-10 text-center"
            >
              <CalendarPlus
                size={28}
                className="mb-3 text-muted/30"
                strokeWidth={1.5}
              />
              <p className="text-[12px] text-muted/50">
                No posts in queue
              </p>
              <p className="mt-1 text-[10px] text-muted/30">
                Approved posts from MOD02 will appear here
              </p>
            </motion.div>
          ) : (
            queue.map((item) => (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="mb-2 rounded-xl border border-white/10 bg-white/[0.03] p-3 transition-colors hover:border-white/15 hover:bg-white/[0.05]"
              >
                {/* Status badge */}
                <div className="mb-2 flex items-center gap-1.5">
                  <span className="flex items-center gap-1 rounded-md border border-saffron/30 bg-saffron/10 px-1.5 py-[1px] font-mono text-[8px] uppercase tracking-wider text-saffron">
                    ⏳ Pending Approval
                  </span>
                  {item.source_mod && (
                    <span className="rounded-md border border-violet/30 bg-violet/10 px-1.5 py-[1px] font-mono text-[8px] uppercase tracking-wider text-violet">
                      {item.source_mod}
                    </span>
                  )}
                </div>

                {/* Post preview */}
                <p
                  className="intl mb-2 text-[11px] leading-relaxed text-chalk/80"
                  dir="auto"
                >
                  {item.text.length > 90
                    ? item.text.slice(0, 90) + "…"
                    : item.text}
                </p>

                {/* Platform */}
                <div className="mb-2.5 flex items-center gap-1.5">
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{
                      background:
                        PLATFORM_DOT[item.platform] || PLATFORM_DOT.instagram,
                    }}
                  />
                  <span className="font-mono text-[9px] text-muted">
                    {item.platform_label || item.platform}
                  </span>
                </div>

                {/* Action buttons */}
                <div className="flex gap-2">
                  {item.status === "approved" ? (
                    <button
                      onClick={() => onSchedule?.(item)}
                      className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-signal/30 bg-signal/10 py-1.5 font-mono text-[10px] font-bold text-signal transition-colors hover:bg-signal/20"
                    >
                      <CalendarPlus size={11} /> Schedule
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => onApprove(item.id)}
                        className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-neon-emerald/30 bg-neon-emerald/10 py-1.5 font-mono text-[10px] font-bold text-neon-emerald transition-colors hover:bg-neon-emerald/20"
                      >
                        <Check size={11} /> Approve
                      </button>
                      <button
                        onClick={() => onReject(item.id)}
                        className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-neon-rose/25 bg-neon-rose/[0.08] py-1.5 font-mono text-[10px] font-bold text-neon-rose transition-colors hover:bg-neon-rose/15"
                      >
                        <X size={11} /> Reject
                      </button>
                    </>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
