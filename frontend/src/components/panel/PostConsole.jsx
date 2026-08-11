import { AnimatePresence, motion } from "framer-motion";
import {
  Play,
  Wand2,
  FilePlus2,
  Loader2,
  Lightbulb,
  TriangleAlert,
} from "lucide-react";
import GlassCard from "../ui/GlassCard.jsx";

function PrimaryButton({ children, icon: Icon, loading, ...props }) {
  return (
    <button
      className="group relative inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-grad-accent px-4 py-2.5 font-medium text-ink-900 shadow-glow-amber transition hover:brightness-110 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : Icon ? (
        <Icon className="h-4 w-4" strokeWidth={2.4} />
      ) : null}
      {children}
    </button>
  );
}

function GhostButton({ children, icon: Icon, ...props }) {
  return (
    <button
      className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/12 bg-white/[0.04] px-4 py-2.5 font-medium text-zinc-200 transition hover:border-white/25 hover:bg-white/[0.08] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
      {...props}
    >
      {Icon ? <Icon className="h-4 w-4" strokeWidth={2.2} /> : null}
      {children}
    </button>
  );
}

const NOTICE_STYLE = {
  info: { icon: Lightbulb, cls: "border-neon-orange/25 bg-neon-orange/8 text-amber-200" },
  warn: { icon: TriangleAlert, cls: "border-amber-500/25 bg-amber-500/8 text-amber-200" },
};

export default function PostConsole({
  post,
  setPost,
  loading,
  hasRounds,
  canRework,
  notice,
  error,
  onRun,
  onReworkAndRun,
  onNewDraft,
}) {
  return (
    <section className="mx-auto max-w-7xl px-5 pt-12 sm:px-8">
      <GlassCard
        className="p-5 sm:p-6"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="eyebrow">Draft under review</h2>
          <span className="font-mono text-[11px] text-zinc-600">
            {post.trim().length} characters
          </span>
        </div>

        <textarea
          value={post}
          onChange={(e) => setPost(e.target.value)}
          rows={5}
          spellCheck={false}
          placeholder="Paste the financial post you want the panel to judge…"
          className="w-full resize-y rounded-xl border border-white/10 bg-ink-800/60 p-4 text-[15px] leading-relaxed text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-neon-orange/40 focus:ring-2 focus:ring-neon-orange/20"
        />

        <div className="mt-4 flex flex-col gap-2.5 sm:flex-row">
          <PrimaryButton icon={Play} loading={loading} onClick={onRun} disabled={loading}>
            {loading ? "Working…" : hasRounds ? "Run the panel again" : "Run the panel"}
          </PrimaryButton>

          <GhostButton
            icon={Wand2}
            onClick={onReworkAndRun}
            disabled={loading || !canRework}
            title={
              canRework
                ? "Revise from the panel's feedback, then vote again"
                : "Available after a round that did not pass."
            }
          >
            Rework &amp; run again
          </GhostButton>

          <GhostButton icon={FilePlus2} onClick={onNewDraft} disabled={loading}>
            New draft
          </GhostButton>
        </div>

        <AnimatePresence>
          {error ? (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 flex items-start gap-2 rounded-xl border border-neon-rose/30 bg-neon-rose/8 px-4 py-3 text-sm text-rose-200"
            >
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </motion.div>
          ) : null}
        </AnimatePresence>

        <AnimatePresence>
          {notice ? (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className={`mt-4 flex items-start gap-2 rounded-xl border px-4 py-3 text-sm ${
                (NOTICE_STYLE[notice.kind] ?? NOTICE_STYLE.info).cls
              }`}
            >
              {(() => {
                const Icon = (NOTICE_STYLE[notice.kind] ?? NOTICE_STYLE.info).icon;
                return <Icon className="mt-0.5 h-4 w-4 shrink-0" />;
              })()}
              <span>{notice.text}</span>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </GlassCard>
    </section>
  );
}
