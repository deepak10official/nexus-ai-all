import { motion } from "framer-motion";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle2,
  Upload,
  ListTodo,
} from "lucide-react";

function Stat({ icon: Icon, value, label, accent = "#35E0D8" }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="grid h-9 w-9 place-items-center rounded-xl border border-white/10"
        style={{ background: `${accent}12` }}
      >
        <Icon className="h-4 w-4" style={{ color: accent }} strokeWidth={2.2} />
      </span>
      <div className="text-left leading-tight">
        <div className="font-display text-lg font-semibold text-white">
          {value}
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
          {label}
        </div>
      </div>
    </div>
  );
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function formatWeekRange(weekStart, dates) {
  if (!dates?.length) return "";
  const start = new Date(dates[0] + "T00:00:00");
  const end = new Date(dates[6] + "T00:00:00");
  const sameMonth = start.getMonth() === end.getMonth();
  if (sameMonth) {
    return `${start.getDate()} – ${end.getDate()} ${MONTHS[end.getMonth()]}`;
  }
  return `${start.getDate()} ${MONTHS[start.getMonth()]} – ${end.getDate()} ${MONTHS[end.getMonth()]}`;
}

export default function CalendarHeader({
  stats,
  dates,
  weekStart,
  onPrev,
  onNext,
  onToday,
}) {
  const now = new Date();
  const timeStr = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
  const weekLabel = formatWeekRange(weekStart, dates);

  return (
    <div className="space-y-6">
      {/* Hero headline */}
      <section className="pt-10 pb-2">
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="eyebrow"
        >
          #5 — Live Social Calendar · Mode 1
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          className="mt-3 max-w-3xl font-display text-3xl font-bold leading-[1.08] tracking-tight text-chalk sm:text-4xl"
        >
          <span className="text-chalk">Human-Intervened </span>
          <span className="bg-gradient-to-r from-neon-orange via-[#FF6B9D] to-signal bg-clip-text text-transparent">
            Approval Flow
          </span>
        </motion.h1>
      </section>

      {/* Stats + controls strip */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.12 }}
        className="flex flex-wrap items-center justify-between gap-4"
      >
        {/* Left: week nav */}
        <div className="flex items-center gap-3">
          <button
            onClick={onPrev}
            className="grid h-8 w-8 place-items-center rounded-lg border border-white/12 bg-white/[0.04] text-chalk transition-colors hover:bg-white/[0.09]"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={onToday}
            className="rounded-lg border border-white/12 bg-white/[0.04] px-3 py-1.5 font-mono text-[11px] text-chalk transition-colors hover:bg-white/[0.09]"
          >
            Today
          </button>
          <button
            onClick={onNext}
            className="grid h-8 w-8 place-items-center rounded-lg border border-white/12 bg-white/[0.04] text-chalk transition-colors hover:bg-white/[0.09]"
          >
            <ChevronRight size={16} />
          </button>
          <span className="ml-2 font-display text-sm font-semibold text-chalk">
            {weekLabel}
          </span>
        </div>

        {/* Right: quick stats + badges */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-1.5">
            <CheckCircle2 size={13} className="text-neon-emerald" />
            <span className="font-mono text-[11px] text-chalk">
              All posts await human sign-off
            </span>
          </div>

          <Stat
            icon={CheckCircle2}
            value={stats.live + stats.scheduled}
            label="Approved"
            accent="#34d399"
          />
          <Stat
            icon={ListTodo}
            value={stats.inQueue}
            label="In Queue"
            accent="#f59e0b"
          />

          <span className="font-mono text-[11px] text-muted">
            {timeStr}
          </span>
        </div>
      </motion.div>
    </div>
  );
}
