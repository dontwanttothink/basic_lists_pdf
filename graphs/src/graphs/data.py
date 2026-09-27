"""Parse App.java benchmark logs and aggregate runs with the median.

Output format produced by ``App.java``::

    @Enlazada simplemente sin cola
    :1
    15125,1542,2834,1667,1416,958,1625,917,0125
    :2
    541,459,625,291,292,417,291,208,042

* ``@...``     structure banner (one per file)
* ``:N``       powers of two; the next CSV row has one nanosecond
  measurement per method, in the same order the calls appear in
  ``App.java``.
* ``:NqTIME``  "quick" samples (only for DynamicStack / DynamicQueue):
  a single extra measurement of ``push`` / ``enqueue`` at intermediate
  sizes (the ``QUICK_FACTOR`` growth loop).

The quick samples give us 7 extra measurements per octave, which show us
the best case behaviour, rather than only the worst case behaviour :))
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

LIST_METHODS = (
    "isEmpty",
    "pushBack",
    "popBack",
    "pushFront",
    "popFront",
    "find",
    "addBefore",
    "addAfter",
    "erase",
)
STACK_METHODS = ("isEmpty", "push", "pop", "peek", "size", "delete")
QUEUE_METHODS = ("isEmpty", "enqueue", "dequeue", "front", "size", "delete")

# file stem -> (methods, quick method or None, display title)
STRUCTURES: dict[str, tuple[tuple[str, ...], str | None, str]] = {
    "sll": (LIST_METHODS, None, "Enlazada simplemente sin cola"),
    "sllt": (LIST_METHODS, None, "Enlazada simplemente con cola"),
    "dll": (LIST_METHODS, None, "Enlazada doblemente sin cola"),
    "dllt": (LIST_METHODS, None, "Enlazada doblemente con cola"),
    "s": (STACK_METHODS, "push", "Pila dinámica"),
    "q": (QUEUE_METHODS, "enqueue", "Cola dinámica"),
}

_ROW_RE = re.compile(r"^:(\d+)(?:q(\d+))?\s*$")


@dataclass
class Series:
    """Median nanosecond cost of one method, keyed by n."""

    name: str
    points: dict[int, float] = field(default_factory=dict)

    def sorted(self) -> tuple[list[int], list[float]]:
        ns = sorted(self.points)
        return ns, [self.points[n] for n in ns]


@dataclass
class QuickSeries:
    """Median of the ``:NqTIME`` amortized-resize samples."""

    name: str
    points: dict[int, float] = field(default_factory=dict)

    def sorted(self) -> tuple[list[int], list[float]]:
        ns = sorted(self.points)
        return ns, [self.points[n] for n in ns]


@dataclass
class StructureData:
    """Everything aggregated from one family of run files (``sll``, ``q``...)."""

    key: str
    title: str
    methods: dict[str, Series]
    quick: QuickSeries | None
    n_runs: int


def _load_run(path: Path, n_methods: int) -> tuple[dict[int, list[int]], dict[int, int]]:
    """Read one run file.

    Returns ``rows`` — ``{n: [ns per method]}`` — and ``quick`` — ``{n: ns}``.
    """
    rows: dict[int, list[int]] = {}
    quick: dict[int, int] = {}
    pending_n: int | None = None

    with path.open() as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("@"):
                pending_n = None
                continue

            m = _ROW_RE.match(line)
            if m:
                n = int(m.group(1))
                if m.group(2) is not None:
                    quick[n] = int(m.group(2))
                    pending_n = None
                else:
                    pending_n = n
                continue

            values = [int(tok) for tok in line.split(",") if tok != ""]
            if pending_n is None:
                continue

            if len(values) != n_methods:
                raise ValueError(
                    f"{path.name}:{lineno}: expected {n_methods} fields, got {len(values)}"
                )
            rows[pending_n] = values
            pending_n = None

    return rows, quick


def _median_per_n(runs: list[dict[int, list[int]]], method_index: int) -> dict[int, float]:
    by_n: dict[int, list[int]] = {}
    for run in runs:
        for n, values in run.items():
            by_n.setdefault(n, []).append(values[method_index])
    return {n: float(statistics.median(samples)) for n, samples in by_n.items()}


def _median_sum_per_n(runs: list[dict[int, list[int]]], i: int, j: int) -> dict[int, float]:
    """Median across runs of ``(col_i + col_j)`` — for delete = find + erase."""
    by_n: dict[int, list[int]] = {}
    for run in runs:
        for n, values in run.items():
            by_n.setdefault(n, []).append(values[i] + values[j])
    return {n: float(statistics.median(s)) for n, s in by_n.items()}


def _median_quick(runs: list[dict[int, int]]) -> dict[int, float]:
    by_n: dict[int, list[int]] = {}
    for run in runs:
        for n, v in run.items():
            by_n.setdefault(n, []).append(v)
    return {n: float(statistics.median(s)) for n, s in by_n.items()}


def load_benchmarks(bench_dir: Path) -> dict[str, StructureData]:
    """Aggregate every ``benchmarks/*.txt`` family into median series (20 runs)."""
    run_paths: dict[str, list[Path]] = {}
    for path in sorted(bench_dir.glob("*.txt")):
        stem = path.name.split(".", 1)[0]  # sll.1.txt -> sll
        if stem not in STRUCTURES:
            continue
        run_paths.setdefault(stem, []).append(path)

    raw_runs: dict[str, list[tuple[dict[int, list[int]], dict[int, int]]]] = {}
    for key, (methods, _, _) in STRUCTURES.items():
        if key not in run_paths:
            continue
        paths = sorted(run_paths[key], key=lambda p: int(p.stem.split(".")[1]))
        raw_runs[key] = [_load_run(p, len(methods)) for p in paths]

    out: dict[str, StructureData] = {}
    for key, (methods, quick_name, title) in STRUCTURES.items():
        if key not in raw_runs:
            continue
        rows_list = [r for r, _q in raw_runs[key]]
        series = {
            name: Series(name, _median_per_n(rows_list, idx))
            for idx, name in enumerate(methods)
        }
        quick = (
            QuickSeries(quick_name, _median_quick([q for _r, q in raw_runs[key]]))
            if quick_name
            else None
        )
        out[key] = StructureData(key, title, series, quick, len(rows_list))

    return out


# sintetizamos la combinación de find + erase para hacer comparaciones luego :(((

def derive_delete(row_runs: list[dict[int, list[int]]]) -> Series:
    """delete ≡ find + erase, median across runs of the per-run sum."""
    return Series(
        "delete",
        _median_sum_per_n(row_runs, LIST_METHODS.index("find"), LIST_METHODS.index("erase")),
    )


def delete_series(bench_dir: Path, list_key: str) -> Series:
    """Median of ``(find + erase)`` for one list implementation, for comparisons."""
    paths = sorted(
        bench_dir.glob(f"{list_key}.*.txt"),
        key=lambda p: int(p.stem.split(".")[1]),  # sll.1.txt -> 1
    )
    runs = [_load_run(p, len(LIST_METHODS))[0] for p in paths]
    return derive_delete(runs)
