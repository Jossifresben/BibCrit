"""Chi-square test and Cramér's V in pure Python (no SciPy on the server)."""
from __future__ import annotations

import math


def _gammainc_upper_reg(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x). Numerical Recipes gser/gcf."""
    if x <= 0:
        return 1.0
    if x < a + 1:
        # series for P(a,x)
        ap, s, d = a, 1.0 / a, 1.0 / a
        for _ in range(500):
            ap += 1
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-14:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # continued fraction for Q(a,x)
    b = x + 1 - a
    c = 1.0 / 1e-300
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        if abs(d) < 1e-300:
            d = 1e-300
        c = b + an / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_sf(x: float, k: int) -> float:
    return _gammainc_upper_reg(k / 2.0, x / 2.0)


def _clean(matrix: list[list[int]]) -> list[list[int]]:
    """Drop all-zero rows, then all-zero columns."""
    rows = [r for r in matrix if sum(r) > 0]
    if not rows:
        return []
    ncol = len(rows[0])
    col_tot = [sum(r[j] for r in rows) for j in range(ncol)]
    keep = [j for j in range(ncol) if col_tot[j] > 0]
    return [[r[j] for j in keep] for r in rows]


def chi_square(matrix: list[list[int]]) -> dict:
    rows = _clean(matrix)
    if not rows or len(rows) < 2:
        return {'stat': 0.0, 'dof': 0, 'p': 1.0, 'unreliable': True}
    if len(rows[0]) < 2:
        return {'stat': 0.0, 'dof': 0, 'p': 1.0, 'unreliable': True}

    ncol = len(rows[0])
    col_tot = [sum(r[j] for r in rows) for j in range(ncol)]
    n = sum(col_tot)
    if n == 0:
        return {'stat': 0.0, 'dof': 0, 'p': 1.0, 'unreliable': True}

    stat, unreliable = 0.0, False
    for r in rows:
        rt = sum(r)
        for j, obs in enumerate(r):
            exp = rt * col_tot[j] / n
            if exp < 5:
                unreliable = True
            stat += (obs - exp) ** 2 / exp
    dof = (len(rows) - 1) * (ncol - 1)
    return {'stat': round(stat, 4), 'dof': dof, 'p': chi2_sf(stat, dof), 'unreliable': unreliable}


def cramers_v(matrix: list[list[int]], stat: float) -> float:
    rows = _clean(matrix)
    if not rows or len(rows) < 2:
        return 0.0
    ncol = len(rows[0]) if rows else 0
    if ncol < 2:
        return 0.0
    n = sum(sum(r) for r in rows)
    if n == 0:
        return 0.0
    k = min(len(rows), ncol)
    return round(math.sqrt(stat / (n * (k - 1))), 4)
