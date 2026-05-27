'use client';

import { useEffect, useRef } from 'react';

export function useAnimationFrame(
  callback: (delta: number) => void,
  active: boolean
): void {
  const callbackRef = useRef(callback);
  const rafRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number | null>(null);

  // Keep callback ref up to date
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!active) {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
        lastTimeRef.current = null;
      }
      return;
    }

    const loop = (timestamp: number) => {
      const last = lastTimeRef.current;
      const delta = last !== null ? timestamp - last : 0;
      lastTimeRef.current = timestamp;
      callbackRef.current(delta);
      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
        lastTimeRef.current = null;
      }
    };
  }, [active]);
}
