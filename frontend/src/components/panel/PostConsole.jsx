import { useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Play,
  Wand2,
  FilePlus2,
  Loader2,
  Lightbulb,
  TriangleAlert,
  ImagePlus,
  X,
  Image as ImageIcon,
  FileText,
  Check,
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
  image,
  imageUploading,
  onUploadImage,
  onRemoveImage,
  validateText = true,
  setValidateText,
  validateImage = true,
  setValidateImage,
}) {
  const fileRef = useRef(null);

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) onUploadImage?.(file);
    if (fileRef.current) fileRef.current.value = "";
  }

  function handleDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      onUploadImage?.(file);
    }
  }

  return (
    <section className="mx-auto max-w-7xl px-5 pt-12 sm:px-8">
      <GlassCard
        className="p-5 sm:p-6"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header with character count and validation target checkboxes */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-white/8 pb-3">
          <div>
            <h2 className="eyebrow">Draft under review</h2>
            <p className="mt-0.5 text-xs text-zinc-500">
              Choose what to validate: Text, Image, or Both
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Text checkbox */}
            <label
              className={`flex cursor-pointer select-none items-center gap-2 rounded-xl border px-3.5 py-1.5 text-xs font-medium transition ${
                validateText
                  ? "border-neon-orange/40 bg-neon-orange/12 text-amber-200 shadow-glow-amber-sm"
                  : "border-white/10 bg-white/[0.03] text-zinc-500 hover:border-white/20 hover:text-zinc-300"
              }`}
            >
              <input
                type="checkbox"
                checked={validateText}
                onChange={(e) => setValidateText?.(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-white/20 bg-ink-800 text-neon-orange accent-neon-orange focus:ring-0 focus:ring-offset-0"
              />
              <FileText className={`h-3.5 w-3.5 ${validateText ? "text-neon-orange" : "text-zinc-500"}`} />
              <span>Text</span>
            </label>

            {/* Image checkbox */}
            <label
              className={`flex cursor-pointer select-none items-center gap-2 rounded-xl border px-3.5 py-1.5 text-xs font-medium transition ${
                validateImage
                  ? "border-neon-orange/40 bg-neon-orange/12 text-amber-200 shadow-glow-amber-sm"
                  : "border-white/10 bg-white/[0.03] text-zinc-500 hover:border-white/20 hover:text-zinc-300"
              }`}
            >
              <input
                type="checkbox"
                checked={validateImage}
                onChange={(e) => setValidateImage?.(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-white/20 bg-ink-800 text-neon-orange accent-neon-orange focus:ring-0 focus:ring-offset-0"
              />
              <ImageIcon className={`h-3.5 w-3.5 ${validateImage ? "text-neon-orange" : "text-zinc-500"}`} />
              <span>Image</span>
            </label>
          </div>
        </div>

        {/* Text editor (disabled/dimmed when Text checkbox is unchecked) */}
        <div className={`transition-opacity ${validateText ? "opacity-100" : "opacity-40"}`}>
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-[11px] text-zinc-500">
              {validateText ? "Post Copy" : "Post Copy (Validation disabled)"}
            </span>
            <span className="font-mono text-[11px] text-zinc-600">
              {post.trim().length} characters
            </span>
          </div>
          <textarea
            value={post}
            onChange={(e) => setPost(e.target.value)}
            rows={validateText ? 5 : 3}
            spellCheck={false}
            placeholder={
              validateText
                ? "Paste the financial post copy you want the panel to judge…"
                : "Text validation is unchecked. The panel will validate the image only."
            }
            className="w-full resize-y rounded-xl border border-white/10 bg-ink-800/60 p-4 text-[15px] leading-relaxed text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-neon-orange/40 focus:ring-2 focus:ring-neon-orange/20"
          />
        </div>

        {/* Image upload / preview */}
        <div className={`mt-3 transition-opacity ${validateImage ? "opacity-100" : "opacity-40"}`}>
          <AnimatePresence mode="wait">
            {imageUploading ? (
              <motion.div
                key="uploading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-zinc-400"
              >
                <Loader2 className="h-4 w-4 animate-spin text-neon-orange" />
                Uploading image…
              </motion.div>
            ) : image ? (
              <motion.div
                key="preview"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="relative overflow-hidden rounded-xl border border-white/10 bg-white/[0.03]"
              >
                <div className="flex items-start gap-3 p-3">
                  <img
                    src={image.url}
                    alt="Attached"
                    className="h-20 w-20 rounded-lg border border-white/10 object-cover"
                  />
                  <div className="flex-1 pt-1">
                    <div className="flex items-center gap-1.5 text-sm text-zinc-300">
                      <ImageIcon className="h-3.5 w-3.5 text-neon-orange" />
                      Image attached
                    </div>
                    <p className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zinc-500">
                      {validateImage
                        ? "Will be evaluated by persona agents via qwen/qwen3.8-27b"
                        : "Image attached but image validation is unchecked"}
                    </p>
                  </div>
                  <button
                    onClick={onRemoveImage}
                    disabled={loading}
                    className="grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-white/10 bg-white/[0.04] text-zinc-500 transition hover:border-neon-rose/30 hover:bg-neon-rose/10 hover:text-neon-rose disabled:opacity-40"
                    title="Remove image"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.button
                key="dropzone"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-white/12 bg-white/[0.02] px-4 py-3 text-sm text-zinc-500 transition hover:border-neon-orange/30 hover:bg-neon-orange/[0.04] hover:text-zinc-300 disabled:opacity-40"
              >
                <ImagePlus className="h-4 w-4" />
                Attach an image (optional) — drag & drop or click
              </motion.button>
            )}
          </AnimatePresence>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>

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
