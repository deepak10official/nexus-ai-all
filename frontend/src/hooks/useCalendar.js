import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api/calendarApi.js";

// ---------------------------------------------------------------------------
// Dates are handled in IST throughout.
//
// The obvious approach — new Date(...).toISOString().slice(0, 10) — is wrong
// here, and was the cause of every day being labelled one ahead. toISOString()
// converts to UTC first, so on an IST machine (UTC+5:30) local midnight becomes
// 18:30 the *previous* day, and slicing that yields yesterday's date. It also
// breaks between 00:00 and 05:30 IST, when UTC is still on the previous date.
//
// So the calendar never round-trips through UTC. Dates are formatted from IST
// calendar parts, and ISO date strings are treated as plain calendar dates with
// no timezone attached — which is exactly what they are on the backend.
// ---------------------------------------------------------------------------

const IST_TZ = "Asia/Kolkata";

/** Today's date in IST, as YYYY-MM-DD, regardless of where the browser is. */
export function istToday() {
  // en-CA formats as YYYY-MM-DD, which is the shape we want.
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: IST_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

/** Current wall-clock time in IST, as HH:MM. */
export function istNowTime() {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: IST_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date());
}

/**
 * Parse YYYY-MM-DD into a Date fixed at UTC noon.
 *
 * Noon is deliberate: it is far enough from both midnights that no timezone
 * offset can push the date across a day boundary, so weekday and arithmetic
 * stay correct everywhere.
 */
function parseISODate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12, 0, 0));
}

/** Format a UTC-noon Date back to YYYY-MM-DD. */
function formatISODate(dt) {
  return dt.toISOString().slice(0, 10);
}

/** Add days to a YYYY-MM-DD string, returning YYYY-MM-DD. */
export function addDays(iso, days) {
  const dt = parseISODate(iso);
  dt.setUTCDate(dt.getUTCDate() + days);
  return formatISODate(dt);
}

/** Monday of the week containing the given YYYY-MM-DD date. */
function toMonday(iso) {
  const dt = parseISODate(iso);
  const day = dt.getUTCDay();             // 0 = Sun, 1 = Mon, …
  const diff = day === 0 ? -6 : 1 - day;  // Sunday belongs to the week before
  dt.setUTCDate(dt.getUTCDate() + diff);
  return formatISODate(dt);
}

/** The seven dates [Mon … Sun] of the week starting at the given Monday. */
function weekDates(mondayISO) {
  return Array.from({ length: 7 }, (_, i) => addDays(mondayISO, i));
}

const DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

/**
 * Owns the calendar's state: the visible week, scheduled posts, the
 * approval queue, and all CRUD actions. Mirrors usePanel's approach.
 */
export function useCalendar() {
  const today = istToday();
  const [weekStart, setWeekStart] = useState(() => toMonday(today));
  const [posts, setPosts] = useState([]);
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bootstrapped = useRef(false);

  // ── Derived ──────────────────────────────────────────────────────
  const dates = weekDates(weekStart);
  const days = dates.map((d, i) => ({
    name: DAY_NAMES[i],
    date: d,
    isToday: d === today,
    posts: posts.filter((p) => p.scheduled_date === d),
  }));

  const stats = {
    total: posts.length,
    scheduled: posts.filter((p) => p.status === "scheduled").length,
    live: posts.filter((p) => p.status === "live").length,
    inQueue: queue.length,
  };

  // ── Fetchers ─────────────────────────────────────────────────────
  const fetchPosts = useCallback(async (week) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getPosts(week);
      setPosts(res.posts ?? []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await api.getQueue();
      setQueue(res.queue ?? []);
    } catch {
      // Queue fetch failure is non-fatal.
    }
  }, []);

  // Bootstrap: load posts for current week + queue.
  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    fetchPosts(weekStart);
    fetchQueue();
  }, [weekStart, fetchPosts, fetchQueue]);

  // When the week changes, reload posts.
  const prevWeek = useRef(weekStart);
  useEffect(() => {
    if (prevWeek.current !== weekStart) {
      prevWeek.current = weekStart;
      fetchPosts(weekStart);
    }
  }, [weekStart, fetchPosts]);

  // ── Week navigation ──────────────────────────────────────────────
  // addDays keeps the arithmetic on plain calendar dates — stepping a week
  // must never depend on the browser's timezone.
  const goToPrevWeek = useCallback(() => {
    setWeekStart((ws) => addDays(ws, -7));
  }, []);

  const goToNextWeek = useCallback(() => {
    setWeekStart((ws) => addDays(ws, 7));
  }, []);

  const goToToday = useCallback(() => {
    setWeekStart(toMonday(today));
  }, [today]);

  // ── Actions ──────────────────────────────────────────────────────
  const schedule = useCallback(
    async (data) => {
      setError(null);
      try {
        await api.schedulePost(data);
        await fetchPosts(weekStart);
        await fetchQueue();
      } catch (e) {
        setError(e.message);
      }
    },
    [weekStart, fetchPosts, fetchQueue],
  );

  const publish = useCallback(
    async (id) => {
      setError(null);
      try {
        await api.publishPost(id);
        await fetchPosts(weekStart);
      } catch (e) {
        setError(e.message);
      }
    },
    [weekStart, fetchPosts],
  );

  const remove = useCallback(
    async (id) => {
      setError(null);
      try {
        await api.deletePost(id);
        await fetchPosts(weekStart);
      } catch (e) {
        setError(e.message);
      }
    },
    [weekStart, fetchPosts],
  );

  const approveItem = useCallback(
    async (id) => {
      try {
        await api.approveQueueItem(id);
        await fetchQueue();
      } catch (e) {
        setError(e.message);
      }
    },
    [fetchQueue],
  );

  const rejectItem = useCallback(
    async (id) => {
      try {
        await api.rejectQueueItem(id);
        await fetchQueue();
      } catch (e) {
        setError(e.message);
      }
    },
    [fetchQueue],
  );

  const addToQueue = useCallback(
    async (data) => {
      try {
        await api.addToQueue(data);
        await fetchQueue();
      } catch (e) {
        setError(e.message);
      }
    },
    [fetchQueue],
  );

  const refresh = useCallback(() => {
    fetchPosts(weekStart);
    fetchQueue();
  }, [weekStart, fetchPosts, fetchQueue]);

  return {
    // state
    weekStart,
    today,
    days,
    dates,
    posts,
    queue,
    stats,
    loading,
    error,
    // navigation
    goToPrevWeek,
    goToNextWeek,
    goToToday,
    // actions
    schedule,
    publish,
    remove,
    approveItem,
    rejectItem,
    addToQueue,
    refresh,
  };
}
