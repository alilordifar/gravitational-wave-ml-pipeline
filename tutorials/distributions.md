# 🔭 LIGO Signal Detection — Study Notes

## Table of Contents

- [🔥 Two Different Distributions](#-two-different-distributions-very-important)
- [🧠 Part 1 — Distribution of Data Values (z-scores)](#-part-1--distribution-of-data-values-z-scores)
- [🧠 Part 2 — Distribution of Window Stds](#-part-2--distribution-of-window-stds)
- [⚡ Critical Difference](#-critical-difference)
- [🔍 Why Low Std = Noise?](#-why-low-std--noise)
- [✅ What Does "20% Lowest Std" Mean?](#-what-does-20-lowest-std-mean)
- [🔁 Full Pipeline](#-full-pipeline-connect-everything)
- [🎯 Final Intuition](#-final-intuition)
- [🔊 Understanding LIGO Signals — Concrete Numbers](#-understanding-ligo-signals--concrete-numbers)
  - [1. Noise](#1-noise--random-behavior)
  - [2. Low Frequency Signal](#2-low-frequency-signal--slow-oscillation)
  - [3. High Frequency Signal](#3-high-frequency-signal--fast-oscillation)
  - [4. LIGO Event — The Chirp](#4-ligo-event--the-chirp)
  - [5. Realistic Signal — Noise + Event](#5-realistic-signal--noise--event)
  - [Signal Types at a Glance](#signal-types-at-a-glance)

---

## 🔥 Two Different Distributions (VERY IMPORTANT)

Do not mix **two different distributions**. Let's separate them clearly.

| Distribution | What it looks at | What we look for |
|---|---|---|
| z-score values | individual strain samples | **tails** = events |
| window std values | chunks of time (windows) | **left side** = noise |

> ❌ **Wrong:** "we select tails for noise"
>
> ✅ **Correct:** we select **low-std windows** (left side) for noise, and **high z-values** (tails) for events.

---

## 🧠 Part 1 — Distribution of Data Values (z-scores)

This is about **individual strain values**. After normalization, each sample gets a z-score.

### Example (after normalization)

```
[-2, -1, 0, 1, 2, 0.5, -0.8, 3, -4]
```

### Interpretation

| z-score | Meaning |
|---------|---------|
| `z ≈ 0` | normal noise |
| `z ≈ ±1` | typical |
| `z ≈ ±2` | a bit unusual |
| `z ≈ ±3+` | rare |
| `z ≈ ±5` | very rare → 🚨 possible event |

> **Key idea:** this distribution tells you — *"how unusual is a single data point?"*

---

## 🧠 Part 2 — Distribution of Window Stds

Now we switch perspective. We are **not** looking at individual points anymore — we are looking at **windows** (chunks of time).

### Example (std per window)

```
stds = [0.9, 1.1, 0.8, 1.0, 5.0, 6.2, 0.7, 1.2]
```

> ⚠️ **Important:** window stds are **always positive** and we treat them as an **ordered (incremental) scale** — from the quietest windows on the left to the most active on the right.

### Interpretation

| Window std | Meaning |
|------------|---------|
| Small std | calm window → little movement → likely **noise** |
| Large std | lots of movement → possible **signal** |

> **Key idea:** this distribution tells you — *"how active is this window?"*

---

## ⚡ Critical Difference

| Concept | What it measures | What we look for |
|---------|-----------------|-----------------|
| z-score (values) | how unusual a point is | **tails** = events |
| std (windows) | how active a window is | **left side** = noise |

```
z-score distribution:   look at the TAILS    → events
window std distribution: look at the LEFT SIDE → noise
```

---

## 🔍 Why Low Std = Noise?

Imagine two windows:

**Window A — quiet**

```
[0.1, -0.2, 0.15, -0.1]
→ small movement
→ std small
→ ✅ noise
```

**Window B — event**

```
[0.1, -0.2, 5.0, -0.1]
→ huge spike
→ std large
→ 🚨 possible event
```

---

## ✅ What Does "20% Lowest Std" Mean?

We compute std for each window, then sort them from smallest to largest.

> Window stds are **always positive** and naturally **incremental** — sorting them gives a clean ordered scale from "most boring" to "most active."

### Step 1 — Compute and sort

```
stds = [0.7, 0.8, 0.9, 1.0, 1.1, 5.0, 6.2]
         ↑ sorted, smallest to largest, all positive
```

### Step 2 — Take the lowest 20%

```
Total windows = 7
20% of 7 ≈ 1–2 windows

→ We take: [0.7, 0.8]
```

These are the **quietest windows** — the most boring parts of the signal.

### Why these?

- Small std → little movement → **noise** ✅
- Large std → spikes / activity → **possible signal** ⚠️

```
[0.7, 0.8] | 0.9, 1.0, 1.1, 5.0, 6.2
 ↑ keep     ↑ discard for noise estimation
```

> **Final intuition:** we are picking the **most boring parts of the signal** to learn what "normal noise" looks like.

### What we are NOT doing

- ❌ picking random windows
- ❌ picking large values
- ❌ picking tails

We are specifically picking:

> ✅ the **smallest std values** — the calmest, flattest regions of the signal.

---

## 🔁 Full Pipeline — Connect Everything

**Step 1 — Find noise baseline**

Take windows with the lowest std (bottom 20%) → calm regions → learn "normal behavior".

```python
threshold = np.percentile(window_stds, 20)
noise_windows = [w for w, s in zip(windows, stds) if s <= threshold]
```

**Step 2 — Normalize data**

Compute mean and std from the noise windows. Convert every sample to a z-score.

$$z = \frac{x - \mu_{\text{noise}}}{\sigma_{\text{noise}}}$$

```python
mu    = np.mean(noise_signal)
sigma = np.std(noise_signal)

z_scores = (strain - mu) / sigma
```

**Step 3 — Detect events**

Look for large `|z|` values (tails).

```python
events = np.where(np.abs(z_scores) >= 5)[0]
```

---

## 🎯 Final Intuition

```
center of z-distribution   →  normal noise
tails of z-distribution    →  unusual  →  events

left side of std-distribution  →  quiet windows  →  noise baseline
right side of std-distribution →  active windows →  possible signal
```

> **One-line summary:** we use low-std windows to *define* noise, and high z-values to *detect* events.
>
> If you understand this, you've unlocked the core idea behind signal detection.
---

## 🔊 Understanding LIGO Signals — Concrete Numbers

Four signal types, shown as raw numbers so the pattern is impossible to miss.

---

### 1. Noise — Random Behavior

```
[ 0.2, -0.1, 0.3, -0.4, 0.1, -0.2, 0.05, -0.1 ]
```

No pattern. Random ups and downs. Small fluctuations around zero.

> **Intuition:** noise = random wiggles around 0 with no structure.

---

### 2. Low Frequency Signal — Slow Oscillation

```
[ 0.0, 0.5, 1.0, 0.5, 0.0, -0.5, -1.0, -0.5 ]
```

Values change slowly. Smooth wave-like pattern — takes a long time to complete one cycle.

> **Intuition:** low frequency = slow, lazy movement over time.

---

### 3. High Frequency Signal — Fast Oscillation

```
[ 1, -1, 1, -1, 1, -1, 1, -1 ]
```

Rapid flipping between values. Many ups and downs packed into a short time.

> **Intuition:** high frequency = fast, tight oscillation.

---

### 4. LIGO Event — The Chirp

This is the key one. A chirp **starts slow and gets faster and stronger** — that's the gravitational wave signature.

```
[
  0.1,  0.2,  0.3,  0.2,  0.1,       # slow start   → low frequency
 -0.2, -0.4, -0.2,  0.2,  0.4,       # speeding up  → frequency increasing
 -0.6,  0.6, -0.7,  0.7, -0.8,  0.8  # fast + loud  → high frequency, high amplitude
]
```

Breaking it down:

| Phase | Values | What's happening |
|-------|--------|-----------------|
| 🟢 Beginning | `0.1 → 0.2 → 0.3 → 0.2 → 0.1` | smooth, slow changes — low frequency |
| 🟡 Middle | `-0.2 → -0.4 → -0.2 → 0.2 → 0.4` | transitions getting faster — frequency rising |
| 🔴 End | `-0.6, 0.6, -0.7, 0.7, -0.8, 0.8` | rapid oscillation + large values — peak of the event |

> **Intuition:** a LIGO event is a chirp — starts slow, becomes faster, gets stronger.

---

### 5. Realistic Signal — Noise + Event

What you actually see in LIGO data: a quiet stretch, then the event, then quiet again.

```
[
  0.2, -0.1,  0.1, -0.2,  0.1,    # noise
  0.3,  0.4,  0.3,                 # event begins
 -0.5,  0.5, -0.6,  0.6,          # faster oscillation
 -0.8,  0.8, -1.0,  1.0,          # strong + fast → peak
  0.1, -0.2,  0.1                  # back to noise
]
```

| Section | Character |
|---------|-----------|
| Beginning | just noise — no structure |
| Middle | structured pattern emerges |
| Peak | strong, fast oscillation |
| End | returns to noise |

---

### Signal Types at a Glance

| Type | Behavior | Pattern | Std |
|------|----------|---------|-----|
| Noise | Random | No structure | small, stable |
| Low frequency | Slow oscillation | Smooth wave | moderate |
| High frequency | Fast oscillation | Rapid flips | moderate |
| LIGO event (chirp) | Frequency + amplitude both rise | Starts slow → ends fast & loud | **large** |

> **One-line summary:** LIGO events look like numbers that start slow and smooth, then oscillate faster and stronger — that's what makes them detectable against background noise.