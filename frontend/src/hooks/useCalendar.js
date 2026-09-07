import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api/calendarApi.js";

/**
 * Returns the ISO date string (YYYY-MM-DD) for the Monday of the week
 * containing the given date.
 */
function toMonday(d) {
  const dt = new Date(d);
  const day = dt.getDay();            // 0 = Sun, 1 = Mon, …
  const diff = day === 0 ? -6 : 1 - day;
  dt.setDate(dt.getDate() + diff);
  return dt.toISOString().slice(0, 10);
}

/**
 * Build an array of 7 date strings [Mon … Sun] for the week starting
 * at the given Monday ISO string.
 */
function weekDates(mondayISO) {
  const dates = [];
  const d = new Date(mondayISO + "T00:00:00");
  for (let i = 0; i < 7; i++) {
    const dt = new Date(d);
    dt.setDate(d.getDate() + i);
    dates.push(dt.toISOString().slice(0, 10));
  }
  return dates;
}

const DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

/**
 * Owns the calendar's state: the visible week, scheduled posts, the
 * approval queue, and all CRUD actions. Mirrors usePanel's approach.
 */
export function useCalendar() {
  const today = new Date().toISOString().slice(0, 10);
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
  const goToPrevWeek = useCallback(() => {
    setWeekStart((ws) => {
      const d = new Date(ws + "T00:00:00");
      d.setDate(d.getDate() - 7);
      return d.toISOString().slice(0, 10);
    });
  }, []);

  const goToNextWeek = useCallback(() => {
    setWeekStart((ws) => {
      const d = new Date(ws + "T00:00:00");
      d.setDate(d.getDate() + 7);
      return d.toISOString().slice(0, 10);
    });
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
