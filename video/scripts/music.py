"""Synthesize the soundtrack from src/cues.json. No samples, no stock music.

    uv run --with numpy scripts/music.py                                   # launch reel
    uv run --with numpy scripts/music.py src/cues-repo.json music-repo.wav  # repo reel

Every drum, riser and UI sound is placed at a cue the picture also reads, so
retiming a cue moves both. 120 BPM, A minor, one chord per bar.
"""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent.parent
CUES = json.loads((HERE / (sys.argv[1] if len(sys.argv) > 1 else "src/cues.json")).read_text())
OUT_NAME = sys.argv[2] if len(sys.argv) > 2 else "music.wav"
SR = 48000
PRE = CUES["pre"]
LENGTH = PRE + CUES["duration"] + 0.5
N = int(LENGTH * SR)
BEAT = 60 / CUES["bpm"]
BAR = 4 * BEAT
rng = np.random.default_rng(7)

L = np.zeros(N)
R = np.zeros(N)


def at(t: float) -> int:
    """Cue time (seconds after the cold open) to a sample index."""
    return int((t + PRE) * SR)


def add(sig: np.ndarray, t: float, gain: float = 1.0, pan: float = 0.0) -> None:
    i = at(t)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    L[i : i + len(sig)] += sig * (1 - max(0, pan))
    R[i : i + len(sig)] += sig * (1 + min(0, pan))


def env(n: int, attack: float, decay: float) -> np.ndarray:
    x = np.arange(n) / SR
    return np.minimum(1, x / max(attack, 1e-4)) * np.exp(-x / decay)


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def hz(note: str, octave: int) -> float:
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    return 440.0 * 2 ** ((names[note] + 12 * (octave - 4)) / 12)


CHORDS = {"Am": ["A", "C", "E"], "F": ["F", "A", "C"], "C": ["C", "E", "G"], "G": ["G", "B", "D"]}

# ---------------------------------------------------------------- drums
def kick() -> np.ndarray:
    n = int(0.45 * SR)
    x = np.arange(n) / SR
    f = 45 + 95 * np.exp(-x * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 7.5)


def clap() -> np.ndarray:
    n = int(0.25 * SR)
    noise = rng.standard_normal(n)
    e = np.zeros(n)
    for off in (0.0, 0.011, 0.022):
        e += env(n, 0.001, 0.05) * (np.arange(n) >= int(off * SR))
    return np.diff(noise, prepend=0) * e * 0.35


def hat() -> np.ndarray:
    n = int(0.06 * SR)
    return np.diff(rng.standard_normal(n), prepend=0) * env(n, 0.0005, 0.012) * 0.18


def boom() -> np.ndarray:
    n = int(1.6 * SR)
    x = np.arange(n) / SR
    f = 32 + 60 * np.exp(-x * 6)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 2.2)
    air = lowpass(rng.standard_normal(n), 900) * np.exp(-x * 5) * 0.6
    return body + air


def riser(dur: float) -> np.ndarray:
    n = int(dur * SR)
    x = np.arange(n) / SR
    noise = rng.standard_normal(n)
    hp = np.diff(noise, prepend=0)
    shape = (x / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * (x / dur) ** 2) / SR) * 0.25
    return (hp * 0.3 + tone) * shape


# ---------------------------------------------------------------- UI sounds
def tick(freq: float = 1800, dur: float = 0.05) -> np.ndarray:
    n = int(dur * SR)
    x = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * x) * env(n, 0.0005, dur / 4)


def thud() -> np.ndarray:
    n = int(0.3 * SR)
    x = np.arange(n) / SR
    f = 70 + 140 * np.exp(-x * 40)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 14) + lowpass(rng.standard_normal(n), 2500) * np.exp(-x * 30) * 0.5


def chime(base: float) -> np.ndarray:
    n = int(1.2 * SR)
    x = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * base * k * x) / k for k in (1, 2, 3))
    return s * np.exp(-x * 3.5) * env(n, 0.003, 10)


# ---------------------------------------------------------------- music
music = CUES["music"]
kick_times: list[float] = []

t = music["drums_in"]
while t < music["drums_out"] - 1e-9:
    in_break = music["break"][0] <= t < music["break"][1]
    if not in_break:
        kick_times.append(t)
        add(kick(), t, 0.95)
        if abs((t % 1.0) - 0.5) < 1e-6:
            add(clap(), t, 0.7, pan=0.1)
    if t >= music.get("hats_in", 8.0) and not in_break:
        add(hat(), t + BEAT / 2, 1.0, pan=-0.3)
        if t >= music["drop"]:
            add(hat(), t + BEAT / 4, 0.6, pan=0.3)
            add(hat(), t + 3 * BEAT / 4, 0.6, pan=0.3)
    t += BEAT

# Sidechain: pad and bass duck under every kick.
duck = np.ones(N)
for kt in kick_times:
    i = at(kt)
    n = min(int(0.32 * SR), N - i)
    duck[i : i + n] = np.minimum(duck[i : i + n], 1 - 0.65 * np.exp(-np.arange(n) / SR * 11))

pad = np.zeros(N)
bass = np.zeros(N)
for bar, name in enumerate(music["chords"]):
    t0 = bar * BAR
    n = int(BAR * SR)
    x = np.arange(n) / SR
    shape = np.minimum(1, x / 0.08) * np.minimum(1, (BAR - x) / 0.15)
    tone = np.zeros(n)
    for note in CHORDS[name]:
        f = hz(note, 3)
        for det in (-0.006, 0.0, 0.006):
            ph = 2 * np.pi * f * (1 + det) * x
            tone += (2 * ((ph / (2 * np.pi)) % 1) - 1) * 0.08  # soft saw
    i = at(t0)
    seg = tone * shape
    pad[i : i + len(seg)] += seg[: N - i]
    # Bass: root on every eighth, once the drums are in.
    if t0 >= music["drums_in"]:
        root = hz(CHORDS[name][0], 1 if CHORDS[name][0] in "AB" else 2)
        for k in range(8):
            if music["break"][0] <= t0 + k * BEAT / 2 < music["break"][1]:
                continue
            m = int(BEAT / 2 * SR * 0.9)
            xx = np.arange(m) / SR
            note = np.tanh(3 * np.sin(2 * np.pi * root * xx)) * env(m, 0.004, 0.18)
            j = at(t0 + k * BEAT / 2)
            bass[j : j + m] += note[: N - j] * 0.55

pad = lowpass(pad, 1400)
# Quieter pad under the cold open, fuller from the drop.
level = np.full(N, 0.55)
level[: at(music["drums_in"])] = 0.35
level[at(music["drop"]) :] = 0.75
pad *= level * duck
bass *= duck
delay = int(0.012 * SR)
L += pad + bass * 0.9
R += np.concatenate([np.zeros(delay), pad[:-delay]]) + bass * 0.9

for a, b in music["risers"]:
    add(riser(b - a), a, 0.55)
for i, bt in enumerate(music.get("booms", [music["drums_in"], music["drop"]])):
    add(boom(), bt, 1.0 if bt == music["drop"] else 0.7)

# ---------------------------------------------------------------- UI hits
SOUNDS = {"tick": lambda *a: tick(1800, 0.05), "thud": lambda *a: thud(), "boom": lambda *a: boom(),
          "chime": lambda f=660, *a: chime(f)}
GAIN = {"tick": 0.28, "thud": 0.8, "boom": 0.8, "chime": 0.35}
if "hits" in CUES:
    for hit in CUES["hits"]:
        t_, kind, *args = hit
        add(SOUNDS[kind](*args), t_, GAIN[kind])
    a_, b_, chars = CUES["typing"]
    for k in range(chars):
        add(tick(3000 + rng.integers(-300, 300), 0.02), a_ + k * (b_ - a_) / chars, 0.12)
else:
    for at_, _ in CUES["problem"]["words"]:
        add(tick(2200, 0.04), at_, 0.25, pan=-0.2)
    for at_, _ in CUES["problem"]["slams"]:
        add(thud(), at_, 0.8)
    for x in CUES["rule"]["cards"]:
        add(tick(1500, 0.06), x, 0.3, pan=0.3)
    for x in CUES["rule"]["stamps"]:
        add(thud(), x, 0.55, pan=-0.1)
    for x in CUES["diff"]["lines"]:
        add(tick(2600, 0.03), x, 0.2)
    add(chime(660), CUES["diff"]["fanout"], 0.25)
    add(chime(880), CUES["diff"]["hit"], 0.35)
    add(thud(), CUES["diff"]["verdict"], 0.8)
    for x in CUES["route"]["cves"]:
        add(tick(1200, 0.05), x + 0.6, 0.25, pan=0.25)
    add(chime(990), CUES["route"]["total"], 0.4)
    for x in CUES["bench"]["slams"]:
        add(thud(), x, 0.9)
    o = CUES["outro"]
    chars = 55
    for k in range(chars):
        add(tick(3000 + rng.integers(-300, 300), 0.02), o["type_start"] + k * (o["type_end"] - o["type_start"]) / chars, 0.12)
    add(chime(523.25), o["title"], 0.45)
    add(chime(784), o["url"], 0.25)


# ---------------------------------------------------------------- master
fade = np.ones(N)
tail = int(1.2 * SR)
fade[-tail:] = np.linspace(1, 0, tail)
mix = np.stack([L, R]) * fade
mix = np.tanh(mix * 1.1)
mix /= np.max(np.abs(mix)) / 0.89
# About -14 LUFS, where X and LinkedIn normalise to anyway.
mix *= 0.6

out = HERE / "public" / OUT_NAME
out.parent.mkdir(exist_ok=True)
pcm = (mix.T * 32767).astype("<i2")
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f"wrote {out} ({LENGTH:.1f}s)")
