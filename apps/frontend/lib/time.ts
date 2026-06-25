/**
 * Time helpers.
 *
 * IMPORTANT: the backend emits Unix timestamps in **seconds** (Python `time.time()`),
 * but `Date.now()` is in **milliseconds**. Diffing them directly produced the
 * "494598h ago" bug. Always convert backend seconds → ms before diffing.
 */
export function secondsToMs(tsSeconds: number | undefined | null): number {
  return (tsSeconds ?? 0) * 1000;
}

/** Whole seconds elapsed since a backend (seconds) timestamp. Never negative. */
export function elapsedSeconds(tsSeconds: number | undefined | null): number {
  return Math.max(0, Math.floor((Date.now() - secondsToMs(tsSeconds)) / 1000));
}

/** Human "Ns / Nm / Nh / Nd ago" from a backend (seconds) timestamp. */
export function timeAgo(tsSeconds: number | undefined | null): string {
  const s = elapsedSeconds(tsSeconds);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}
