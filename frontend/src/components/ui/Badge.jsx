const TONES = {
  neutral: "border-white/12 bg-white/5 text-zinc-300",
  emerald: "border-neon-emerald/30 bg-neon-emerald/10 text-neon-emerald",
  rose: "border-neon-rose/30 bg-neon-rose/10 text-neon-rose",
  amber: "border-neon-orange/30 bg-neon-orange/10 text-neon-orange",
  gray: "border-white/10 bg-white/[0.03] text-zinc-500",
};

export default function Badge({ children, tone = "neutral", icon: Icon, className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium tracking-wide ${TONES[tone]} ${className}`}
    >
      {Icon ? <Icon className="h-3.5 w-3.5" strokeWidth={2.2} /> : null}
      {children}
    </span>
  );
}
