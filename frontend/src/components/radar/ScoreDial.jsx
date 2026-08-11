import { motion } from "framer-motion";

/**
 * The signature element: the BBPS Relevance Score drawn as a radar dial
 * rather than a progress bar. Concentric range rings mark the four MOD03
 * band thresholds, a sweep line rotates continuously, and the arc fills to
 * the score. Reads as an instrument, which is what "Trend Radar" implies.
 */

const BAND_COLOR = {
  auto_draft: "#35E0D8",
  review: "#FF9A3C",
  monitor: "#A78BFA",
  ignore: "#4A5468",
  blocked: "#F2536D",
};

export default function ScoreDial({ score = 0, band = "ignore", size = 132 }) {
  const stroke = 7;
  const r = (size - stroke * 2) / 2 - 6;
  const c = size / 2;
  const circumference = 2 * Math.PI * r;
  // Leave a 90° gap at the bottom so the dial reads as a gauge, not a donut.
  const arcFraction = 0.75;
  const filled = (score / 100) * arcFraction * circumference;
  const color = BAND_COLOR[band] ?? BAND_COLOR.ignore;

  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Relevance score ${score} out of 100, band ${band}`}
    >
      <svg width={size} height={size} className="-rotate-[225deg]">
        {/* Range rings at the band thresholds: 40 / 60 / 80 */}
        {[0.4, 0.6, 0.8].map((t) => (
          <circle
            key={t}
            cx={c}
            cy={c}
            r={r - 11}
            fill="none"
            stroke="rgba(255,255,255,0.07)"
            strokeWidth="1"
            strokeDasharray={`2 ${2 * Math.PI * (r - 11) * 0.02}`}
            style={{ opacity: t }}
          />
        ))}

        {/* Track */}
        <circle
          cx={c}
          cy={c}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcFraction * circumference} ${circumference}`}
        />

        {/* Score arc */}
        <motion.circle
          cx={c}
          cy={c}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          initial={{ strokeDasharray: `0 ${circumference}` }}
          animate={{ strokeDasharray: `${filled} ${circumference}` }}
          transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
          style={{ filter: `drop-shadow(0 0 7px ${color}88)` }}
        />
      </svg>

      {/* Sweep line — the radar tell */}
      <div className="absolute inset-0 grid place-items-center">
        <div
          className="animate-sweep"
          style={{ width: r * 2, height: r * 2, borderRadius: "50%" }}
        >
          <div
            className="h-1/2 w-px origin-bottom"
            style={{
              margin: "0 auto",
              background: `linear-gradient(to top, ${color}00, ${color}bb)`,
            }}
          />
        </div>
      </div>

      <div className="absolute inset-0 grid place-content-center text-center">
        <div
          className="font-mono text-3xl font-bold leading-none"
          style={{ color }}
        >
          {score}
        </div>
        <div className="eyebrow mt-1.5">/ 100</div>
      </div>
    </div>
  );
}

export { BAND_COLOR };
