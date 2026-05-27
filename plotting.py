"""Graficos dos resultados usando pyplot."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean
import os
import sys

try:
    import matplotlib

    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        matplotlib.use("Agg")

    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


def _mode_label(row: dict) -> str:
    mode = row["mode"]
    if mode == "serial":
        return "Serial"
    if mode == "parallel":
        return f"Paralelo local ({row['local_workers']} proc.)"
    if mode == "distributed":
        return f"Distribuido serial ({row['servers']} serv.)"
    if mode == "hybrid":
        return (
            f"Distribuido hibrido "
            f"({row['servers']} serv. x {row['workers_per_server']} proc.)"
        )
    return mode


def _base_mode_label(mode: str) -> str:
    if mode == "serial":
        return "Serial"
    if mode == "parallel":
        return "Paralelo local"
    if mode == "distributed":
        return "Distribuido serial"
    if mode == "hybrid":
        return "Distribuido hibrido"
    return mode


def _variation_modes(scenario: str) -> set[str]:
    if scenario == "quantidade_servidores":
        return {"distributed", "hybrid"}
    if scenario == "workers_locais":
        return {"parallel"}
    if scenario == "workers_por_servidor":
        return {"hybrid"}
    return {"serial", "parallel", "distributed", "hybrid"}


def _average_by_keys(results: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups = defaultdict(list)
    for row in results:
        groups[tuple(row[key] for key in keys) + (_mode_label(row),)].append(row)

    averaged = []
    for group, rows in sorted(groups.items()):
        values = dict(zip(keys, group[:-1]))
        values.update(
            {
                "label": group[-1],
                "time": mean(row["time"] for row in rows),
                "speedup": mean(row["speedup"] for row in rows),
                "efficiency": mean(row["efficiency"] for row in rows),
            }
        )
        averaged.append(values)
    return averaged


def _plot_metric_by_size(
    results: list[dict],
    output_dir: Path,
    scenario: str,
    metric: str,
    ylabel: str,
) -> None:
    averaged = _average_by_keys(results, ("size",))
    fig, ax = plt.subplots(figsize=(11, 6))
    labels = sorted({row["label"] for row in averaged})

    for label in labels:
        points = [row for row in averaged if row["label"] == label]
        x = [row["size"] for row in points]
        y = [row[metric] for row in points]
        ax.plot(x, y, marker="o", linewidth=2, markersize=5, label=label)

    ax.set_title(f"{ylabel} por tamanho da matriz - {scenario}")
    ax.set_xlabel("Ordem da matriz (N)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted({row["size"] for row in averaged}))
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / f"{scenario}_{metric}_por_tamanho.png", dpi=150)


def _plot_metric_by_variation(
    results: list[dict],
    output_dir: Path,
    scenario: str,
    metric: str,
    ylabel: str,
) -> None:
    varied_parameter = results[0]["varied_parameter"]
    if varied_parameter == "size":
        return

    selected_modes = _variation_modes(scenario)
    selected_results = [row for row in results if row["mode"] in selected_modes]
    averaged = _average_by_keys(selected_results, ("varied_value", "size", "mode"))
    fig, ax = plt.subplots(figsize=(11, 6))

    for mode in sorted({row["mode"] for row in averaged}):
        for size in sorted({row["size"] for row in averaged if row["mode"] == mode}):
            points = [
                row
                for row in averaged
                if row["mode"] == mode and row["size"] == size
            ]
            label = f"{_base_mode_label(mode)} | N={size}"
            x = [row["varied_value"] for row in points]
            y = [row[metric] for row in points]
            ax.plot(x, y, marker="o", linewidth=2, markersize=5, label=label)

    ax.set_title(f"{ylabel} por {varied_parameter} - {scenario}")
    ax.set_xlabel(varied_parameter)
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted({row["varied_value"] for row in averaged}))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize="small")
    fig.tight_layout()
    fig.savefig(output_dir / f"{scenario}_{metric}_por_variacao.png", dpi=150)


def plot_results(results: list[dict], save_dir: str = "results/plots", show: bool = True) -> None:
    if plt is None:
        print(
            "\nmatplotlib nao foi encontrado neste Python; graficos nao foram gerados.\n"
            f"Python em uso: {sys.executable}"
        )
        return

    output_dir = Path(save_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for scenario in sorted({row["scenario"] for row in results}):
        scenario_rows = [row for row in results if row["scenario"] == scenario]
        for metric, ylabel in [
            ("time", "Tempo medio (s)"),
            ("speedup", "Speedup medio"),
            ("efficiency", "Eficiencia media"),
        ]:
            _plot_metric_by_size(scenario_rows, output_dir, scenario, metric, ylabel)
            _plot_metric_by_variation(scenario_rows, output_dir, scenario, metric, ylabel)

    if show and plt.get_backend().lower() != "agg":
        plt.show()
    elif show:
        print(
            "\nGraficos salvos em results/plots/. "
            "A exibicao em janela foi pulada porque o backend grafico e Agg."
        )
    else:
        plt.close("all")
