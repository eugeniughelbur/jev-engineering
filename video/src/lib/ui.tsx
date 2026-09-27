// The sketchnote look: sepia-cream lined paper, navy marker ink, one rust
// accent, emerald for "the good path". Same palette as the post image.

import React from "react";
import { loadFont as loadGeist } from "@remotion/google-fonts/Geist";
import { loadFont as loadGeistMono } from "@remotion/google-fonts/GeistMono";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadSora } from "@remotion/google-fonts/Sora";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";
import { wobble } from "./anim";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const opts = (weights: string[]): any => ({ weights, subsets: ["latin"], ignoreTooManyRequestsWarning: true });
const geist = loadGeist("normal", opts(["400", "500", "700", "800"])).fontFamily;
const spaceGrotesk = loadSpaceGrotesk("normal", opts(["500", "700"])).fontFamily;
const sora = loadSora("normal", opts(["500", "700", "800"])).fontFamily;
const inter = loadInter("normal", opts(["500", "700", "800"])).fontFamily;

// One text stack: Geist, then Space Grotesk, Sora and Inter for any missing glyph.
const STACK = `${geist}, ${spaceGrotesk}, ${sora}, ${inter}, sans-serif`;
export const MARKER = STACK; // headlines, set heavy where used
export const HAND = STACK; // body and labels
export const MONO = `${loadGeistMono("normal", opts(["400", "500", "700"])).fontFamily}, ui-monospace, monospace`;

export const C = {
  paper: "#EDE3D2",
  line: "rgba(26,40,64,0.08)",
  ink: "#1A2840",
  soft: "rgba(26,40,64,0.55)",
  rust: "#C8612D",
  green: "#2E8B57",
  gray: "#8A8A8A",
  card: "#FBF6EC",
  purple: "#6B4FA0",
};

export const abs: React.CSSProperties = { position: "absolute" };

export const Paper: React.FC<{ frame: number }> = ({ frame }) => (
  <>
    <div
      style={{
        ...abs,
        inset: 0,
        background: C.paper,
        backgroundImage: `repeating-linear-gradient(to bottom, transparent 0, transparent 53px, ${C.line} 53px, ${C.line} 55px)`,
      }}
    />
    <svg style={{ ...abs, inset: 0, mixBlendMode: "multiply", opacity: 0.22 }} width={1920} height={1080}>
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={Math.floor(frame / 3) % 40} />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  </>
);

export const Watermark: React.FC = () => (
  <div style={{ ...abs, right: 64, bottom: 44, fontFamily: MONO, fontSize: 22, color: C.soft }}>
    theaioperator.io
  </div>
);

/** A hand-drawn underline, drawn left to right as `p` goes 0 to 1. */
export const Underline: React.FC<{ width: number; p: number; color?: string; y?: number }> = ({
  width,
  p,
  color = C.rust,
  y = 0,
}) => (
  <svg width={width} height={28} style={{ display: "block", marginTop: y, overflow: "visible" }}>
    <path
      d={`M4 16 C ${width * 0.3} 6, ${width * 0.6} 24, ${width - 4} 12`}
      fill="none"
      stroke={color}
      strokeWidth={9}
      strokeLinecap="round"
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - p}
    />
  </svg>
);

/** A file card: the thing a path rule judges by its name alone. */
export const FileCard: React.FC<{
  name: string;
  x: number;
  y: number;
  scale?: number;
  rot?: number;
  stamp?: number;
  tone?: "plain" | "safe";
  opacity?: number;
}> = ({ name, x, y, scale = 1, rot = 0, stamp = 0, tone = "plain", opacity = 1 }) => (
  <div
    style={{
      ...abs,
      left: x,
      top: y,
      minWidth: 300,
      height: 84,
      paddingRight: stamp > 0 ? 64 : 30,
      whiteSpace: "nowrap",
      transform: `translate(-50%,-50%) scale(${scale}) rotate(${rot}deg)`,
      opacity,
      background: C.card,
      border: `4px solid ${C.ink}`,
      borderRadius: 10,
      boxShadow: `6px 6px 0 ${C.ink}`,
      display: "flex",
      alignItems: "center",
      gap: 16,
      paddingLeft: 22,
      fontFamily: MONO,
      fontWeight: 700,
      fontSize: 30,
      color: C.ink,
    }}
  >
    <svg width={30} height={38} style={{ flex: "none" }}>
      <path
        d="M3 3 H19 L27 11 V35 H3 Z M19 3 V11 H27"
        fill={tone === "safe" ? "#E4EFE6" : C.paper}
        stroke={C.ink}
        strokeWidth={3.5}
        strokeLinejoin="round"
      />
    </svg>
    {name}
    {stamp > 0 && (
      <div
        style={{
          ...abs,
          right: -40,
          top: -42,
          transform: `scale(${1.8 - 0.8 * stamp}) rotate(${-14 + wobble(name.length, 4)}deg)`,
          opacity: Math.min(1, stamp * 1.6),
          padding: "4px 14px",
          border: `5px solid ${C.rust}`,
          borderRadius: 8,
          color: C.rust,
          background: "rgba(237,227,210,0.9)",
          fontFamily: MONO,
          fontWeight: 700,
          fontSize: 32,
          letterSpacing: 2,
        }}
      >
        CVE
      </div>
    )}
  </div>
);

/** The rust sunburst that stands for Jev, same as in the post image. */
export const Burst: React.FC<{ size: number; spin: number; label?: string }> = ({ size, spin, label = "JEV" }) => {
  const pts: string[] = [];
  const n = 14;
  for (let i = 0; i < n * 2; i++) {
    const r = i % 2 === 0 ? size / 2 : size / 2.9;
    const a = (i / (n * 2)) * Math.PI * 2 + spin;
    pts.push(`${size / 2 + r * Math.cos(a)},${size / 2 + r * Math.sin(a)}`);
  }
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ overflow: "visible" }}>
        <polygon points={pts.join(" ")} fill={C.rust} stroke={C.ink} strokeWidth={5} strokeLinejoin="round" />
      </svg>
      <div
        style={{
          ...abs,
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: MARKER, fontWeight: 800, letterSpacing: -1,
          fontSize: size * 0.24,
          color: C.ink,
        }}
      >
        {label}
      </div>
    </div>
  );
};

/** A marker-drawn checkbox with a score bar, for one of Jev's checks. */
export const CheckRow: React.FC<{ label: string; p: number; score: number; hot: boolean }> = ({
  label,
  p,
  score,
  hot,
}) => {
  const shown = score * p;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 18, height: 50 }}>
      <div
        style={{
          width: 34,
          height: 34,
          border: `4px solid ${C.ink}`,
          borderRadius: 6,
          background: hot && p > 0.95 ? C.rust : "transparent",
        }}
      />
      <div style={{ width: 250, fontFamily: HAND, fontWeight: 700, fontSize: 30, color: C.ink }}>{label}</div>
      <div style={{ width: 330, height: 22, border: `3px solid ${C.ink}`, borderRadius: 12, overflow: "hidden" }}>
        <div
          style={{
            width: `${shown * 100}%`,
            height: "100%",
            background: hot ? C.rust : C.green,
          }}
        />
      </div>
      <div style={{ width: 80, fontFamily: MONO, fontSize: 26, color: hot ? C.rust : C.soft }}>
        {shown.toFixed(2)}
      </div>
    </div>
  );
};
