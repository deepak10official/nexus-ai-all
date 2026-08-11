import { motion } from "framer-motion";

const GLOW = {
  none: "",
  amber: "shadow-glow-amber",
  emerald: "shadow-glow-emerald border-neon-emerald/30",
  rose: "shadow-glow-rose border-neon-rose/30",
};

/**
 * Frosted-glass container. Pass `hover` for the lift/glow interaction and
 * `glow` for a colored halo (used to tint approve/reject vote cards).
 */
export default function GlassCard({
  children,
  className = "",
  glow = "none",
  hover = false,
  as = "div",
  ...motionProps
}) {
  const MotionTag = motion[as] ?? motion.div;
  return (
    <MotionTag
      className={`glass ${hover ? "glass-hover" : ""} ${GLOW[glow] ?? ""} ${className}`}
      {...motionProps}
    >
      {children}
    </MotionTag>
  );
}
