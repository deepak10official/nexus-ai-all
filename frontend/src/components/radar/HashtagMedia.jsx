import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronDown,
  Heart,
  Instagram,
  Loader2,
  MessageCircle,
  Info,
} from "lucide-react";

import * as api from "../../api/radarApi.js";

/**
 * Real Instagram posts currently carrying the selected hashtag.
 *
 * Two jobs: it shows the reviewer what the conversation actually looks like
 * before they draft, and the same captions are sent to the model as grounding.
 *
 * Fetching is deliberate, not automatic on every selection: Instagram allows
 * only 30 unique hashtag lookups per rolling 7 days, and a tag counts the
 * moment it is queried whether or not the reviewer uses it.
 */
export default function HashtagMedia({ hashtag }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("top");

  // A new hashtag invalidates everything — never show one tag's posts under
  // another's name.
  useEffect(() => {
    setData(null);
    setError(null);
    setOpen(false);
  }, [hashtag]);

  async function load() {
    if (data || loading) {
      setOpen((v) => !v);
      return;
    }
    setOpen(true);
    setLoading(true);
    setError(null);
    try {
      setData(await api.hashtagMedia(hashtag));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (!hashtag) return null;

  const items = data ? (tab === "top" ? data.top : data.recent) || [] : [];

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02]">
      <button
        onClick={load}
        className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left transition hover:bg-white/[0.03]"
      >
        <span className="flex items-center gap-2 text-xs text-chalk">
          <Instagram size={13} className="text-violet" />
          Reference posts on Instagram
          {data ? (
            <span className="font-mono text-[10px] text-muted">
              {(data.top?.length || 0) + (data.recent?.length || 0)} English
              {data.filtered_out ? ` · ${data.filtered_out} filtered` : ""}
              {data.cached ? " · cached" : ""}
            </span>
          ) : null}
        </span>
        <span className="flex items-center gap-2">
          {loading ? (
            <Loader2 size={13} className="animate-spin text-muted" />
          ) : null}
          <ChevronDown
            size={14}
            className={`text-muted transition ${open ? "rotate-180" : ""}`}
          />
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden border-t border-white/8"
          >
            <div className="p-3">
              {loading && (
                <p className="py-4 text-center font-mono text-[11px] text-muted">
                  Asking Instagram what is being posted under {hashtag}…
                </p>
              )}

              {error && (
                <div className="flex items-start gap-2 rounded-lg border border-saffron/25 bg-saffron/[0.07] px-3 py-2.5">
                  <Info size={13} className="mt-0.5 shrink-0 text-saffron" />
                  <div className="text-xs leading-relaxed text-muted">
                    {error}
                    <div className="mt-1 text-[11px] text-muted/70">
                      The draft can still be written — it just will not be
                      grounded in real posts.
                    </div>
                  </div>
                </div>
              )}

              {data && !loading && (
                <>
                  <div className="mb-2.5 flex items-center justify-between">
                    <div className="flex gap-1">
                      {["top", "recent"].map((t) => (
                        <button
                          key={t}
                          onClick={() => setTab(t)}
                          className={`rounded-md px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider transition ${
                            tab === t
                              ? "bg-white/10 text-chalk"
                              : "text-muted hover:text-chalk"
                          }`}
                        >
                          {t} ({(t === "top" ? data.top : data.recent)?.length || 0})
                        </button>
                      ))}
                    </div>
                    {typeof data.budget_used === "number" && (
                      <span
                        className="font-mono text-[10px] text-muted"
                        title="Instagram allows 30 unique hashtag lookups per rolling 7 days."
                      >
                        {data.budget_used}/30 tags used this week
                      </span>
                    )}
                  </div>

                  {items.length === 0 ? (
                    <p className="px-3 py-4 text-center text-[11px] leading-relaxed text-muted">
                      No English posts in this tab.
                      {data.filtered_out
                        ? ` ${data.filtered_out} post${data.filtered_out === 1 ? " was" : "s were"} in other languages and excluded.`
                        : ""}
                    </p>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {items.map((m) => (
                        <a
                          key={m.id}
                          href={m.permalink}
                          target="_blank"
                          rel="noreferrer"
                          className="group overflow-hidden rounded-lg border border-white/8 bg-ink-800/60 transition hover:border-white/20"
                        >
                          {m.media_url && m.media_type !== "VIDEO" ? (
                            <img
                              src={m.media_url}
                              alt=""
                              loading="lazy"
                              className="h-24 w-full object-cover transition group-hover:opacity-90"
                            />
                          ) : (
                            <div className="grid h-24 w-full place-items-center bg-white/[0.03] font-mono text-[10px] text-muted">
                              {m.media_type || "MEDIA"}
                            </div>
                          )}
                          <div className="p-2">
                            <p className="line-clamp-3 text-[11px] leading-snug text-muted">
                              {m.caption || "(no caption)"}
                            </p>
                            <div className="mt-1.5 flex items-center gap-2.5 font-mono text-[10px] text-muted/70">
                              <span className="flex items-center gap-1">
                                <Heart size={9} /> {m.like_count ?? "–"}
                              </span>
                              <span className="flex items-center gap-1">
                                <MessageCircle size={9} /> {m.comments_count ?? "–"}
                              </span>
                            </div>
                          </div>
                        </a>
                      ))}
                    </div>
                  )}

                  <p className="mt-2.5 font-mono text-[10px] leading-relaxed text-muted/70">
                    Only English captions are kept — posts in other languages
                    are excluded from both this list and the draft. These feed
                    the model as context for tone, angle and the image brief.
                    They are other people's posts, never copied.
                  </p>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
