"""Operacoes de matriz usadas nos experimentos."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import random
from typing import Iterable


Matrix = list[list[int | float]]
Block = tuple[int, int, Matrix]


def generate_matrix(rows: int, cols: int, seed: int, min_value: int = -9, max_value: int = 9) -> Matrix:
    if rows <= 0 or cols <= 0:
        raise ValueError("As dimensoes da matriz devem ser positivas.")

    rng = random.Random(seed)
    return [[rng.randint(min_value, max_value) for _ in range(cols)] for _ in range(rows)]


def shape(matrix: Matrix) -> tuple[int, int]:
    if not matrix or not matrix[0]:
        raise ValueError("A matriz nao pode ser vazia.")

    cols = len(matrix[0])
    if any(len(row) != cols for row in matrix):
        raise ValueError("A matriz deve ser retangular.")

    return len(matrix), cols


def validate_multiplication(a: Matrix, b: Matrix) -> None:
    rows_a, cols_a = shape(a)
    rows_b, cols_b = shape(b)
    if cols_a != rows_b:
        raise ValueError(
            f"Dimensoes invalidas: A={rows_a}x{cols_a}, B={rows_b}x{cols_b}."
        )


def multiply_serial(a: Matrix, b: Matrix) -> Matrix:
    validate_multiplication(a, b)
    _, cols_a = shape(a)
    _, cols_b = shape(b)
    b_columns = [[row[col] for row in b] for col in range(cols_b)]

    return [
        [sum(row[k] * column[k] for k in range(cols_a)) for column in b_columns]
        for row in a
    ]


def split_rows(matrix: Matrix, parts: int) -> list[Block]:
    rows, _ = shape(matrix)
    if parts <= 0:
        raise ValueError("A quantidade de partes deve ser positiva.")

    parts = min(parts, rows)
    base = rows // parts
    remainder = rows % parts
    blocks: list[Block] = []
    start = 0

    for index in range(parts):
        size = base + (1 if index < remainder else 0)
        end = start + size
        blocks.append((start, end, matrix[start:end]))
        start = end

    return blocks


def combine_blocks(blocks: Iterable[Block]) -> Matrix:
    result: Matrix = []
    expected_start = 0

    for start, end, block in sorted(blocks, key=lambda item: item[0]):
        if start != expected_start:
            raise ValueError("Blocos ausentes ou fora de ordem.")
        if end - start != len(block):
            raise ValueError("Intervalo de linhas inconsistente.")
        result.extend(block)
        expected_start = end

    return result


def _multiply_block(args: tuple[Block, Matrix]) -> Block:
    start, end, block = args[0]
    b = args[1]
    return start, end, multiply_serial(block, b)


def multiply_parallel(a: Matrix, b: Matrix, workers: int) -> Matrix:
    validate_multiplication(a, b)
    if workers <= 1 or len(a) == 1:
        return multiply_serial(a, b)

    blocks = split_rows(a, workers)
    with ProcessPoolExecutor(max_workers=min(workers, len(blocks))) as executor:
        result_blocks = list(executor.map(_multiply_block, [(block, b) for block in blocks]))

    return combine_blocks(result_blocks)


def matrices_equal(a: Matrix, b: Matrix) -> bool:
    return a == b
