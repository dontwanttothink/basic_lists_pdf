"""Chart generation for the data-structures benchmarks.

Every figure is written as PDF (vector, embeds the typeface) to the output
directory
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display needed
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from .data import (
    LIST_METHODS,
    QUEUE_METHODS,
    STACK_METHODS,
    STRUCTURES,
    Series,
    StructureData,
)

# --- typeface ---------------------------------------------------------------

_FIRA_CANDIDATES = ("Fira Sans", "Fira Sans OT", "Fira Sans Book", "FiraSans")


def _set_up_font() -> None:
    """Register bundled Fira Sans, then prefer it; measured fallback keeps any figure usable."""
    fonts_dir = Path(__file__).resolve().parent / "fonts"
    if fonts_dir.is_dir():
        for ttf in sorted(fonts_dir.glob("*.ttf")):
            font_manager.fontManager.addfont(str(ttf))

    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = [
        *_FIRA_CANDIDATES,
        "DejaVu Sans",
        "Helvetica",
        "Arial",
    ]
    matplotlib.rcParams["mathtext.fontset"] = "dejavusans"
    known = {f.name for f in font_manager.fontManager.ttflist}
    if not any(name in known for name in _FIRA_CANDIDATES):
        print(
            "warning: Fira Sans is not available; falling back to DejaVu Sans",
            file=sys.stderr,
        )


_set_up_font()

# ---------------------------------------------------------------------------
# Comparaciones entre MyStack, MyQueue y listas enlazadas
# ---------------------------------------------------------------------------

MYSTACK_PAIRS: list[tuple[str, str, str]] = [
    # (array method, list key, list method, why this List impl)
    ("push", "sllt", "pushBack"),
    ("pop", "dllt", "popBack"),
    ("delete", "sll", "find + erase"),
]
MYSTACK_NON_COMPARED = ("peek", "isEmpty", "size")

MYQUEUE_PAIRS: list[tuple[str, str, str]] = [
    ("enqueue", "sllt", "pushBack"),
    ("dequeue", "sll", "popFront"),
    ("delete", "sll", "find + erase"),
]

_Y_FLOOR = 1.0  # ns, floor for the log scale
_METHOD_CYCLE = plt.get_cmap("tab20")  # up to 20 distinguishable series


def _prep_axes(ax, y_label: str) -> None:
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, which="both", linestyle=":")
    ax.set_xlabel("n (elementos)")
    ax.set_ylabel(y_label)


def _prep_points(points: dict[int, float]) -> tuple[list[int], list[float]]:
    """Sorted xs and ys floored at ``_Y_FLOOR`` (log scale rejects zeros)."""
    xs = sorted(points)
    ys = [max(points[n], _Y_FLOOR) for n in xs]
    return xs, ys


def _points(series_or_points: Series | dict[int, float]) -> dict[int, float]:
    return series_or_points if isinstance(series_or_points, dict) else series_or_points.points


# --- running average of past push/enqueue (amortized view) ---
# Comentado: las muestras del harness no cronometran cada operación del llenado,
# así que la media de las mediciones no representa bien el amortizado.
#
# def _running_mean(points: dict[int, float]) -> tuple[list[int], list[float]]:
#     """Cumulative mean of the measurements up to each size (amortized view).
#
#     The series walk the fill loop in order, so at every sampled ``n`` the value is
#     the average of all measured ``push`` / ``enqueue`` costs so far — resize
#     outliers pull it up briefly, then it settles again (amortized O(1)).
#     """
#     xs = sorted(points)
#     acc = 0.0
#     ys: list[float] = []
#     for i, n in enumerate(xs, 1):
#         acc += points[n]
#         ys.append(max(acc / i, _Y_FLOOR))
#     return xs, ys
#
#
# def _merged_push_samples(spec: StructureData, method_name: str) -> dict[int, float]:
#     """Both measurement series of push/enqueue: :Nq and powers of two."""
#     samples = dict(spec.methods[method_name].points)
#     if spec.quick:
#         samples.update(spec.quick.points)
#     return samples


def _save(fig, path: Path) -> Path:
    """Write a PDF (typeface is embedded automatically by matplotlib)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf")
    plt.close(fig)
    return path


def _method_names(spec: StructureData) -> tuple[str, ...]:
    return STACK_METHODS if spec.key == "s" else QUEUE_METHODS if spec.key == "q" else LIST_METHODS


# ---------------------------------------------------------------------------
# Figures 1–4: every method of each linked-list implementation (3x3)
# ---------------------------------------------------------------------------


def plot_list_methods(spec: StructureData, out_dir: Path) -> Path:
    """Every method of one linked-list implementation, one subplot per method."""
    fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(12, 9))
    fig.suptitle(f"Cada método de la estructura List — {spec.title}", fontsize=13)

    for ax, method_name in zip(axes.flat, LIST_METHODS):
        xs, ys = _prep_points(spec.methods[method_name].points)
        ax.plot(xs, ys, marker="o", linewidth=1.5, markersize=3, color="C0")
        ax.set_title(method_name)
        _prep_axes(ax, "ns")

    for ax in axes.flat[len(LIST_METHODS) :]:
        ax.axis("off")

    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    return _save(fig, out_dir / f"list_{spec.key}_methods.pdf")


# ---------------------------------------------------------------------------
# Figures 5–6: every method of MyStack / MyQueue (2x3)
# ---------------------------------------------------------------------------


def plot_array_methods(spec: StructureData, out_dir: Path, accent: str = "C0") -> Path:
    """Every method of MyStack / MyQueue, one subplot per method."""
    fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(12, 7))
    fig.suptitle(f"Métodos de la estructura — {spec.title}", fontsize=13)

    for ax, method_name in zip(axes.flat, _method_names(spec)):
        xs, ys = _prep_points(spec.methods[method_name].points)

        if spec.quick and method_name == spec.quick.name:
            # :Nq — el n crece en el bucle principal; sin redimensionamiento
            qx, qy = _prep_points(spec.quick.points)
            ax.plot(
                qx,
                qy,
                linewidth=1.5,
                markersize=2,
                color=accent,
                label="sin redimensionamiento",
            )
            # potencias de dos — peor caso: pueden tocar crecer
            ax.plot(
                xs,
                ys,
                linestyle="none",
                marker="x",
                markersize=6,
                color=accent,
                label="potencias de dos (peor caso)",
            )
            # promedio de las operaciones previas — amortizado
            # (comentado: las muestras no representan cada push del llenado)
            # rx, ry = _running_mean(_merged_push_samples(spec, method_name))
            # ax.plot(
            #     rx,
            #     ry,
            #     linestyle="--",
            #     linewidth=1.4,
            #     color=accent,
            #     label="promedio acumulado (amortizado)",
            # )
        else:
            ax.plot(
                xs,
                ys,
                marker="o",
                linewidth=1.5,
                markersize=3,
                color=accent,
                label=method_name,
            )

        ax.set_title(method_name)
        _prep_axes(ax, "ns")
        ax.legend(loc="upper left", fontsize=7, frameon=False)

    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    return _save(fig, out_dir / f"array_{'stack' if spec.key == 's' else 'queue'}_methods.pdf")


# ---------------------------------------------------------------------------
# Overlay figures: all methods of one implementation on the same grid
# ---------------------------------------------------------------------------


def plot_overlay_methods(spec: StructureData, out_dir: Path) -> Path:
    """All methods of one implementation, superimposed on a single grid."""
    names = _method_names(spec)
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle(
        spec.title,
        fontsize=12,
    )

    for idx, method_name in enumerate(names):
        color = _METHOD_CYCLE(idx % _METHOD_CYCLE.N)
        xs, ys = _prep_points(spec.methods[method_name].points)

        if spec.quick and method_name == spec.quick.name:
            # :Nq — método sin redimensionamiento (línea continua)
            qx, qy = _prep_points(spec.quick.points)
            ax.plot(
                qx,
                qy,
                linewidth=1.4,
                markersize=2,
                color=color,
                label=f"{method_name}: sin redimensionamiento",
            )
            # potencias de dos — peor caso (pueden tocar crecer)
            ax.plot(
                xs,
                ys,
                linestyle="none",
                marker="x",
                markersize=6,
                color=color,
                label=f"{method_name}: potencias de dos (peor caso)",
            )
            # promedio acumulado — comportamiento amortizado
            # (comentado: las muestras no representan cada push del llenado)
            # rx, ry = _running_mean(_merged_push_samples(spec, method_name))
            # ax.plot(
            #     rx,
            #     ry,
            #     linestyle="--",
            #     linewidth=1.4,
            #     color=color,
            #     label=f"{method_name}: promedio acumulado (amortizado)",
            # )
        else:
            ax.plot(
                xs,
                ys,
                marker="o",
                linewidth=1.4,
                markersize=3,
                color=color,
                label=method_name,
            )

    _prep_axes(ax, "ns")
    ax.legend(loc="best", fontsize=8, frameon=False, ncol=2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))

    if spec.key in ("s", "q"):
        stem = f"array_{'stack' if spec.key == 's' else 'queue'}_overlay"
    else:
        stem = f"list_{spec.key}_overlay"
    return _save(fig, out_dir / f"{stem}.pdf")


# ---------------------------------------------------------------------------
# Comparison figures: List / (Stack, Queue) — one optimal List impl per method
# ---------------------------------------------------------------------------


def render_comparisons(
    all_data: dict[str, StructureData],
    delete_series_map: dict[str, Series],
    out_dir: Path,
) -> list[Path]:
    """List / (Stack, Queue): one optimal List impl per equivalent method."""
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    specs = (
        ("mystack_comparativa.pdf", "Pila dinámica", "s", MYSTACK_PAIRS),
        ("myqueue_comparativa.pdf", "Cola dinámica", "q", MYQUEUE_PAIRS),
    )

    for fname, array_title, key, pairs in specs:
        nrows, ncols = 3, 1
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(6, 10))
        axes = axes.flat

        spec = all_data[key]
        for ax, (arr_meth, lkey, lmeth) in zip(axes, pairs):
            if spec.quick and arr_meth == spec.quick.name:
                qx, qy = _prep_points(spec.quick.points)
                ax.plot(
                    qx,
                    qy,
                    linewidth=1.5,
                    markersize=2,
                    color="C0",
                    label=f"{array_title} · {arr_meth}: sin redimensionamiento",
                )
                xs, ys = _prep_points(spec.methods[arr_meth].points)
                ax.plot(
                    xs,
                    ys,
                    linestyle="none",
                    marker="x",
                    markersize=6,
                    color="C0",
                    label=f"{array_title} · {arr_meth}: potencias de dos (peor caso)",
                )
            else:
                xs, ys = _prep_points(spec.methods[arr_meth].points)
                ax.plot(
                    xs,
                    ys,
                    marker="o",
                    linewidth=1.5,
                    color="C0",
                    label=f"{array_title} · {arr_meth}",
                )

            if lmeth == "find + erase":
                lseries = delete_series_map.get(lkey)
                lpts = _points(lseries) if lseries is not None else {}
            else:
                lpts = all_data[lkey].methods[lmeth].points
            lxs, lys = _prep_points(lpts)
            list_label = f"{STRUCTURES[lkey][2]} · {lmeth}"
            ax.plot(lxs, lys, marker="s", linewidth=1.5, color="C3", label=list_label)

            _prep_axes(ax, "ns")
            ax.legend(loc="upper left", fontsize=7, frameon=False)
            ax.set_title(f"{arr_meth} y {lmeth}", fontsize=9)

        fig.tight_layout(rect=(0, 0.02, 1, 0.96))
        outputs.append(_save(fig, out_dir / fname))

    return outputs
