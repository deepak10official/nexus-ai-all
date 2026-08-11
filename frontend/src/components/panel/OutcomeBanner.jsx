import { motion } from "framer-motion";
import { PartyPopper, Gavel } from "lucide-react";

export default function OutcomeBanner({ round, roundNumber }) {
  if (!round) return null;
  const passed = round.passed;

  return (
    <section className="mx-auto max-w-7xl px-5 pt-8 sm:px-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className={`flex items-start gap-3 rounded-2xl border p-4 sm:p-5 ${
          passed
            ? "border-neon-emerald/30 bg-neon-emerald/8 shadow-glow-emerald"
            : "border-neon-rose/30 bg-neon-rose/8 shadow-glow-rose"
        }`}
      >
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
              ? "The panel approved this draft. It's ready to hand off."
              : "Rework the post to fold in the panel's feedback, then run it again."}
          </p>
        </div>
      </motion.div>
    </section>
  );
}
