import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Download,
  Image as ImageIcon,
  Loader2,
  Pencil,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";

/**
 * Image generation for a draft.
 *
 * Kept as its own component and its own API call: generation is slow and
 * costs credits, so the reviewer decides whether the copy is worth
 * illustrating before spending either.
 *
 * The visual brief comes from the same LLM call that wrote the post, so
 * copy and image stay coherent — but it is editable here, because a
 * reviewer will often want a different scene for the same words.
 */
export default function ImagePanel({ draft, health }) {
  const [prompt, setPrompt] = useState("");
  const [editing, setEditing] = useState(false);
  const [image, setImage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  // New draft → new brief, and drop any previous image.
  useEffect(() => {
    setPrompt(draft?.post?.image_prompt ?? "");
    setImage(null);
    setError(null);
    setEditing(false);
  }, [draft?.draft_id, draft?.post?.image_prompt]);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          draft_id: draft.draft_id,
          prompt_override: prompt.trim() || null,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `${res.status}`);
      setImage(body);
      setEditing(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!draft) return null;

  const nonCommercial = (image?.licence ?? health?.image_licence ?? "")
    .toLowerCase()
    .includes("non-commercial");

  return (
    <div className="mt-3 rounded-2xl border border-white/[0.07] bg-white/[0.02] p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ImageIcon size={13} className="text-violet" />
          <p className="eyebrow text-violet">Post image</p>
        </div>
        {(image || health?.image_model) && (
          <span className="font-mono text-[9px] text-muted">
            {(image?.model ?? health.image_model).split("/").pop()}
          </span>
        )}
      </div>

      {/* The visual brief — model-written, reviewer-editable */}
      <div className="rounded-xl border border-white/[0.07] bg-ink-900/50 p-3">
        <div className="mb-1.5 flex items-center justify-between">
          <p className="eyebrow">Visual brief</p>
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className="flex items-center gap-1 font-mono text-[10px] text-muted transition-colors hover:text-chalk"
          >
            <Pencil size={9} />
            {editing ? "done" : "edit"}
          </button>
        </div>

        {editing ? (
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            className="w-full resize-none rounded-lg border border-white/10 bg-ink-900/60 px-2.5 py-2 text-[12px] leading-relaxed text-chalk"
          />
        ) : (
          <p className="text-[12px] leading-relaxed text-chalk/80">
            {prompt || "No brief on this draft — regenerate the post, or write one."}
          </p>
        )}
      </div>

      <motion.button
        type="button"
        onClick={run}
        disabled={busy || !prompt.trim()}
        whileHover={{ scale: busy ? 1 : 1.015 }}
        whileTap={{ scale: busy ? 1 : 0.985 }}
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-violet/40 bg-violet/15 py-2.5 font-display text-sm text-violet transition-colors hover:bg-violet/25 disabled:opacity-40"
      >
        {busy ? (
          <>
            <Loader2 size={14} className="animate-spin" />
            Generating image…
          </>
        ) : (
          <>
            {image ? <RefreshCw size={14} /> : <ImageIcon size={14} />}
            {image ? "Regenerate image" : "Generate image"}
          </>
        )}
      </motion.button>

      {busy && (
        <div className="mt-3 aspect-[16/9] w-full animate-pulse rounded-xl bg-white/[0.04]" />
      )}

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 flex gap-2.5 rounded-xl border border-[#F2536D]/30 bg-[#F2536D]/[0.07] p-3"
          >
            <AlertTriangle size={14} className="mt-0.5 shrink-0 text-[#F2536D]" />
            <p className="font-mono text-[10px] leading-relaxed text-[#FFB3C1]">
              {error}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {image && !busy && (
          <motion.div
            key={image.filename}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="mt-3"
          >
            <div className="overflow-hidden rounded-xl border border-white/10">
              <img
                src={image.url}
                alt={`Generated visual for ${draft.hashtag}`}
                className="block w-full"
                loading="lazy"
              />
            </div>

            <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-muted">
              <span>
                1200×672 · {image.latency_ms} ms · via {image.provider}
              </span>
              <a
                href={image.url}
                download={image.filename}
                className="flex items-center gap-1 transition-colors hover:text-chalk"
              >
                <Download size={10} /> download
              </a>
            </div>

            {image.warning && (
              <p className="mt-2 rounded-lg border border-saffron/25 bg-saffron/[0.06] p-2.5 font-mono text-[10px] leading-relaxed text-saffron/90">
                {image.warning}
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Licence state is always visible, not just after generating. A
          non-commercial model producing brand assets is exactly the thing
          that must not slip past a stakeholder unnoticed. */}
      {(image || health?.image_licence) && (
        <div
          className={`mt-3 flex items-start gap-2 rounded-lg border p-2.5 ${
            nonCommercial
              ? "border-saffron/30 bg-saffron/[0.07]"
              : "border-signal/25 bg-signal/[0.05]"
          }`}
        >
          <ShieldAlert
            size={12}
            className={`mt-0.5 shrink-0 ${
              nonCommercial ? "text-saffron" : "text-signal"
            }`}
          />
          <p
            className={`font-mono text-[10px] leading-relaxed ${
              nonCommercial ? "text-saffron/90" : "text-signal/90"
            }`}
          >
            {image?.licence ?? health.image_licence}
            {nonCommercial &&
              " — switch IMAGE_MODEL to FLUX.1-schnell before any live use."}
          </p>
        </div>
      )}
    </div>
  );
}
