import { useCallback, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Radar, Vote, CalendarDays, ArrowRight } from "lucide-react";

import TrendRadar from "./views/TrendRadar.jsx";
import PersonaPanel from "./views/PersonaPanel.jsx";
import SocialCalendar from "./views/SocialCalendar.jsx";
import * as calendarApi from "./api/calendarApi.js";

const MODULES = [
  { id: "radar", label: "Trend Radar", code: "MOD03", icon: Radar },
  { id: "panel", label: "Persona Panel", code: "MOD02", icon: Vote },
  { id: "calendar", label: "Social Calendar", code: "MOD05", icon: CalendarDays },
];

export default function App() {
  const [view, setView] = useState("radar");
  const [handoff, setHandoff] = useState(null);
  const [flash, setFlash] = useState(null);
  const calendarRef = useRef(null);

  // MOD03 approved a draft -> make it available to MOD02.
  // Approving the copy loads it quietly so the MOD03 review flow is not
  // interrupted; the final approval (or the "Run panel" link) switches over.
  const onHandoff = useCallback((draft) => {
    if (!draft?.post) return;
    setHandoff(draft);
    if (draft.switchTo) {
      setView("panel");
      setFlash("Draft handed off from Trend Radar — ready for the panel.");
    } else {
      setFlash("Approved copy sent to the Persona Panel.");
    }
    window.setTimeout(() => setFlash(null), 6000);
  }, []);

  // MOD02 panel approved a post -> send it to the Calendar queue.
  const onApproved = useCallback(async (postData) => {
    try {
      await calendarApi.addToQueue({
        text: postData.text,
        platform: "linkedin",
        image_url: postData.image_url,
        source_mod: postData.source_mod || "MOD02",
        source_label: postData.source_label || "PANEL APPROVED",
        hashtags: postData.hashtags || [],
        draft_id: postData.draft_id,
      });
      setFlash("✅ Approved post sent to the Calendar queue — switch to the Calendar to schedule it.");
      // Refresh the calendar's queue if it's already mounted.
      calendarRef.current?.refresh?.();
    } catch (e) {
      setFlash(`Failed to send to calendar: ${e.message}`);
    }
    window.setTimeout(() => setFlash(null), 8000);
  }, []);

  return (
    <div className="min-h-screen">
      {/* Module switcher — the only sticky bar; each view keeps its own header */}
      <div className="sticky top-0 z-50 border-b border-white/[0.07] bg-ink-900/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-2.5 sm:px-8">
          <div className="flex items-center gap-1.5">
            {MODULES.map((m) => {
              const Icon = m.icon;
              const active = view === m.id;
              return (
                <button
                  key={m.id}
                  onClick={() => setView(m.id)}
                  className={`relative flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    active
                      ? "text-white"
                      : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId="module-pill"
                      className="absolute inset-0 rounded-lg border border-white/12 bg-white/[0.07]"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                  <Icon className="relative h-4 w-4" strokeWidth={2.2} />
                  <span className="relative">{m.label}</span>
                  <span className="relative hidden font-mono text-[10px] text-zinc-600 sm:inline">
                    {m.code}
                  </span>
                </button>
              );
            })}
          </div>

          {handoff ? (
            <button
              onClick={() => setView(view === "radar" ? "panel" : "radar")}
              className="hidden items-center gap-1.5 font-mono text-[11px] text-zinc-500 transition hover:text-zinc-300 sm:flex"
              title={`Draft ${handoff.draft_id?.slice(0, 8)} in review`}
            >
              MOD03 <ArrowRight className="h-3 w-3" /> MOD02
              <span className="text-neon-emerald">
                {handoff.draft_id?.slice(0, 8)}
              </span>
            </button>
          ) : null}
        </div>
      </div>

      <AnimatePresence>
        {flash ? (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mx-auto mt-3 max-w-7xl px-5 sm:px-8"
          >
            <div className="rounded-xl border border-neon-emerald/30 bg-neon-emerald/8 px-4 py-2.5 text-sm text-emerald-200">
              {flash}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {/* All views stay mounted so each keeps its state when switching. */}
      <div style={{ display: view === "radar" ? "block" : "none" }}>
        <TrendRadar onHandoff={onHandoff} />
      </div>
      <div style={{ display: view === "panel" ? "block" : "none" }}>
        <PersonaPanel incomingPost={handoff} onApproved={onApproved} />
      </div>
      <div style={{ display: view === "calendar" ? "block" : "none" }}>
        <SocialCalendar ref={calendarRef} />
      </div>
    </div>
  );
}
