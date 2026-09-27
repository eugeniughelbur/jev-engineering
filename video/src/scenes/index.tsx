import React from "react";
import { CUES, clamp, easeInOut, pop, pulse, ramp, sceneAlpha, wobble } from "../lib/anim";
import { Burst, C, CheckRow, FileCard, HAND, MARKER, MONO, Underline, abs } from "../lib/ui";

type P = { t: number };
const S = CUES.scene;

const Title: React.FC<{ children: React.ReactNode; p: number; top?: number; size?: number; color?: string }> = ({
  children,
  p,
  top = 110,
  size = 92,
  color = C.ink,
}) => (
  <div
    style={{
      ...abs,
      top,
      left: 0,
      right: 0,
      textAlign: "center",
      fontFamily: MARKER, fontWeight: 800, letterSpacing: -1,
      fontSize: size,
      color,
      opacity: clamp(p * 2),
      transform: `translateY(${(1 - p) * 30}px) scale(${0.92 + 0.08 * p})`,
    }}
  >
    {children}
  </div>
);

// ---------------------------------------------------------------- 1. problem
export const Problem: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.problem, S.rule, 0.15);
  const out = ramp(t, 3.75, 0.25);
  return (
    <div style={{ ...abs, inset: 0, opacity: a, transform: `scale(${1 + out * 0.15})` }}>
      <div
        style={{
          ...abs,
          top: 250,
          left: 160,
          right: 160,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "0 28px",
          fontFamily: MARKER, fontWeight: 800, letterSpacing: -1,
          fontSize: 96,
          color: C.ink,
        }}
      >
        {CUES.problem.words.map(([at, w], i) => {
          const p = pop(t, at as number, 0.3);
          return (
            <span key={i} style={{ display: "inline-block", opacity: clamp(p * 3), transform: `scale(${p}) rotate(${wobble(i, 1.5)}deg)` }}>
              {w as string}
            </span>
          );
        })}
      </div>
      <div style={{ ...abs, top: 560, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 70 }}>
        {CUES.problem.slams.map(([at, w], i) => {
          const p = pop(t, at as number, 0.28);
          return (
            <div key={i} style={{ textAlign: "center", opacity: clamp(p * 3), transform: `scale(${p * 1.0}) rotate(${wobble(i + 7, 3)}deg)` }}>
              <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 150, color: C.rust }}>{w as string}</div>
              <div style={{ fontFamily: MONO, fontSize: 30, color: C.soft }}>full re-read #{i + 1}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- 2. the path rule
const CVE_FILES = ["validators.py", "cache.py", "utils.js", "trans_real.py", "signing.py", "smtp.py"];

export const Rule: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.rule, S.diff);
  const R = CUES.rule;
  const cap = ramp(t, R.caption, 0.35);
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <Title p={ramp(t, R.title, 0.35)}>So you skip by filename.</Title>
      {/* the rule, as a sticky note */}
      <div
        style={{
          ...abs,
          left: 150,
          top: 300,
          width: 680,
          padding: "30px 38px",
          background: "#F7E7B4",
          border: `4px solid ${C.ink}`,
          boxShadow: `8px 8px 0 ${C.ink}`,
          transform: `rotate(-2.5deg) scale(${pop(t, R.title + 0.25, 0.4)})`,
          fontFamily: HAND,
          fontWeight: 700,
          fontSize: 38,
          color: C.ink,
          lineHeight: 1.45,
        }}
      >
        <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 40, marginBottom: 10, whiteSpace: "nowrap" }}>Full review if the path is:</div>
        {[".github/workflows/", "auth*, login*, token*", "migrations/", "package.json, Dockerfile"].map((r) => (
          <div key={r} style={{ fontFamily: MONO, fontSize: 30, fontWeight: 500 }}>
            • {r}
          </div>
        ))}
        <div style={{ marginTop: 14, color: C.soft }}>everything else: quick</div>
      </div>
      {/* the files that pass it */}
      {CVE_FILES.map((name, i) => {
        const p = pop(t, R.cards[i], 0.35);
        const st = ramp(t, R.stamps[i], 0.18);
        const col = i % 2;
        const row = Math.floor(i / 2);
        return (
          <React.Fragment key={name}>
            <FileCard
              name={name}
              x={1110 + col * 440 + (1 - p) * 300}
              y={360 + row * 150}
              scale={p}
              rot={wobble(i + 3, 3)}
              stamp={st}
              opacity={clamp(p * 2)}
            />
            <div
              style={{
                ...abs,
                left: 1110 + col * 440 - 60,
                top: 360 + row * 150 + 46,
                fontFamily: HAND,
                fontSize: 26,
                color: C.gray,
                opacity: clamp(p * 2) * (1 - st * 0.4),
              }}
            >
              → quick review
            </div>
          </React.Fragment>
        );
      })}
      <div style={{ ...abs, left: 0, right: 0, top: 830, textAlign: "center", opacity: clamp(cap * 2) }}>
        <div style={{ display: "inline-block" }}>
          <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 80, color: C.ink }}>13 CVE fixes. Waved through.</div>
          <Underline width={1120} p={ramp(t, R.caption + 0.3, 0.5)} />
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- 3. read the diff
const DIFF: [string, string][] = [
  ["@@", "def open_upload(root, name):"],
  ["-", '    if ".." in name or name.startswith("/"):'],
  ["-", '        raise ValueError("bad path")'],
  [" ", '    return open(os.path.join(root, name), "rb")'],
];
const CHECKS: [string, number][] = [
  ["permissions", 0.58],
  ["network call", 0.04],
  ["shell / eval", 0.07],
  ["unsafe loading", 0.03],
  ["secret in log", 0.02],
  ["flag flipped on", 0.24],
  ["crypto / TLS", 0.03],
  ["input check", 0.98],
  ["CI / supply chain", 0.02],
  ["talks to reviewer", 0.03],
];

export const Diff: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.diff, S.route);
  const D = CUES.diff;
  const fan = pop(t, D.fanout, 0.45);
  const verdict = pop(t, D.verdict, 0.3);
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <Title p={ramp(t, S.diff, 0.35)} top={70}>
        Read the diff instead.
      </Title>
      <div
        style={{
          ...abs,
          left: 110,
          top: 250,
          width: 860,
          padding: "26px 30px",
          background: "#1A2840",
          borderRadius: 14,
          boxShadow: `10px 10px 0 rgba(26,40,64,0.25)`,
          fontFamily: MONO,
          fontSize: 27,
          lineHeight: 1.8,
        }}
      >
        <div style={{ color: "#C9D1E0", marginBottom: 10, fontSize: 24 }}>app/files.py · 1 commit</div>
        {DIFF.map(([k, line], i) => {
          const p = ramp(t, D.lines[i], 0.2);
          const color = k === "-" ? "#F2A07B" : k === "+" ? "#8FD3A9" : k === "@@" ? "#8FA3C8" : "#E9E4D8";
          const bg = k === "-" ? "rgba(200,97,45,0.22)" : k === "+" ? "rgba(46,139,87,0.2)" : "transparent";
          const hot = k === "-" && t > D.hit;
          return (
            <div
              key={i}
              style={{
                opacity: p,
                transform: `translateX(${(1 - p) * -30}px)`,
                color,
                background: bg,
                whiteSpace: "pre",
                outline: hot ? `3px solid ${C.rust}` : "none",
                borderRadius: 4,
              }}
            >
              {k === "@@" ? "@@ " : `${k} `}
              {line}
            </div>
          );
        })}
      </div>
      <div
        style={{
          ...abs,
          left: 110,
          top: 720,
          width: 860,
          fontFamily: HAND,
          fontWeight: 700,
          fontSize: 36,
          color: C.ink,
          opacity: ramp(t, D.fanout, 0.4),
        }}
      >
        "Is this risky?" is too vague.
        <br />
        So it becomes <span style={{ color: C.rust }}>10 yes/no checks</span>, asked at once.
      </div>
      {/* Jev */}
      <div style={{ ...abs, left: 1030, top: 210, transform: `scale(${fan})`, transformOrigin: "left center" }}>
        <Burst size={150} spin={t * 0.6} />
      </div>
      <div style={{ ...abs, left: 1200, top: 258, fontFamily: MONO, fontSize: 26, color: C.soft, opacity: clamp(fan) }}>
        one request · ~0.3s
      </div>
      <div style={{ ...abs, left: 1040, top: 390 }}>
        {CHECKS.map(([label, score], i) => {
          const hot = score > 0.9;
          const start = hot ? D.hit : D.checks_fill + i * 0.08;
          const p = ramp(t, start, hot ? 0.5 : 0.4);
          return (
            <div key={label} style={{ opacity: clamp((t - D.fanout - i * 0.05) * 4) }}>
              <CheckRow label={label} p={p} score={score} hot={hot} />
            </div>
          );
        })}
      </div>
      <div
        style={{
          ...abs,
          left: 1180,
          top: 900,
          padding: "8px 26px",
          border: `6px solid ${C.rust}`,
          borderRadius: 10,
          color: C.rust,
          fontFamily: MARKER, fontWeight: 800, letterSpacing: -1,
          fontSize: 64,
          opacity: clamp(verdict * 2),
          transform: `scale(${1.6 - 0.6 * clamp(verdict)}) rotate(-6deg)`,
          background: "rgba(237,227,210,0.85)",
        }}
      >
        FULL REVIEW
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- 4. the fork
const SAFE = ["README.md", "tests/", "docs/", "rename"];
const along = (p: number, top: boolean) => {
  // Two hand-drawn lanes from a shared start. Returns x, y at progress p.
  const x = 360 + p * 1100;
  const bend = Math.sin(clamp(p) * Math.PI * 0.5);
  const y = 560 + (top ? -250 : 230) * bend;
  return { x, y };
};

export const Route: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.route, S.bench);
  const R = CUES.route;
  const draw = ramp(t, R.fork, 0.6, easeInOut);
  const done = R.cves.filter((c) => t >= c + 0.6).length;
  const total = pop(t, R.total, 0.35);
  const lane = (top: boolean) => {
    const pts = Array.from({ length: 30 }, (_, i) => along(i / 29, top));
    return `M ${pts.map((q) => `${q.x} ${q.y}`).join(" L ")}`;
  };
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <svg style={{ ...abs, inset: 0 }} width={1920} height={1080}>
        <path d={lane(true)} fill="none" stroke={C.gray} strokeWidth={14} strokeDasharray="30 24" strokeLinecap="round" opacity={draw} />
        <path d={lane(false)} fill="none" stroke={C.green} strokeWidth={26} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - draw} />
      </svg>
      <div style={{ ...abs, left: 250, top: 500, transform: `scale(${pop(t, R.fork - 0.1, 0.4)})` }}>
        <Burst size={130} spin={t * 0.8} />
      </div>
      <div style={{ ...abs, left: 1530, top: 205, fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 58, color: C.gray, opacity: draw }}>
        QUICK
      </div>
      <div style={{ ...abs, left: 1440, top: 830, fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 62, color: C.green, opacity: draw, whiteSpace: "nowrap" }}>
        FULL REVIEW
      </div>
      {R.safe.map((at, i) => {
        const p = ramp(t, at, 0.9, easeInOut);
        if (p <= 0) return null;
        const { x, y } = along(p, true);
        return <FileCard key={i} name={SAFE[i]} tone="safe" x={x} y={y} scale={0.7} rot={wobble(i + 30, 4)} opacity={1 - clamp((p - 0.9) * 10)} />;
      })}
      {R.cves.map((at, i) => {
        const p = ramp(t, at, 0.9, easeInOut);
        if (p <= 0) return null;
        const { x, y } = along(p, false);
        return <FileCard key={i} name={`CVE fix ${i + 1}`} x={x} y={y} scale={0.7} rot={wobble(i + 11, 5)} stamp={1} opacity={1 - clamp((p - 0.9) * 10)} />;
      })}
      <div style={{ ...abs, left: 0, right: 0, top: 70, textAlign: "center", fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 84, color: C.ink }}>
        <span style={{ display: "inline-block", transform: `scale(${1 + 0.25 * (total > 0 ? Math.max(0, 1.2 - total) : 0)})`, color: t >= R.total ? C.rust : C.ink }}>
          {t >= R.total ? 13 : done} / 13
        </span>{" "}
        CVE fixes → full review
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 975, textAlign: "center", fontFamily: HAND, fontWeight: 700, fontSize: 34, color: C.soft, opacity: ramp(t, R.fork + 0.4, 0.4) }}>
        Any error, timeout or missing key → full. It can raise a review, never lower one.
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- 5. the numbers
const STATS: [string, string][] = [
  ["561", "commits from FastAPI, Express, Django"],
  ["42%", "could still skip the full review"],
  ["13 / 13", "CVE fixes sent to full review"],
  ["$0.029", "Jev, for the whole run"],
];

export const Bench: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.bench, S.outro);
  const B = CUES.bench;
  return (
    <div style={{ ...abs, inset: 0, opacity: a, transform: `scale(${pulse(t, 20, 25.5, 0.012)})` }}>
      <div style={{ ...abs, left: 170, right: 170, top: 120, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "60px 90px" }}>
        {STATS.map(([big, small], i) => {
          const p = pop(t, B.slams[i], 0.3);
          return (
            <div key={big} style={{ opacity: clamp(p * 3), transform: `scale(${p}) rotate(${wobble(i + 50, 1.5)}deg)` }}>
              <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 176, lineHeight: 1, color: i === 2 ? C.rust : C.ink }}>{big}</div>
              <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 40, color: C.ink, marginTop: 10 }}>{small}</div>
            </div>
          );
        })}
      </div>
      <div
        style={{
          ...abs,
          left: 0,
          right: 0,
          top: 930,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 26,
          color: C.soft,
          opacity: ramp(t, B.disclosure, 0.4),
        }}
      >
        commits, not pushes · a flag is not a bug found · rerun it yourself: bench_public.py
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- 6. install
const LINE = "- uses: eugeniughelbur/jev-engineering/review-router@v1";

export const Outro: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.outro, S.end + 1, 0.2);
  const O = CUES.outro;
  const n = Math.round(LINE.length * clamp((t - O.type_start) / (O.type_end - O.type_start)));
  const title = pop(t, O.title, 0.4);
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 0, right: 0, top: 170, textAlign: "center", transform: `scale(${title})`, opacity: clamp(title * 2) }}>
        <div style={{ display: "inline-block" }}>
          <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 150, color: C.ink }}>review-router</div>
          <Underline width={980} p={ramp(t, O.title + 0.25, 0.5)} />
        </div>
        <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 52, color: C.ink, marginTop: 6 }}>
          read the diff, not the filename
        </div>
      </div>
      <div
        style={{
          ...abs,
          left: 230,
          right: 230,
          top: 590,
          padding: "30px 40px",
          background: C.ink,
          borderRadius: 14,
          fontFamily: MONO,
          fontSize: 38,
          color: "#E9E4D8",
          whiteSpace: "pre",
          opacity: ramp(t, O.type_start - 0.2, 0.2),
        }}
      >
        {LINE.slice(0, n)}
        <span style={{ opacity: Math.floor(t * 4) % 2 ? 1 : 0, color: C.rust }}>▍</span>
      </div>
      <div
        style={{
          ...abs,
          left: 0,
          right: 0,
          top: 820,
          textAlign: "center",
          fontFamily: MONO,
          fontWeight: 700,
          fontSize: 42,
          color: C.green,
          opacity: ramp(t, O.url, 0.4),
        }}
      >
        github.com/eugeniughelbur/jev-engineering
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- key art
export const PosterArt: React.FC = () => (
  <div style={{ ...abs, inset: 0 }}>
    <div style={{ ...abs, left: 0, right: 0, top: 90, textAlign: "center" }}>
      <div style={{ display: "inline-block" }}>
        <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 138, color: C.ink, lineHeight: 1.05 }}>13 CVE fixes</div>
        <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 138, color: C.ink, lineHeight: 1.05 }}>looked harmless</div>
        <Underline width={1100} p={1} />
      </div>
    </div>
    {CVE_FILES.map((name, i) => (
      <FileCard key={name} name={name} x={420 + (i % 3) * 540} y={610 + Math.floor(i / 3) * 150} rot={wobble(i + 3, 3)} stamp={1} />
    ))}
    <div style={{ ...abs, left: 0, right: 0, top: 900, textAlign: "center", fontFamily: HAND, fontWeight: 700, fontSize: 58, color: C.ink }}>
      read the diff, not the filename · <span style={{ color: C.rust }}>review-router</span>
    </div>
  </div>
);

