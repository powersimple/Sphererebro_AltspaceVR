"""Every sound in the talk, synthesised here (no downloads, so nothing to license; CREDITS.md). The only recorded sound is
Ben's own Om bowl (2020Vision/assets/sound/Om-Bowl.wav) inside the cue 1 bed. Writes 44.1 kHz 16-bit WAVs to
Assets/_Sphererebro/Talk/Audio/. Levels are kept low (beds peak around -16 dBFS) so Ben's voice stays clear.
Run: <blender python> tools/talk/sounds.py
"""
import numpy as np, os, wave, struct

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "Assets", "_Sphererebro", "Talk", "Audio")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1110)

def t_(d): return np.arange(int(round(d * SR))) / SR
def noise(d): return rng.standard_normal(int(round(d * SR)))
def spec_filter(x, fn):
    """filter by a gain curve over frequency (Hz) in the FFT domain"""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * fn(f), len(x))
def lp(x, fc, order=2): return spec_filter(x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order)))
def hp(x, fc, order=2): return spec_filter(x, lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order)))
def bp(x, fc, q=2.0): return spec_filter(x, lambda f: 1 / (1 + (q * (f / fc - fc / np.maximum(f, 1e-3))) ** 2))
def pink(d):
    return spec_filter(noise(d), lambda f: 1 / np.sqrt(np.maximum(f, 20) / 20))
def env(n, a, d_, total=None):
    """attack a s, exponential decay with time constant d_ s"""
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(t - a, 0) / d_)
def adsr(n, a, r):
    t = np.arange(n) / SR; T = n / SR
    return np.clip(np.minimum(t / a, (T - t) / r), 0, 1)
def sine(f, d, ph=0): return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, int(round(d * SR))) / SR) + ph)
def norm(x, peak_db):
    m = np.max(np.abs(x)) or 1
    return x / m * 10 ** (peak_db / 20)
def reverb(x, size=1.6, mix=0.3):
    n = int(round(size * SR)); ir = noise(size) * np.exp(-np.arange(n) / SR / (size / 5))
    ir = lp(ir, 5000)
    y = np.fft.irfft(np.fft.rfft(x, len(x) + n) * np.fft.rfft(ir, len(x) + n))[:len(x) + n]
    y = norm(y, 0) * np.max(np.abs(x))
    out = np.zeros(len(x) + n); out[:len(x)] += x * (1 - mix); out += y * mix
    return out
def loopify(x, xf=2.0):
    """seamless loop: crossfade the tail into the head"""
    n = int(xf * SR); head, tail = x[:n], x[-n:]
    w = np.linspace(0, 1, n)
    y = x[n:].copy(); y[-n:] = tail * (1 - w) + head * w
    return y
def save(name, x, peak_db=-6.0):
    x = norm(x, peak_db)
    x = np.clip(x, -1, 1)
    p = os.path.join(OUT, name)
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    print(f"  {name:22s} {len(x) / SR:5.1f}s  peak {peak_db} dBFS")
def read_wav(p):
    import subprocess, glob, tempfile
    ff = glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe"))[0]
    q = os.path.join(tempfile.gettempdir(), "sb_om16.wav")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", q], check=True)
    p = q
    with wave.open(p) as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    a = np.frombuffer(raw, "<i2" if sw == 2 else "<i4").astype(np.float64)
    a = a.reshape(-1, ch).mean(1) / (32768 if sw == 2 else 2 ** 31)
    if sr != SR: a = np.interp(np.arange(int(len(a) * SR / sr)) * sr / SR, np.arange(len(a)), a)
    return a

print("talk sounds ->", OUT)

# ---------------------------------------------------------------- beds (loops)
D = 42.0
t = t_(D + 2)
drone = sum(a * sine(f * (1 + 0.002 * np.sin(2 * np.pi * t * r)), D + 2) for f, a, r in ((55, 1, 0.05), (82.4, 0.6, 0.07), (110, 0.35, 0.03), (164.8, 0.18, 0.09)))
drone *= 0.6 + 0.4 * np.sin(2 * np.pi * t / 21) ** 2
wind = lp(hp(pink(D + 2), 120), 900) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 13 + 1))
bed = drone * 0.5 + wind * 0.35
om = os.path.join(r"B:\_powersimple\OmniScience\2020Vision\assets\sound", "Om-Bowl.wav")
if os.path.exists(om):
    b = read_wav(om); b = b[: int(min(len(b) / SR, 30) * SR)]; b = b * adsr(len(b), 0.01, 6)
    b = norm(b, 0) * np.max(np.abs(bed)) * 0.9
    for at in (3.0, 24.0):
        i = int(at * SR); seg = b[: len(bed) - i]; bed[i:i + len(seg)] += seg
save("bed_space.wav", loopify(reverb(bed, 2.5, 0.25)[: len(bed)]), -16)

D = 32.0; t = t_(D + 2)
hum = sum(a * sine(f, D + 2) for f, a in ((60, 1), (120, 0.5), (180, 0.25), (240, 0.12))) * 0.08
hiss = bp(noise(D + 2), 3200, 0.7) * 0.05
crackle = np.zeros(len(t)); idx = rng.integers(0, len(t) - 400, 900)
for i in idx: crackle[i:i + 300] += rng.uniform(-1, 1) * np.exp(-np.arange(300) / 40)
crackle = hp(crackle, 1500) * 0.25
chord = sum(sine(f * (1 + 0.004 * np.sin(2 * np.pi * t * 4.8)), D + 2) for f in (196.0, 246.9, 293.7, 392.0)) * 0.07
chord = lp(chord, 1800) * (0.55 + 0.45 * np.sin(2 * np.pi * t / 16) ** 2)
save("bed_media.wav", loopify(reverb(hum + hiss + crackle + chord, 1.8, 0.35)[: len(t)]), -18)

D = 19.2; t = t_(D + 2); x = np.zeros(len(t))
notes = [440, 523.3, 659.3, 784, 880, 659.3, 523.3, 587.3]
step = 60 / 100 / 2
for k in range(int((D + 2) / step)):
    f = notes[k % len(notes)] * (0.5 if k % 16 >= 8 else 1)
    n = int(0.6 * SR); i = int(k * step * SR)
    if i + n > len(x): break
    s = (sine(f, 0.6) + 0.3 * sine(f * 2.01, 0.6)) * env(n, 0.004, 0.18)
    x[i:i + n] += s * (0.5 + 0.5 * (k % 3 == 0))
pad = sum(sine(f, D + 2) for f in (220, 329.6, 493.9)) * 0.12 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 9.6) ** 2)
x = hp(x, 300) * 0.4 + lp(pad, 2500)
dl = int(0.3 * SR); y = x.copy(); y[dl:] += x[:-dl] * 0.35; y[2 * dl:] += x[:-2 * dl] * 0.15
save("bed_feed.wav", loopify(y), -19)

D = 36.0; t = t_(D + 2)
fans = lp(pink(D + 2), 700) * 0.6 + bp(noise(D + 2), 2400, 3) * 0.05
hum = sum(a * sine(f, D + 2) for f, a in ((50, 0.6), (100, 0.4), (150, 0.2), (400, 0.04))) * 0.25
drone = sine(36.7, D + 2) * 0.35 * (0.6 + 0.4 * np.sin(2 * np.pi * t / 18) ** 2)
relay = np.zeros(len(t))
for at in rng.uniform(0, D, 14):
    i = int(at * SR); relay[i:i + 600] += hp(noise(600 / SR), 2000) * np.exp(-np.arange(600) / 90) * 0.4
save("bed_hall.wav", loopify(reverb(fans + hum + drone + relay, 2.2, 0.3)[: len(t)]), -15)

D = 40.0; t = t_(D + 2)
chord = [146.8, 220.0, 293.7, 329.6, 440.0, 554.4]
pad = sum(sine(f * (1 + 0.003 * np.sin(2 * np.pi * t * (0.1 + 0.03 * i))), D + 2) / (1 + i * 0.3) for i, f in enumerate(chord))
pad = lp(pad, 2200) * (0.6 + 0.4 * np.sin(2 * np.pi * t / 20) ** 2)
shimmer = bp(noise(D + 2), 6000, 4) * 0.02 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 7) ** 2)
save("bed_commons.wav", loopify(reverb(pad * 0.4 + shimmer, 3.0, 0.4)[: len(t)]), -17)

# ---------------------------------------------------------------- one-shots
def whoosh(d, f0, f1, name, peak, low=True):
    n = int(d * SR); t = np.arange(n) / SR
    x = noise(d); fc = f0 * (f1 / f0) ** (t / d)
    # time-varying band: process in short blocks
    y = np.zeros(n); B = 2048
    for i in range(0, n, B):
        seg = x[i:i + B * 2]
        if len(seg) < 16: break
        y[i:i + B] += bp(seg, fc[min(i, n - 1)], 1.2)[:B][: len(y[i:i + B])]
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.6
    out = y * e
    if low: out += lp(noise(d), 120) * e * 1.2
    save(name, reverb(out, 1.2, 0.2), peak)

whoosh(5.0, 180, 900, "whoosh_slow.wav", -14)
whoosh(3.2, 300, 2400, "whoosh_fast.wav", -9)
whoosh(2.6, 1400, 160, "whoosh_over.wav", -6)

def impact(d, f_body, partials, name, peak, noise_amt=0.6, decay=0.9):
    n = int(d * SR); t = np.arange(n) / SR
    body = sine(f_body * (1 + 0.5 * np.exp(-t / 0.05)), d) * np.exp(-t / (decay * 0.5)) * 1.4
    metal = sum(a * sine(f, d) * np.exp(-t / (decay * (0.3 + 0.7 / (1 + k)))) for k, (f, a) in enumerate(partials))
    nz = lp(noise(d), 2500) * np.exp(-t / 0.06) * noise_amt
    save(name, reverb(body + metal * 0.35 + nz, 2.0, 0.3), peak)

impact(4.0, 42, [(187, 1), (341, 0.7), (523, 0.5), (911, 0.35), (1460, 0.2), (2210, 0.12)], "rack_land.wav", -4, 0.9, 1.4)
impact(1.6, 70, [(240, 0.4), (610, 0.3)], "stamp_thud.wav", -4, 1.2, 0.4)
impact(2.2, 120, [(880, 1), (1320, 0.6), (2650, 0.4)], "padlock.wav", -8, 0.4, 0.5)

t = t_(7.0); r = sine(32 + 6 * np.sin(2 * np.pi * t / 7), 7.0) * np.sin(np.pi * t / 7) ** 1.2 + lp(noise(7.0), 60) * np.sin(np.pi * t / 7)
save("rumble.wav", r, -6)

def mech(d, f0, f1, name, peak, grit=0.5):
    t = t_(d); f = f0 + (f1 - f0) * t / d
    x = (sine(f, d) + 0.5 * sine(f * 2.03, d) + 0.25 * sine(f * 3.1, d)) * 0.4
    g = bp(noise(d), 900, 2) * grit
    save(name, (x + g) * adsr(len(t), 0.25, 0.6), peak)

mech(3.0, 70, 95, "rack_turn.wav", -12)
mech(4.0, 50, 40, "rack_slide.wav", -10, 0.9)
mech(4.5, 60, 140, "screen_rise.wav", -12, 0.3)
mech(4.0, 38, 70, "tanks_rise.wav", -11, 0.6)
mech(6.0, 30, 55, "hall_rise.wav", -10, 1.0)
mech(14.0, 45, 48, "drift_low.wav", -14, 0.2)

t = t_(7.5); rust = np.zeros(len(t))
for at in rng.uniform(0, 7.3, 260):
    i = int(at * SR); k = int(rng.uniform(200, 1500)); rust[i:i + k] += hp(noise(k / SR), 1800) * np.exp(-np.arange(k) / (k / 4)) * rng.uniform(0.2, 1)
rust += bp(noise(7.5), 2500, 0.8) * 0.12
save("paper_unroll.wav", rust * adsr(len(t), 0.3, 1.0), -10)
save("paper_roll.wav", rust[: int(3 * SR)][::-1] * adsr(int(3 * SR), 0.2, 0.5), -12)

t = t_(7.6); od = np.zeros(len(t))
for k in range(22):
    i = int((k / 3) * SR); od[i:i + 900] += hp(noise(900 / SR), 3000) * np.exp(-np.arange(900) / 120) + sine(1800, 900 / SR) * np.exp(-np.arange(900) / 80) * 0.3
save("odometer.wav", od, -14)

t = t_(9.0); f = 300 + 500 * (t / 9)
bub = np.zeros(len(t))
for at in rng.uniform(0, 8.8, 420):
    i = int(at * SR); k = 1400; fb = rng.uniform(300, 900) * (1 + at / 9)
    bub[i:i + k] += sine(fb * (1 + 2 * np.arange(k) / SR), k / SR) * np.exp(-np.arange(k) / 260) * 0.2
flow = lp(noise(9.0), 700) * 0.5
save("water_fill.wav", reverb((bub + flow) * adsr(len(t), 0.6, 1.2), 1.0, 0.2), -11)

t = t_(6.0)
glass = sum(sine(f, 6.0) * np.exp(-t / rng.uniform(0.4, 2.0)) * rng.uniform(0.2, 1) for f in rng.uniform(2200, 9000, 40))
burst = hp(noise(6.0), 1200) * np.exp(-t / 0.25)
air = bp(noise(6.0), 5000, 1.5) * np.exp(-t / 1.6) * 0.4
save("shatter.wav", reverb(glass * 0.25 + burst + air, 2.5, 0.35), -6)

t = t_(6.0); f = 220 * (2 ** (t / 2.0))
rise = (sine(np.minimum(f, 1800), 6.0) * 0.4 + bp(noise(6.0), 3000, 2) * 0.2) * adsr(len(t), 4.5, 1.0)
save("feed_rise.wav", reverb(rise, 1.5, 0.3), -12)

t = t_(10.0); sh = np.zeros(len(t))
scale = [523.3, 587.3, 659.3, 784, 880, 1046.5, 1174.7, 1318.5]
for k in range(32):
    i = int(k * 0.28 * SR); n = int(2.2 * SR)
    if i + n > len(sh): break
    sh[i:i + n] += sine(scale[k % 8] * (1 + (k // 8) * 0.5), 2.2) * env(n, 0.002, 0.5) * 0.2
save("timeline_shimmer.wav", reverb(sh, 2.8, 0.45), -14)

t = t_(3.0); tune = np.zeros(len(t))
whistle = sine(2400 - 1800 * (t / 3) ** 0.5, 3.0) * 0.15 * (1 - t / 3)
static = bp(noise(3.0), 2000, 0.6) * (1 - t / 3.2) * 0.5
warm = sum(sine(f, 3.0) for f in (196, 293.7)) * 0.2 * np.clip((t - 1.6) / 1.0, 0, 1)
save("radio_tune.wav", lp(whistle + static + warm, 6000) * adsr(len(t), 0.05, 0.8), -12)
t = t_(2.5); zap = hp(noise(2.5), 2000) * np.exp(-t / 0.05) * 0.6 + sine(60, 2.5) * 0.3 * np.exp(-t / 1.2) + sine(120, 2.5) * 0.15 * np.exp(-t / 1.0)
save("tv_hum.wav", zap, -12)
t = t_(2.6); mod = np.zeros(len(t))
for k, (a, b, f) in enumerate(((0, 0.4, 1650), (0.45, 0.9, 1850), (0.95, 1.25, 2100), (1.3, 2.4, 1200))):
    i0, i1 = int(a * SR), int(b * SR); mod[i0:i1] += sine(f + (300 if k == 3 else 0) * np.sign(np.sin(2 * np.pi * 25 * t[i0:i1])), (i1 - i0) / SR) * 0.3
mod[int(1.3 * SR):] += hp(noise(1.3), 1500)[: len(mod) - int(1.3 * SR)] * 0.15
save("modem.wav", lp(mod, 3600) * adsr(len(t), 0.02, 0.4), -16)

t = t_(3.5); doors = np.zeros(len(t))
for at in (0.0, 0.25, 0.5, 0.8, 1.1):
    i = int(at * SR); doors[i:i + 2000] += hp(noise(2000 / SR), 1500) * np.exp(-np.arange(2000) / 200) * 0.6
doors += lp(noise(3.5), 300) * adsr(len(t), 0.4, 1.5) * 0.6
save("doors_open.wav", reverb(doors, 1.8, 0.3), -9)

t = t_(7.0)
hum = sum(sine(f * (1 + 0.5 * np.clip(t / 2.5, 0, 1) * 0), 7.0) for f in (110, 165, 220)) * 0.25
glow = bp(noise(7.0), 4000, 3) * 0.08
save("beam_hum.wav", reverb((hum + glow) * adsr(len(t), 2.0, 2.0), 2.0, 0.35), -14)

t = t_(5.0); ch = np.zeros(len(t))
for k, f in enumerate((659.3, 830.6, 987.8, 1318.5)):
    i = int(k * 0.18 * SR); n = len(t) - i
    ch[i:] += (sine(f, n / SR) + 0.3 * sine(f * 2.76, n / SR)) * env(n, 0.003, 1.2) * 0.25
save("devices_chime.wav", reverb(ch, 2.5, 0.4), -12)

t = t_(9.0)
sw = sum(sine(f, 9.0) / (1 + i * 0.4) for i, f in enumerate((146.8, 220, 293.7, 369.9, 440, 587.3)))
save("commons_swell.wav", reverb(lp(sw, 2500) * adsr(len(t), 4.0, 3.0), 3.0, 0.4), -12)
print("done")
