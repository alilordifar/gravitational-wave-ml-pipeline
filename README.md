# Gravitational Waves Detection
## 🌌 What is LIGO?

**LIGO (Laser Interferometer Gravitational-Wave Observatory)** is a large-scale physics experiment designed to detect **gravitational waves**—tiny ripples in spacetime predicted by Albert Einstein in 1916.

---

## 🧠 Definition (Core Idea)

- Uses **laser interferometry** to measure extremely small changes in distance  
- Detects waves from:
  - black hole mergers  
  - neutron star collisions  
- Sensitivity: ~1/10,000 the size of a proton  

---

## 🕰️ Brief History

- **1916** → Gravitational waves predicted (Einstein)  
- **1970s–80s** → Concept developed (Rainer Weiss and others)  
- **1990s** → Construction begins (funded by NSF)  
- **2015** → First detection (GW150914)  
- **2017** → Nobel Prize awarded  

---

## 📍 Detectors

### 🔹 H1 — Hanford

- Location: Washington, USA  
- Name: **H1**  
- Environment: relatively stable, less environmental noise  

---

### 🔹 L1 — Livingston

- Location: Louisiana, USA  
- Name: **L1**  
- Environment: more seismic and environmental noise  

---

## ⚙️ Structure (Both H1 & L1)

- Two **perpendicular arms (4 km each)**  
- Laser beams travel inside vacuum tubes  
- Gravitational wave → tiny stretch/compression → detected as signal  

---

## 🎯 Why Two Detectors?

- Confirm signals are **real (not noise)**  
- Measure **time delay between sites**  
- Help **locate source in the sky**  

---

## 🧩 One-Line Summary

**LIGO = two 4 km laser interferometers measuring tiny spacetime distortions from cosmic events**

---
## LIGO Data
### What is an HDF5 file?
- HDF5 = a container file, not a flat table.

Think of it like:
- A filesystem inside a single file

Just like a disk has folders and files, an HDF5 file has:
- Groups → like folders
- Datasets → like files (arrays, tables, numbers)
- Attributes → metadata (key–value info)

```
myfile.hdf5
│
├── /strain
│    └── strain           ← 1D NumPy-like array (the signal)
│
├── /meta
│    ├── detector         ← "H1" or "L1"
│    ├── sample_rate
│    └── gps_start_time
│
└── /quality
     └── data_flags
```

### Why LIGO uses HDF5
Because LIGO data is:
1. Huge
2. Hierarchical
3. Mixed data types
4. Needs metadata tightly coupled to the signal
5. CSV or Parquet would be a bad fit.

### What’s inside a LIGO HDF5 (practically)

You will almost always find:

1️⃣ Strain (the main thing)

- A 1D array
- Length = sample_rate × duration
- This is what you plot, filter, and model

2️⃣ Metadata

- Sample rate
- GPS time
- Detector name (H1 / L1)
- Units

3️⃣ Quality flags (sometimes)

- Marks bad segments
- Glitches
- Missing data

### One-sentence intuition (lock this in)

**An HDF5 file is a mini data lake: signal + metadata + structure, all in one file.**

----
### LIGO filenames are very informative. Let’s decode them piece by piece.
`
<Observatory>-<Detector>_<Source>_<SampleRate>_<Release>-<GPS_START>-<DURATION>.hdf5
`

| Part         | Meaning                                |
| ------------ | -------------------------------------- |
| `H`          | Hanford observatory                    |
| `H1`         | Hanford detector (interferometer)      |
| `L`          | Livingstone observatory                    |
| `L1`         | Livingstone detector (interferometer)      |
| `GWOSC`      | Gravitational Wave Open Science Center |
| `4KHZ`       | Sampling rate = **4096 Hz**            |
| `R1`         | Data release version                   |
| `1264316101` | GPS start time (seconds)               |
| `32`         | Duration = **32 seconds**              |
| `.hdf5`      | File format                            |

---
## Sample Rate
LIGO data is a 1D time-series of strain measurements. A sample is one measurement taken at a specific instant. The sampling rate (e.g., 4096 Hz) means the detector records 4096 samples every second. Time is implicit: sample index × (1 / sampling rate). The duration of a file is total samples ÷ sampling rate (e.g., 131,072 ÷ 4096 = 32 s). Higher sampling rate gives finer time resolution, not longer duration.

---

### Here’s how size is calculated in that code, step by step, briefly:
1. N = len(strain) → Counts how many samples are in strain.
2. strain.itemsize → Size of one element in bytes (e.g., 8 bytes for a float64).
3. N * strain.itemsize → Total bytes used by all samples.
4. 1024**2 → Converts bytes to megabytes (MB).

Computers represent data in binary (base-2), so memory sizes are counted in powers of 2, not powers of 10. One byte equals 8 bits. The closest power of 2 to 1000 is 2¹⁰ = 1024, so 1 KB = 1024 bytes. Each larger unit adds another factor of 1024: 1 MB = 2²⁰ bytes, 1 GB = 2³⁰ bytes. This convention aligns memory measurement with how computers actually store and address data.

---

`total_time = total_samples ÷ samples_per_second`

`131072 ÷ 4096 = 32 seconds`

---

#### The real difference np.linspace and np.arange:

**np.linspace(start, stop, N):**
→ exactly N evenly spaced points (step is computed)
`np.linspace(0, 1, 4)`
`[0.00, 0.33, 0.67, 1.00]  ← evenly spaced, not random`


**np.arange(start, stop, step):**
→ exact step size, number of points depends on it
`np.arange(0, 1, 0.25)`
`[0.00, 0.25, 0.50, 0.75]`

---

# Time ↔ Sample Index Conversion (Clean Intuition)

## Core idea
LIGO data is stored as **samples**, not time.  
The **sampling rate (`fs`)** tells us how many samples are taken per second.

---

## What is sampling rate?
- `fs = 4096 Hz`  
- Meaning: **4096 samples every 1 second**

---

## Two conversion rules (memorize these)

### 1️⃣ Time → Sample index (MULTIPLY)
Use this when you want to know **which sample corresponds to a time**.

**Formula:**
sample_index = time_in_seconds × fs

---

**Example:**
- 1 second → `1 × 4096 = 4096`
- 10 seconds → `10 × 4096 = 40960`

Interpretation:  
> How many samples have occurred by this time?

---

### 2️⃣ Sample index → Time (DIVIDE)
Use this when you want to know **what time a sample represents**.

**Formula:**
time_in_seconds = sample_index ÷ fs


**Example:**
- sample 4096 → `4096 ÷ 4096 = 1 second`
- sample 2048 → `2048 ÷ 4096 = 0.5 seconds`

Interpretation:  
> How many seconds does this many samples represent?

---

## Why both are needed
- **Multiply** → choose where to zoom or slice
- **Divide** → label the x-axis in plots

---

## Analogy (video frames)
- Frames per second (FPS) ≈ samples per second (fs)
- Time → frame number → multiply
- Frame number → time → divide

---

## One-line takeaway
**Multiply to go from time to samples.  
Divide to go from samples to time.**
