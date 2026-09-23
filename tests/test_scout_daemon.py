import asyncio

import pytest

from coins_on_the_ground.runtime import run_scout_daemon


@pytest.mark.asyncio
async def test_daemon_continues_after_failed_cycle() -> None:
    calls: list[int] = []

    async def cycle(number: int) -> int:
        calls.append(number)
        return 1 if number == 1 else 0

    async def no_sleep(_: float) -> None:
        await asyncio.sleep(0)

    summary = await run_scout_daemon(
        cycle,
        tick_seconds=1,
        max_cycles=3,
        sleep=no_sleep,
    )

    assert calls == [1, 2, 3]
    assert summary.cycles == 3
    assert summary.successful_cycles == 2
    assert summary.failed_cycles == 1
    assert summary.last_exit_code == 0


@pytest.mark.asyncio
async def test_daemon_contains_unexpected_cycle_exception() -> None:
    async def cycle(number: int) -> int:
        if number == 1:
            raise RuntimeError("transient failure")
        return 0

    async def no_sleep(_: float) -> None:
        await asyncio.sleep(0)

    summary = await run_scout_daemon(
        cycle,
        tick_seconds=1,
        max_cycles=2,
        sleep=no_sleep,
    )

    assert summary.cycles == 2
    assert summary.successful_cycles == 1
    assert summary.failed_cycles == 1
    assert summary.last_exit_code == 0


@pytest.mark.asyncio
async def test_daemon_validates_tick_and_cycle_limit() -> None:
    async def cycle(_: int) -> int:
        return 0

    with pytest.raises(ValueError, match="tick_seconds"):
        await run_scout_daemon(cycle, tick_seconds=0, max_cycles=1)

    with pytest.raises(ValueError, match="max_cycles"):
        await run_scout_daemon(cycle, tick_seconds=1, max_cycles=0)
