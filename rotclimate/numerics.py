"""Small numerical kernels with consistent behavior across matrix backends."""
import numpy as np


def matrix_product(a, b):
    """2-D times 1-D/2-D without BLAS floating-point status side effects.

    Apple Accelerate on some Macs reports overflow/division flags for benign
    matmul inputs (NumPy #28687). Explicit contraction avoids that backend;
    optimize=False is intentional. It does not suppress arithmetic warnings.
    """
    a, b = np.asarray(a), np.asarray(b)
    if a.ndim != 2 or b.ndim not in (1, 2) or a.shape[1] != b.shape[0]:
        raise ValueError("Expected compatible 2-D times 1-D or 2-D arrays")
    return np.einsum("ij,j->i" if b.ndim == 1 else "ij,jk->ik",
                     a, b, optimize=False)
