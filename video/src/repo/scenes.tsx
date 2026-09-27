// The whole-repo reel: gate, attack kit, question packs, review-router,
// use cases, install. Every number is from the repo README or results/.

import React from "react";
import cues from "../cues-repo.json";
import { clamp, pop, pulse, ramp, sceneAlpha, wobble } from "../lib/anim";
import { Burst, C, FileCard, HAND, MARKER, MONO, Underline, abs } from "../lib/ui";

type P = { t: number };
const S = cues.scene;

const Heading: React.FC<{ n?: number; text: string; t: number; at: number; top?: number }> = ({ n, text, t, at, top = 90 }) => {
  const p = ramp(t, at, 0.35);
  return (
    <div style={{ ...abs, top, left: 0, right: 0, textAlign: "center", opacity: clamp(p * 2), transform: `translateY(${(1 - p) * 26}px)` }}>
      {n !== undefined && (
        <span style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 64, color: C.rust, marginRight: 22 }}>{n}.</span>
      )}
      <span style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 82, color: C.ink }}>{text}</span>
    </div>
  );
};

const Verdict: React.FC<{ v: string; p: number; size?: number }> = ({ v, p, size = 40 }) => {
  const col = v === "allow" ? C.green : C.rust;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 16px",
        border: `4px solid ${col}`,
        borderRadius: 8,
        color: col,
        fontFamily: MARKER, fontWeight: 800, letterSpacing: -1,
        fontSize: size,
        opacity: clamp(p * 2),
        transform: `scale(${1.5 - 0.5 * clamp(p)}) rotate(-4deg)`,
        background: "rgba(237,227,210,0.9)",
      }}
    >
      {v.toUpperCase()}
    </span>
  );
};

// ---------------------------------------------------------------- hook
export const Hook: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.hook, S.gate, 0.15);
  const H = cues.hook;
  const jev = pop(t, H.jev, 0.4);
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, top: 130, left: 0, right: 0, textAlign: "center" }}>
        {H.lines.map(([at, text], i) => {
          const p = ramp(t, at as number, 0.3);
          return (
            <div key={i} style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 70, color: i ? C.rust : C.ink, opacity: p, transform: `translateY(${(1 - p) * 20}px)` }}>
              {text as string}
            </div>
          );
        })}
      </div>
      <div style={{ ...abs, left: 170, top: 470, transform: `scale(${jev})` }}>
        <Burst size={220} spin={t * 0.7} />
      </div>
      <div style={{ ...abs, left: 460, top: 480, display: "flex", gap: 70 }}>
        {H.stats.map(([at, big], i) => {
          const p = pop(t, at as number, 0.3);
          return (
            <div key={i} style={{ opacity: clamp(p * 3), transform: `scale(${p})` }}>
              <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 126, color: C.ink, lineHeight: 1, whiteSpace: "nowrap" }}>{big as string}</div>
              <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 40, color: C.soft }}>{i ? "per check" : "median answer"}</div>
            </div>
          );
        })}
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 850, textAlign: "center", fontFamily: HAND, fontWeight: 700, fontSize: 54, color: C.ink, opacity: ramp(t, 3.4, 0.3) }}>
        So you can finally check <span style={{ color: C.rust }}>everything</span>.
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- gate
export const Gate: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.gate, S.attack);
  const G = cues.gate;
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <Heading n={1} text="A gate on every tool call." t={t} at={G.title} />
      <div style={{ ...abs, left: 200, right: 200, top: 280, padding: "34px 44px", background: C.ink, borderRadius: 16, boxShadow: "10px 10px 0 rgba(26,40,64,0.25)" }}>
        <div style={{ fontFamily: MONO, fontSize: 24, color: "#8FA3C8", marginBottom: 18 }}>coding agent → jev_gate.py → your shell</div>
        {G.rows.map(([at, cmd, verdict, reason, ms], i) => {
          const p = ramp(t, at as number, 0.25);
          const v = ramp(t, (at as number) + 0.45, 0.25);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", height: 108, opacity: p, transform: `translateX(${(1 - p) * -40}px)` }}>
              <div style={{ width: 760, fontFamily: MONO, fontSize: 34, color: "#E9E4D8" }}>
                <span style={{ color: C.green }}>$ </span>
                {cmd as string}
              </div>
              <div style={{ width: 200 }}>
                <Verdict v={verdict as string} p={v} />
              </div>
              <div style={{ fontFamily: MONO, fontSize: 26, color: "#C9D1E0", opacity: v }}>
                {reason as string} · {ms as string}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 790, textAlign: "center", opacity: ramp(t, G.caption, 0.35) }}>
        <div style={{ display: "inline-block" }}>
          <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 62, color: C.ink }}>Hard rules first. Jev for the long tail.</div>
          <Underline width={1150} p={ramp(t, G.caption + 0.25, 0.5)} />
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- attack
export const Attack: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.attack, S.packs);
  const A = cues.attack;
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <Heading n={2} text="Then I attacked it. 300 times." t={t} at={A.title} />
      <div style={{ ...abs, left: 230, top: 290, fontFamily: HAND, fontWeight: 700, fontSize: 36, color: C.soft }}>
        dangerous commands that got through, out of 30
      </div>
      {A.bars.map(([at, label, through], i) => {
        const p = ramp(t, at as number, 0.5);
        return (
          <div key={i} style={{ ...abs, left: 230, top: 370 + i * 190, opacity: clamp(p * 3) }}>
            <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 50, color: C.ink }}>{label as string}</div>
            <div style={{ display: "flex", gap: 10, marginTop: 14, alignItems: "center" }}>
              {Array.from({ length: 30 }, (_, k) => {
                const on = k < (through as number) && p > k / 30;
                return (
                  <div
                    key={k}
                    style={{
                      width: 36,
                      height: 46,
                      borderRadius: 6,
                      border: `3px solid ${C.ink}`,
                      background: on ? C.rust : "transparent",
                      opacity: p > k / 30 ? 1 : 0.15,
                    }}
                  />
                );
              })}
              <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 64, color: (through as number) ? C.rust : C.green, marginLeft: 30, opacity: p }}>
                {through as number} / 30
              </div>
            </div>
          </div>
        );
      })}
      <div style={{ ...abs, left: 0, right: 0, top: 800, textAlign: "center", transform: `scale(${pop(t, A.punch, 0.4)})` }}>
        <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 70, color: C.ink }}>
          Shouting doesn't get in. <span style={{ color: C.rust }}>Politeness does.</span>
        </div>
        <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 38, color: C.soft, marginTop: 8 }}>
          That's why the hard rules run before the model.
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- packs
export const Packs: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.packs, S.review);
  const K = cues.packs;
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <Heading n={3} text="Not only shell commands." t={t} at={K.title} />
      {K.cards.map(([at, kind, text, score, verdict], i) => {
        const p = pop(t, at as number, 0.4);
        const v = ramp(t, (at as number) + 0.75, 0.25);
        return (
          <div
            key={i}
            style={{
              ...abs,
              left: 170 + i * 820,
              top: 300,
              width: 760,
              padding: "34px 40px",
              background: C.card,
              border: `4px solid ${C.ink}`,
              borderRadius: 14,
              boxShadow: `8px 8px 0 ${C.ink}`,
              transform: `scale(${p}) rotate(${wobble(i + 60, 1.5)}deg)`,
              opacity: clamp(p * 2),
            }}
          >
            <div style={{ fontFamily: MONO, fontSize: 26, color: C.soft, letterSpacing: 2 }}>{(kind as string).toUpperCase()} · before it sends</div>
            <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 44, color: C.ink, margin: "20px 0 26px", minHeight: 120 }}>{text as string}</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: MONO, fontSize: 34, color: C.rust, opacity: v }}>{score as string}</span>
              <Verdict v={verdict as string} p={v} size={46} />
            </div>
          </div>
        );
      })}
      <div style={{ ...abs, left: 0, right: 0, top: 800, textAlign: "center", opacity: ramp(t, K.chips, 0.35) }}>
        <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 36, color: C.soft, marginBottom: 16 }}>five question packs ship</div>
        <div style={{ display: "inline-flex", gap: 22 }}>
          {["shell", "message", "money", "data", "publish"].map((c, i) => (
            <span
              key={c}
              style={{
                fontFamily: MONO,
                fontWeight: 700,
                fontSize: 36,
                padding: "8px 24px",
                border: `4px solid ${C.ink}`,
                borderRadius: 30,
                color: C.ink,
                transform: `scale(${pop(t, K.chips + i * 0.1, 0.3)})`,
                display: "inline-block",
              }}
            >
              {c}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- review-router
const CVE_FILES = ["validators.py", "cache.py", "utils.js", "trans_real.py", "signing.py", "smtp.py"];

export const Review: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.review, S.cases);
  const R = cues.review;
  const count = pop(t, R.count, 0.4);
  return (
    <div style={{ ...abs, inset: 0, opacity: a, transform: `scale(${pulse(t, 21, 26.5, 0.01)})` }}>
      <Heading n={4} text="It reads your pull requests too." t={t} at={R.title} />
      {CVE_FILES.map((name, i) => {
        const p = pop(t, R.cards[i], 0.35);
        return (
          <FileCard
            key={name}
            name={name}
            x={330 + (i % 3) * 630}
            y={330 + Math.floor(i / 3) * 140}
            scale={p}
            rot={wobble(i + 3, 3)}
            stamp={ramp(t, R.count - 0.2, 0.2)}
            opacity={clamp(p * 2)}
          />
        );
      })}
      <div style={{ ...abs, left: 0, right: 0, top: 560, textAlign: "center", transform: `scale(${count})`, opacity: clamp(count * 2) }}>
        <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 84, color: C.ink }}>
          A filename rule waved <span style={{ color: C.rust }}>13 CVE fixes</span> through.
        </div>
        <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 84, color: C.green }}>review-router sent all 13 to full review.</div>
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 820, display: "flex", justifyContent: "center", gap: 120 }}>
        {[["42%", "of 561 commits still skip"], ["$0.029", "for the whole run"]].map(([big, small], i) => {
          const p = pop(t, R.stats[i], 0.3);
          return (
            <div key={big} style={{ textAlign: "center", transform: `scale(${p})`, opacity: clamp(p * 3) }}>
              <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 96, color: C.ink, lineHeight: 1 }}>{big}</div>
              <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 34, color: C.soft }}>{small}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- use cases
const TILES: [string, string, string][] = [
  ["Inbox triage", "16 / 16", "emails sorted right"],
  ["AI writing tells", "12 / 12", "names the tell"],
  ["Slack follow-ups", "14 / 14", "messages waiting on you"],
  ["route", "fast · frontier", "which model for this turn"],
  ["rank", "255 options", "in one call"],
  ["keep", "347ms", "which context is still worth it"],
];

export const Cases: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.cases, S.outro);
  const K = cues.cases;
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <Heading n={5} text="And the decisions around it." t={t} at={K.title} />
      <div style={{ ...abs, left: 150, right: 150, top: 250, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 40 }}>
        {TILES.map(([name, big, small], i) => {
          const p = pop(t, K.tiles[i], 0.35);
          return (
            <div
              key={name}
              style={{
                padding: "26px 30px",
                background: i < 3 ? C.card : "#E7EEF0",
                border: `4px solid ${C.ink}`,
                borderRadius: 14,
                boxShadow: `7px 7px 0 ${C.ink}`,
                transform: `scale(${p}) rotate(${wobble(i + 80, 1.2)}deg)`,
                opacity: clamp(p * 2),
                height: 232,
              }}
            >
              <div style={{ fontFamily: i < 3 ? HAND : MONO, fontWeight: 700, fontSize: 38, color: C.ink }}>{name}</div>
              <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 54, color: C.rust, lineHeight: 1.3, whiteSpace: "nowrap" }}>{big}</div>
              <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 30, color: C.soft }}>{small}</div>
            </div>
          );
        })}
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 880, textAlign: "center", fontFamily: HAND, fontWeight: 700, fontSize: 44, color: C.ink, opacity: ramp(t, K.caption, 0.35) }}>
        One move every time: split a fuzzy question into <span style={{ color: C.rust }}>yes/no checks</span>, combine them in code.
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- outro
const INSTALL = "claude plugin install jev-engineering@jev-engineering";

export const RepoOutro: React.FC<P> = ({ t }) => {
  const a = sceneAlpha(t, S.outro, S.end + 1, 0.2);
  const O = cues.outro;
  const n = Math.round(INSTALL.length * clamp((t - O.type_start) / (O.type_end - O.type_start)));
  const title = pop(t, O.title, 0.4);
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 0, right: 0, top: 150, textAlign: "center", transform: `scale(${title})`, opacity: clamp(title * 2) }}>
        <div style={{ display: "inline-block" }}>
          <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 150, color: C.ink }}>jev-engineering</div>
          <Underline width={1150} p={ramp(t, O.title + 0.25, 0.5)} />
        </div>
        <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 52, color: C.ink, marginTop: 6 }}>the decision layer for AI agents</div>
      </div>
      <div
        style={{
          ...abs,
          left: 250,
          right: 250,
          top: 580,
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
        <span style={{ color: C.green }}>$ </span>
        {INSTALL.slice(0, n)}
        <span style={{ opacity: Math.floor(t * 4) % 2 ? 1 : 0, color: C.rust }}>▍</span>
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 800, textAlign: "center", opacity: ramp(t, O.url, 0.4) }}>
        <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 42, color: C.green }}>github.com/eugeniughelbur/jev-engineering</div>
        <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 34, color: C.soft, marginTop: 10 }}>free · MIT · every number measured</div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- key art
export const RepoPoster: React.FC = () => (
  <div style={{ ...abs, inset: 0 }}>
    <div style={{ ...abs, left: 0, right: 0, top: 150, textAlign: "center" }}>
      <div style={{ display: "inline-block" }}>
        <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 160, color: C.ink }}>jev-engineering</div>
        <Underline width={1230} p={1} />
      </div>
      <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 58, color: C.ink }}>the decision layer for AI agents</div>
    </div>
    <div style={{ ...abs, left: 0, right: 0, top: 620, display: "flex", justifyContent: "center", gap: 60 }}>
      {[["371ms", "per decision"], ["$0.0000189", "per check"], ["13 / 13", "CVE fixes caught"]].map(([big, small]) => (
        <div key={big} style={{ textAlign: "center", padding: "20px 36px", border: `4px solid ${C.ink}`, borderRadius: 16, background: C.card, boxShadow: `7px 7px 0 ${C.ink}` }}>
          <div style={{ fontFamily: MARKER, fontWeight: 800, letterSpacing: -1, fontSize: 84, color: C.rust, lineHeight: 1.1 }}>{big}</div>
          <div style={{ fontFamily: HAND, fontWeight: 700, fontSize: 34, color: C.ink }}>{small}</div>
        </div>
      ))}
    </div>
  </div>
);
