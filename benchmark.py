"""Experimentos e comparacoes de desempenho."""

from __future__ import annotations

import csv
from pathlib import Path
import subprocess
import sys
import time

from distributed import PROCESS_POOL, SERIAL, distributed_multiply, start_servers, stop_servers
from matrix_ops import generate_matrix, matrices_equal, multiply_parallel, multiply_serial
from plotting import plot_results


def measure(fn) -> tuple[object, float]:
    """Executa fn() medindo o tempo com time.perf_counter; retorna (resultado, tempo)."""
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


def print_result(row: dict) -> None:
    """Imprime uma linha formatada de resultado no terminal durante a execucao."""
    print(
        f"{row['scenario']:<28} "
        f"{row['label']:<28} "
        f"N={row['size']:<5} "
        f"serv={row['servers']:<2} "
        f"local={row['local_workers']:<2} "
        f"w/serv={row['workers_per_server']:<2} "
        f"tempo={row['time']:.6f}s  "
        f"speedup={row['speedup']:.3f}  "
        f"eficiencia={row['efficiency']:.3f}  "
        f"valido={row['valid']}"
    )


def print_matrix(name: str, matrix: list[list[int | float]]) -> None:
    """Imprime uma matriz no terminal com nome, dimensoes e valores alinhados em colunas."""
    print(f"{name} =")
    for row in matrix:
        print("  " + " ".join(f"{value:>5}" for value in row))


def print_demo_matrix_result(
    server_count: int,
    workers_per_server: int,
    distributed_timeout: float,
) -> None:
    """Executa a demonstracao com as matrizes 3x3 do enunciado do trabalho, imprimindo
    A, B e o resultado C no terminal antes de iniciar o benchmark."""
    a = [[1, 0, -1], [4, -1, 2], [-1, 2, 4]]
    b = [[-1, 2, -3], [5, -4, 2], [4, 1, 0]]

    servers, processes = start_servers(server_count, workers_per_server)
    try:
        result = distributed_multiply(
            a,
            b,
            servers,
            mode=PROCESS_POOL,
            workers_per_server=workers_per_server,
            timeout=distributed_timeout,
        )
    finally:
        stop_servers(processes)

    serial_result = multiply_serial(a, b)
    print("\nDemonstracao da multiplicacao distribuida")
    print_matrix("A", a)
    print_matrix("B", b)
    print_matrix("C = A x B", result["matrix"])
    print(f"Resultado valido: {matrices_equal(serial_result, result['matrix'])}")


def make_row(
    label: str,
    mode: str,
    size: int,
    elapsed: float,
    serial_time: float,
    valid: bool,
    scenario: str,
    repeat: int,
    varied_parameter: str,
    varied_value: int,
    servers: int = 1,
    workers: int = 1,
    local_workers: int = 1,
    workers_per_server: int = 1,
) -> dict:
    """Constroi um dicionario com todas as colunas do CSV, calculando speedup e
    eficiencia a partir do tempo serial de referencia."""
    speedup = serial_time / elapsed if elapsed > 0 else 0.0
    parallel_units = max(1, workers)
    efficiency = speedup / parallel_units
    return {
        "scenario": scenario,
        "repeat": repeat,
        "varied_parameter": varied_parameter,
        "varied_value": varied_value,
        "label": label,
        "mode": mode,
        "size": size,
        "time": elapsed,
        "serial_time": serial_time,
        "speedup": speedup,
        "efficiency": efficiency,
        "servers": servers,
        "workers": workers,
        "local_workers": local_workers,
        "workers_per_server": workers_per_server,
        "parallel_units": parallel_units,
        "valid": valid,
    }


def compare_all_modes(
    size: int,
    seed: int,
    servers: list[tuple[str, int]],
    local_workers: int,
    workers_per_server: int,
    distributed_timeout: float,
    scenario: str,
    repeat: int,
    varied_parameter: str,
    varied_value: int,
) -> list[dict]:
    """Executa os quatro modos (serial, paralelo local, distribuido serial e distribuido
    hibrido) sobre o mesmo par de matrizes, retornando uma lista de dicionarios de resultado."""
    a = generate_matrix(size, size, seed)
    b = generate_matrix(size, size, seed + 1)

    serial_result, serial_time = measure(lambda: multiply_serial(a, b))
    server_count = len(servers)
    rows = [
        make_row(
            "Serial",
            "serial",
            size,
            serial_time,
            serial_time,
            True,
            scenario,
            repeat,
            varied_parameter,
            varied_value,
            local_workers=local_workers,
            workers_per_server=workers_per_server,
        )
    ]

    parallel_result, parallel_time = measure(lambda: multiply_parallel(a, b, local_workers))
    rows.append(
        make_row(
            "Paralelo local",
            "parallel",
            size,
            parallel_time,
            serial_time,
            matrices_equal(serial_result, parallel_result),
            scenario,
            repeat,
            varied_parameter,
            varied_value,
            workers=local_workers,
            local_workers=local_workers,
            workers_per_server=workers_per_server,
        )
    )

    distributed_result = distributed_multiply(
        a,
        b,
        servers,
        mode=SERIAL,
        workers_per_server=1,
        timeout=distributed_timeout,
    )
    rows.append(
        make_row(
            "Distribuido serial",
            "distributed",
            size,
            distributed_result["time"],
            serial_time,
            matrices_equal(serial_result, distributed_result["matrix"]),
            scenario,
            repeat,
            varied_parameter,
            varied_value,
            servers=server_count,
            workers=server_count,
            local_workers=local_workers,
            workers_per_server=workers_per_server,
        )
    )

    hybrid_result = distributed_multiply(
        a,
        b,
        servers,
        mode=PROCESS_POOL,
        workers_per_server=workers_per_server,
        timeout=distributed_timeout,
    )
    rows.append(
        make_row(
            "Distribuido hibrido",
            "hybrid",
            size,
            hybrid_result["time"],
            serial_time,
            matrices_equal(serial_result, hybrid_result["matrix"]),
            scenario,
            repeat,
            varied_parameter,
            varied_value,
            servers=server_count,
            workers=server_count * workers_per_server,
            local_workers=local_workers,
            workers_per_server=workers_per_server,
        )
    )

    return rows


def run_benchmark(
    sizes: list[int],
    repeats: int,
    server_count: int,
    local_workers: int,
    workers_per_server: int,
    distributed_timeout: float,
    seed: int,
    scenario: str,
    varied_parameter: str,
    varied_value: int,
) -> list[dict]:
    """Laco principal de benchmark: itera sobre tamanhos e repeticoes, chama
    compare_all_modes e acumula os resultados."""
    servers, processes = start_servers(server_count, workers_per_server)
    all_rows: list[dict] = []

    try:
        for size in sizes:
            for repeat in range(repeats):
                current_varied_value = size if varied_parameter == "size" else varied_value
                print(
                    f"\nCenario={scenario} | {varied_parameter}={current_varied_value} | "
                    f"N={size} | repeticao={repeat + 1}/{repeats}"
                )
                rows = compare_all_modes(
                    size=size,
                    seed=seed + repeat + size,
                    servers=servers,
                    local_workers=local_workers,
                    workers_per_server=workers_per_server,
                    distributed_timeout=distributed_timeout,
                    scenario=scenario,
                    repeat=repeat + 1,
                    varied_parameter=varied_parameter,
                    varied_value=current_varied_value,
                )
                all_rows.extend(rows)
                for row in rows:
                    print_result(row)
    finally:
        stop_servers(processes)

    return all_rows


def run_matrix_size_scenario(
    sizes: list[int],
    repeats: int,
    server_count: int,
    local_workers: int,
    workers_per_server: int,
    distributed_timeout: float,
    seed: int,
) -> list[dict]:
    """Cenario 1: varia o tamanho da matriz com configuracao fixa de servidores e workers."""
    return run_benchmark(
        sizes=sizes,
        repeats=repeats,
        server_count=server_count,
        local_workers=local_workers,
        workers_per_server=workers_per_server,
        distributed_timeout=distributed_timeout,
        seed=seed,
        scenario="tamanho_matriz",
        varied_parameter="size",
        varied_value=0,
    )


def run_server_count_scenario(
    sizes: list[int],
    repeats: int,
    server_counts: list[int],
    local_workers: int,
    total_server_workers: int,
    distributed_timeout: float,
    seed: int,
) -> list[dict]:
    """Cenario 2: varia a quantidade de servidores mantendo o total de workers no modo
    hibrido fixo em TOTAL_SERVER_WORKERS."""
    results: list[dict] = []
    for server_count in server_counts:
        adjusted_workers_per_server = max(1, total_server_workers // server_count)
        results.extend(
            run_benchmark(
                sizes=sizes,
                repeats=repeats,
                server_count=server_count,
                local_workers=local_workers,
                workers_per_server=adjusted_workers_per_server,
                distributed_timeout=distributed_timeout,
                seed=seed,
                scenario="quantidade_servidores",
                varied_parameter="server_count",
                varied_value=server_count,
            )
        )
    return results


def run_local_workers_scenario(
    sizes: list[int],
    repeats: int,
    server_count: int,
    local_workers_values: list[int],
    workers_per_server: int,
    distributed_timeout: float,
    seed: int,
) -> list[dict]:
    """Cenario 3: varia o numero de workers locais do modo paralelo local, mantendo
    servidores e demais parametros fixos."""
    results: list[dict] = []
    for local_workers in local_workers_values:
        results.extend(
            run_benchmark(
                sizes=sizes,
                repeats=repeats,
                server_count=server_count,
                local_workers=local_workers,
                workers_per_server=workers_per_server,
                distributed_timeout=distributed_timeout,
                seed=seed,
                scenario="workers_locais",
                varied_parameter="local_workers",
                varied_value=local_workers,
            )
        )
    return results


def run_workers_per_server_scenario(
    sizes: list[int],
    repeats: int,
    server_count: int,
    local_workers: int,
    workers_per_server_values: list[int],
    distributed_timeout: float,
    seed: int,
) -> list[dict]:
    """Cenario 4: varia os workers por servidor no modo distribuido hibrido, mantendo
    o numero de servidores fixo."""
    results: list[dict] = []
    for workers_per_server in workers_per_server_values:
        results.extend(
            run_benchmark(
                sizes=sizes,
                repeats=repeats,
                server_count=server_count,
                local_workers=local_workers,
                workers_per_server=workers_per_server,
                distributed_timeout=distributed_timeout,
                seed=seed,
                scenario="workers_por_servidor",
                varied_parameter="workers_per_server",
                varied_value=workers_per_server,
            )
        )
    return results


def save_csv(results: list[dict], path: str = "results/benchmark_results.csv") -> None:
    """Escreve todos os resultados acumulados em um arquivo CSV com cabecalho,
    criando o diretorio se necessario."""
    if not results:
        return

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)


def run_tests() -> None:
    """Invoca pytest via subprocess e encerra o programa em caso de falha, garantindo
    que o benchmark so rode com codigo validado."""
    test_files = list(Path(".").glob("test_*.py")) + list(Path(".").glob("tests/test_*.py"))
    if not test_files:
        print("\nNenhum teste automatizado encontrado; pulando pytest.")
        return

    print("\nExecutando testes automatizados...")
    completed = subprocess.run([sys.executable, "-m", "pytest"], check=False)
    if completed.returncode != 0:
        raise RuntimeError("Os testes falharam.")


def run_all(
    matrix_sizes: list[int],
    control_matrix_sizes: list[int],
    worker_matrix_sizes: list[int],
    repeats: int,
    server_count: int,
    server_counts: list[int],
    local_workers: int,
    local_workers_values: list[int],
    total_server_workers: int,
    workers_per_server: int,
    workers_per_server_values: list[int],
    distributed_timeout: float,
    seed: int,
    run_pytest: bool,
    save_results: bool,
    show_plots: bool,
) -> list[dict]:
    """Ponto de entrada chamado por main.py: executa os testes, a demonstracao, os quatro
    cenarios e salva o CSV e os graficos."""
    if run_pytest:
        run_tests()

    print_demo_matrix_result(
        server_count=server_count,
        workers_per_server=workers_per_server,
        distributed_timeout=distributed_timeout,
    )

    results: list[dict] = []
    results.extend(
        run_matrix_size_scenario(
            sizes=matrix_sizes,
            repeats=repeats,
            server_count=server_count,
            local_workers=local_workers,
            workers_per_server=workers_per_server,
            distributed_timeout=distributed_timeout,
            seed=seed,
        )
    )
    results.extend(
        run_server_count_scenario(
            sizes=control_matrix_sizes,
            repeats=repeats,
            server_counts=server_counts,
            local_workers=local_workers,
            total_server_workers=total_server_workers,
            distributed_timeout=distributed_timeout,
            seed=seed,
        )
    )
    results.extend(
        run_local_workers_scenario(
            sizes=worker_matrix_sizes,
            repeats=repeats,
            server_count=server_count,
            local_workers_values=local_workers_values,
            workers_per_server=workers_per_server,
            distributed_timeout=distributed_timeout,
            seed=seed,
        )
    )
    results.extend(
        run_workers_per_server_scenario(
            sizes=worker_matrix_sizes,
            repeats=repeats,
            server_count=server_count,
            local_workers=local_workers,
            workers_per_server_values=workers_per_server_values,
            distributed_timeout=distributed_timeout,
            seed=seed,
        )
    )

    if save_results:
        save_csv(results)

    plot_results(results, show=show_plots)
    return results
