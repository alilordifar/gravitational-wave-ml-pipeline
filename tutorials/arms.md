## ⚖️ Why Noise Fluctuates Around Zero

### What LIGO measures

$$\text{signal} \propto L_x - L_y$$

Everything follows from this one formula.

---

### Case 1 — Perfect common noise (same in both arms)

```
Arm X = +0.5
Arm Y = +0.5

X - Y = 0  →  cancels completely  ✅
```

---

### Case 2 — Realistic noise (almost the same)

```
Arm X = +0.50
Arm Y = +0.48

X - Y = +0.02  →  small residual value around 0
```

> This is what noise actually looks like in the signal — tiny leftover differences.

---

### Case 3 — Gravitational wave (opposite)

```
Arm X = +0.5
Arm Y = -0.5

X - Y = 1.0  →  large, structured difference  🚀
```

---

### Why the mean of noise ≈ 0

Noise differences are not consistently positive or negative — they fluctuate:

- sometimes `X > Y` → positive residual
- sometimes `X < Y` → negative residual

```
positive + negative  →  cancel over time  →  mean ≈ 0
```

---

### ⚠️ Important nuance — not all noise is common-mode

Not every noise source hits both arms equally. There are also:

| Noise type | Behaviour |
|------------|-----------|
| Local vibrations | can affect one arm more than the other |
| Thermal noise | independent fluctuations in each arm |
| Quantum noise | inherent shot noise in the laser |

These create arm differences too — but they're **small and random**, so they still look like noise clustered around zero rather than a structured signal.

---

### Final intuition

```
Noise  =  small, imperfect differences between arms  →  small ± values around 0
Signal =  structured, large differences              →  stands out from noise
```

> **One-line answer:** noise is the small leftover difference when both arms move almost — but not perfectly — the same way, which is why the signal fluctuates around zero.