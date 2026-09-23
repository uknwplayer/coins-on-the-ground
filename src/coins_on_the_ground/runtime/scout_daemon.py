from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoutDaemonSummary:
    cycles: int
    successful_cycles: int
    failed_cycles: int
    last_exit_code: int


async def run_scout_daemon(
    cycle: Callable[[int], Awaitable[int]],
    *,
    tick_seconds: float,
    max_cycles: int | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> ScoutDaemonSummary:
    """Run adaptive Scout cycles continuously without treating one failed cycle as fatal."""

    if tick_seconds <= 0:
        raise ValueError("tick_seconds must be positive")
    if max_cycles is not None and max_cycles < 1:
        raise ValueError("max_cycles must be positive when provided")

    cycles = 0
    successes = 0
    failures = 0
    last_exit_code = 0

    while True:
        cycles += 1
        try:
            last_exit_code = await cycle(cycles)
        except Exception:
            last_exit_code = 1

        if last_exit_code == 0:
            successes += 1
        else:
            failures += 1

        if max_cycles is not None and cycles >= max_cycles:
            break

        await sleep(tick_seconds)

    return ScoutDaemonSummary(
        cycles=cycles,
        successful_cycles=successes,
        failed_cycles=failures,
        last_exit_code=last_exit_code,
    )
