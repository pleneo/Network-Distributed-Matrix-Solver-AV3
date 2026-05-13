"""Parametros principais do trabalho."""

from benchmark import run_all


MATRIX_SIZES = [5, 60, 120, 500, 1000]
REPEATS = 2
SEED = 42

SERVER_COUNT = 2
LOCAL_PARALLEL_WORKERS = 12
WORKERS_PER_SERVER = 6

RUN_PYTEST = True
SAVE_RESULTS = True
SHOW_PLOTS = True


if __name__ == "__main__":
    run_all(
        matrix_sizes=MATRIX_SIZES,
        repeats=REPEATS,
        server_count=SERVER_COUNT,
        local_workers=LOCAL_PARALLEL_WORKERS,
        workers_per_server=WORKERS_PER_SERVER,
        seed=SEED,
        run_pytest=RUN_PYTEST,
        save_results=SAVE_RESULTS,
        show_plots=SHOW_PLOTS,
    )
