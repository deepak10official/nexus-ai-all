import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/panelApi.js";

export const SAMPLE_POST =
  "Get an instant personal loan in 5 minutes! No paperwork, no questions " +
  "asked. Just share your OTP and the money is yours. Limited time offer, " +
  "apply now before it's gone!";

function newThreadId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `t-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * Owns the whole session: the LangGraph thread_id, the editable post, the
 * rounds returned by the panel, and the three actions (run / rework / reset).
 * Deliberately mirrors the Streamlit app's state machine.
 */
export function usePanel() {
  const [threadId, setThreadId] = useState(newThreadId);
  const [personas, setPersonas] = useState([]);
  const [settings, setSettings] = useState(null);
  const [post, setPost] = useState(SAMPLE_POST);
  const [rounds, setRounds] = useState([]);
  const [waiting, setWaiting] = useState(false);
  const [canRework, setCanRework] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);
  // Bumped on every completed run so the newest round animates its reveal.
  const [revealKey, setRevealKey] = useState(0);
  const bootstrapped = useRef(false);

  const applyState = useCallback((s) => {
    setRounds(s.rounds ?? []);
    setWaiting(!!s.waiting);
    setCanRework(!!s.can_rework);
  }, []);

  // One-time bootstrap: personas + settings (+ any existing session state).
  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    (async () => {
      try {
        const [p, s] = await Promise.all([api.personas(), api.settings()]);
        setPersonas(p);
        setSettings(s);
      } catch (e) {
        setError(
          `Couldn't reach the panel API. Is the backend running on :8000? (${e.message})`
        );
      }
    })();
  }, []);

  const runPanel = useCallback(async () => {
    const text = post.trim();
    if (!text) {
      setNotice({ kind: "warn", text: "Please enter a post." });
      return;
    }
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const s = await api.run(threadId, text);
      applyState(s);
      setRevealKey((k) => k + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [post, threadId, applyState]);

  const rework = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const s = await api.rework(threadId);
      applyState(s);
      if (s.current_post) setPost(s.current_post);
      setNotice({
        kind: "info",
        text:
          "Post reworked from the panel's feedback. Review it above, edit if " +
          "you like, then run the panel to vote again.",
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [threadId, applyState]);

  /**
   * One click: rework the post from the panel's feedback, then immediately
   * re-vote on the revised text. Uses the post returned by the rework call
   * directly, so it never races the `post` state update.
   */
  const reworkAndRun = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const reworked = await api.rework(threadId);
      const revised = (reworked.current_post || "").trim();
      if (!revised) {
        applyState(reworked);
        setNotice({
          kind: "warn",
          text: "The reviser returned an empty post. Edit the draft and run again.",
        });
        return;
      }
      setPost(revised);
      const s = await api.run(threadId, revised);
      applyState(s);
      setRevealKey((k) => k + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [threadId, applyState]);

  /** Clear the board and start a brand-new draft on a fresh graph thread. */
  const newDraft = useCallback((text = "") => {
    setThreadId(newThreadId());
    setRounds([]);
    setWaiting(false);
    setCanRework(false);
    setNotice(null);
    setError(null);
    setPost(text);
    setRevealKey(0);
  }, []);

  const reset = useCallback(() => newDraft(SAMPLE_POST), [newDraft]);

  return {
    threadId,
    personas,
    settings,
    post,
    setPost,
    rounds,
    waiting,
    canRework,
    loading,
    notice,
    setNotice,
    error,
    revealKey,
    runPanel,
    rework,
    reworkAndRun,
    newDraft,
    reset,
  };
}
