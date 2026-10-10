"""Gunicorn settings, loaded automatically from the working directory.

Lives here rather than only in render.yaml because the Render service's start
command and env vars are set in the dashboard and may not follow render.yaml.

Memory: the 512 MB instance hit its limit on 2026-10-09 after holding at 100%
for close to an hour. The baseline is ~170 MB, so the problem is growth: four
threads repeatedly load and evict large book CSVs, and glibc's per-thread malloc
arenas fragment and never return the memory to the OS.
"""
import ctypes
import sys

# Recycle the worker periodically so any creep is wiped out (jitter avoids
# a restart landing on a fixed request count).
max_requests = 1000
max_requests_jitter = 100


def _cap_malloc_arenas(n: int = 2) -> None:
    """Equivalent of MALLOC_ARENA_MAX=n, applied in-process (glibc only)."""
    if not sys.platform.startswith('linux'):
        return
    try:
        M_ARENA_MAX = -8
        ctypes.CDLL('libc.so.6').mallopt(M_ARENA_MAX, n)
    except Exception:
        pass


def post_fork(server, worker):
    _cap_malloc_arenas()
