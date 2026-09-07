import { AnimatePresence, motion } from "framer-motion";
import PostCard from "./PostCard.jsx";

const DAY_SHORT_MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function dayLabel(dateStr) {
  const d = new Date(dateStr + "T00:00:00");
  return `${d.getDate()} ${DAY_SHORT_MONTHS[d.getMonth()]}`;
}

export default function CalendarGrid({ days, onPublish, onDelete }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.18 }}
      className="calendar-grid"
    >
      {/* Column headers */}
      <div className="grid grid-cols-7 gap-px rounded-t-2xl border border-white/10 bg-white/[0.04] overflow-hidden">
        {days.map((day) => (
          <div
            key={day.date}
            className={`px-3 py-2.5 text-center font-mono text-[11px] uppercase tracking-[0.2em] ${
              day.isToday
                ? "bg-signal/[0.08] text-signal font-bold"
                : "text-muted"
            }`}
          >
            <div className="flex items-center justify-center gap-1.5">
              {day.name}
              {day.isToday && (
                <span className="h-1.5 w-1.5 rounded-full bg-signal" />
              )}
            </div>
            <div
              className={`mt-0.5 text-[10px] tracking-normal ${
                day.isToday ? "text-signal/70" : "text-muted/60"
              }`}
            >
              {dayLabel(day.date)}
            </div>
          </div>
        ))}
      </div>

      {/* Grid cells */}
      <div className="grid grid-cols-7 gap-px rounded-b-2xl border border-t-0 border-white/10 overflow-hidden">
        {days.map((day) => (
          <div
            key={day.date}
            className={`min-h-[220px] p-2 transition-colors ${
              day.isToday
                ? "bg-signal/[0.03]"
                : "bg-white/[0.015] hover:bg-white/[0.03]"
            }`}
          >
            <AnimatePresence mode="popLayout">
              {day.posts.length > 0 ? (
                <div className="flex flex-col gap-2">
                  {day.posts.map((post) => (
                    <PostCard
                      key={post.id}
                      post={post}
                      compact
                      onPublish={onPublish}
                      onDelete={onDelete}
                    />
                  ))}
                </div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex h-full items-center justify-center"
                >
                  <p className="font-mono text-[10px] text-muted/30">
                    No posts
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
