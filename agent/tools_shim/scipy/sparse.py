"""Minimal numpy stand-in for scipy.sparse.coo_matrix(...).tocsr() as used by import_sculpt.py and paint.py:
build an adjacency matrix, set data to 1, take row sums (A.sum(1)) and multiply (A @ x)."""
import numpy as np


class _Sparse:
    def __init__(self, rows, cols, data, shape):
        self.shape = shape
        key = rows.astype(np.int64) * shape[1] + cols.astype(np.int64)
        uq, inv = np.unique(key, return_inverse=True)      # duplicates are summed, as tocsr() does
        self.data = np.zeros(len(uq)); np.add.at(self.data, inv.reshape(-1), data)
        self.row, self.col = uq // shape[1], uq % shape[1]

    def tocsr(self): return self

    def sum(self, axis=None):
        if axis is None: return self.data.sum()
        idx = self.row if axis == 1 else self.col
        out = np.zeros(self.shape[0] if axis == 1 else self.shape[1]); np.add.at(out, idx, self.data)
        return out.reshape(-1, 1) if axis == 1 else out.reshape(1, -1)

    def __matmul__(self, x):
        x = np.asarray(x)
        out = np.zeros((self.shape[0],) + x.shape[1:], dtype=np.result_type(x, np.float64))
        w = self.data.reshape((-1,) + (1,) * (x.ndim - 1))
        np.add.at(out, self.row, w * x[self.col])
        return out

    dot = __matmul__


def coo_matrix(arg, shape):
    data, (rows, cols) = arg
    return _Sparse(np.asarray(rows), np.asarray(cols), np.asarray(data, np.float64), shape)
