import { useMemo, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  ChevronRight,
  MapPin,
  GraduationCap,
  Briefcase,
  Store,
  Home,
  Clock,
  Check,
  Users,
} from "lucide-react";

/** Category display order + icons + accent colors. */
const CATEGORY_META = {
  "Students & Early Career": {
    icon: GraduationCap,
    accent: "text-amber-400",
    accentBg: "bg-amber-400",
    border: "border-amber-400/20",
    glow: "from-amber-400/10",
    checkbox: "accent-amber-400",
  },
  "Salaried Professionals": {
    icon: Briefcase,
    accent: "text-teal-400",
    accentBg: "bg-teal-400",
    border: "border-teal-400/20",
    glow: "from-teal-400/10",
    checkbox: "accent-teal-400",
  },
  "Business Owners & Traders": {
    icon: Store,
    accent: "text-orange-400",
    accentBg: "bg-orange-400",
    border: "border-orange-400/20",
    glow: "from-orange-400/10",
    checkbox: "accent-orange-400",
  },
  "Household Managers": {
    icon: Home,
    accent: "text-pink-400",
    accentBg: "bg-pink-400",
    border: "border-pink-400/20",
    glow: "from-pink-400/10",
    checkbox: "accent-pink-400",
  },
  "Retirees & Seniors": {
    icon: Clock,
    accent: "text-emerald-400",
    accentBg: "bg-emerald-400",
    border: "border-emerald-400/20",
    glow: "from-emerald-400/10",
    checkbox: "accent-emerald-400",
  },
};

const CATEGORY_ORDER = [
  "Students & Early Career",
  "Salaried Professionals",
  "Business Owners & Traders",
  "Household Managers",
  "Retirees & Seniors",
];

export default function PersonaBento({
  personas,
  selectedPersonas,
  onSelectionChange,
}) {
  const [panelOpen, setPanelOpen] = useState(false);
  const [expandedCats, setExpandedCats] = useState(
    () => new Set(CATEGORY_ORDER)
  );
  // Local selection state for "apply" pattern.
  const [localSelection, setLocalSelection] = useState(
    () => new Set(selectedPersonas ?? [])
  );
  const [dirty, setDirty] = useState(false);

  // Sync when parent changes (e.g. reset).
  useMemo(() => {
    if (selectedPersonas) {
      setLocalSelection(new Set(selectedPersonas));
      setDirty(false);
    }
  }, [selectedPersonas]);

  const grouped = useMemo(() => {
    if (!personas?.length) return [];
    const map = new Map();
    for (const p of personas) {
      const cat = p.category || "Uncategorised";
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat).push(p);
    }
    const sorted = [];
    for (const cat of CATEGORY_ORDER) {
      if (map.has(cat)) sorted.push([cat, map.get(cat)]);
    }
    for (const [cat, members] of map) {
      if (!CATEGORY_ORDER.includes(cat)) sorted.push([cat, members]);
    }
    return sorted;
  }, [personas]);

  const toggleCat = useCallback((cat) => {
    setExpandedCats((prev) => {
      const next = new Set(prev);
      next.has(cat) ? next.delete(cat) : next.add(cat);
      return next;
    });
  }, []);

  const togglePersona = useCallback((id) => {
    setLocalSelection((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
    setDirty(true);
  }, []);

  const toggleAllInCategory = useCallback(
    (members) => {
      const ids = members.map((m) => m.id);
      const allSelected = ids.every((id) => localSelection.has(id));
      setLocalSelection((prev) => {
        const next = new Set(prev);
        ids.forEach((id) => (allSelected ? next.delete(id) : next.add(id)));
        return next;
      });
      setDirty(true);
    },
    [localSelection]
  );

  const selectAll = useCallback(() => {
    setLocalSelection(new Set(personas.map((p) => p.id)));
    setDirty(true);
  }, [personas]);

  const deselectAll = useCallback(() => {
    setLocalSelection(new Set());
    setDirty(true);
  }, []);

  const handleApply = useCallback(() => {
    onSelectionChange?.([...localSelection]);
    setDirty(false);
  }, [localSelection, onSelectionChange]);

  if (!personas?.length) return null;

  const totalSelected = localSelection.size;
  const totalPersonas = personas.length;

  return (
    <section className="mx-auto max-w-7xl px-5 pt-10 sm:px-8">
      {/* Selector bar */}
      <button
        onClick={() => setPanelOpen((o) => !o)}
        className="group flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/[0.035] px-5 py-3.5 backdrop-blur-xl transition-all duration-300 hover:border-white/20 hover:bg-white/[0.06]"
      >
        <div className="flex items-center gap-3">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-neon-orange/20 to-neon-pink/10 border border-neon-orange/20">
            <Users className="h-4 w-4 text-neon-orange" />
          </span>
          <div className="text-left">
            <div className="font-display text-sm font-semibold text-white">
              Select Panelists
            </div>
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
              {totalSelected} of {totalPersonas} selected
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Count badge */}
          <span className="flex h-6 items-center rounded-full bg-neon-orange/15 px-2.5 font-mono text-[11px] font-medium text-neon-orange">
            {totalSelected}
          </span>
          <motion.span
            animate={{ rotate: panelOpen ? 180 : 0 }}
            transition={{ duration: 0.25 }}
          >
            <ChevronDown className="h-4.5 w-4.5 text-zinc-500 transition-colors group-hover:text-zinc-300" />
          </motion.span>
        </div>
      </button>

      {/* Expandable panel */}
      <AnimatePresence>
        {panelOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-2 rounded-2xl border border-white/10 bg-white/[0.025] backdrop-blur-xl">
              {/* Top bar: Select All / Deselect All */}
              <div className="flex items-center justify-between border-b border-white/8 px-5 py-2.5">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
                  {totalSelected} personas active
                </span>
                <div className="flex gap-3">
                  <button
                    onClick={selectAll}
                    className="font-mono text-[11px] text-neon-orange/80 transition hover:text-neon-orange"
                  >
                    Select all
                  </button>
                  <span className="text-zinc-700">|</span>
                  <button
                    onClick={deselectAll}
                    className="font-mono text-[11px] text-zinc-500 transition hover:text-zinc-300"
                  >
                    Deselect all
                  </button>
                </div>
              </div>

              {/* Category sections */}
              <div className="divide-y divide-white/6">
                {grouped.map(([category, members]) => {
                  const meta = CATEGORY_META[category] || {
                    icon: GraduationCap,
                    accent: "text-zinc-400",
                    accentBg: "bg-zinc-400",
                    border: "border-zinc-700",
                    glow: "from-zinc-500/10",
                  };
                  const Icon = meta.icon;
                  const isExpanded = expandedCats.has(category);
                  const catIds = members.map((m) => m.id);
                  const selectedInCat = catIds.filter((id) =>
                    localSelection.has(id)
                  ).length;
                  const allInCat = selectedInCat === catIds.length;

                  return (
                    <div key={category}>
                      {/* Category header */}
                      <button
                        onClick={() => toggleCat(category)}
                        className="flex w-full items-center justify-between px-5 py-3 transition hover:bg-white/[0.02]"
                      >
                        <div className="flex items-center gap-2.5">
                          <motion.span
                            animate={{ rotate: isExpanded ? 0 : -90 }}
                            transition={{ duration: 0.2 }}
                          >
                            <ChevronDown className="h-3.5 w-3.5 text-zinc-600" />
                          </motion.span>
                          <div
                            className={`flex h-6 w-6 items-center justify-center rounded-md border bg-gradient-to-br to-transparent ${meta.border} ${meta.glow}`}
                          >
                            <Icon
                              className={`h-3 w-3 ${meta.accent}`}
                            />
                          </div>
                          <span
                            className={`font-display text-[13px] font-semibold ${meta.accent}`}
                          >
                            {category}
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-[10px] text-zinc-600">
                            {selectedInCat}/{catIds.length}
                          </span>
                          {/* Category toggle-all button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleAllInCategory(members);
                            }}
                            className={`flex h-5 w-5 items-center justify-center rounded border transition ${
                              allInCat
                                ? `${meta.border} ${meta.accentBg} bg-opacity-20`
                                : "border-zinc-700 bg-transparent hover:border-zinc-500"
                            }`}
                          >
                            {allInCat && (
                              <Check className="h-3 w-3 text-ink-900" />
                            )}
                          </button>
                        </div>
                      </button>

                      {/* Persona rows */}
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="pb-2">
                              {members.map((p) => {
                                const isSelected = localSelection.has(p.id);
                                return (
                                  <button
                                    key={p.id}
                                    title={p.tagline}
                                    onClick={() => togglePersona(p.id)}
                                    className={`flex w-full items-center gap-3 px-5 py-2 pl-14 transition hover:bg-white/[0.03] ${
                                      isSelected
                                        ? "opacity-100"
                                        : "opacity-50"
                                    }`}
                                  >
                                    {/* Checkbox */}
                                    <span
                                      className={`flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded border transition ${
                                        isSelected
                                          ? "border-neon-orange/50 bg-neon-orange/20"
                                          : "border-zinc-700 bg-transparent"
                                      }`}
                                    >
                                      {isSelected && (
                                        <Check className="h-2.5 w-2.5 text-neon-orange" />
                                      )}
                                    </span>
                                    {/* Persona info */}
                                    <span className="text-lg leading-none">
                                      {p.emoji}
                                    </span>
                                    <div className="flex-1 text-left">
                                      <span className="text-sm font-medium text-white">
                                        {p.name}
                                      </span>
                                      <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.12em] text-zinc-600">
                                        {p.archetype}
                                      </span>
                                    </div>
                                    <div className="hidden items-center gap-1 text-[11px] text-zinc-600 sm:flex">
                                      <MapPin className="h-2.5 w-2.5" />
                                      <span>{p.location}</span>
                                    </div>
                                  </button>
                                );
                              })}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  );
                })}
              </div>

              {/* Bottom bar: Apply button */}
              <div className="flex items-center justify-between border-t border-white/8 px-5 py-3">
                <span className="text-xs text-zinc-500">
                  {totalSelected === 0 ? (
                    <span className="text-neon-rose">
                      Select at least 1 persona to run the panel
                    </span>
                  ) : (
                    <>
                      <span className="font-semibold text-white">
                        {totalSelected}
                      </span>{" "}
                      persona{totalSelected !== 1 ? "s" : ""} will evaluate your
                      post
                    </>
                  )}
                </span>
                <button
                  onClick={handleApply}
                  disabled={!dirty || totalSelected === 0}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-grad-accent px-5 py-2 text-sm font-semibold text-ink-900 shadow-glow-amber transition hover:brightness-110 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Check className="h-3.5 w-3.5" />
                  Apply
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
