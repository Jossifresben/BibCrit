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


def chi_square(matrix: list[list[int]]) -> dict:
    rows = [r for r in matrix if sum(r) > 0]
    if not rows:
        return {'stat': 0.0, 'dof': 0, 'p': 1.0, 'unreliable': True}
    ncol = len(rows[0])
    col_tot = [sum(r[j] for r in rows) for j in range(ncol)]
    keep = [j for j in range(ncol) if col_tot[j] > 0]
    rows = [[r[j] for j in keep] for r in rows]
    col_tot = [col_tot[j] for j in keep]
    n = sum(col_tot)
    if len(rows) < 2 or len(keep) < 2 or n == 0:
        return {'stat': 0.0, 'dof': 0, 'p': 1.0, 'unreliable': True}
    stat, unreliable = 0.0, False
    for r in rows:
        rt = sum(r)
        for j, obs in enumerate(r):
            exp = rt * col_tot[j] / n
            if exp < 5:
                unreliable = True
            stat += (obs - exp) ** 2 / exp
    dof = (len(rows) - 1) * (len(keep) - 1)
    return {'stat': round(stat, 4), 'dof': dof, 'p': chi2_sf(stat, dof), 'unreliable': unreliable}


def cramers_v(matrix: list[list[int]], stat: float) -> float:
    n = sum(sum(r) for r in matrix)
    k = min(len(matrix), len(matrix[0]) if matrix else 0)
    if n == 0 or k < 2:
        return 0.0
    return round(math.sqrt(stat / (n * (k - 1))), 4)
