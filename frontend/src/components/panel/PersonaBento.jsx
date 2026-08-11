import { motion } from "framer-motion";
import { MapPin } from "lucide-react";
import GlassCard from "../ui/GlassCard.jsx";


export default function PersonaBento({ personas }) {
  if (!personas?.length) return null;

  return (
    <section className="mx-auto max-w-7xl px-5 pt-12 sm:px-8">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="eyebrow">The panel</h2>
        <span className="font-mono text-[11px] text-zinc-600">
          {personas.length} synthetic reviewers
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {personas.map((p, i) => (
          <GlassCard
            key={p.id}
            hover
            className="p-4"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: i * 0.06 }}
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 text-2xl leading-none">{p.emoji}</span>
              <div className="min-w-0 flex-1">
                <div className="truncate font-display text-[15px] font-semibold text-white">
                  {p.name}
                </div>
                <div className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.14em] text-neon-orange/90">
                  {p.archetype}
                </div>
                {p.tagline && (
                  <p className="mt-2 text-xs leading-relaxed text-zinc-400">
                    {p.tagline}
                  </p>
                )}
                <div className="mt-3 flex items-center gap-1.5 text-xs text-zinc-600">
                  <MapPin className="h-3 w-3 shrink-0" />
                  <span className="truncate">{p.location}</span>
                </div>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>
    </section>
  );
}
