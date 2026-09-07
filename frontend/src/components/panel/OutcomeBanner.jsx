import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  PartyPopper,
  Gavel,
  Instagram,
  Facebook,
  Loader2,
  Check,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";

import { api } from "../../api/panelApi.js";

/**
 * Outcome of the round, and — only once the panel has passed the post — the
 * controls to publish it.
 *
 * Publishing lives here rather than in the draft console on purpose: this is
 * the one point in the app where a post is known to have cleared validation,
 * so it is the only place it can go live from.
 */
export default function OutcomeBanner({ round, roundNumber, threadId, hasImage }) {
  const [busy, setBusy] = useState(null); // "instagram" | "facebook" | null
  const [results, setResults] = useState({}); // platform -> { ok, permalink, error }

  // A new round means different text. Anything published earlier refers to a
  // post that no longer matches what is on screen, so the state is cleared.
  useEffect(() => {
    setResults({});
    setBusy(null);
  }, [roundNumber, threadId]);

  if (!round) return null;
  const passed = round.passed;

  async function publish(platform) {
    setBusy(platform);
    try {
      const res = await api.publish(threadId, platform);
      setResults((r) => ({ ...r, [platform]: { ok: true, ...res } }));
    } catch (e) {
      setResults((r) => ({ ...r, [platform]: { ok: false, error: e.message } }));
    } finally {
      setBusy(null);
    }
  }

  const platforms = [
    {
      id: "instagram",
      label: "Upload to Instagram",
      icon: Instagram,
      // Instagram will not accept a post without media, so say so up front
      // rather than letting the click fail.
      blocked: !hasImage,
      blockedReason: "Instagram needs an image. Attach one and run the panel again.",
    },
    {
      id: "facebook",
      label: "Upload to Facebook",
      icon: Facebook,
      blocked: false,
    },
  ];

  return (
    <section className="mx-auto max-w-7xl px-5 pt-8 sm:px-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className={`rounded-2xl border p-4 sm:p-5 ${
          passed
            ? "border-neon-emerald/30 bg-neon-emerald/8 shadow-glow-emerald"
            : "border-neon-rose/30 bg-neon-rose/8 shadow-glow-rose"
        }`}
      >
        <div className="flex items-start gap-3">
          {passed ? (
            <PartyPopper className="mt-0.5 h-5 w-5 shrink-0 text-neon-emerald" />
          ) : (
            <Gavel className="mt-0.5 h-5 w-5 shrink-0 text-neon-rose" />
          )}
          <div>
            <div className="font-display text-base font-semibold text-white">
              {passed
                ? `Round ${roundNumber} passed with ${round.tally}.`
                : `Round ${roundNumber} did not pass (${round.tally}).`}
            </div>
            <p className="mt-0.5 text-sm text-zinc-400">
              {passed
                ? "The panel approved this post. It can now be published."
                : "Rework the post to fold in the panel's feedback, then run it again."}
            </p>
          </div>
        </div>

        {passed && (
          <div className="mt-4 border-t border-white/10 pt-4">
            <div className="mb-2.5 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
              Publish
            </div>

            <div className="flex flex-col gap-2.5 sm:flex-row">
              {platforms.map(({ id, label, icon: Icon, blocked, blockedReason }) => {
                const result = results[id];

                if (result?.ok) {
                  return (
                    <div
                      key={id}
                      className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-neon-emerald/30 bg-neon-emerald/10 px-4 py-2.5 text-sm text-neon-emerald"
                    >
                      <Check className="h-4 w-4" strokeWidth={2.4} />
                      Published
                      {result.permalink && (
                        <a
                          href={result.permalink}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 underline underline-offset-2 hover:text-white"
                        >
                          view <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  );
                }

                return (
                  <button
                    key={id}
                    onClick={() => publish(id)}
                    disabled={blocked || busy !== null}
                    title={blocked ? blockedReason : undefined}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/12 bg-white/[0.05] px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:border-white/25 hover:bg-white/[0.09] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {busy === id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Icon className="h-4 w-4" strokeWidth={2.2} />
                    )}
                    {busy === id ? "Publishing…" : label}
                  </button>
                );
              })}
            </div>

            <AnimatePresence>
              {platforms
                .filter((p) => results[p.id] && !results[p.id].ok)
                .map((p) => (
                  <motion.div
                    key={p.id}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2.5 flex items-start gap-2 rounded-xl border border-neon-rose/30 bg-neon-rose/8 px-3 py-2.5 text-xs text-rose-200"
                  >
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span className="capitalize">
                      {p.id}:{" "}
                      <span className="normal-case">{results[p.id].error}</span>
                    </span>
                  </motion.div>
                ))}
            </AnimatePresence>

            {!hasImage && (
              <p className="mt-2.5 text-[11px] leading-relaxed text-zinc-500">
                No image attached — Facebook will publish text only, and
                Instagram is unavailable.
              </p>
            )}
            <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">
              This posts for real. Instagram captions cannot be edited once
              published.
            </p>
          </div>
        )}
      </motion.div>
    </section>
  );
}
