import { useState } from "react";
import { motion } from "framer-motion";
import { PartyPopper, Gavel, CalendarDays, Check, Loader2 } from "lucide-react";

export default function OutcomeBanner({ round, roundNumber, onSendToCalendar, sentToCalendar }) {
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
        <div className="flex-1">
          <div className="font-display text-base font-semibold text-white">
            {passed
              ? `Round ${roundNumber} passed with ${round.tally}.`
              : `Round ${roundNumber} did not pass (${round.tally}).`}
          </div>
          <p className="mt-0.5 text-sm text-zinc-400">
            {passed
              ? "The panel approved this draft. It's ready to schedule."
              : "Rework the post to fold in the panel's feedback, then run it again."}
          </p>

          {/* Send to Calendar button — only shown when the round passed */}
          {passed && onSendToCalendar && (
            <motion.button
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              onClick={onSendToCalendar}
              disabled={sentToCalendar}
              className={`mt-3 flex items-center gap-2 rounded-xl px-4 py-2.5 font-display text-sm font-medium transition-all ${
                sentToCalendar
                  ? "border border-signal/30 bg-signal/[0.08] text-signal cursor-default"
                  : "bg-gradient-to-r from-signal to-[#7DD3FC] text-ink-900 shadow-[0_0_24px_-6px_rgba(53,224,216,0.4)] hover:shadow-[0_0_32px_-6px_rgba(53,224,216,0.6)]"
              }`}
            >
              {sentToCalendar ? (
                <>
                  <Check size={15} />
                  Sent to Calendar
                </>
              ) : (
                <>
                  <CalendarDays size={15} />
                  Schedule in Calendar →
                </>
              )}
            </motion.button>
          )}
        </div>
      </motion.div>
    </section>
  );
}
