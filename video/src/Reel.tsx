import React from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from "remotion";
import { CUES } from "./lib/anim";
import { Paper, Watermark } from "./lib/ui";
import { Bench, Diff, Outro, PosterArt, Problem, Route, Rule } from "./scenes";

const S = CUES.scene;
const SCENES = [
  { from: S.problem, to: S.rule, C: Problem },
  { from: S.rule, to: S.diff, C: Rule },
  { from: S.diff, to: S.route, C: Diff },
  { from: S.route, to: S.bench, C: Route },
  { from: S.bench, to: S.outro, C: Bench },
  { from: S.outro, to: S.end + 1, C: Outro },
];

export const Reel: React.FC = () => {
  const frame = useCurrentFrame();
  // Feeds thumbnail an early frame, so the first PRE seconds hold the key art.
  const t = frame / CUES.fps - CUES.pre;
  return (
    <AbsoluteFill>
      <Paper frame={frame} />
      {t < 0 ? (
        <PosterArt />
      ) : (
        SCENES.filter((s) => t >= s.from - 0.3 && t <= s.to + 0.3).map(({ from, C }) => <C key={from} t={t} />)
      )}
      <Watermark />
      <Audio src={staticFile("music.wav")} />
    </AbsoluteFill>
  );
};

export const Poster: React.FC = () => (
  <AbsoluteFill>
    <Paper frame={0} />
    <PosterArt />
    <Watermark />
  </AbsoluteFill>
);
