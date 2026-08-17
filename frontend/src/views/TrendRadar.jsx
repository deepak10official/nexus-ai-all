import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Database,
  HelpCircle,
  FlaskConical,
  Radar,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import * as api from "../api/radarApi.js";
import TrendFeed from "../components/radar/TrendFeed.jsx";
import DraftPanel from "../components/radar/DraftPanel.jsx";

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.6, ease: [0.16, 1, 0.3, 1] },
  }),
};

function Tile({ icon: Icon, label, value, hint, accent = "#35E0D8", i = 0 }) {
  const [open, setOpen] = useState(false);

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="show"
      custom={i}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      tabIndex={hint ? 0 : -1}
      className="glass glass-hover relative cursor-default p-4"
    >
      <div className="flex items-center gap-2">
        <Icon size={13} style={{ color: accent }} />
        <p className="eyebrow">{label}</p>
        {hint && (
          <HelpCircle
            size={11}
            className="ml-auto text-muted/50 transition-colors"
            style={{ color: open ? accent : undefined }}
          />
        )}
      </div>
      <p className="mt-2 truncate font-mono text-lg font-bold text-chalk">
        {value}
      </p>

      {/* Explanation on hover. Rendered above the tile so it never pushes
          the bento grid around, and kept keyboard-reachable so it is not
          mouse-only. */}
      <AnimatePresence>
        {hint && open && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: 0.16 }}
            role="tooltip"
            className="absolute bottom-[calc(100%+10px)] left-0 z-[100] w-[min(22rem,86vw)] rounded-xl border p-4"
            style={{
              // Near-opaque, not glass. A translucent tooltip over the
              // hero headline puts two layers of text on top of each
              // other and neither is readable.
              background: "#0B1020",
              borderColor: `${accent}55`,
              boxShadow: `0 18px 50px -12px rgba(0,0,0,0.95), 0 0 0 1px ${accent}20, 0 0 26px -8px ${accent}55`,
            }}
          >
            <p
              className="mb-1.5 font-display text-[13px] font-semibold"
              style={{ color: accent }}
            >
              {label}
            </p>
            <p className="text-[13px] leading-[1.55] text-chalk">{hint}</p>
            {/* Pointer down to the tile it belongs to */}
            <span
              className="absolute -bottom-[6px] left-6 h-3 w-3 rotate-45 border-b border-r"
              style={{ background: "#0B1020", borderColor: `${accent}55` }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function TrendRadar({ onHandoff }) {
  const [health, setHealth] = useState(null);
  const [feed, setFeed] = useState(null);
  const [loadingFeed, setLoadingFeed] = useState(false);
  const [feedError, setFeedError] = useState(null);

  const [selected, setSelected] = useState(null);
  const [draft, setDraft] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState(null);
  const [decision, setDecision] = useState(null);
  const [deciding, setDeciding] = useState(false);

  // Manual test input — score any hashtag, in the feed or not.
  const [manual, setManual] = useState("");
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    api.getHealth().then(setHealth).catch(() => setHealth(null));
    scan(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function scan(refresh = true) {
    setLoadingFeed(true);
    setFeedError(null);
    try {
      setFeed(await api.getTrends(refresh));
    } catch (e) {
      setFeedError(e.message);
      setFeed(null);
    } finally {
      setLoadingFeed(false);
    }
  }

  function select(trend) {
    setSelected(trend);
    setDraft(null);
    setDecision(null);
    setGenError(null);
  }

  async function testHashtag() {
    const name = manual.trim();
    if (!name) return;
    setTesting(true);
    setGenError(null);
    try {
      const scored = await api.evaluateOne(name);
      select({ ...scored, manual: true });
    } catch (e) {
      setGenError(e.message);
    } finally {
      setTesting(false);
    }
  }

  async function generate() {
    setGenerating(true);
    setGenError(null);
    setDecision(null);
    try {
      setDraft(await api.generate(selected.name, Boolean(selected.manual)));
    } catch (e) {
      setGenError(e.message);
      setDraft(null);
    } finally {
      setGenerating(false);
    }
  }


  const actionable =
    feed?.trends.filter((t) => ["auto_draft", "review"].includes(t.band))
      .length ?? 0;
  const blocked = feed?.trends.filter((t) => t.band === "blocked").length ?? 0;

  return (
    <div className="min-h-screen">
      {/* Sticky blurred nav */}
      <header className="z-40 border-b border-white/[0.07] bg-ink-900/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="relative grid h-8 w-8 place-items-center rounded-lg bg-signal/10">
              <span className="absolute inset-0 animate-pulseRing rounded-lg border border-signal/40" />
              <Radar size={16} className="text-signal" />
            </div>
            <div className="leading-tight">
              <p className="font-display text-sm font-bold tracking-tight text-chalk">
                Trend Radar
              </p>
              <p className="font-mono text-[10px] text-muted">
                Bharat Connect
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-1.5 font-mono text-[10px] text-muted sm:flex">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  health?.llm_configured ? "bg-signal" : "bg-[#F2536D]"
                }`}
              />
              {health?.llm_configured ? "System ready" : "Setup required"}
            </span>
            <button
              type="button"
              onClick={() => scan(true)}
              disabled={loadingFeed}
              className="flex items-center gap-2 rounded-lg border border-white/12 bg-white/[0.04] px-3.5 py-2 font-display text-xs text-chalk transition-colors hover:bg-white/[0.09] disabled:opacity-50"
            >
              <RefreshCw
                size={12}
                className={loadingFeed ? "animate-spin" : ""}
              />
              Scan now
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] px-6 pb-20">
        {/* Hero — the thesis: a scan is running, here is what it found */}
        <section className="pb-8 pt-14">
          <motion.p
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="eyebrow"
          >
            Reactive social · Bharat Connect · BBPS
          </motion.p>
          <motion.h1
            variants={fadeUp}
            initial="hidden"
            animate="show"
            custom={1}
            className="mt-3 max-w-3xl font-display text-4xl font-bold leading-[1.08] tracking-tight text-chalk sm:text-5xl"
          >
            India is talking.{" "}
            <span className="bg-gradient-to-r from-saffron via-[#FF6B9D] to-signal bg-clip-text text-transparent">
              Find the one thread
            </span>{" "}
            worth answering.
          </motion.h1>
          <motion.p
            variants={fadeUp}
            initial="hidden"
            animate="show"
            custom={2}
            className="mt-4 max-w-xl text-[15px] leading-relaxed text-muted"
          >
            Every scan pulls live X trends for India, scores each one against
            Bharat Connect, and drafts a post for the ones that earn it.
            Nothing publishes without a human saying so.
          </motion.p>
        </section>

        {/* Bento: stat strip */}
        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Tile
            icon={Activity}
            label="Trends scanned"
            value={feed?.trends.length ?? "—"}
            hint="Every trending topic pulled from X for India in this scan. Each one is scored against Bharat Connect before anything is drafted, so this is the full pool the system considered — not just the ones it acted on."
            i={0}
          />
          <Tile
            icon={Radar}
            label="Actionable"
            value={feed ? actionable : "—"}
            hint="Trends scoring 60 or above — relevant enough to Bharat Connect to be worth a post. These are the only ones you can draft against. Zero is a normal result: most of what India talks about has nothing to do with bill payments."
            accent="#FF9A3C"
            i={1}
          />
          <Tile
            icon={ShieldCheck}
            label="Blocked by policy"
            value={feed ? blocked : "—"}
            hint="Trends the brand will never post about — political, religious, protest, national-security or competitor topics. These are filtered out before scoring, so they are never drafted and never reach the writing step, whatever they score on relevance."
            accent="#F2536D"
            i={2}
          />
          <Tile
            icon={Database}
            label="Data freshness"
            value={feed ? (feed.tier === "live" ? "Current" : "Recent") : "—"}
            hint={
              feed?.tier === "live"
                ? "Current — these trends were pulled just now, in this scan."
                : "Recent — the live source could not be reached, so these are from the last successful scan. Press Scan now to retry. The timestamp below shows exactly how old they are."
            }
            accent="#A78BFA"
            i={3}
          />
        </section>

        {/* Honest labelling of data freshness */}
        {feed && (
          <p className="mt-3 font-mono text-[11px] text-muted">
            {feed.tier === "live" ? "Live scan" : "Last available scan"} ·
            India · {new Date(feed.fetched_at).toLocaleTimeString()}
          </p>
        )}

        {/* Scoring legend — the four bands, stated plainly. This is
            the panel stakeholders will point at when they ask "how does it
            decide?" */}
        <section className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["80-100", "Auto-draft", "Drafted immediately", "#35E0D8"],
            ["60-79", "Human review", "Drafted, flagged for review", "#FF9A3C"],
            ["40-59", "Monitor only", "Watched, no draft", "#A78BFA"],
            ["0-39", "Ignore", "Not processed further", "#4A5468"],
          ].map(([range, action, note, color], i) => (
            <motion.div
              key={range}
              variants={fadeUp}
              initial="hidden"
              animate="show"
              custom={i}
              className="rounded-xl border p-3"
              style={{ borderColor: `${color}30`, background: `${color}08` }}
            >
              <div className="flex items-baseline gap-2">
                <span
                  className="font-mono text-sm font-bold"
                  style={{ color }}
                >
                  {range}
                </span>
                <span className="font-display text-[13px] text-chalk">
                  {action}
                </span>
              </div>
              <p className="mt-1 text-[11px] leading-snug text-muted">{note}</p>
            </motion.div>
          ))}
        </section>

        {/* Bento: asymmetric two-column work area */}
        <section className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="show"
            custom={4}
            className="glass p-5"
          >
            <div className="mb-4 flex items-baseline justify-between">
              <h2 className="font-display text-lg font-bold text-chalk">
                Signal feed
              </h2>
              <span className="font-mono text-[10px] text-muted">
                sorted by relevance
              </span>
            </div>

            {/* Manual test bench — type any hashtag to score and draft it.
                Blocked terms are still refused; only the score threshold
                is bypassed. */}
            <div className="mb-4 rounded-xl border border-violet/25 bg-violet/[0.05] p-3">
              <div className="mb-2 flex items-center gap-2">
                <FlaskConical size={12} className="text-violet" />
                <p className="eyebrow text-violet">Test any hashtag</p>
              </div>
              <div className="flex gap-2">
                <input
                  value={manual}
                  onChange={(e) => setManual(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && testHashtag()}
                  placeholder="#DigitalIndiaAt10 or #बिजलीबिल"
                  lang="auto"
                  dir="auto"
                  className="intl-mono min-w-0 flex-1 rounded-lg border border-white/10 bg-ink-900/60 px-3 py-2 text-[12px] text-chalk placeholder:text-muted/60"
                />
                <button
                  type="button"
                  onClick={testHashtag}
                  disabled={testing || !manual.trim()}
                  className="shrink-0 rounded-lg border border-violet/40 bg-violet/15 px-3.5 py-2 font-display text-xs text-violet transition-colors hover:bg-violet/25 disabled:opacity-40"
                >
                  {testing ? "Scoring…" : "Score it"}
                </button>
              </div>
            </div>

            {feedError ? (
              <div className="rounded-xl border border-[#F2536D]/30 bg-[#F2536D]/[0.07] p-4">
                <p className="font-display text-sm text-chalk">
                  Trend fetch failed
                </p>
                <p className="mt-1.5 font-mono text-[11px] leading-relaxed text-[#FFB3C1]">
                  {feedError}
                </p>
              </div>
            ) : (
              <TrendFeed
                feed={feed}
                selected={selected}
                onSelect={select}
                loading={loadingFeed}
              />
            )}
          </motion.div>

          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="show"
            custom={5}
          >
            <DraftPanel
              selected={selected}
              draft={draft}
              setDraft={setDraft}
              generating={generating}
              error={genError}
              onGenerate={generate}
              health={health}
              onHandoff={onHandoff}
            />
          </motion.div>
        </section>
      </main>

      <footer className="border-t border-white/[0.07] py-8">
        <div className="mx-auto flex max-w-[1400px] flex-col gap-2 px-6 font-mono text-[11px] text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>Preview environment · nothing is published from here</p>
          <p>Approved posts continue to brand sign-off</p>
        </div>
      </footer>
    </div>
  );
}
