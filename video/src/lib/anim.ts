// Animation helpers. Scenes work in absolute seconds `t`, so every cue in
// cues.json can be used as a literal.

import cues from "../cues.json";

export const CUES = cues;
export const BEAT = 60 / cues.bpm;

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));

export const easeOut = (x: number) => 1 - Math.pow(1 - clamp(x), 3);
export const easeInOut = (x: number) => {
  const v = clamp(x);
  return v < 0.5 ? 4 * v * v * v : 1 - Math.pow(-2 * v + 2, 3) / 2;
};
// Overshoots past 1 before settling: the "hand-placed" pop.
export const backOut = (x: number, s = 1.9) => {
  const v = clamp(x) - 1;
  return 1 + (s + 1) * v * v * v + s * v * v;
};

/** 0 before `at`, 1 after `at + dur`, eased between. */
export const ramp = (t: number, at: number, dur = 0.3, ease = easeOut) =>
  ease((t - at) / dur);

/** Pop in with overshoot. */
export const pop = (t: number, at: number, dur = 0.35) => (t < at ? 0 : backOut((t - at) / dur));

/** A short pulse after each beat, for things that breathe with the kick. */
export const pulse = (t: number, from: number, to: number, strength = 0.035) => {
  if (t < from || t > to) return 1;
  const phase = ((t - from) % BEAT) / BEAT;
  return 1 + strength * Math.exp(-phase * 9);
};

/** Fade a scene in at its start and out at its end. */
export const sceneAlpha = (t: number, start: number, end: number, fade = 0.2) =>
  clamp((t - start) / fade) * clamp((end - t) / fade);

/** Deterministic jitter, so hand-drawn wobble is stable across renders. */
export const wobble = (seed: number, amp = 1) => Math.sin(seed * 12.9898) * amp;
