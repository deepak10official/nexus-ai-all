import { ArrowLeftRight } from "lucide-react";

export default function Footer({ settings }) {
  return (
    <footer className="mx-auto mt-20 max-w-7xl px-5 pb-12 sm:px-8">
      <div className="flex flex-col items-start justify-between gap-3 border-t border-white/8 pt-6 sm:flex-row sm:items-center">
        <p className="font-mono text-[11px] text-zinc-600">
          MOD02 prototype · not connected to any publishing endpoint
        </p>
        <p className="flex items-center gap-1.5 font-mono text-[11px] text-zinc-600">
          <ArrowLeftRight className="h-3.5 w-3.5" />
          Receives approved drafts from MOD03 · National Trend Radar
        </p>
      </div>
    </footer>
  );
}
