import { BadgeCheck, Heart, MessageCircle, Repeat2, Upload } from "lucide-react";

/**
 * The full post preview — copy and image rendered together the way X
 * would show them. This is the focus of the review panel: a reviewer
 * judges the post as a reader will see it, not as two separate assets.
 *
 * Status rings around each half show what has been approved without
 * splitting the preview apart, so the composition stays readable while
 * the review state stays legible.
 */

const RING = {
  approved: "ring-1 ring-signal/40",
  rejected: "ring-1 ring-[#F2536D]/40",
  pending: "",
};

function highlight(text) {
  // Hashtags and @handles render in the link colour, as on X. Splitting on
  // a capturing group keeps the delimiters in the output.
  return text.split(/(#[\p{L}\p{N}_]+|@[A-Za-z0-9_]+)/gu).map((part, i) =>
    part.startsWith("#") || part.startsWith("@") ? (
      <span key={i} className="text-[#7DD3FC]">
        {part}
      </span>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

function Action({ icon: Icon, count }) {
  return (
    <span className="flex items-center gap-1.5 text-muted/70">
      <Icon size={14} />
      <span className="font-mono text-[10px]">{count}</span>
    </span>
  );
}

export default function PostPreview({
  draft,
  image,
  postStatus = "pending",
  imageStatus = "pending",
  imageBusy = false,
}) {
  if (!draft) return null;

  const text = draft.post.post_text;
  // Hashtags already inside the copy should not be repeated underneath.
  const inline = new Set(
    (text.match(/#[\p{L}\p{N}_]+/gu) ?? []).map((h) => h.toLowerCase())
  );
  const extra = draft.post.hashtags.filter(
    (h) => !inline.has(h.toLowerCase())
  );

  return (
    <div className="rounded-2xl border border-white/10 bg-ink-800/70 p-5">
      {/* Account row */}
      <div className="flex items-center gap-2.5">
        <div className="h-10 w-10 shrink-0 rounded-full bg-gradient-to-br from-saffron via-[#FF6B9D] to-signal" />
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1 font-display text-[14px] font-medium text-chalk">
            Bharat Connect
            <BadgeCheck size={14} className="text-[#7DD3FC]" />
          </p>
          <p className="font-mono text-[10px] text-muted">
            @BharatConnect · draft
            {draft.edited && (
              <span className="ml-1.5 text-violet">· edited by reviewer</span>
            )}
          </p>
        </div>
      </div>

      {/* Copy */}
      <div className={`mt-3 rounded-xl ${RING[postStatus]}`}>
        <p
          lang={draft.language}
          dir="auto"
          className="intl whitespace-pre-wrap text-[15px] leading-relaxed text-chalk"
        >
          {highlight(text)}
        </p>

        {extra.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {extra.map((h) => (
              <span key={h} dir="auto" className="intl text-[14px] text-[#7DD3FC]">
                {h}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Image, inline as X renders it */}
      <div className="mt-3">
        {imageBusy ? (
          <div className="grid aspect-[16/9] w-full place-items-center rounded-2xl border border-white/10 bg-white/[0.03]">
            <div className="text-center">
              <div className="mx-auto mb-2 h-6 w-6 animate-spin rounded-full border-2 border-white/15 border-t-signal" />
              <p className="font-mono text-[10px] text-muted">
                generating image…
              </p>
            </div>
          </div>
        ) : image ? (
          <div
            className={`overflow-hidden rounded-2xl border border-white/10 ${RING[imageStatus]}`}
          >
            <img
              src={image.url}
              alt={`Visual for ${draft.hashtag}`}
              className="block w-full"
            />
          </div>
        ) : (
          <div className="grid aspect-[16/9] w-full place-items-center rounded-2xl border border-dashed border-white/12 bg-white/[0.015]">
            <p className="max-w-[16rem] text-center text-[11px] leading-relaxed text-muted">
              No image yet. Generate one below to see the complete post.
            </p>
          </div>
        )}
      </div>

      {/* Decorative action row — sells the preview as a real post */}
      <div className="mt-3 flex items-center gap-7 border-t border-white/[0.07] pt-3">
        <Action icon={MessageCircle} count="—" />
        <Action icon={Repeat2} count="—" />
        <Action icon={Heart} count="—" />
        <Action icon={Upload} count="" />
        <span className="ml-auto font-mono text-[10px] text-muted">
          {[...text].length} characters
        </span>
      </div>
    </div>
  );
}
