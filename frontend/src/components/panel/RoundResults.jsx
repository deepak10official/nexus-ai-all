import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { BadgeCheck, Gavel, ArrowDown } from "lucide-react";
import GlassCard from "../ui/GlassCard.jsx";
import Badge from "../ui/Badge.jsx";
import VoteCard from "./VoteCard.jsx";
import Tally from "./Tally.jsx";

const REVEAL_DELAY = 0.16; // seconds between each vote card revealing

function Round({ round, index, personaById, animate }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="mb-3 flex items-center gap-3">
        <h3 className="font-display text-lg font-semibold text-white">
          Round {index + 1}
        </h3>
        {round.passed ? (
          <Badge tone="emerald" icon={BadgeCheck}>
            Passed
          </Badge>
        ) : (
          <Badge tone="rose" icon={Gavel}>
            Failed
          </Badge>
        )}
      </div>

      <GlassCard className="mb-4 p-4">
        <div className="flex flex-col sm:flex-row items-start gap-4">
          <div className="flex-1">
            <div className="eyebrow mb-1.5">Post under review</div>
            <p className="text-[15px] leading-relaxed text-zinc-200">{round.post}</p>
          </div>
          {round.image_url && (
            <div className="shrink-0">
              <div className="eyebrow mb-1.5">Attached Image</div>
              <img
                src={round.image_url}
                alt="Post attachment"
                className="h-24 w-36 rounded-lg border border-white/10 object-cover shadow-sm"
              />
            </div>
          )}
        </div>
      </GlassCard>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {round.votes.map((vote, i) => (
          <VoteCard
            key={`${vote.persona_id}-${i}`}
            vote={vote}
            persona={personaById[vote.persona_id]}
            index={i}
            animate={animate}
            revealDelay={REVEAL_DELAY}
          />
        ))}
      </div>

      <Tally
        approve={round.approve_count}
        reject={round.reject_count}
        threshold={round.threshold}
        passed={round.passed}
      />
    </motion.div>
  );
}

export default function RoundResults({ rounds, personas, revealKey }) {
  const personaById = Object.fromEntries((personas ?? []).map((p) => [p.id, p]));
  const lastIndex = rounds.length - 1;
  const latestRef = useRef(null);

  // Bring the newest round into view so a re-run never looks like "nothing
  // happened" just because the result rendered below the fold.
  useEffect(() => {
    if (!latestRef.current || rounds.length === 0) return;
    const id = window.setTimeout(() => {
      latestRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 120);
    return () => window.clearTimeout(id);
  }, [rounds.length, revealKey]);

  return (
    <section className="mx-auto max-w-7xl px-5 pt-12 sm:px-8">
      <div className="mb-5 flex items-baseline justify-between">
        <h2 className="eyebrow">Deliberation</h2>
        <span className="font-mono text-[11px] text-zinc-600">
          {rounds.length} {rounds.length === 1 ? "round" : "rounds"}
        </span>
      </div>
      <div className="space-y-8">
        {rounds.map((round, idx) => {
          const isLast = idx === lastIndex;
          // Stable key for prior rounds; the newest round remounts on each run
          // (revealKey bump) so its staggered vote reveal replays.
          const key = isLast ? `last-${revealKey}` : `round-${idx}`;
          return (
            <div key={key} ref={isLast ? latestRef : null} className="scroll-mt-24">
              <Round
                round={round}
                index={idx}
                personaById={personaById}
                // Only the newest round animates its reveal, keyed on revealKey
                // so re-runs re-trigger the stagger.
                animate={isLast}
              />
              {!isLast ? (
                <div className="mt-6 flex items-center justify-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-600">
                  <ArrowDown className="h-3.5 w-3.5" />
                  Next iteration
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
