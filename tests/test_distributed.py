from distributed import PROCESS_POOL, SERIAL, distributed_multiply, start_servers, stop_servers
from matrix_ops import matrices_equal, multiply_serial


def test_distributed_serial_matches_serial():
    servers, processes = start_servers(count=2, workers=2)
    try:
        a = [[1, 2], [3, 4], [5, 6]]
        b = [[7, 8, 9], [10, 11, 12]]

        result = distributed_multiply(a, b, servers, mode=SERIAL)

        assert matrices_equal(result["matrix"], multiply_serial(a, b))
    finally:
        stop_servers(processes)


def test_distributed_hybrid_matches_serial():
    servers, processes = start_servers(count=2, workers=2)
    try:
        a = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [2, 3, 4]]
        b = [[1, 0], [0, 1], [1, 1]]

        result = distributed_multiply(a, b, servers, mode=PROCESS_POOL, workers_per_server=2)

        assert matrices_equal(result["matrix"], multiply_serial(a, b))
    finally:
        stop_servers(processes)
