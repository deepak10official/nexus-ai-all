import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CalendarDays, Clock, X } from "lucide-react";

// Only platforms this prototype can actually publish to. Offering LinkedIn or
// Twitter here would let someone schedule a post that could never go live.
const PLATFORMS = [
  { id: "instagram", label: "Instagram", dot: "#E1306C" },
  { id: "facebook", label: "Facebook", dot: "#1877F2" },
];

export default function ScheduleModal({ item, dates, onSchedule, onClose }) {
  const [selectedDate, setSelectedDate] = useState(dates?.[0] || "");
  const [selectedTime, setSelectedTime] = useState("09:00");
  const [selectedPlatform, setSelectedPlatform] = useState(
    item?.platform || "instagram",
  );
  const [submitting, setSubmitting] = useState(false);

  if (!item) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    await onSchedule({
      text: item.text,
      platform: selectedPlatform,
      scheduled_date: selectedDate,
      scheduled_time: selectedTime,
      image_url: item.image_url || null,
      source_mod: item.source_mod || "MOD02",
      source_label: item.source_label || "APPROVED",
      hashtags: item.hashtags || [],
      draft_id: item.draft_id || null,
    });
    setSubmitting(false);
    onClose();
  }

  const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: "spring", stiffness: 350, damping: 30 }}
          onClick={(e) => e.stopPropagation()}
          className="relative w-full max-w-md rounded-2xl border border-white/12 bg-ink-900 p-6 shadow-2xl"
          style={{
            boxShadow:
              "0 25px 80px -20px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.06), 0 0 40px -10px rgba(53,224,216,0.15)",
          }}
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute right-3 top-3 grid h-7 w-7 place-items-center rounded-lg text-muted transition-colors hover:bg-white/10 hover:text-chalk"
          >
            <X size={16} />
          </button>

          <div className="mb-5 flex items-center gap-2.5">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-signal/10">
              <CalendarDays size={16} className="text-signal" />
            </div>
            <div>
              <h3 className="font-display text-lg font-bold text-chalk">
                Schedule Post
              </h3>
              <p className="font-mono text-[10px] text-muted">
                Pick a date, time & platform
              </p>
            </div>
          </div>

          {/* Post preview */}
          <div className="mb-5 rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <p className="eyebrow mb-1">Post preview</p>
            <p
              className="intl text-[12px] leading-relaxed text-chalk/85"
              dir="auto"
            >
              {item.text.length > 150
                ? item.text.slice(0, 150) + "…"
                : item.text}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Date selection — week days as clickable pills */}
            <div>
              <label className="eyebrow mb-2 block">Date</label>
              <div className="flex flex-wrap gap-1.5">
                {dates.map((d) => {
                  const dt = new Date(d + "T00:00:00");
                  const active = d === selectedDate;
                  return (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setSelectedDate(d)}
                      className={`rounded-lg border px-3 py-2 text-center transition-all ${
                        active
                          ? "border-signal/50 bg-signal/15 text-signal"
                          : "border-white/10 bg-white/[0.03] text-muted hover:border-white/20 hover:text-chalk"
                      }`}
                    >
                      <div className="font-mono text-[10px] uppercase">
                        {DAY_NAMES[dt.getDay()]}
                      </div>
                      <div className="font-display text-sm font-semibold">
                        {dt.getDate()}
                      </div>
                      <div className="font-mono text-[9px] opacity-60">
                        {MONTHS[dt.getMonth()]}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Time */}
            <div>
              <label className="eyebrow mb-2 block">Time</label>
              <div className="relative">
                <Clock
                  size={13}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                />
                <input
                  type="time"
                  value={selectedTime}
                  onChange={(e) => setSelectedTime(e.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-ink-900/80 py-2.5 pl-9 pr-3 font-mono text-sm text-chalk outline-none focus:border-signal/50"
                />
              </div>
            </div>

            {/* Platform */}
            <div>
              <label className="eyebrow mb-2 block">Platform</label>
              <div className="grid grid-cols-2 gap-2">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setSelectedPlatform(p.id)}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 font-mono text-[11px] transition-all ${
                      selectedPlatform === p.id
                        ? "border-signal/40 bg-signal/10 text-chalk"
                        : "border-white/10 bg-white/[0.03] text-muted hover:border-white/20 hover:text-chalk"
                    }`}
                  >
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ background: p.dot }}
                    />
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Submit */}
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={submitting || !selectedDate}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-signal to-[#7DD3FC] py-3 font-display text-sm font-medium text-ink-900 shadow-[0_0_28px_-6px_rgba(53,224,216,0.4)] transition-opacity disabled:opacity-40"
              >
                <CalendarDays size={15} />
                {submitting ? "Scheduling…" : "Schedule Post"}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-white/12 bg-white/[0.04] px-5 py-3 font-display text-sm text-chalk transition-colors hover:bg-white/[0.09]"
              >
                Cancel
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
