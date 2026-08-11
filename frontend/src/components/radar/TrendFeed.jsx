import { motion } from "framer-motion";
import { Ban, Radio, ShieldAlert, TrendingUp } from "lucide-react";
import { BAND_COLOR } from "./ScoreDial.jsx";

/** Action label per band — what the pipeline DOES, not just what it is. */
const ACTION_LABEL = {
  AUTO_DRAFT: "Auto-draft",
  HUMAN_REVIEW: "Human review",
  MONITOR: "Monitor only",
  IGNORE: "Ignore",
  BLOCKED: "Off-limits",
};

/** One accent per topic category so the feed is scannable by colour. */
const CATEGORY_COLOR = {
  finance: "#35E0D8",
  tech: "#7DD3FC",
  sport: "#86EFAC",
  ent: "#F0ABFC",
  pol: "#FCA5A5",
  gov: "#FDBA74",
  health: "#5EEAD4",
  edu: "#C4B5FD",
  rel: "#FDE68A",
  news: "#94A3B8",
  other: "#64748B",
};

/**
 * The scorer emits a debug-style rationale ("payments:upi, +8 across 2
 * categories, +5 joinable hashtag"). Useful internally, meaningless to a
 * stakeholder. Translate it into a plain reason, keeping the raw string
 * on the tooltip for anyone who wants the detail.
 */
function readableReason(trend) {
  const r = trend.rationale ?? "";

  if (trend.band === "blocked") {
    const cat = {
      political: "Political topic — excluded by policy",
      religious: "Religious topic — excluded by policy",
      protest: "Protest or agitation — excluded by policy",
      security: "National security topic — excluded by policy",
      competitor: "Mentions a competitor — excluded by policy",
    };
    return cat[trend.blocked_reason] ?? "Excluded by brand policy";
  }

  if (r.includes("no BBPS-adjacent")) {
    return r.includes("off-territory")
      ? "Not related to payments — entertainment or sport"
      : "Not related to bill payments";
  }

  const themes = [];
  if (/core:/.test(r)) themes.push("bill payments");
  if (/payments:/.test(r)) themes.push("digital payments");
  if (/digital-india:/.test(r)) themes.push("digital India");
  if (/finance:/.test(r)) themes.push("everyday finance");
  if (/india-context:/.test(r) && themes.length === 0) themes.push("India");

  // Sector adjacency: relevant by topic area rather than by keyword.
  // Only stated when nothing more specific matched, so a payments trend
  // still reads as payments rather than as a whole sector.
  if (themes.length === 0 && /sector:business/.test(r)) {
    return "Business and finance — adjacent to Bharat Connect";
  }
  if (themes.length === 0 && /sector:technology/.test(r)) {
    return "Technology — adjacent to Bharat Connect";
  }

  if (themes.length === 0) return "Weak connection to Bharat Connect";

  const list =
    themes.length === 1
      ? themes[0]
      : themes.slice(0, -1).join(", ") + " and " + themes[themes.length - 1];
  return `Relates to ${list}`;
}

function Chip({ label, color, title }) {
  return (
    <span
      title={title}
      className="rounded-md border px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-wider"
      style={{ color, borderColor: `${color}38`, background: `${color}10` }}
    >
      {label}
    </span>
  );
}

function TrendRow({ trend, index, selected, onSelect }) {
  const disabled = trend.band === "blocked" || trend.band === "ignore";
  const bandColor = BAND_COLOR[trend.band];
  const catColor = CATEGORY_COLOR[trend.category_key] ?? CATEGORY_COLOR.other;
  const showLang = trend.script !== "Latin" || trend.language !== "en";

  return (
    <motion.button
      type="button"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.45), duration: 0.4 }}
      whileHover={disabled ? {} : { scale: 1.012 }}
      whileTap={disabled ? {} : { scale: 0.995 }}
      onClick={() => !disabled && onSelect(trend)}
      disabled={disabled}
      aria-pressed={selected}
      className={`group flex w-full items-start gap-3 rounded-xl border p-3 text-left transition-all duration-300
        ${
          selected
            ? "border-signal/50 bg-signal/[0.07]"
            : "border-white/[0.07] bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.05]"
        }
        ${disabled ? "cursor-not-allowed opacity-45" : "cursor-pointer"}`}
    >
      {/* BBPS Relevance Score — always visible, always the first thing read */}
      <span
        className="grid h-11 w-11 shrink-0 place-items-center rounded-lg"
        style={{
          background: `${bandColor}14`,
          boxShadow: selected ? `0 0 16px ${bandColor}55` : "none",
        }}
      >
        <span
          className="font-mono text-sm font-bold leading-none"
          style={{ color: bandColor }}
        >
          {trend.score}
        </span>
        <span className="mt-[2px] font-mono text-[7px] text-muted">/100</span>
      </span>

      <span className="min-w-0 flex-1">
        {/* lang + dir let the browser shape Devanagari correctly */}
        <span className="flex items-center gap-2">
          <span
            lang={trend.language}
            dir="auto"
            className="intl truncate text-[15px] font-medium text-chalk"
          >
            {trend.name}
          </span>
          {trend.blocked_reason && (
            <Ban size={13} className="shrink-0 text-[#F2536D]" />
          )}
        </span>

        <span className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <Chip label={trend.category} color={catColor} title="Topic category" />
          {showLang && (
            <Chip
              label={trend.language_label}
              color="#A78BFA"
              title={`Script: ${trend.script}${
                trend.language_confidence === "low"
                  ? " — heuristic guess, low confidence"
                  : ""
              }`}
            />
          )}
          <Chip
            label={ACTION_LABEL[trend.action]}
            color={bandColor}
            title={`Score band ${trend.band_range}`}
          />
        </span>

        <span
          title={trend.rationale}
          className="intl mt-1 block truncate text-[10px] text-muted"
        >
          {readableReason(trend)}
        </span>
      </span>
    </motion.button>
  );
}

export default function TrendFeed({ feed, selected, onSelect, loading }) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 7 }).map((_, i) => (
          <div
            key={i}
            className="h-[78px] animate-pulse rounded-xl bg-white/[0.035]"
            style={{ animationDelay: `${i * 90}ms` }}
          />
        ))}
      </div>
    );
  }

  if (!feed?.trends?.length) {
    return (
      <div className="grid place-items-center rounded-xl border border-dashed border-white/10 py-14 text-center">
        <Radio size={22} className="mb-3 text-muted" />
        <p className="font-display text-sm text-chalk">No signal yet</p>
        <p className="mt-1 max-w-xs text-xs text-muted">
          Run a scan to pull the current India trend list and score it.
        </p>
      </div>
    );
  }

  const drafts = feed.trends.filter((t) =>
    ["auto_draft", "review"].includes(t.band)
  );
  const rest = feed.trends.filter(
    (t) => !["auto_draft", "review"].includes(t.band)
  );

  // Category spread — shows stakeholders what India is actually talking
  // about, and therefore why so little of it is payments-adjacent.
  const spread = feed.trends.reduce((acc, t) => {
    acc[t.category] = (acc[t.category] || 0) + 1;
    return acc;
  }, {});
  const topCategories = Object.entries(spread)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-1.5 rounded-xl border border-white/[0.07] bg-white/[0.02] p-2.5">
        <span className="eyebrow mr-1 self-center">Topics</span>
        {topCategories.map(([label, n]) => (
          <span
            key={label}
            className="rounded-md bg-white/[0.04] px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-wider text-muted"
          >
            {label} {n}
          </span>
        ))}
      </div>

      <section>
        <div className="mb-2.5 flex items-center gap-2">
          <TrendingUp size={13} className="text-signal" />
          <h3 className="eyebrow">Actionable — {drafts.length}</h3>
        </div>
        <div className="space-y-2">
          {drafts.length === 0 && (
            <p className="rounded-xl border border-dashed border-white/10 p-4 text-xs text-muted">
              Nothing scored high enough this cycle. That is a normal
              outcome — most trends are not related to bill payments.
            </p>
          )}
          {drafts.map((t, i) => (
            <TrendRow
              key={t.name}
              trend={t}
              index={i}
              selected={selected?.name === t.name}
              onSelect={onSelect}
            />
          ))}
        </div>
      </section>

      <section>
        <div className="mb-2.5 flex items-center gap-2">
          <ShieldAlert size={13} className="text-muted" />
          <h3 className="eyebrow">Filtered out — {rest.length}</h3>
        </div>
        <div className="space-y-2">
          {rest.map((t, i) => (
            <TrendRow
              key={t.name}
              trend={t}
              index={i}
              selected={false}
              onSelect={onSelect}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

export { CATEGORY_COLOR, ACTION_LABEL };
