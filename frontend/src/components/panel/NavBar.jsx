import { Vote, Circle } from "lucide-react";

export default function NavBar({ settings, threadId }) {
  return (
    <header className="sticky top-0 z-50 border-b border-white/8 bg-ink-900/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3.5 sm:px-8">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-grad-accent shadow-glow-amber">
            <Vote className="h-4 w-4 text-ink-900" strokeWidth={2.4} />
          </span>
          <div className="leading-tight">
            <div className="font-display text-sm font-semibold tracking-tight text-white">
              MOD02
            </div>
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              Persona Panel
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="hidden items-center gap-1.5 font-mono text-[11px] text-zinc-600 md:inline-flex">
            <Circle className="h-2 w-2 fill-neon-emerald text-neon-emerald" />
            {threadId.slice(0, 8)}
          </span>
        </div>
      </div>
    </header>
  );
}
