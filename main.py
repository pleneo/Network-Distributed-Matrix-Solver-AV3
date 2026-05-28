"""Parametros principais do trabalho."""

from benchmark import run_all


MATRIX_SIZES = [1, 5, 60, 120, 250, 500, 750]
CONTROL_MATRIX_SIZES = [250, 500]
WORKER_MATRIX_SIZES = [1, 5, 60, 120, 250, 500, 750]
REPEATS = 3
SEED = 42

SERVER_COUNT = 2
SERVER_COUNTS = [1, 2, 3, 4]

LOCAL_PARALLEL_WORKERS = 12
LOCAL_PARALLEL_WORKERS_VALUES = [1, 2, 4, 8, 12]

TOTAL_SERVER_WORKERS = 12
WORKERS_PER_SERVER = 6
WORKERS_PER_SERVER_VALUES = [1, 2, 4, 6]

DISTRIBUTED_TIMEOUT = 1000.0

RUN_PYTEST = True
SAVE_RESULTS = True
SHOW_PLOTS = True


if __name__ == "__main__":
    run_all(
        matrix_sizes=MATRIX_SIZES,
        control_matrix_sizes=CONTROL_MATRIX_SIZES,
        worker_matrix_sizes=WORKER_MATRIX_SIZES,
        repeats=REPEATS,
        server_count=SERVER_COUNT,
        server_counts=SERVER_COUNTS,
        local_workers=LOCAL_PARALLEL_WORKERS,
        local_workers_values=LOCAL_PARALLEL_WORKERS_VALUES,
        total_server_workers=TOTAL_SERVER_WORKERS,
        workers_per_server=WORKERS_PER_SERVER,
        workers_per_server_values=WORKERS_PER_SERVER_VALUES,
        distributed_timeout=DISTRIBUTED_TIMEOUT,
        seed=SEED,
        run_pytest=RUN_PYTEST,
        save_results=SAVE_RESULTS,
        show_plots=SHOW_PLOTS,
    )
