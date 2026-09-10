import { motion } from "framer-motion";
import { Check, Radio, ExternalLink, Trash2 } from "lucide-react";

/** Platform badge colors + icons. */
const PLATFORM_STYLES = {
  facebook: {
    label: "Facebook",
    bg: "bg-[#1877F2]/12",
    border: "border-[#1877F2]/25",
    text: "text-[#5B9BD5]",
    dot: "#1877F2",
  },
  instagram: {
    label: "Instagram",
    bg: "bg-[#E1306C]/12",
    border: "border-[#E1306C]/25",
    text: "text-[#E1306C]",
    dot: "#E1306C",
  },
};

function PlatformBadge({ platform }) {
  const s = PLATFORM_STYLES[platform] || PLATFORM_STYLES.instagram;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-[2px] font-mono text-[9px] uppercase tracking-wider ${s.bg} ${s.border} ${s.text}`}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.dot }} />
      {s.label}
    </span>
  );
}

function StatusChip({ status }) {
  if (status === "live") {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-neon-emerald/30 bg-neon-emerald/10 px-1.5 py-[2px] font-mono text-[9px] uppercase tracking-wider text-neon-emerald">
        <Check size={9} /> Approved → Live
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-signal/30 bg-signal/10 px-1.5 py-[2px] font-mono text-[9px] uppercase tracking-wider text-signal">
      <Check size={9} /> Scheduled
    </span>
  );
}

export default function PostCard({
  post,
  onPublish,
  onDelete,
  compact = false,
}) {
  const maxChars = compact ? 60 : 100;
  const snippet =
    post.text.length > maxChars
      ? post.text.slice(0, maxChars) + "…"
      : post.text;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="group rounded-xl border border-white/10 bg-white/[0.035] p-3 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.06]"
    >
      {/* Top row: source badge + platform */}
      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        {post.source_mod && (
          <span className="rounded-md border border-saffron/30 bg-saffron/10 px-1.5 py-[1px] font-mono text-[8px] font-bold uppercase tracking-wider text-saffron">
            {post.source_mod}
          </span>
        )}
        {post.source_label && (
          <span className="rounded-md border border-white/12 bg-white/[0.04] px-1.5 py-[1px] font-mono text-[8px] uppercase tracking-wider text-chalk/60">
            {post.source_label}
          </span>
        )}
      </div>

      {/* Platform */}
      <div className="mb-2">
        <PlatformBadge platform={post.platform} />
      </div>

      {/* Post text */}
      <p
        className="intl mb-2 text-[12px] leading-relaxed text-chalk/85"
        dir="auto"
      >
        {snippet}
      </p>

      {/* Status + time */}
      <div className="flex items-center justify-between gap-2">
        <StatusChip status={post.status} />
        {post.scheduled_time && (
          <span className="font-mono text-[9px] text-muted">
            {post.scheduled_time}
          </span>
        )}
      </div>

      {/* Hover actions */}
      <div className="mt-2 flex gap-1.5 opacity-0 transition-opacity group-hover:opacity-100">
        {post.status === "scheduled" && onPublish && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPublish(post.id);
            }}
            className="flex items-center gap-1 rounded-lg border border-neon-emerald/30 bg-neon-emerald/10 px-2 py-1 font-mono text-[9px] text-neon-emerald transition-colors hover:bg-neon-emerald/20"
          >
            <Radio size={9} /> Go Live
          </button>
        )}
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(post.id);
            }}
            className="flex items-center gap-1 rounded-lg border border-neon-rose/25 bg-neon-rose/[0.07] px-2 py-1 font-mono text-[9px] text-neon-rose transition-colors hover:bg-neon-rose/15"
          >
            <Trash2 size={9} />
          </button>
        )}
      </div>
    </motion.div>
  );
}
