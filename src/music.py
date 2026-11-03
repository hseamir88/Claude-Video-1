"""Generate original royalty-free background music + transition whooshes (numpy synthesis).
Usage: python3 src/music.py out.wav
"""
import sys, wave
import numpy as np

SR = 44100
TOTAL = 177.0
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
TRANSITIONS = [9, 21, 45, 73, 101, 131, 156, 171]
rng = np.random.default_rng(514)
N = int(SR * TOTAL)
t_all = np.arange(N) / SR

def midi(m): return 440.0 * 2 ** ((m - 69) / 12)

# Am - F - C - G  (one chord per bar)
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
BASS = [45, 41, 48, 43]

def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e

PADN = N + 3 * SR  # headroom so note tails never overflow; trimmed below
pad = np.zeros(PADN); arp = np.zeros(PADN); bass = np.zeros(PADN); drums = np.zeros(PADN)
nbars = int(np.ceil(TOTAL / BAR))
for b in range(nbars):
    start = int(b * BAR * SR); n = int(BAR * SR)
    if start >= N: break
    tt = np.arange(n) / SR
    ch = CHORDS[b % 4]
    # warm pad: detuned sines + soft 2nd/3rd harmonics
    seg = np.zeros(n)
    for m in ch + [ch[0] + 12]:
        f = midi(m)
        for det in (-0.12, 0.12):
            ff = f * 2 ** (det / 12)
            seg += np.sin(2 * np.pi * ff * tt) + 0.25 * np.sin(4 * np.pi * ff * tt) + 0.08 * np.sin(6 * np.pi * ff * tt)
    pad[start:start + n] += seg * env_adsr(n, 0.6, 0.6) * 0.05
    # bass: root, plucky per beat
    for k in range(4):
        s0 = int(k * BEAT * SR); nn = min(int(BEAT * SR), n - s0)
        if nn <= 0: continue
        tb = np.arange(nn) / SR
        f = midi(BASS[b % 4])
        bass[start + s0:start + s0 + nn] += (np.sin(2 * np.pi * f * tb) + 0.3 * np.sin(4 * np.pi * f * tb)) * np.exp(-tb * 3.0) * 0.22
    # arpeggio 8ths (starts bar 2)
    if b >= 2:
        pattern = [0, 1, 2, 3, 2, 1, 2, 3]
        notes = ch + [ch[0] + 12]
        for k in range(8):
            s0 = int(k * BEAT / 2 * SR); nn = min(int(BEAT / 2 * SR * 1.8), n - s0)
            if nn <= 0: continue
            tb = np.arange(nn) / SR
            f = midi(notes[pattern[k]] + 12)
            tone = np.sin(2 * np.pi * f * tb) + 0.35 * np.sin(2 * np.pi * 2 * f * tb) * np.exp(-tb * 10)
            arp[start + s0:start + s0 + nn] += tone * np.exp(-tb * 7) * 0.06
    # soft drums (from bar 4): kick 1&3, hat on 8ths
    if b >= 4:
        for k in range(4):
            s0 = start + int(k * BEAT * SR)
            if k in (0, 2):
                nn = int(0.35 * SR); tb = np.arange(nn) / SR
                f = 50 + 70 * np.exp(-tb * 30)
                ph = 2 * np.pi * np.cumsum(f) / SR
                drums[s0:s0 + nn] += np.sin(ph) * np.exp(-tb * 9) * 0.45
            if k in (1, 3):  # soft clap/snare
                nn = int(0.18 * SR); tb = np.arange(nn) / SR
                drums[s0:s0 + nn] += rng.standard_normal(nn) * np.exp(-tb * 25) * 0.06
            for h in (0, 1):
                s1 = s0 + int(h * BEAT / 2 * SR); nn = int(0.04 * SR)
                noise = rng.standard_normal(nn); noise = np.diff(noise, prepend=0)
                drums[s1:s1 + nn] += noise * np.exp(-np.arange(nn) / SR * 90) * 0.025

# slight reverb-ish tail on pad/arp via feedback delays
def echo(x, delay, fb, mix):
    d = int(delay * SR); y = x.copy()
    for i in range(1, 5):
        y[d * i:] += x[:-d * i] * (fb ** i) * mix
    return y

music = (echo(pad, 0.31, 0.5, 0.6) + echo(arp, BEAT * 0.75, 0.45, 0.5) + bass + drums)[:N]

# transitions: whoosh = band-shaped noise sweep
fx = np.zeros(N)
for tr in TRANSITIONS:
    nn = int(0.9 * SR); s0 = int((tr - 0.55) * SR)
    tb = np.arange(nn) / SR
    noise = rng.standard_normal(nn)
    # crude sweep: progressively smoothed noise
    sm = np.convolve(noise, np.ones(8) / 8, mode='same')
    shape = np.sin(np.pi * tb / tb[-1]) ** 2
    fx[s0:s0 + nn] += sm * shape * 0.18

mix = music + fx
# fade in/out
fi, fo = int(1.5 * SR), int(4 * SR)
mix[:fi] *= np.linspace(0, 1, fi)
mix[-fo:] *= np.linspace(1, 0, fo)
mix = np.tanh(mix * 1.2)
mix = mix / np.max(np.abs(mix)) * 0.7
# stereo: slight width via delayed copy
L = mix; R = np.concatenate([np.zeros(int(0.012 * SR)), mix[:-int(0.012 * SR)]]) * 0.5 + mix * 0.5
st = np.stack([L, R], axis=1)
pcm = (st * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('wrote', sys.argv[1], TOTAL, 's')
