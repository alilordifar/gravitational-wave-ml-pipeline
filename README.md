# 🔭 LIGO & Signal Processing — Study Notes

## Table of Contents

- [🌌 What is LIGO?](#-what-is-ligo)
- [📁 HDF5 Data Format](#-hdf5-data-format)
- [🗂️ Filename Decoder](#️-filename-decoder)
- [⏱️ Sample Rate & Time Conversion](#️-sample-rate--time-conversion)
- [📐 Min-Max Normalization](#-min-max-normalization)
- [📐 Z-score Standardization](#-z-score-standardization)
- [⚖️ Min-Max vs. Standardization](#️-min-max-vs-standardization)
- [📊 The Gaussian Rules](#-the-gaussian-rules)
- [🔍 Deep Intuition — Std & Z-scores](#-deep-intuition--std--z-scores)

---

## 🌌 What is LIGO?

**LIGO (Laser Interferometer Gravitational-Wave Observatory)** is a large-scale physics experiment designed to detect **gravitational waves** — tiny ripples in spacetime first predicted by Albert Einstein in 1916.

- Uses **laser interferometry** to measure distance changes smaller than 1/10,000 the size of a proton
- Detects waves from events like black hole mergers and neutron star collisions

### Brief History

| Year | Event |
|------|-------|
| 1916 | Gravitational waves predicted — Einstein |
| 1970s–80s | Concept developed — Rainer Weiss & others |
| 1990s | Construction begins — funded by NSF |
| 2015 | First detection — **GW150914** |
| 2017 | Nobel Prize awarded |

### The Two Detectors

| Detector | Location | Notes |
|----------|----------|-------|
| **H1** | Hanford, Washington | Relatively stable — less environmental noise |
| **L1** | Livingston, Louisiana | More seismic and environmental noise |

**Structure (both sites):**
- Two **perpendicular arms (4 km each)**
- Laser beams travel inside vacuum tubes
- A gravitational wave causes a tiny stretch/compression → detected as a signal

**Why two detectors?**
- Confirm signals are **real** (not noise)
- Measure the **time delay between sites**
- Help **locate the source** in the sky

> **One-line summary:** LIGO = two 4 km laser interferometers measuring tiny spacetime distortions from cosmic events.

---

## 📁 HDF5 Data Format

HDF5 is a **container file**, not a flat table. Think of it like a filesystem inside a single file:

| HDF5 Concept | Analogy |
|--------------|---------|
| Groups | Folders |
| Datasets | Files — arrays, numbers |
| Attributes | Metadata — key–value pairs |

```
myfile.hdf5
│
├── /strain
│    └── strain           ← 1D array (the signal)
│
├── /meta
│    ├── detector         ← "H1" or "L1"
│    ├── sample_rate
│    └── gps_start_time
│
└── /quality
     └── data_flags
```

### What's Inside

**① Strain** — the main signal
- A 1D array of length `sample_rate × duration`
- This is what you plot, filter, and model

**② Metadata**
- Sample rate, GPS time, detector name, units

**③ Quality flags** *(sometimes)*
- Marks bad segments, glitches, and missing data

**Why not CSV or Parquet?**
LIGO data is huge, hierarchical, mixed-type, and needs metadata tightly coupled to the signal — flat formats can't handle that.

> **One-line intuition:** An HDF5 file is a mini data lake — signal + metadata + structure, all in one file.

### File Size Calculation

```python
N              = len(strain)          # number of samples
bytes_per_item = strain.itemsize      # e.g. 8 bytes for float64
total_bytes    = N * bytes_per_item
size_in_mb     = total_bytes / 1024**2
```

Memory is measured in powers of 2 because computers use binary:
`1 KB = 1024 B`, `1 MB = 2²⁰ B`, `1 GB = 2³⁰ B`.

---

## 🗂️ Filename Decoder

```
<Observatory>-<Detector>_<Source>_<SampleRate>_<Release>-<GPS_START>-<DURATION>.hdf5
```

| Part | Meaning |
|------|---------|
| `H` | Hanford observatory |
| `H1` | Hanford detector (interferometer) |
| `L` | Livingston observatory |
| `L1` | Livingston detector (interferometer) |
| `GWOSC` | Gravitational Wave Open Science Center |
| `4KHZ` | Sampling rate = **4096 Hz** |
| `R1` | Data release version |
| `1264316101` | GPS start time (seconds) |
| `32` | Duration = **32 seconds** |
| `.hdf5` | File format |

---

## ⏱️ Sample Rate & Time Conversion

LIGO data is a 1D time-series of strain measurements.

- A **sample** is one measurement taken at a specific instant
- `fs = 4096 Hz` means **4096 samples recorded every second**
- Time is implicit: `sample_index × (1 / fs)`
- Duration = `total_samples ÷ sample_rate` → e.g. `131072 ÷ 4096 = 32 s`

> Higher sampling rate = finer time resolution — **not** longer duration.

### Rule 1 — Time → Sample Index (multiply)

$$\text{sample\\_index} = \text{time} \times f_s$$

```
1 second   →  1  × 4096 = 4096
10 seconds →  10 × 4096 = 40960
```

> *"How many samples have occurred by this time?"*

### Rule 2 — Sample Index → Time (divide)

$$\text{time} = \frac{\text{sample\\_index}}{f_s}$$

```
sample 4096  →  4096 ÷ 4096 = 1.0 second
sample 2048  →  2048 ÷ 4096 = 0.5 seconds
```

> *"How many seconds does this many samples represent?"*

### When to Use Each

| Operation | Direction | Rule |
|-----------|-----------|------|
| Zoom / slice the signal | time → samples | **Multiply** |
| Label the x-axis in a plot | samples → time | **Divide** |

### `np.linspace` vs `np.arange`

| | `np.linspace(start, stop, N)` | `np.arange(start, stop, step)` |
|---|-------------------------------|-------------------------------|
| **Controls** | Number of points | Step size |
| **Output** | Exactly N evenly spaced points | As many as step allows |
| **Example** | `[0.00, 0.33, 0.67, 1.00]` | `[0.00, 0.25, 0.50, 0.75]` |

> **One-line takeaway:** Multiply to go from time to samples. Divide to go from samples to time.

---

## 📐 Min-Max Normalization

Converts all values into the range **[0, 1]**. The smallest becomes 0, the largest becomes 1.

### Formula

$$x' = \frac{x - x_{\min}}{x_{\max} - x_{\min}}$$

| Part | What it measures |
|------|-----------------|
| $x - x_{\min}$ (numerator) | Distance from the minimum |
| $x_{\max} - x_{\min}$ (denominator) | Total possible distance — the full range |
| Result | *"What fraction of the full range have we covered?"* |

### Worked Example

```
data = [10, 20, 30]
x_min = 10,   x_max = 30,   range = 20
```

| Original | Calculation | Normalized |
|----------|-------------|------------|
| 10 | (10 − 10) / 20 | **0.0** |
| 20 | (20 − 10) / 20 | **0.5** ← halfway |
| 30 | (30 − 10) / 20 | **1.0** |

> ⚠️ **Sensitive to outliers.** A single value like `1000` in `[10, 20, 30, 1000]` stretches the scale — everything else collapses toward `0`.

### Python

```python
x_min = np.min(strain1)
x_max = np.max(strain1)

strain_minmax = (strain1 - x_min) / (x_max - x_min)
```

---

## 📐 Z-score Standardization

Instead of fixing values to a range, standardization asks: *how unusual is this value compared to normal behavior?*

### Formula

$$z = \frac{x - \mu}{\sigma}$$

| Part | What it measures |
|------|-----------------|
| $x - \mu$ (numerator) | How far from average? |
| $\sigma$ (denominator) | What is a typical movement size? |
| Result | *"How many normal-sized jumps away from average?"* |

### Worked Example

```
data = [10, 12, 14]
μ = 12,   σ ≈ 2
```

| Original | Calculation | z-score | Meaning |
|----------|-------------|---------|---------|
| 10 | (10 − 12) / 2 | **−1** | 1 std dev below mean |
| 12 | (12 − 12) / 2 | **0** | exactly at the mean |
| 14 | (14 − 12) / 2 | **+1** | 1 std dev above mean |

### Std is NOT a Maximum

Std is **one normal-sized step** — not a ceiling. Z-scores are unbounded:

```
z = 1    →  normal
z = 3    →  unusual
z = 10   →  very rare
z = 100  →  extreme outlier
```

### LIGO Example

```
Hanford:  μ ≈ 0,   σ ≈ 4.6e-20

x = 5e-20  →  z ≈ 1.09   (normal noise — not unusual)
x = 2e-19  →  z ≈ 4.35   (worth investigating!)
```

### Python

```python
mean = np.mean(strain1)
std  = np.std(strain1)

strain_standardized = (strain1 - mean) / std
```

---

## ⚖️ Min-Max vs. Standardization

| | Min-Max | Standardization |
|---|---------|-----------------|
| **Formula** | $\dfrac{x - x_{\min}}{x_{\max} - x_{\min}}$ | $\dfrac{x - \mu}{\sigma}$ |
| **Denominator means** | Full range | One typical jump (σ) |
| **Output range** | Always `[0, 1]` | Unbounded, centered at 0 |
| **Has a maximum?** | ✅ Yes — always 1 | ❌ No — unbounded |
| **Sensitive to outliers?** | ✅ Yes | ❌ Less so |
| **Core question** | *"Where are we between min and max?"* | *"How unusual is this?"* |
| **Best for** | Fixed-scale inputs (e.g. neural nets) | Anomaly detection in signals |

> **For LIGO:** standardization wins — we care about detecting unusual values vs. normal noise, not fitting a `[0, 1]` scale.

---

## 📊 The Gaussian Rules

For a **Normal (Gaussian)** distribution, std tells you the *"typical spread"* of your data.

| Range | Coverage | Plain English |
|-------|----------|---------------|
| $\mu \pm 1\sigma$ | **~68%** of values | most values live here |
| $\mu \pm 2\sigma$ | **~95%** of values | almost all values live here |
| $\mu \pm 3\sigma$ | **~99.7%** of values | nearly everything lives here |

### Worked Example — `mean = 100`, `std = 5`

```
1σ range:   100 ± 5   =  [95,  105]   →  ~68%   of values
2σ range:   100 ± 10  =  [90,  110]   →  ~95%   of values
3σ range:   100 ± 15  =  [85,  115]   →  ~99.7% of values
```

> ⚠️ `100 ± 5` captures **~68%** of values — not 95%, not all of them.

**Key intuitions:**
- Std = the **"typical jump size"** away from the mean
- Most data stays within **a few stds** of the mean
- Values many stds away are **rare and unusual**

> This holds when data is roughly **Gaussian and centered around the mean**.

---

## 🔍 Deep Intuition — Std & Z-scores

### Why We Divide by σ

$$z = \frac{x - \mu}{\sigma} = \frac{\text{distance from average}}{\text{size of one typical jump}}$$

**Step 1 — subtract the mean:** $x - \mu$
Centers the data at zero. *"How far is this value from average?"*

**Step 2 — divide by std:** $\frac{x - \mu}{\sigma}$
*"How large is that distance compared to a typical movement?"*

### Worked Example

```
mean = 100,   std = 5,   value = 115

distance from mean:  115 - 100 = 15
typical jump size:   5

z = 15 / 5 = 3  →  3 typical jumps away (unusual)
```

### Interpreting Z-scores

| z-score | Meaning | Rarity |
|---------|---------|--------|
| `0` | Exactly at the mean | Typical |
| `±1` | One typical jump away | Common (~68%) |
| `±2` | Two typical jumps away | Less common (~95%) |
| `±3` | Three typical jumps away | Rare (~99.7%) |
| `≥ 4` | Far from normal | **Potentially interesting** |

### One-Line Intuitions

```
Min-Max:          "relative position in the range"
Standardization:  "how many typical jumps from average"
```

> For LIGO: a z-score of `4.35` immediately signals *this is unusual* — far more informative than a min-max value of `0.003`.