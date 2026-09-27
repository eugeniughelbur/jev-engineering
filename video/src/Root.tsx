import React from "react";
import { Composition } from "remotion";
import { CUES } from "./lib/anim";
import repoCues from "./cues-repo.json";
import { Poster, Reel, RepoPosterStill, RepoReel } from "./Reel";

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
    <Composition
      id="RepoReel"
      component={RepoReel}
      durationInFrames={Math.round((repoCues.pre + repoCues.duration) * repoCues.fps)}
      fps={repoCues.fps}
      width={1920}
      height={1080}
    />
    <Composition id="RepoPoster" component={RepoPosterStill} durationInFrames={1} fps={repoCues.fps} width={1920} height={1080} />
    <Composition id="Poster" component={Poster} durationInFrames={1} fps={CUES.fps} width={1920} height={1080} />
  </>
);
