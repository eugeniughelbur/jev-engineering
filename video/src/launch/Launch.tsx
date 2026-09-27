// The launch reel, built around the viewer, not the architecture:
//   pain -> two bad options -> the third option -> a session -> proof -> trust -> install
// Every number is from the repo README or results/.

import React from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from "remotion";
import cues from "../cues-launch.json";
import { backOut, clamp, easeInOut, easeOut, pop, ramp, sceneAlpha } from "../lib/anim";
import { MARKER as HEAD, MONO, abs } from "../lib/ui";

const S = cues.scene;
const W = 1920;
const H = 1080;

const K = {
  light: "#F3EDE2",
  dark: "#111214",
  ink: "#15171C",
  soft: "rgba(21,23,28,0.55)",
  faint: "rgba(21,23,28,0.12)",
  cream: "#F3EDE2",
  creamSoft: "rgba(243,237,226,0.55)",
  creamFaint: "rgba(243,237,226,0.12)",
  rust: "#E0602F",
  amber: "#E9A23B",
  rustDeep: "#C8512A",
  green: "#3BAA6E",
};

const bold = (size: number, color: string, extra: React.CSSProperties = {}): React.CSSProperties => ({
  fontFamily: HEAD,
  fontWeight: 800,
  fontSize: size,
  letterSpacing: -size * 0.025,
  color,
  lineHeight: 1.05,
  ...extra,
});
const mono = (size: number, color: string, extra: React.CSSProperties = {}): React.CSSProperties => ({
  fontFamily: MONO,
  fontSize: size,
  color,
  ...extra,
});

// ------------------------------------------------------------ chrome
const Backdrop: React.FC<{ dark: boolean; frame: number }> = ({ dark, frame }) => (
  <>
    <div style={{ ...abs, inset: 0, background: dark ? K.dark : K.light }} />
    <div
      style={{
        ...abs,
        inset: 0,
        background: dark
          ? "radial-gradient(ellipse at 50% 55%, rgba(224,96,47,0.16), transparent 60%)"
          : "radial-gradient(ellipse at 50% 45%, rgba(255,255,255,0.7), transparent 65%)",
      }}
    />
    <div style={{ ...abs, inset: 0, background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.18))" }} />
    <svg style={{ ...abs, inset: 0, mixBlendMode: "overlay", opacity: dark ? 0.35 : 0.22 }} width={W} height={H}>
      <filter id="g">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={Math.floor(frame / 2) % 40} />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#g)" />
    </svg>
  </>
);

const Hud: React.FC<{ t: number; dark: boolean; label: string }> = ({ t, dark, label }) => {
  const c = dark ? K.creamSoft : K.soft;
  const mark = (x: number, y: number, dx: number, dy: number) => (
    <path d={`M${x} ${y + dy * 22} V${y} H${x + dx * 22}`} fill="none" stroke={c} strokeWidth={2} />
  );
  const secs = Math.max(0, t);
  const tc = `00:${String(Math.floor(secs)).padStart(2, "0")}:${String(Math.floor((secs % 1) * 30)).padStart(2, "0")}`;
  return (
    <>
      <svg style={abs} width={W} height={H}>
        {mark(40, 40, 1, 1)}
        {mark(1880, 40, -1, 1)}
        {mark(40, 1040, 1, -1)}
        {mark(1880, 1040, -1, -1)}
      </svg>
      <div style={{ ...abs, left: 72, top: 46, ...mono(16, c, { letterSpacing: 3 }) }}>
        JEV-GATE <span style={{ color: K.rust }}>●</span> auto-approve
      </div>
      <div style={{ ...abs, right: 72, top: 46, ...mono(16, c, { letterSpacing: 3 }) }}>
        {label} · {tc}
      </div>
      <div style={{ ...abs, left: 72, right: 72, bottom: 58, height: 2, background: dark ? K.creamFaint : K.faint }}>
        <div style={{ width: `${clamp(t / cues.duration) * 100}%`, height: 2, background: K.rust }} />
      </div>
    </>
  );
};

const Wordmark: React.FC<{ size: number; color?: string; text?: string }> = ({ size, color = K.ink, text = "jev-gate" }) => (
  <div style={{ position: "relative", display: "inline-block", ...bold(size, color) }}>
    <span style={{ position: "absolute", left: size * 0.02, top: -size * 0.12, width: size * 0.16, height: size * 0.16, borderRadius: "50%", background: K.rust }} />
    {text}
  </div>
);

const Terminal: React.FC<{ width: number; children: React.ReactNode; dim?: number; title?: string }> = ({ width, children, dim = 1, title = "~/my-project — zsh" }) => (
  <div
    style={{
      width,
      background: "#16181C",
      borderRadius: 16,
      boxShadow: "0 30px 80px rgba(0,0,0,0.28), 0 0 0 1px rgba(255,255,255,0.06) inset",
      overflow: "hidden",
      opacity: dim,
    }}
  >
    <div style={{ height: 44, display: "flex", alignItems: "center", gap: 10, paddingLeft: 18, background: "#1D2025" }}>
      {["#E0602F", "#E9B949", "#3BAA6E"].map((c) => (
        <div key={c} style={{ width: 13, height: 13, borderRadius: 7, background: c }} />
      ))}
      <span style={{ ...mono(16, "rgba(243,237,226,0.45)"), marginLeft: 12 }}>{title}</span>
    </div>
    <div style={{ padding: "26px 30px", ...mono(30, K.cream, { lineHeight: 1.65 }) }}>{children}</div>
  </div>
);

const Caret: React.FC<{ t: number }> = ({ t }) => (
  <span style={{ display: "inline-block", width: 16, height: 34, marginLeft: 4, verticalAlign: "-6px", background: K.rust, opacity: Math.floor(t * 3) % 2 ? 1 : 0.15 }} />
);

// ------------------------------------------------------------ 1. problem
const COMMANDS = [
  "npm install", "git status", "rm -rf ./build", "ls -la", "git push", "curl … | bash", "pytest -q", "cat .env",
  "docker compose up", "git stash clear", "npm run dev", "psql prod", "git rebase -i", "chmod -R 777 .", "make deploy", "kubectl get pods",
  "sed -i …", "brew upgrade", "git reset --hard", "aws s3 rm …", "pip install -U", "ssh prod", "yarn build", "terraform apply",
];

const Problem: React.FC<{ t: number }> = ({ t }) => {
  const P = cues.pain;
  const a = sceneAlpha(t, S.pain, S.options, 0.15);
  const implode = ramp(t, P.implode, 0.4, easeInOut);
  const approvals = Math.round(40 * clamp((t - 0.6) / 2.8));
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 120, top: 120, width: 1680, height: 520 }}>
        {COMMANDS.map((cmd, i) => {
          const col = i % 6;
          const row = Math.floor(i / 6);
          const x = col * 282;
          const y = row * 128;
          const idx = P.prompts.indexOf(P.prompts[i % P.prompts.length]);
          const at = P.prompts[i % P.prompts.length] + (i >= P.prompts.length ? 0.07 : 0);
          const on = t >= at;
          const fresh = clamp(1 - (t - at) / 0.45);
          const cx = 840 - 130;
          const cy = 260 - 30;
          const ix = x + (cx - x) * implode;
          const iy = y + (cy - y) * implode;
          return (
            <div
              key={i}
              style={{
                ...abs,
                left: ix,
                top: iy,
                transform: `scale(${1 - implode * 0.8})`,
                opacity: (0.35 + 0.65 * ramp(t, 0.1 + i * 0.02, 0.3)) * (1 - implode * 0.9),
              }}
            >
              <div
                data-i={idx}
                style={{
                  width: 268,
                  height: 64,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  borderRadius: 12,
                  border: `2px solid ${on ? K.ink : K.faint}`,
                  background: on ? "#FFFFFF" : "rgba(255,255,255,0.35)",
                  display: "flex",
                  alignItems: "center",
                  paddingLeft: 18,
                  ...mono(22, on ? K.ink : K.soft),
                  boxShadow: on ? "0 8px 22px rgba(0,0,0,0.08)" : "none",
                }}
              >
                <span style={{ color: K.rust, marginRight: 8 }}>$</span>
                {cmd}
              </div>
              {on && (
                <div
                  style={{
                    ...abs,
                    right: -12,
                    top: -22,
                    padding: "4px 12px",
                    borderRadius: 8,
                    background: fresh > 0 ? K.rust : K.ink,
                    ...mono(17, "#FFF", { fontWeight: 700 }),
                    transform: `scale(${0.8 + 0.3 * fresh})`,
                  }}
                >
                  {fresh > 0 ? "Allow? y/n" : "✓ approved"}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div style={{ ...abs, left: 120, top: 720, opacity: 1 - implode * 0.4 }}>
        {[P.words.slice(0, 4), P.words.slice(4)].map((line, li) => (
          <div key={li} style={{ display: "flex", gap: 20, ...bold(li ? 64 : 84, li ? K.soft : K.ink) }}>
            {line.map(([at, w], wi) => {
              const p = ramp(t, at as number, 0.22);
              return (
                <span key={wi} style={{ opacity: p, transform: `translateY(${(1 - p) * 18}px)`, color: w === "\"Allow?\"" ? K.rust : undefined }}>
                  {w as string}
                </span>
              );
            })}
          </div>
        ))}
      </div>
      <div style={{ ...abs, right: 120, top: 700, textAlign: "right" }}>
        <div style={mono(16, K.soft, { letterSpacing: 3 })}>YOU CLICKED ALLOW THIS HOUR</div>
        <div style={bold(110, K.ink, { fontFamily: MONO, fontWeight: 700, letterSpacing: -2 })}>{approvals}</div>
        <div style={{ height: 4, background: K.rust, width: `${approvals * 2.5}%`, marginLeft: "auto" }} />
      </div>
    </div>
  );
};


// ------------------------------------------------------------ 2. two bad options
const Options: React.FC<{ t: number }> = ({ t }) => {
  const O = cues.options;
  const a = sceneAlpha(t, S.options, S.reveal, 0.2);
  const left = pop(t, O.left, 0.4);
  const right = pop(t, O.right, 0.4);
  const boom = ramp(t, O.boom, 0.25);
  const clicks = Math.min(99, Math.max(0, Math.floor((t - O.left) * 22)));
  const shake = t > O.boom && t < O.boom + 0.4 ? Math.sin(t * 90) * 10 * (1 - (t - O.boom) / 0.4) : 0;
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 0, right: 0, top: 120, textAlign: "center", ...bold(78, K.cream), opacity: ramp(t, O.title, 0.3) }}>
        So you pick one of <span style={{ color: K.rust }}>two bad options</span>.
      </div>
      <div style={{ ...abs, left: 150, top: 300, width: 740, transform: `scale(${left})`, opacity: clamp(left * 2) }}>
        <div style={{ ...mono(20, K.creamSoft, { letterSpacing: 3 }), marginBottom: 16 }}>OPTION 1</div>
        <div style={bold(54, K.cream)}>Click "yes" all day</div>
        <div style={{ marginTop: 30, padding: "30px 34px", borderRadius: 14, background: "#1E2126", border: "2px solid rgba(243,237,226,0.15)" }}>
          <div style={mono(28, K.cream)}>Allow Bash(npm test)?</div>
          <div style={{ display: "flex", gap: 16, marginTop: 20 }}>
            <span style={{ ...mono(26, "#FFF", { fontWeight: 700 }), padding: "8px 22px", borderRadius: 8, background: K.green }}>Yes</span>
            <span style={{ ...mono(26, K.creamSoft), padding: "8px 22px", borderRadius: 8, border: "2px solid rgba(243,237,226,0.25)" }}>No</span>
          </div>
          <div style={{ ...mono(24, K.creamSoft), marginTop: 22 }}>clicked "yes" <span style={{ color: K.rust, fontWeight: 700 }}>{clicks}</span> times, stopped reading at 12</div>
        </div>
      </div>
      <div style={{ ...abs, left: 1030, top: 300, width: 740, transform: `scale(${right}) translateX(${shake}px)`, opacity: clamp(right * 2) }}>
        <div style={{ ...mono(20, K.creamSoft, { letterSpacing: 3 }), marginBottom: 16 }}>OPTION 2</div>
        <div style={bold(54, K.cream)}>Turn prompts off and hope</div>
        <div style={{ marginTop: 30 }}>
          <Terminal width={740} title="yolo mode">
            <div style={{ fontSize: 24 }}>
              <span style={{ color: K.rust }}>› </span>claude --dangerously-skip-permissions
            </div>
            <div style={{ fontSize: 24, opacity: ramp(t, O.right + 0.5, 0.2) }}>
              <span style={{ color: "rgba(243,237,226,0.5)" }}>● </span>Bash(rm -rf ./src)
            </div>
            <div style={{ fontSize: 26, fontWeight: 700, color: K.rust, opacity: boom }}>
              ✗ src/ deleted · 3 days of work gone
            </div>
          </Terminal>
        </div>
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 840, textAlign: "center", opacity: ramp(t, O.caption, 0.3), ...bold(40, K.creamSoft, { fontWeight: 500, letterSpacing: 0 }) }}>
        Tired, or reckless. Nothing in between.
      </div>
      {boom > 0 && boom < 1 && <div style={{ ...abs, inset: 0, background: K.rust, opacity: 0.25 * (1 - boom) }} />}
    </div>
  );
};

// ------------------------------------------------------------ 3. the third option
const Reveal: React.FC<{ t: number }> = ({ t }) => {
  const R = cues.reveal;
  const a = sceneAlpha(t, S.reveal, S.demo, 0.2);
  const logo = pop(t, R.logo, 0.6);
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 0, right: 0, top: 300, textAlign: "center", ...mono(22, K.soft, { letterSpacing: 4 }), opacity: ramp(t, R.logo, 0.3) }}>
        THE THIRD OPTION
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 360, textAlign: "center", transform: `scale(${0.85 + 0.15 * logo})`, opacity: clamp(logo * 2) }}>
        <Wordmark size={210} />
        <div style={{ ...bold(52, K.ink, { fontWeight: 500, letterSpacing: -0.5 }), marginTop: 22, opacity: ramp(t, R.tagline, 0.3) }}>
          Auto-approve that can tell <span style={{ fontFamily: MONO, color: K.green }}>ls</span> from{" "}
          <span style={{ fontFamily: MONO, color: K.rust }}>rm -rf</span>.
        </div>
      </div>
    </div>
  );
};

// ------------------------------------------------------------ 4. a session
const Demo: React.FC<{ t: number }> = ({ t }) => {
  const D = cues.demo;
  const a = sceneAlpha(t, S.demo, S.proof, 0.2);
  const skipped = D.rows.filter(([at, , v]) => v === "ran" && t >= (at as number) + 0.35).length;
  const promptP = pop(t, D.prompt, 0.4);
  const badge = (v: string) =>
    v === "ran"
      ? { text: "✓ ran · no prompt", col: K.green }
      : v === "blocked"
        ? { text: "✗ blocked · reads a private key", col: K.rust }
        : { text: "? asks you · unsure, p=0.78", col: K.amber };
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 120, top: 120, ...mono(18, K.creamSoft, { letterSpacing: 3 }) }}>CLAUDE CODE, WITH JEV-GATE IN AUTO MODE</div>
      <div style={{ ...abs, left: 120, top: 170 }}>
        <Terminal width={1340} title="~/my-project — claude">
          {D.rows.map(([at, cmd, v]) => {
            const p = ramp(t, at as number, 0.2);
            const b = badge(v as string);
            const vp = ramp(t, (at as number) + 0.3, 0.2);
            return (
              <div key={cmd as string} style={{ display: "flex", alignItems: "center", gap: 20, opacity: p, fontSize: 28, lineHeight: 1.9 }}>
                <span style={{ color: "rgba(243,237,226,0.45)" }}>●</span>
                <span style={{ width: 660, whiteSpace: "nowrap" }}>Bash({cmd as string})</span>
                <span style={{ color: b.col, fontWeight: 700, opacity: vp, whiteSpace: "nowrap", fontSize: 25 }}>{b.text}</span>
              </div>
            );
          })}
          <div style={{ marginTop: 14, padding: "14px 20px", borderRadius: 10, border: `2px solid ${K.amber}`, display: "inline-block", opacity: clamp(promptP * 2), transform: `scale(${0.9 + 0.1 * promptP})`, fontSize: 26 }}>
            Allow Bash(git push --force origin main)? <span style={{ color: K.amber, fontWeight: 700 }}>y / n</span>
          </div>
        </Terminal>
      </div>
      <div style={{ ...abs, right: 100, top: 260, textAlign: "right" }}>
        <div style={mono(18, K.creamSoft, { letterSpacing: 3 })}>PROMPTS SKIPPED</div>
        <div style={mono(150, K.green, { fontWeight: 700, lineHeight: 1 })}>{skipped}</div>
        <div style={{ ...mono(18, K.creamSoft, { letterSpacing: 3 }), marginTop: 40 }}>PROMPTS LEFT</div>
        <div style={mono(150, K.amber, { fontWeight: 700, lineHeight: 1 })}>{t >= D.prompt ? 1 : 0}</div>
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 930, textAlign: "center", opacity: ramp(t, D.prompt + 0.4, 0.3), ...bold(40, K.cream, { fontWeight: 500, letterSpacing: 0 }) }}>
        You only see the prompt that <span style={{ color: K.amber, fontWeight: 800 }}>deserves a look</span>.
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 995, textAlign: "center", opacity: ramp(t, D.prompt + 0.6, 0.3), ...mono(16, K.creamSoft) }}>
        each verdict is the gate's real answer to that command, from the tests in the repo
      </div>
    </div>
  );
};

// ------------------------------------------------------------ 5. proof
const Bench: React.FC<{ t: number }> = ({ t }) => {
  const B = cues.proof;
  const a = sceneAlpha(t, S.proof, S.trust, 0.2);
  const grow = ramp(t, B.bars, 1.1, easeOut);
  const slam = pop(t, B.slam, 0.35);
  const before = 3622;
  const after = 1226;
  const beforeW = 1000 * grow;
  const afterW = 1000 * (after / before) * grow;
  const shards = Array.from({ length: 16 }, (_, i) => i);
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 120, top: 130, ...mono(16, K.soft, { letterSpacing: 3 }) }}>3,622 COMMANDS CLAUDE CODE REALLY RAN FOR ME</div>
      <div style={{ ...abs, left: 120, top: 175, ...bold(64, K.ink), opacity: ramp(t, B.title, 0.3) }}>
        Permission prompts, <span style={{ color: K.rust }}>before and after</span>.
      </div>
      <div style={{ ...abs, left: 500, top: 360, width: 2, height: 330, background: K.ink }} />
      {[
        ["Without jev-gate", "every command asks", beforeW, K.ink, Math.round(before * grow).toLocaleString("en-US")],
        ["With auto mode", "only the unclear ones ask", afterW, K.rust, Math.round(after * grow).toLocaleString("en-US")],
      ].map(([name, sub, w, col, val], i) => (
        <div key={name as string} style={{ ...abs, left: 120, top: 400 + i * 150, display: "flex", alignItems: "center" }}>
          <div style={{ width: 380 }}>
            <div style={bold(40, i ? K.rust : K.ink)}>{name as string}</div>
            <div style={mono(18, K.soft)}>{sub as string}</div>
          </div>
          <div style={{ width: w as number, height: 88, background: col as string, borderRadius: 4 }} />
          <div style={{ ...bold(62, i ? K.rust : K.ink, { fontFamily: MONO, fontWeight: 700, letterSpacing: -1 }), marginLeft: 26, opacity: clamp(grow * 2) }}>{val as string}</div>
        </div>
      ))}
      <div style={{ ...abs, left: 1360, top: 318, transform: `translate(-50%,-50%) scale(${slam}) rotate(-3deg)`, opacity: clamp(slam * 3), ...bold(84, K.rust), whiteSpace: "nowrap" }}>
        66% fewer prompts
      </div>
      {shards.map((i) => {
        const p = clamp((t - B.slam) / 0.9);
        if (p <= 0 || p >= 1) return null;
        const ang = (i / shards.length) * Math.PI * 2;
        const d = 120 + 420 * easeOut(p);
        return (
          <div key={i} style={{ ...abs, left: 1400 + Math.cos(ang) * d, top: 318 + Math.sin(ang) * d * 0.5 + p * p * 120, width: 18, height: 18, background: i % 3 ? K.ink : K.rust, transform: `rotate(${ang * 90 + p * 300}deg)`, opacity: 1 - p }} />
        );
      })}
      <div style={{ ...abs, left: 0, right: 0, top: 800, textAlign: "center", opacity: ramp(t, B.caption, 0.35), ...bold(52, K.ink) }}>
        Not one <span style={{ color: K.rust }}>rm, git push or sudo</span> was auto-approved.
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 900, textAlign: "center", opacity: ramp(t, B.fine, 0.4), ...mono(17, K.soft) }}>
        Replay of real Claude Code history, 2026-09-27 · $0.069 in Jev for all 3,622 checks · some would not have prompted anyway, so 66% is an upper bound
      </div>
    </div>
  );
};


// ------------------------------------------------------------ 6. why you can trust it
const TRUST: [string, string][] = [
  ["Rules run first", "Plain regex blocks the classics before any model sees them."],
  ["Only clear answers act", "Approved only when the model is confident it is safe."],
  ["Fails to your normal prompt", "No key, a timeout or an error: Claude Code asks you, as today."],
  ["Open source, about 1¢ a day", "MIT. Every decision logged on your machine."],
];
const Trust: React.FC<{ t: number }> = ({ t }) => {
  const Tr = cues.trust;
  const a = sceneAlpha(t, S.trust, S.outro, 0.2);
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 120, top: 130, ...bold(70, K.cream) }}>
        Why you can <span style={{ color: K.rust }}>trust it</span>
      </div>
      {TRUST.map(([title, sub], i) => {
        const p = pop(t, Tr.items[i], 0.35);
        return (
          <div key={title} style={{ ...abs, left: 120 + (i % 2) * 850, top: 320 + Math.floor(i / 2) * 260, width: 780, padding: "30px 36px", borderRadius: 16, background: "#1E2126", border: "2px solid rgba(243,237,226,0.12)", transform: `scale(${p})`, opacity: clamp(p * 2) }}>
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <span style={{ ...mono(26, K.green, { fontWeight: 700 }) }}>✓</span>
              <span style={bold(42, K.cream)}>{title}</span>
            </div>
            <div style={{ ...bold(26, K.creamSoft, { fontWeight: 500, letterSpacing: 0, lineHeight: 1.35 }), marginTop: 12, marginLeft: 44 }}>{sub}</div>
          </div>
        );
      })}
    </div>
  );
};

// ------------------------------------------------------------ 7. install
const INSTALL = [
  "claude plugin marketplace add eugeniughelbur/jev-engineering",
  "claude plugin install jev-engineering@jev-engineering",
  "/jev-on",
];
const Outro: React.FC<{ t: number }> = ({ t }) => {
  const O = cues.outro;
  const a = sceneAlpha(t, S.outro, S.end + 1, 0.25);
  const logo = pop(t, O.logo, 0.5);
  const total = INSTALL.join("").length;
  let left = Math.round(total * clamp((t - O.type_start) / (O.type_end - O.type_start)));
  const shown = INSTALL.map((line) => {
    const n = Math.max(0, Math.min(line.length, left));
    left -= line.length;
    return line.slice(0, n);
  });
  return (
    <div style={{ ...abs, inset: 0, opacity: a }}>
      <div style={{ ...abs, left: 0, right: 0, top: 170, textAlign: "center", transform: `scale(${0.9 + 0.1 * logo})`, opacity: clamp(logo * 2) }}>
        <Wordmark size={170} />
        <div style={{ ...bold(50, K.ink, { fontWeight: 500, letterSpacing: -0.5 }), marginTop: 12 }}>
          Stop clicking "Allow". <span style={{ color: K.rust, fontWeight: 800 }}>Keep the brakes.</span>
        </div>
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 510, display: "flex", justifyContent: "center", opacity: ramp(t, O.type_start - 0.2, 0.25) }}>
        <div style={{ padding: "22px 34px", borderRadius: 12, background: "#16181C", ...mono(30, K.cream, { lineHeight: 1.7 }) }}>
          {shown.map((line, i) => (
            <div key={i} style={{ opacity: line || i === 0 ? 1 : 0, color: i === 2 ? K.green : K.cream }}>
              <span style={{ color: K.rust }}>› </span>
              {line || " "}
            </div>
          ))}
        </div>
      </div>
      <div style={{ ...abs, left: 0, right: 0, top: 800, textAlign: "center", opacity: ramp(t, O.meta, 0.35), ...mono(24, K.soft) }}>
        works in Claude Code and Codex · github.com/eugeniughelbur/jev-engineering · MIT
      </div>
    </div>
  );
};

// ------------------------------------------------------------ the reel
const SCENES: { from: number; to: number; dark: boolean; label: string; C: React.FC<{ t: number }> }[] = [
  { from: S.pain, to: S.options, dark: false, label: cues.labels.pain, C: Problem },
  { from: S.options, to: S.reveal, dark: true, label: cues.labels.options, C: Options },
  { from: S.reveal, to: S.demo, dark: false, label: cues.labels.reveal, C: Reveal },
  { from: S.demo, to: S.proof, dark: true, label: cues.labels.demo, C: Demo },
  { from: S.proof, to: S.trust, dark: false, label: cues.labels.proof, C: Bench },
  { from: S.trust, to: S.outro, dark: true, label: cues.labels.trust, C: Trust },
  { from: S.outro, to: S.end + 1, dark: false, label: cues.labels.outro, C: Outro },
];

export const Launch: React.FC = () => {
  const frame = useCurrentFrame();
  // The first PRE seconds hold the reveal, because feeds thumbnail an early frame.
  const raw = frame / cues.fps - cues.pre;
  const t = raw < 0 ? 10.5 : raw;
  const current = SCENES.find((s) => t >= s.from && t < s.to) ?? SCENES[SCENES.length - 1];
  return (
    <AbsoluteFill>
      <Backdrop dark={current.dark} frame={frame} />
      {SCENES.filter((s) => t >= s.from - 0.3 && t <= s.to + 0.3).map(({ from, C }) => (
        <C key={from} t={t} />
      ))}
      <Hud t={raw < 0 ? 0 : t} dark={current.dark} label={current.label} />
      <Audio src={staticFile("music-launch.wav")} />
    </AbsoluteFill>
  );
};
