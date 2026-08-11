import { motion } from "framer-motion";
import { Users, ShieldCheck, Sparkles } from "lucide-react";

function Stat({ icon: Icon, value, label }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid h-9 w-9 place-items-center rounded-xl border border-white/10 bg-white/[0.04]">
        <Icon className="h-4 w-4 text-neon-orange" strokeWidth={2.2} />
      </span>
      <div className="text-left leading-tight">
        <div className="font-display text-lg font-semibold text-white">{value}</div>
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
          {label}
        </div>
      </div>
    </div>
  );
}

export default function Hero({ settings }) {
  const threshold = settings?.approval_threshold ?? 3;
  const panelSize = settings?.panel_size ?? 5;

  return (
    <section className="mx-auto flex max-w-7xl flex-col items-center px-5 pt-12 text-center sm:px-8 sm:pt-16">
      <motion.p
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="eyebrow"
      >
        Synthetic panel · Bharat consumers · Human-in-the-loop
      </motion.p>

      <motion.h1
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.05 }}
        className="mt-4 max-w-3xl font-display text-4xl font-semibold leading-[1.05] tracking-tight text-white sm:text-6xl"
      >
        Five consumers. <span className="gradient-text">One verdict.</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.12 }}
        className="mt-4 max-w-2xl text-base leading-relaxed text-zinc-400 sm:text-lg"
      >
        Every financial post is judged by a panel of synthetic Indian
        consumers — from a cash-first retiree to a fintech power user. It needs{" "}
        <span className="font-semibold text-zinc-200">
          {threshold} of {panelSize}
        </span>{" "}
        approvals to pass. When it fails, rework it from their feedback and vote
        again. Nothing ships without the panel saying yes.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="mt-8 flex flex-wrap items-center justify-center gap-x-9 gap-y-4"
      >
        <Stat icon={Users} value={panelSize} label="Panelists" />
        <Stat icon={ShieldCheck} value={`${threshold}/${panelSize}`} label="Pass threshold" />
        <Stat icon={Sparkles} value="Live" label="Structured votes" />
      </motion.div>
    </section>
  );
}
