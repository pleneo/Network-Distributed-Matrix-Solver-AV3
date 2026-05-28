from matrix_ops import combine_blocks, matrices_equal, multiply_parallel, multiply_serial, split_rows


def test_multiply_serial_known_result():
    a = [[1, 0, -1], [4, -1, 2], [-1, 2, 4]]
    b = [[-1, 2, -3], [5, -4, 2], [4, 1, 0]]

    assert multiply_serial(a, b) == [[-5, 1, -3], [-1, 14, -14], [27, -6, 7]]


def test_parallel_matches_serial():
    a = [[1, 2], [3, 4], [5, 6]]
    b = [[7, 8, 9], [10, 11, 12]]

    assert multiply_parallel(a, b, workers=2) == multiply_serial(a, b)


def test_split_and_combine_rows():
    matrix = [[1], [2], [3], [4], [5]]
    blocks = split_rows(matrix, 2)

    assert blocks == [(0, 3, [[1], [2], [3]]), (3, 5, [[4], [5]])]
    assert combine_blocks(reversed(blocks)) == matrix


def test_matrices_equal():
    assert matrices_equal([[1, 2]], [[1, 2]])
    assert not matrices_equal([[1, 2]], [[2, 1]])
