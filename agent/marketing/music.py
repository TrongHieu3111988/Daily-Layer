"""An original, cheerful 120 bpm loop (no samples, no third-party music), rendered to WAV for the Shorts.
usage: python3 music.py seconds out.wav [seed]"""
import sys, wave, numpy as np
SR = 44100
def note(f, dur, kind="pluck", vol=0.3):
    t = np.arange(int(SR * dur)) / SR
    if kind == "pluck":   # soft marimba-like tone
        w = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 4 * f * t)
        env = np.exp(-t * 7) * np.minimum(1, t * 400)
    elif kind == "bass":
        w = np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 2 * f * t); env = np.exp(-t * 4) * np.minimum(1, t * 200)
    else:                 # little shaker
        w = np.random.default_rng(int(f)).standard_normal(len(t)); env = np.exp(-t * 60)
    return w * env * vol
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def render(seconds, seed=1):
    rng = np.random.default_rng(seed); beat = 0.5; out = np.zeros(int(SR * (seconds + 2)))
    chords = [[60, 64, 67], [67, 71, 74], [69, 72, 76], [65, 69, 72]]          # C G Am F
    scale = [72, 74, 76, 79, 81, 84]
    def add(x, at):
        i = int(at * SR); j = min(len(out), i + len(x)); out[i:j] += x[:j - i]
    bar = 0; t = 0.0
    while t < seconds:
        ch = chords[bar % 4]
        add(note(hz(ch[0] - 24), beat * 2, "bass", 0.32), t); add(note(hz(ch[0] - 24), beat * 2, "bass", 0.26), t + beat * 2)
        for k in range(8): add(note(hz(ch[k % 3]), beat * 0.5, "pluck", 0.08), t + k * beat * 0.5)   # arpeggio
        for k in range(8): add(note(9000 + k, 0.05, "shaker", 0.025 if k % 2 else 0.04), t + k * beat * 0.5)
        motif = [scale[i] for i in rng.integers(0, len(scale), 5)]
        for k, m in enumerate(motif): add(note(hz(m), beat * 0.9, "pluck", 0.16), t + [0, 0.5, 1, 2, 3][k] * beat)
        t += beat * 4; bar += 1
    out = out[:int(SR * seconds)]
    fade = int(SR * 1.2); out[-fade:] *= np.linspace(1, 0, fade)
    out /= max(1e-9, np.abs(out).max()) / 0.8
    return out
if __name__ == "__main__":
    sec, path = float(sys.argv[1]), sys.argv[2]; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    a = (render(sec, seed) * 32767).astype("<i2")
    with wave.open(path, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(a.tobytes())
    print("music", sec, "s")
