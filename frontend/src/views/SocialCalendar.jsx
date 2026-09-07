import { forwardRef, useImperativeHandle, useState } from "react";
import { motion } from "framer-motion";
import { CalendarDays, RefreshCw } from "lucide-react";
import { useCalendar } from "../hooks/useCalendar.js";
import CalendarHeader from "../components/calendar/CalendarHeader.jsx";
import CalendarGrid from "../components/calendar/CalendarGrid.jsx";
import ApprovalQueue from "../components/calendar/ApprovalQueue.jsx";
import ScheduleModal from "../components/calendar/ScheduleModal.jsx";

const SocialCalendar = forwardRef(function SocialCalendar(_props, ref) {
  const cal = useCalendar();
  const [scheduleItem, setScheduleItem] = useState(null);

  // Expose refresh so App.jsx can trigger a queue reload after MOD02 handoff.
  useImperativeHandle(ref, () => ({ refresh: cal.refresh }), [cal.refresh]);

  return (
    <div className="min-h-screen">
      {/* Sticky nav */}
      <header className="z-40 border-b border-white/[0.07] bg-ink-900/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="relative grid h-8 w-8 place-items-center rounded-lg bg-signal/10">
              <span className="absolute inset-0 animate-pulseRing rounded-lg border border-signal/40" />
              <CalendarDays size={16} className="text-signal" />
            </div>
            <div className="leading-tight">
              <p className="font-display text-sm font-bold tracking-tight text-chalk">
                Social Calendar
              </p>
              <p className="font-mono text-[10px] text-muted">
                Bharat Connect
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-1.5 font-mono text-[10px] text-muted sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-signal" />
              Calendar active
            </span>
            <button
              type="button"
              onClick={cal.refresh}
              disabled={cal.loading}
              className="flex items-center gap-2 rounded-lg border border-white/12 bg-white/[0.04] px-3.5 py-2 font-display text-xs text-chalk transition-colors hover:bg-white/[0.09] disabled:opacity-50"
            >
              <RefreshCw
                size={12}
                className={cal.loading ? "animate-spin" : ""}
              />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] px-6 pb-20">
        <CalendarHeader
          stats={cal.stats}
          dates={cal.dates}
          weekStart={cal.weekStart}
          onPrev={cal.goToPrevWeek}
          onNext={cal.goToNextWeek}
          onToday={cal.goToToday}
        />

        {/* Error bar */}
        {cal.error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 rounded-xl border border-[#F2536D]/30 bg-[#F2536D]/[0.07] px-4 py-2.5 text-sm text-[#FFB3C1]"
          >
            {cal.error}
          </motion.div>
        )}

        {/* Two-column layout: Calendar + Approval Queue */}
        <section className="mt-6 grid gap-5 lg:grid-cols-[1fr_280px]">
          {/* Calendar grid */}
          <CalendarGrid
            days={cal.days}
            onPublish={cal.publish}
            onDelete={cal.remove}
          />

          {/* Sidebar: approval queue */}
          <ApprovalQueue
            queue={cal.queue}
            onApprove={cal.approveItem}
            onReject={cal.rejectItem}
            onSchedule={(item) => setScheduleItem(item)}
          />
        </section>
      </main>

      <footer className="border-t border-white/[0.07] py-8">
        <div className="mx-auto flex max-w-[1400px] flex-col gap-2 px-6 font-mono text-[11px] text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>Preview environment · nothing is published from here</p>
          <p>Approved posts are scheduled, not auto-published</p>
        </div>
      </footer>

      {/* Schedule modal */}
      {scheduleItem && (
        <ScheduleModal
          item={scheduleItem}
          dates={cal.dates}
          onSchedule={cal.schedule}
          onClose={() => setScheduleItem(null)}
        />
      )}
    </div>
  );
});

export default SocialCalendar;
