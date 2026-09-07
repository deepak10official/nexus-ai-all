import { useEffect, useRef } from "react";
import { usePanel } from "../hooks/usePanel.js";
import NavBar from "../components/panel/NavBar.jsx";
import Hero from "../components/panel/Hero.jsx";
import PersonaBento from "../components/panel/PersonaBento.jsx";
import PostConsole from "../components/panel/PostConsole.jsx";
import RoundResults from "../components/panel/RoundResults.jsx";
import OutcomeBanner from "../components/panel/OutcomeBanner.jsx";
import EmptyState from "../components/panel/EmptyState.jsx";
import Footer from "../components/panel/Footer.jsx";

export default function PersonaPanel({ incomingPost }) {
  const panel = usePanel();
  const lastHandoff = useRef(null);
  const { newDraft } = panel;

  // A draft handed over from the Trend Radar starts a clean review session with
  // that wording already loaded, so the reviewer just presses Run the panel.
  // The key includes the text, not just the id: re-approving an edited draft
  // must load the new wording, while re-sending identical text must not wipe
  // a review already in progress.
  useEffect(() => {
    if (!incomingPost?.post) return;
    const key = `${incomingPost.draft_id}::${incomingPost.post}::${incomingPost.image_url || ""}`;
    if (lastHandoff.current === key) return;
    lastHandoff.current = key;
    newDraft(incomingPost.post, incomingPost.image_url || null);
  }, [incomingPost, newDraft]);
  const hasRounds = panel.rounds.length > 0;
  const lastRound = hasRounds ? panel.rounds[panel.rounds.length - 1] : null;

  return (
    <div className="min-h-screen">
      <NavBar settings={panel.settings} threadId={panel.threadId} />

      <main className="pb-8">
        <Hero settings={panel.settings} selectedCount={panel.selectedPersonas?.length} />

        {/* Provenance: makes clear this wording arrived from the Trend Radar
            rather than being typed here. */}
        {incomingPost?.post ? (
          <div className="mx-auto max-w-7xl px-5 pt-6 sm:px-8">
            <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-xs text-zinc-400">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-neon-orange/90">
                From Trend Radar
              </span>
              <span className="text-zinc-600">·</span>
              <span>draft {incomingPost.draft_id?.slice(0, 8)}</span>
              {incomingPost.hashtags?.length ? (
                <>
                  <span className="text-zinc-600">·</span>
                  <span className="font-mono text-[11px] text-zinc-500">
                    {incomingPost.hashtags.join(" ")}
                  </span>
                </>
              ) : null}
            </div>
          </div>
        ) : null}
        <PersonaBento
          personas={panel.personas}
          selectedPersonas={panel.selectedPersonas}
          onSelectionChange={panel.setSelectedPersonas}
        />

        <PostConsole
          post={panel.post}
          setPost={panel.setPost}
          loading={panel.loading}
          hasRounds={hasRounds}
          canRework={panel.canRework}
          notice={panel.notice}
          error={panel.error}
          onRun={panel.runPanel}
          onReworkAndRun={panel.reworkAndRun}
          onNewDraft={() => panel.newDraft("")}
          image={panel.image}
          imageUploading={panel.imageUploading}
          onUploadImage={panel.uploadImage}
          onRemoveImage={panel.removeImage}
          validateText={panel.validateText}
          setValidateText={panel.setValidateText}
          validateImage={panel.validateImage}
          setValidateImage={panel.setValidateImage}
        />

        {hasRounds ? (
          <>
            <RoundResults
              rounds={panel.rounds}
              personas={panel.personas}
              revealKey={panel.revealKey}
            />
            <OutcomeBanner
              round={lastRound}
              roundNumber={panel.rounds.length}
              threadId={panel.threadId}
              hasImage={!!panel.image?.url}
            />
          </>
        ) : (
          <EmptyState />
        )}
      </main>

      <Footer settings={panel.settings} />
    </div>
  );
}
