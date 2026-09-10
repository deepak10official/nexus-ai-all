import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  Clock,
  Download,
  Image as ImageIcon,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  Type,
} from "lucide-react";
import * as api from "../../api/radarApi.js";
import PostPreview from "./PostPreview.jsx";
import ReviewControls from "./ReviewControls.jsx";
import ScoreDial from "./ScoreDial.jsx";

/** Internal band enums -> language a stakeholder reads without a glossary. */
const ACTION_TEXT = {
  AUTO_DRAFT: "Auto-draft",
  HUMAN_REVIEW: "Needs review",
  MONITOR: "Monitor",
  IGNORE: "Below threshold",
  BLOCKED: "Off-limits",
};

/**
 * Human review.
 *
 * The post and the image are reviewed independently, because in practice
 * one is often fine while the other is not — and forcing a reviewer to
 * reroll both wastes a model call and throws away work that was already
 * good.
 *
 * "Review or Edit" opens an inline editor rather than immediately
 * regenerating. A reviewer who wants one word changed should not have to
 * spend a generation and gamble the rest of the draft on it. Regenerate
 * is available inside that editor for when a reroll genuinely is what
 * you want.
 *
 * Final approval unlocks only once both halves are approved.
 */

function EditBox({
  value,
  onChange,
  onSave,
  onCancel,
  onRegenerate,
  saving,
  regenerating,
  regenLabel,
  hint,
  rows = 4,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-2 rounded-xl border border-violet/25 bg-violet/[0.05] p-3">
        <p className="eyebrow mb-2 text-violet">{hint}</p>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={rows}
          dir="auto"
          className="intl w-full resize-y rounded-lg border border-white/10 bg-ink-900/70 p-2.5 text-[13px] leading-relaxed text-chalk outline-none focus:border-violet/50"
        />
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onSave}
            disabled={saving || regenerating}
            className="flex items-center gap-1.5 rounded-lg border border-violet/40 bg-violet/15 px-3 py-1.5 font-display text-[12px] text-violet transition-colors hover:bg-violet/25 disabled:opacity-40"
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : null}
            Save edit
          </button>
          <button
            type="button"
            onClick={onRegenerate}
            disabled={saving || regenerating}
            className="flex items-center gap-1.5 rounded-lg border border-white/12 bg-white/[0.04] px-3 py-1.5 font-display text-[12px] text-chalk/80 transition-colors hover:bg-white/[0.09] disabled:opacity-40"
          >
            {regenerating ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <RefreshCw size={12} />
            )}
            {regenLabel}
          </button>
          <button
            type="button"
            onClick={onCancel}
            disabled={saving || regenerating}
            className="rounded-lg px-3 py-1.5 font-display text-[12px] text-muted transition-colors hover:text-chalk disabled:opacity-40"
          >
            Cancel
          </button>
        </div>
      </div>
    </motion.div>
  );
}

function ErrorNote({ children }) {
  return (
    <div className="mt-2 flex gap-2 rounded-xl border border-[#F2536D]/30 bg-[#F2536D]/[0.07] p-3">
      <AlertTriangle size={14} className="mt-0.5 shrink-0 text-[#F2536D]" />
      <p className="intl-mono text-[11px] leading-relaxed text-[#FFB3C1]">
        {children}
      </p>
    </div>
  );
}

export default function DraftPanel({
  selected,
  draft,
  setDraft,
  generating,
  error,
  onGenerate,
  health,
  onHandoff,
}) {
  const [image, setImage] = useState(null);
  const [imageBusy, setImageBusy] = useState(false);
  const [imageError, setImageError] = useState(null);
  const [actionError, setActionError] = useState(null);

  const [postStatus, setPostStatus] = useState("pending");
  const [imageStatus, setImageStatus] = useState("pending");
  const [sentToPanel, setSentToPanel] = useState(false);
  const [finalDecision, setFinalDecision] = useState(null);

  const [editingPost, setEditingPost] = useState(false);
  const [editingImage, setEditingImage] = useState(false);
  const [postDraftText, setPostDraftText] = useState("");
  const [briefText, setBriefText] = useState("");
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);

  // A new draft resets every review decision. Carrying an approval across
  // regenerations would let unreviewed copy inherit a previous approval.
  useEffect(() => {
    setImage(null);
    setImageError(null);
    setActionError(null);
    setPostStatus("pending");
    setImageStatus("pending");
    setSentToPanel(false);
    setFinalDecision(null);
    setEditingPost(false);
    setEditingImage(false);
  }, [draft?.draft_id]);

  if (!selected) {
    return (
      <div className="glass grid h-full min-h-[420px] place-items-center p-10 text-center">
        <div>
          <div className="relative mx-auto mb-5 grid h-14 w-14 place-items-center">
            <span className="absolute inset-0 animate-pulseRing rounded-full border border-signal/40" />
            <Sparkles size={22} className="text-signal" />
          </div>
          <h3 className="font-display text-lg text-chalk">
            Pick a trend to draft against
          </h3>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted">
            Anything scoring 60 or above is eligible. Blocked and
            below-threshold trends cannot be selected.
          </p>
        </div>
      </div>
    );
  }

  async function makeImage(overrideBrief = null) {
    setImageBusy(true);
    setImageError(null);
    try {
      const res = await api.makeImage(draft.draft_id, overrideBrief);
      setImage(res);
      setImageStatus("pending"); // a new image needs reviewing again
    } catch (e) {
      setImageError(e.message);
    } finally {
      setImageBusy(false);
    }
  }

  async function savePostEdit() {
    setSaving(true);
    try {
      const updated = await api.editDraft(draft.draft_id, {
        post_text: postDraftText,
      });
      setDraft(updated);
      setEditingPost(false);
      setPostStatus("pending");
      // The wording changed, so anything already sent to the panel is stale.
      setSentToPanel(false);
    } catch (e) {
      setActionError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function saveBriefEdit() {
    setSaving(true);
    try {
      const updated = await api.editDraft(draft.draft_id, {
        image_prompt: briefText,
      });
      setDraft(updated);
      setEditingImage(false);
    } catch (e) {
      setActionError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function record(action, target) {
    setBusy(true);
    setActionError(null);
    try {
      const res = await api.decide(draft.draft_id, action, target);
      if (target === "post") {
        setPostStatus(action === "approve" ? "approved" : "rejected");
        if (action === "reject") setSentToPanel(false);
      }
      if (target === "image") setImageStatus(action === "approve" ? "approved" : "rejected");
      if (target === "final") setFinalDecision(res);

      // Approved copy is what the Persona Panel validates, so send the wording
      // (and approved image if available) over to MOD02 as soon as approved.
      // Approving the copy loads the draft without stealing focus; the final
      // approval ends the MOD03 flow, so that one switches the view.
      if (action === "approve" && (target === "post" || target === "final" || target === "image") && onHandoff) {
        const isImgApproved = target === "image" ? action === "approve" : imageStatus === "approved";
        onHandoff({
          draft_id: draft.draft_id,
          post: draft.post.post_text,
          hashtags: draft.post.hashtags ?? [],
          image_url: isImgApproved && image?.url ? image.url : null,
          switchTo: target === "final",
        });
        setSentToPanel(true);
      }
    } catch (e) {
      setActionError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const bothApproved = postStatus === "approved" && imageStatus === "approved";

  return (
    <div className="glass flex h-full flex-col p-6">
      {/* Signal header */}
      <div className="flex items-start gap-5">
        <ScoreDial score={selected.score} band={selected.band} size={104} />
        <div className="min-w-0 flex-1 pt-1">
          <p className="eyebrow">Selected signal</p>
          <h2
            lang={selected.language}
            dir="auto"
            className="intl mt-1 break-words text-2xl font-bold text-chalk"
          >
            {selected.name}
          </h2>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <span className="rounded-md border border-white/12 bg-white/[0.04] px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-wider text-chalk/70">
              {selected.category}
            </span>
            <span className="rounded-md border border-violet/30 bg-violet/10 px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-wider text-violet">
              {selected.language_label}
            </span>
            <span className="rounded-md border border-white/12 bg-white/[0.04] px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-wider text-chalk/70">
              {ACTION_TEXT[selected.action] ?? selected.action} ·{" "}
              {selected.band_range}
            </span>
          </div>
        </div>
      </div>

      {!draft && (
        <motion.button
          type="button"
          onClick={onGenerate}
          disabled={generating}
          whileHover={{ scale: generating ? 1 : 1.015 }}
          whileTap={{ scale: generating ? 1 : 0.985 }}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-saffron to-[#FF6B9D] py-3 font-display text-sm font-medium text-ink-900 shadow-[0_0_28px_-6px_rgba(255,154,60,0.6)] disabled:opacity-60"
        >
          {generating ? (
            <>
              <Loader2 size={15} className="animate-spin" /> Drafting…
            </>
          ) : (
            <>
              <Sparkles size={15} /> Generate draft
            </>
          )}
        </motion.button>
      )}

      {error && <ErrorNote>{error}</ErrorNote>}

      {draft && (
        <div className="mt-5 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
          {/* ── The preview: copy and image, as a reader sees them ── */}
          <PostPreview
            draft={draft}
            image={image}
            postStatus={postStatus}
            imageStatus={imageStatus}
            imageBusy={imageBusy}
          />

          {/* ── Post review ── */}
          <ReviewControls
            label={
              <span className="flex items-center gap-1.5">
                <Type size={11} /> Post copy
              </span>
            }
            status={postStatus}
            busy={busy || generating}
            editing={editingPost}
            approveText="Approve"
            editText="Review / Edit"
            rejectText="Reject"
            onApprove={() => record("approve", "post")}
            onReject={() => record("reject", "post")}
            onEdit={() => {
              setPostDraftText(draft.post.post_text);
              setEditingPost((v) => !v);
              setEditingImage(false);
            }}
          />

          {/* Confirms the wording reached MOD02, so the handoff is not silent. */}
          <AnimatePresence>
            {sentToPanel && (
              <motion.button
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                onClick={() => onHandoff?.({
                  draft_id: draft.draft_id,
                  post: draft.post.post_text,
                  hashtags: draft.post.hashtags ?? [],
                  switchTo: true,
                })}
                className="group flex w-full items-center justify-between gap-2 rounded-xl border border-signal/30 bg-signal/[0.07] px-3 py-2.5 text-left transition hover:border-signal/50 hover:bg-signal/[0.12]"
              >
                <span className="flex items-center gap-2 text-xs text-signal">
                  <Check size={13} />
                  Sent to the Persona Panel for validation
                </span>
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted transition group-hover:text-chalk">
                  Run panel →
                </span>
              </motion.button>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {editingPost && (
              <EditBox
                hint="Edit the copy directly, or create a new version. The image is untouched either way."
                value={postDraftText}
                onChange={setPostDraftText}
                onSave={savePostEdit}
                onCancel={() => setEditingPost(false)}
                onRegenerate={() => {
                  setEditingPost(false);
                  onGenerate();
                }}
                saving={saving}
                regenerating={generating}
                regenLabel="New version"
                rows={4}
              />
            )}
          </AnimatePresence>

          {/* ── Image review ── */}
          {!image && !imageBusy ? (
            <motion.button
              type="button"
              onClick={() => makeImage()}
              disabled={!health?.image_configured}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-violet/35 bg-violet/[0.09] py-2.5 font-display text-[13px] text-violet transition-colors hover:bg-violet/20 disabled:opacity-40"
            >
              <ImageIcon size={14} />
              {health?.image_configured
                ? "Generate image"
                : "Image generation unavailable"}
            </motion.button>
          ) : (
            <ReviewControls
              label={
                <span className="flex items-center gap-1.5">
                  <ImageIcon size={11} /> Image
                </span>
              }
              status={imageStatus}
              busy={busy || imageBusy}
              disabled={!image}
              editing={editingImage}
              approveText="Approve"
              editText="Review / Edit"
              rejectText="Reject"
              onApprove={() => record("approve", "image")}
              onReject={() => record("reject", "image")}
              onEdit={() => {
                setBriefText(draft.post.image_prompt ?? "");
                setEditingImage((v) => !v);
                setEditingPost(false);
              }}
            />
          )}

          <AnimatePresence>
            {editingImage && (
              <EditBox
                hint="Edit the visual direction, then create a new image. The copy is untouched."
                value={briefText}
                onChange={setBriefText}
                onSave={saveBriefEdit}
                onCancel={() => setEditingImage(false)}
                onRegenerate={async () => {
                  await api
                    .editDraft(draft.draft_id, { image_prompt: briefText })
                    .then(setDraft)
                    .catch(() => {});
                  setEditingImage(false);
                  makeImage(briefText);
                }}
                saving={saving}
                regenerating={imageBusy}
                regenLabel="New image"
                rows={5}
              />
            )}
          </AnimatePresence>

          {imageError && <ErrorNote>{imageError}</ErrorNote>}
          {actionError && <ErrorNote>{actionError}</ErrorNote>}

          {image && (
            <div className="flex items-center justify-between font-mono text-[10px] text-muted">
              <span>
                {image.width}×{image.height} · generated in{" "}
                {(image.latency_ms / 1000).toFixed(1)}s
              </span>
              <a
                href={image.url}
                download={image.filename}
                className="flex items-center gap-1 transition-colors hover:text-chalk"
              >
                <Download size={10} /> download
              </a>
            </div>
          )}

          {image?.removed_from_brief?.length > 0 && (
            <p className="rounded-lg border border-saffron/25 bg-saffron/[0.06] p-2.5 font-mono text-[10px] leading-relaxed text-saffron/90">
              Removed from the brief before generating: “
              {image.removed_from_brief.join(" ")}” — requested wording is
              applied as a branded overlay instead, so it is always correct.
            </p>
          )}

          {/* ── Final approval ── */}
          <div className="mt-1 rounded-xl border border-white/[0.09] bg-white/[0.02] p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="eyebrow">Final approval</p>
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted">
                {postStatus === "approved" ? "copy ✓" : "copy —"} ·{" "}
                {imageStatus === "approved" ? "image ✓" : "image —"}
              </span>
            </div>

            {finalDecision ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`rounded-lg border p-3 ${
                  finalDecision.action === "approve"
                    ? "border-signal/35 bg-signal/[0.07]"
                    : "border-white/12 bg-white/[0.03]"
                }`}
              >
                <p className="font-display text-[13px] text-chalk">
                  {finalDecision.action === "approve"
                    ? "Approved for publishing"
                    : "Draft rejected"}
                </p>
                <p className="mt-1 text-[11px] leading-relaxed text-muted">
                  {finalDecision.message}
                </p>

                <p className="mt-2 text-[11px] leading-relaxed text-muted">
                  Sent to the Persona Panel. Publishing happens there, once the
                  personas have approved it.
                </p>
              </motion.div>
            ) : (
              <>
                <motion.button
                  type="button"
                  onClick={() => record("approve", "final")}
                  disabled={!bothApproved || busy}
                  whileHover={bothApproved ? { scale: 1.01 } : {}}
                  whileTap={bothApproved ? { scale: 0.99 } : {}}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-signal to-[#7DD3FC] py-2.5 font-display text-[13px] font-medium text-ink-900 transition-opacity disabled:cursor-not-allowed disabled:opacity-30"
                >
                  <Send size={14} /> Approve full post
                </motion.button>
                {!bothApproved && (
                  <p className="mt-1.5 text-center text-[10px] text-muted">
                    Approve both the copy and the image to unlock
                  </p>
                )}
              </>
            )}
          </div>

          <div className="flex items-center gap-3 font-mono text-[10px] text-muted">
            <span className="flex items-center gap-1.5">
              <Clock size={11} /> 15-minute approval window
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
