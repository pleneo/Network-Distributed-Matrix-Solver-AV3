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
    """Retorna um rotulo descritivo para a legenda dos graficos, incluindo o numero
    de workers e servidores quando relevante."""
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
    """Retorna um rotulo curto e fixo para cada modo (ex.: 'Paralelo local')."""
    if mode == "serial":
        return "Serial"
    if mode == "parallel":
        return "Paralelo local"
    if mode == "distributed":
        return "Distribuido serial"
    if mode == "hybrid":
        return "Distribuido hibrido"
    return mode


def _metric_title(metric: str) -> str:
    """Converte o nome interno da metrica (time, speedup, efficiency) em titulo
    legivel para o eixo y do grafico."""
    if metric == "time":
        return "Tempo Medio"
    if metric == "speedup":
        return "Speedup"
    if metric == "efficiency":
        return "Eficiencia"
    return metric


def _parameter_label(parameter: str) -> str:
    """Converte o nome do parametro variado em rotulo para o eixo x."""
    labels = {
        "size": "Tamanho da Matriz",
        "server_count": "Quantidade de Servidores",
        "local_workers": "Workers Locais",
        "workers_per_server": "Workers por Servidor",
    }
    return labels.get(parameter, parameter)


def _scenario_context(results: list[dict], scenario: str) -> str:
    """Gera uma linha de contexto exibida no subtitulo do grafico
    (ex.: '2 servidores · seed 42')."""
    if scenario == "quantidade_servidores":
        hybrid_rows = [row for row in results if row["mode"] == "hybrid"]
        total_workers = sorted(
            {row["servers"] * row["workers_per_server"] for row in hybrid_rows}
        )
        if len(total_workers) == 1:
            return f" ({total_workers[0]} Workers Totais no Hibrido)"
    if scenario == "workers_por_servidor":
        servers = sorted(
            {row["servers"] for row in results if row["mode"] == "hybrid"}
        )
        if len(servers) == 1:
            return f" ({servers[0]} Servidores)"
    return ""


def _variation_modes(scenario: str) -> set[str]:
    """Retorna o conjunto de modos a plotar para um dado cenario
    (ex.: cenario de workers locais omite modos distribuidos)."""
    if scenario == "quantidade_servidores":
        return {"distributed", "hybrid"}
    if scenario == "workers_locais":
        return {"parallel"}
    if scenario == "workers_por_servidor":
        return {"hybrid"}
    return {"serial", "parallel", "distributed", "hybrid"}


def _average_by_keys(results: list[dict], keys: tuple[str, ...]) -> list[dict]:
    """Agrupa os resultados pelas chaves especificadas e calcula a media da metrica
    em cada grupo, retornando um dicionario indexado pelos valores das chaves."""
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


def _plot_server_count_references(
    ax,
    results: list[dict],
    metric: str,
    x_values: list[int],
) -> None:
    """Adiciona linhas horizontais de referencia (serial e paralelo local) aos graficos
    do cenario de quantidade de servidores, para facilitar a comparacao visual."""
    reference_rows = [
        row for row in results if row["mode"] in {"serial", "parallel"}
    ]
    averaged = _average_by_keys(reference_rows, ("size", "mode"))

    for mode in ("serial", "parallel"):
        for size in sorted({row["size"] for row in averaged if row["mode"] == mode}):
            points = [
                row
                for row in averaged
                if row["mode"] == mode and row["size"] == size
            ]
            if not points:
                continue

            value = mean(row[metric] for row in points)
            label = f"{_base_mode_label(mode)} (referencia) | N={size}"
            linestyle = "--" if mode == "serial" else ":"
            ax.plot(
                x_values,
                [value for _ in x_values],
                linestyle=linestyle,
                linewidth=2.0,
                label=label,
            )


def _plot_metric_by_size(
    results: list[dict],
    output_dir: Path,
    scenario: str,
    metric: str,
    ylabel: str,
) -> None:
    """Plota a metrica em funcao do tamanho da matriz N (eixo x);
    usado apenas para o cenario tamanho_matriz."""
    averaged = _average_by_keys(results, ("size",))
    fig, ax = plt.subplots(figsize=(11, 6))
    labels = sorted({row["label"] for row in averaged})

    for label in labels:
        points = [row for row in averaged if row["label"] == label]
        x = [row["size"] for row in points]
        y = [row[metric] for row in points]
        ax.plot(x, y, marker="o", linewidth=2, markersize=5, label=label)

    ax.set_title(f"{_metric_title(metric)} por Tamanho da Matriz")
    ax.set_xlabel("Tamanho da Matriz (N)")
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
    y_limit: tuple[float, float] | None = None,
) -> None:
    """Plota a metrica em funcao do parametro variado do cenario (eixo x);
    usado para os tres cenarios alem do tamanho_matriz."""
    varied_parameter = results[0]["varied_parameter"]
    if varied_parameter == "size":
        return

    selected_modes = _variation_modes(scenario)
    selected_results = [row for row in results if row["mode"] in selected_modes]
    averaged = _average_by_keys(selected_results, ("varied_value", "size", "mode"))
    fig, ax = plt.subplots(figsize=(11, 6))
    x_values = sorted({row["varied_value"] for row in averaged})

    for mode in sorted({row["mode"] for row in averaged}):
        for size in sorted({row["size"] for row in averaged if row["mode"] == mode}):
            points = [
                row
                for row in averaged
                if row["mode"] == mode and row["size"] == size
            ]
            label = f"{_base_mode_label(mode)} | N={size}"
            if scenario == "quantidade_servidores" and mode == "distributed":
                label = f"{label} (1 worker por servidor)"
            elif scenario == "quantidade_servidores" and mode == "hybrid":
                label = f"{label} (workers totais fixos)"
            x = [row["varied_value"] for row in points]
            y = [row[metric] for row in points]
            ax.plot(x, y, marker="o", linewidth=2, markersize=5, label=label)

    if scenario == "quantidade_servidores":
        _plot_server_count_references(ax, results, metric, x_values)

    parameter_label = _parameter_label(varied_parameter)
    ax.set_title(
        f"{_metric_title(metric)} por {parameter_label}"
        f"{_scenario_context(results, scenario)}"
    )
    ax.set_xlabel(parameter_label)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x_values)
    if y_limit is not None:
        ax.set_ylim(y_limit)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize="small")
    fig.tight_layout()
    fig.savefig(output_dir / f"{scenario}_{metric}_por_variacao.png", dpi=150)


def _variation_metric_range(results: list[dict], scenarios: set[str], metric: str) -> tuple[float, float] | None:
    """Calcula o intervalo comum do eixo y para dois cenarios, utilizado para alinhar
    a escala dos graficos de workers locais e por servidor."""
    values = []
    for scenario in scenarios:
        scenario_rows = [row for row in results if row["scenario"] == scenario]
        if not scenario_rows:
            continue

        selected_modes = _variation_modes(scenario)
        selected_results = [row for row in scenario_rows if row["mode"] in selected_modes]
        averaged = _average_by_keys(selected_results, ("varied_value", "size", "mode"))
        values.extend(row[metric] for row in averaged)

    if not values:
        return None

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        padding = abs(maximum) * 0.05 or 1.0
    else:
        padding = (maximum - minimum) * 0.08

    return max(0.0, minimum - padding), maximum + padding


def plot_results(results: list[dict], save_dir: str = "results/plots", show: bool = True) -> None:
    """Ponto de entrada: itera sobre os quatro cenarios e tres metricas, chamando a funcao
    de plotagem adequada para cada combinacao e salvando os 12 PNGs em save_dir."""
    if plt is None:
        print(
            "\nmatplotlib nao foi encontrado neste Python; graficos nao foram gerados.\n"
            f"Python em uso: {sys.executable}"
        )
        return

    output_dir = Path(save_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    worker_scenarios = {"workers_locais", "workers_por_servidor"}

    for scenario in sorted({row["scenario"] for row in results}):
        scenario_rows = [row for row in results if row["scenario"] == scenario]
        for metric, ylabel in [
            ("time", "Tempo Medio (s)"),
            ("speedup", "Speedup Medio"),
            ("efficiency", "Eficiencia Media"),
        ]:
            if scenario == "tamanho_matriz":
                _plot_metric_by_size(scenario_rows, output_dir, scenario, metric, ylabel)
            else:
                y_limit = None
                if scenario in worker_scenarios:
                    y_limit = _variation_metric_range(results, worker_scenarios, metric)
                _plot_metric_by_variation(
                    scenario_rows,
                    output_dir,
                    scenario,
                    metric,
                    ylabel,
                    y_limit=y_limit,
                )

    if show and plt.get_backend().lower() != "agg":
        plt.show()
    elif show:
        print(
            "\nGraficos salvos em results/plots/. "
            "A exibicao em janela foi pulada porque o backend grafico e Agg."
        )
    else:
        plt.close("all")
