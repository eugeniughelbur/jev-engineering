import React from "react";
import { Composition } from "remotion";
import { CUES } from "./lib/anim";
import { Poster, Reel } from "./Reel";

export const Root: React.FC = () => (
  <>
    <Composition
      id="Reel"
      component={Reel}
      durationInFrames={Math.round((CUES.pre + CUES.duration) * CUES.fps)}
      fps={CUES.fps}
      width={1920}
      height={1080}
    />
    <Composition id="Poster" component={Poster} durationInFrames={1} fps={CUES.fps} width={1920} height={1080} />
  </>
);
