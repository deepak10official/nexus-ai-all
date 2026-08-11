import { motion } from "framer-motion";
import { Users } from "lucide-react";

export default function EmptyState() {
  return (
    <section className="mx-auto max-w-7xl px-5 pt-12 sm:px-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="glass flex flex-col items-center gap-3 px-6 py-14 text-center"
      >
        <span className="grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/[0.04]">
          <Users className="h-6 w-6 text-neon-orange" />
        </span>
        <div className="font-display text-lg font-semibold text-white">
          Ready when you are
        </div>
        <p className="max-w-sm text-sm text-zinc-500">
          Paste a post above and run the panel to watch each persona cast a
          ballot in real time.
        </p>
      </motion.div>
    </section>
  );
}
