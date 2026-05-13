"""Computacao distribuida simples com sockets TCP."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process
import json
import socket
import struct
import time
from typing import Any

from matrix_ops import Block, Matrix, combine_blocks, multiply_parallel, multiply_serial, split_rows


HOST = "127.0.0.1"
SERIAL = "serial"
PROCESS_POOL = "process-pool"

Endpoint = tuple[str, int]


def _send(sock: socket.socket, data: dict[str, Any]) -> None:
    payload = json.dumps(data).encode("utf-8")
    sock.sendall(struct.pack("!Q", len(payload)))
    sock.sendall(payload)


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Conexao encerrada antes da mensagem completa.")
        data += chunk
    return data


def _recv(sock: socket.socket) -> dict[str, Any]:
    size = struct.unpack("!Q", _recv_exact(sock, 8))[0]
    return json.loads(_recv_exact(sock, size).decode("utf-8"))


def _calculate(a_block: Matrix, b: Matrix, mode: str, workers: int) -> Matrix:
    if mode == SERIAL:
        return multiply_serial(a_block, b)
    if mode == PROCESS_POOL:
        return multiply_parallel(a_block, b, workers)
    raise ValueError(f"Modo invalido: {mode}")


def handle_client(conn: socket.socket, default_mode: str, default_workers: int) -> None:
    with conn:
        try:
            task = _recv(conn)
            mode = task.get("mode", default_mode)
            workers = int(task.get("workers", default_workers))

            start_time = time.perf_counter()
            c_block = _calculate(task["a_block"], task["b"], mode, workers)
            compute_time = time.perf_counter() - start_time

            _send(
                conn,
                {
                    "row_start": task["row_start"],
                    "row_end": task["row_end"],
                    "c_block": c_block,
                    "compute_time": compute_time,
                },
            )
        except Exception as exc:
            try:
                _send(conn, {"error": str(exc)})
            except OSError:
                pass


def run_server(
    host: str = HOST,
    port: int = 9001,
    mode: str = SERIAL,
    workers: int = 1,
    max_tasks: int | None = None,
) -> None:
    handled = 0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        print(f"Servidor em {host}:{port} | modo={mode} | workers={workers}", flush=True)

        while max_tasks is None or handled < max_tasks:
            conn, _ = server.accept()
            handle_client(conn, mode, workers)
            handled += 1


def find_free_port(host: str = HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def wait_for_server(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"Servidor {host}:{port} nao iniciou a tempo.")


def start_servers(count: int, workers: int, host: str = HOST) -> tuple[list[Endpoint], list[Process]]:
    endpoints: list[Endpoint] = []
    processes: list[Process] = []

    for _ in range(count):
        port = find_free_port(host)
        process = Process(target=run_server, kwargs={"host": host, "port": port, "workers": workers})
        process.start()
        endpoints.append((host, port))
        processes.append(process)

    for host, port in endpoints:
        wait_for_server(host, port)

    return endpoints, processes


def stop_servers(processes: list[Process]) -> None:
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join(timeout=5)


def _send_task(endpoint: Endpoint, task: dict[str, Any], timeout: float) -> dict[str, Any]:
    host, port = endpoint
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        _send(sock, task)
        response = _recv(sock)

    if "error" in response:
        raise RuntimeError(f"Erro no servidor {host}:{port}: {response['error']}")
    return response


def distributed_multiply(
    a: Matrix,
    b: Matrix,
    servers: list[Endpoint],
    mode: str = SERIAL,
    workers_per_server: int = 1,
    timeout: float = 120.0,
) -> dict[str, Any]:
    blocks = split_rows(a, len(servers))
    tasks = [
        {
            "row_start": start,
            "row_end": end,
            "a_block": block,
            "b": b,
            "mode": mode,
            "workers": workers_per_server,
        }
        for start, end, block in blocks
    ]

    start_time = time.perf_counter()
    responses: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = [
            executor.submit(_send_task, endpoint, task, timeout)
            for endpoint, task in zip(servers, tasks)
        ]
        for future in as_completed(futures):
            responses.append(future.result())

    elapsed = time.perf_counter() - start_time
    result_blocks: list[Block] = [
        (response["row_start"], response["row_end"], response["c_block"])
        for response in responses
    ]
    compute_times = [response["compute_time"] for response in responses]

    return {
        "matrix": combine_blocks(result_blocks),
        "time": elapsed,
        "compute_time_max": max(compute_times, default=0.0),
        "compute_time_sum": sum(compute_times),
        "overhead": max(0.0, elapsed - max(compute_times, default=0.0)),
    }
