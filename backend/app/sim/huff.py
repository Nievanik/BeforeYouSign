"""People nearby on a grid, and the Huff model: how they split between the shops within reach."""
import math

import numpy as np

CELL_M = 200
SQMI_PER_CELL = (CELL_M / 1609.344) ** 2
MIN_DIST_MI = 0.05
MI_PER_DEG_LAT = 69.055


def _offsets_mi(lat: float, dlat, dlon):
    return np.asarray(dlon) * MI_PER_DEG_LAT * math.cos(math.radians(lat)), np.asarray(dlat) * MI_PER_DEG_LAT


def grid(lat: float, lon: float, radius_mi: float, density_per_sqmi: float,
         workers: list[tuple[float, float, int]], worker_weight: float):
    """Demand points every 200 m within the radius.

    Returns (x, y) in miles from the site, people per point, total residents, total workers.
    shortcut: every cell uses the site tract's density; upgrade to per-cell tracts if time allows.
    """
    step = CELL_M / 1609.344
    n = int(radius_mi / step)
    gx, gy = np.meshgrid(np.arange(-n, n + 1) * step, np.arange(-n, n + 1) * step)
    inside = np.hypot(gx, gy) <= radius_mi
    x, y = gx[inside], gy[inside]
    residents = np.full(x.shape, density_per_sqmi * SQMI_PER_CELL)

    jobs = np.zeros(x.shape)
    if workers:
        w = np.asarray(workers, dtype=float)
        wx, wy = _offsets_mi(lat, w[:, 0] - lat, w[:, 1] - lon)
        near = np.hypot(wx, wy) <= radius_mi
        if near.any():
            # snap each company to its nearest cell
            idx = np.argmin((x[None, :] - wx[near, None]) ** 2 + (y[None, :] - wy[near, None]) ** 2, axis=1)
            np.add.at(jobs, idx, w[near, 2])
    return x, y, residents + worker_weight * jobs, float(residents.sum()), float(jobs.sum())


def shares(x, y, sx, sy, attract, lam: float):
    """P(point i -> store j): (A_j / d_ij^lam) / sum_k (A_k / d_ik^lam). Shape (points, stores)."""
    d = np.maximum(np.hypot(x[:, None] - np.asarray(sx)[None, :], y[:, None] - np.asarray(sy)[None, :]), MIN_DIST_MI)
    u = np.asarray(attract)[None, :] / d ** lam
    return u / u.sum(axis=1, keepdims=True)


def store_xy(lat: float, lon: float, points: list[tuple[float, float]]):
    lats, lons = zip(*points) if points else ((), ())
    return _offsets_mi(lat, np.subtract(lats, lat), np.subtract(lons, lon))
