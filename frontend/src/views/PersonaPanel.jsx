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

  // A draft handed over from the Trend Radar starts a clean review session with
  // that wording already loaded, so the reviewer just presses Run the panel.
  useEffect(() => {
    if (!incomingPost?.post) return;
    if (lastHandoff.current === incomingPost.draft_id) return;
    lastHandoff.current = incomingPost.draft_id;
    panel.newDraft(incomingPost.post);
  }, [incomingPost, panel]);
  const hasRounds = panel.rounds.length > 0;
  const lastRound = hasRounds ? panel.rounds[panel.rounds.length - 1] : null;

  return (
    <div className="min-h-screen">
      <NavBar settings={panel.settings} threadId={panel.threadId} />

      <main className="pb-8">
        <Hero settings={panel.settings} />
        <PersonaBento personas={panel.personas} />

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
        />

        {hasRounds ? (
          <>
            <RoundResults
              rounds={panel.rounds}
              personas={panel.personas}
              revealKey={panel.revealKey}
            />
            <OutcomeBanner round={lastRound} roundNumber={panel.rounds.length} />
          </>
        ) : (
          <EmptyState />
        )}
      </main>

      <Footer settings={panel.settings} />
    </div>
  );
}
