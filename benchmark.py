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
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


def print_result(row: dict) -> None:
    print(
        f"{row['label']:<28} "
        f"N={row['size']:<5} "
        f"tempo={row['time']:.6f}s  "
        f"speedup={row['speedup']:.3f}  "
        f"eficiencia={row['efficiency']:.3f}  "
        f"valido={row['valid']}"
    )


def make_row(
    label: str,
    mode: str,
    size: int,
    elapsed: float,
    serial_time: float,
    valid: bool,
    servers: int = 1,
    workers: int = 1,
) -> dict:
    speedup = serial_time / elapsed if elapsed > 0 else 0.0
    efficiency = speedup / servers if servers > 0 else speedup
    return {
        "label": label,
        "mode": mode,
        "size": size,
        "time": elapsed,
        "serial_time": serial_time,
        "speedup": speedup,
        "efficiency": efficiency,
        "servers": servers,
        "workers": workers,
        "valid": valid,
    }


def compare_all_modes(
    size: int,
    seed: int,
    servers: list[tuple[str, int]],
    local_workers: int,
    workers_per_server: int,
) -> list[dict]:
    a = generate_matrix(size, size, seed)
    b = generate_matrix(size, size, seed + 1)

    serial_result, serial_time = measure(lambda: multiply_serial(a, b))
    rows = [
        make_row("Serial", "serial", size, serial_time, serial_time, True)
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
            workers=local_workers,
        )
    )

    distributed_result = distributed_multiply(a, b, servers, mode=SERIAL, workers_per_server=1)
    rows.append(
        make_row(
            "Distribuido serial",
            "distributed",
            size,
            distributed_result["time"],
            serial_time,
            matrices_equal(serial_result, distributed_result["matrix"]),
            servers=len(servers),
            workers=1,
        )
    )

    hybrid_result = distributed_multiply(a, b, servers, mode=PROCESS_POOL, workers_per_server=workers_per_server)
    rows.append(
        make_row(
            "Distribuido hibrido",
            "hybrid",
            size,
            hybrid_result["time"],
            serial_time,
            matrices_equal(serial_result, hybrid_result["matrix"]),
            servers=len(servers),
            workers=workers_per_server,
        )
    )

    return rows


def run_benchmark(
    sizes: list[int],
    repeats: int,
    server_count: int,
    local_workers: int,
    workers_per_server: int,
    seed: int,
) -> list[dict]:
    servers, processes = start_servers(server_count, workers_per_server)
    all_rows: list[dict] = []

    try:
        for size in sizes:
            for repeat in range(repeats):
                print(f"\nExecutando N={size} | repeticao={repeat + 1}/{repeats}")
                rows = compare_all_modes(
                    size=size,
                    seed=seed + repeat + size,
                    servers=servers,
                    local_workers=local_workers,
                    workers_per_server=workers_per_server,
                )
                all_rows.extend(rows)
                for row in rows:
                    print_result(row)
    finally:
        stop_servers(processes)

    return all_rows


def save_csv(results: list[dict], path: str = "results/benchmark_results.csv") -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)


def run_tests() -> None:
    print("\nExecutando testes automatizados...")
    completed = subprocess.run([sys.executable, "-m", "pytest"], check=False)
    if completed.returncode != 0:
        raise RuntimeError("Os testes falharam.")


def run_all(
    matrix_sizes: list[int],
    repeats: int,
    server_count: int,
    local_workers: int,
    workers_per_server: int,
    seed: int,
    run_pytest: bool,
    save_results: bool,
    show_plots: bool,
) -> list[dict]:
    if run_pytest:
        run_tests()

    results = run_benchmark(
        sizes=matrix_sizes,
        repeats=repeats,
        server_count=server_count,
        local_workers=local_workers,
        workers_per_server=workers_per_server,
        seed=seed,
    )

    if save_results:
        save_csv(results)

    plot_results(results, show=show_plots)
    return results
