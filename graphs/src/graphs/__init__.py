"""Generate benchmark comparison charts for the data-structures lab.
Figures are written as PDFs to `output/` (para incluirlos con LaTeX)"""

from __future__ import annotations

import sys
from pathlib import Path

from .data import (
    LIST_METHODS,
    QUEUE_METHODS,
    STACK_METHODS,
    STRUCTURES,
    QuickSeries,
    Series,
    StructureData,
    delete_series,
    derive_delete,
    load_benchmarks,
)
from .plotting import (
    MYQUEUE_PAIRS,
    MYSTACK_NON_COMPARED,
    MYSTACK_PAIRS,
    plot_array_methods,
    plot_list_methods,
    plot_overlay_methods,
    render_comparisons,
)

__all__ = [
    "LIST_METHODS",
    "MYQUEUE_PAIRS",
    "MYSTACK_NON_COMPARED",
    "MYSTACK_PAIRS",
    "QUEUE_METHODS",
    "QuickSeries",
    "STACK_METHODS",
    "STRUCTURES",
    "Series",
    "StructureData",
    "delete_series",
    "derive_delete",
    "load_benchmarks",
    "main",
    "plot_array_methods",
    "plot_list_methods",
    "plot_overlay_methods",
    "render_comparisons",
]

USAGE = "usage: graphs [--benchmarks DIR] [--out DIR]"


def main(argv: list[str] | None = None) -> int:
    """Read ``benchmarks/`` and write every figure to ``output/``."""
    argv = list(sys.argv[1:] if argv is None else argv)

    # src/graphs/__init__.py -> project root (benchmarks/, output/)
    root = Path(__file__).resolve().parents[2]
    bench_dir = root / "benchmarks"
    out_dir = root / "output"

    args = iter(argv)
    for opt in args:
        if opt == "--benchmarks":
            bench_dir = Path(next(args))
        elif opt == "--out":
            out_dir = Path(next(args))
        elif opt in ("-h", "--help"):
            print(USAGE)
            return 0
        else:
            print(f"unknown option: {opt}", file=sys.stderr)
            print(USAGE, file=sys.stderr)
            return 2

    if not bench_dir.is_dir():
        print(f"benchmark directory not found: {bench_dir}", file=sys.stderr)
        return 1

    print(f"reading {bench_dir} ...")
    data: dict[str, StructureData] = load_benchmarks(bench_dir)

    expected = ("sll", "sllt", "dll", "dllt", "s", "q")
    missing = [k for k in expected if k not in data]
    if missing:
        print(f"warning: no data for {', '.join(missing)}", file=sys.stderr)

    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) four linked-list figures (all 9 methods each) + overlays (same grid)
    for key in ("sll", "sllt", "dll", "dllt"):
        if key in data:
            for path in (
                plot_list_methods(data[key], out_dir),
                plot_overlay_methods(data[key], out_dir),
            ):
                print(f"  wrote {path.name}")

    # 2) two dynamic-array figures (all 6 methods each) + overlays
    for key, accent in (("s", "C1"), ("q", "C2")):
        if key in data:
            for path in (
                plot_array_methods(data[key], out_dir, accent=accent),
                plot_overlay_methods(data[key], out_dir),
            ):
                print(f"  wrote {path.name}")

    # 3) comparison figures (MyStack / MyQueue vs best List per method)
    delete_map = {
        lk: delete_series(bench_dir, lk)
        for lk in ("sll", "sllt", "dll", "dllt")
        if lk in data
    }
    for path in render_comparisons(data, delete_map, out_dir):
        print(f"  wrote {path.name}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
