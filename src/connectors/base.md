# `base.py` — explained (zero-knowledge decorators primer)

This file defines a **contract** — a promise about shape. It says: "Every data
source in this pipeline (LIGO gravitational wave data, IoT sensors, whatever
else) must hand back data in the same standard format, and every connector
class must have a `fetch` method." It doesn't do any actual work itself.

## Part 1: `RawSignal` (lines 6-16) — a data container

```python
@dataclass
class RawSignal:
```

`@dataclass` is a **decorator** — think of it as a stamp you put above a class
that says "auto-generate the boring stuff for me." Without it, if you wanted
a simple class that just holds some values, you'd have to hand-write an
`__init__` method like:

```python
class RawSignal:
    def __init__(self, data, domain, source_id, ...):
        self.data = data
        self.domain = domain
        self.source_id = source_id
        # ...and so on for every field
```

`@dataclass` reads the field list below the class and writes that constructor
for you automatically. So this:

```python
data: np.ndarray
domain: str
source_id: str
start_time_utc: float
sample_rate_hz: float
duration_sec: float
num_samples: int
extra: dict = field(default_factory=dict)
```

is just a list of "fields this object has, and their expected types." (The
types like `str`, `float` are hints for humans/tools — Python doesn't
actually enforce them at runtime.)

You'd use it like this:

```python
signal = RawSignal(
    data=np.array([1, 2, 3]),
    domain="ligo",
    source_id="H1",
    start_time_utc=1234567890.0,
    sample_rate_hz=4096.0,
    duration_sec=1.0,
    num_samples=4096,
)
```

The odd one out is `extra: dict = field(default_factory=dict)`. You'd think
you could just write `extra: dict = {}`, but Python has a famous gotcha: if
you use a mutable default like `{}` directly, **every instance would share
the same dictionary** (a classic bug). `field(default_factory=dict)` tells
the dataclass "call `dict()` fresh for every new object" so each `RawSignal`
gets its own empty dict. `extra` is a grab-bag for domain-specific extras
that don't fit the standard fields (comment on line 16 gives the example:
LIGO's GPS start time).

## Part 2: `SourceConnector` (lines 19-29) — an enforced blueprint

```python
class SourceConnector(ABC):
```

`ABC` stands for **Abstract Base Class**. This is a class that can never be
used directly — it exists only to be *subclassed*. Think of it as a job
description rather than an employee.

```python
@abstractmethod
def fetch(self, config: dict) -> RawSignal:
```

`@abstractmethod` is another decorator. It marks `fetch` as a method that
**must** be implemented by any subclass. If you try to create a subclass
without writing your own `fetch`, Python will refuse at runtime with an
error — it's not just a style suggestion, it's enforced.

So in practice, elsewhere in the codebase you'd have something like:

```python
class LigoConnector(SourceConnector):
    def fetch(self, config: dict) -> RawSignal:
        # actually go get LIGO data, convert GPS time to UTC, etc.
        return RawSignal(...)

class IotConnector(SourceConnector):
    def fetch(self, config: dict) -> RawSignal:
        # go get IoT sensor data instead
        return RawSignal(...)
```

Both classes are forced to provide a `fetch(config) -> RawSignal` method with
that exact shape. This lets the rest of the pipeline call
`connector.fetch(config)` on *any* connector without caring whether it's
LIGO or IoT underneath — it always gets back a `RawSignal`.

## In one sentence

`RawSignal` is a labeled box with a fixed set of compartments (decorator
auto-builds the box constructor); `SourceConnector` is a rule that says
"anyone who wants to be a connector must implement a `fetch` method that
fills one of these boxes" (decorator enforces that rule).
