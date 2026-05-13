"""Graficos dos resultados usando pyplot."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt


def _mode_label(row: dict) -> str:
    mode = row["mode"]
    if mode == "serial":
        return "Serial"
    if mode == "parallel":
        return f"Paralelo local ({row['workers']} proc.)"
    if mode == "distributed":
        return f"Distribuido serial ({row['servers']} serv.)"
    if mode == "hybrid":
        return f"Distribuido hibrido ({row['servers']} serv. x {row['workers']} proc.)"
    return mode


def _average_by_size_and_mode(results: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in results:
        groups[(row["size"], _mode_label(row))].append(row)

    averaged = []
    for (size, label), rows in sorted(groups.items()):
        averaged.append(
            {
                "size": size,
                "label": label,
                "time": mean(row["time"] for row in rows),
                "speedup": mean(row["speedup"] for row in rows),
                "efficiency": mean(row["efficiency"] for row in rows),
            }
        )
    return averaged


def plot_results(results: list[dict], save_dir: str = "results/plots", show: bool = True) -> None:
    averaged = _average_by_size_and_mode(results)
    output_dir = Path(save_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for metric, ylabel, title, filename in [
        ("time", "Tempo medio (s)", "Tempo medio por tamanho da matriz", "execution_time.png"),
        ("speedup", "Speedup medio", "Speedup medio por tamanho da matriz", "speedup.png"),
        ("efficiency", "Eficiencia media", "Eficiencia media por tamanho da matriz", "efficiency.png"),
    ]:
        fig, ax = plt.subplots(figsize=(11, 6))
        labels = sorted({row["label"] for row in averaged})

        for label in labels:
            points = [row for row in averaged if row["label"] == label]
            x = [row["size"] for row in points]
            y = [row[metric] for row in points]
            ax.plot(x, y, marker="o", linewidth=2, markersize=5, label=label)

        ax.set_title(title)
        ax.set_xlabel("Ordem da matriz (N)")
        ax.set_ylabel(ylabel)
        ax.set_xticks(sorted({row["size"] for row in averaged}))
        ax.tick_params(axis="x", rotation=25)
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)

    if show:
        plt.show()
    else:
        plt.close("all")
