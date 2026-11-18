"""相邻读数差额还原纯算法。

设备只上报累计投入/合格两个计数器，计数器在 ``counter_capacity`` 处回卷（取值 0..cap-1）。
差额还原规则：
- 读数未倒退：唯一解，差额 = 后值 - 前值，回卷次数 0；
- 读数倒退（回卷）：候选解为 k>=1 次回卷，delta = 后值 - 前值 + k*cap；
  以最大产速×秒数作为产能上限裁剪候选，零解=超速，恰好一解=可计件，多解=回卷多解待确认；
- 换表读数（meter_changed）：必须带旧表交接值，旧表段差额加新表初读数；
- 区间内部跨过班次边界且边界时刻没有读数：缺边界读数，暂不计件。

原因判定优先级：bad_interval > missing_handover > rewind_ambiguous > rate_exceeded > missing_boundary。
"""
from dataclasses import dataclass

from src.constants.enums import INTERVAL_CONFIRMED, INTERVAL_PENDING
from src.services.shifts import crosses_shift_boundary, shift_at


@dataclass
class Reading:
    read_at: object
    total_input: int
    total_good: int
    meter_changed: bool = False
    handover_input: int | None = None
    handover_good: int | None = None


def rollover_candidates(prev_value: int, next_value: int, capacity: int, plausibility_cap: int):
    """返回 [(delta, rollovers)]。未倒退给唯一原始差额（仍受产能约束）；倒退给所有产能内的回卷解。"""
    if next_value >= prev_value:
        delta = next_value - prev_value
        return [(delta, 0)] if delta <= plausibility_cap else []
    candidates = []
    k = 1
    while True:
        delta = next_value - prev_value + k * capacity
        if delta > plausibility_cap:
            break
        candidates.append((delta, k))
        k += 1
    return candidates


def _pending(reason, started_at, ended_at):
    return {
        'started_at': started_at,
        'ended_at': ended_at,
        'input_delta': None,
        'good_delta': None,
        'rollovers': 0,
        'status': INTERVAL_PENDING,
        'reason_code': reason,
        'shift_name': None,
    }


def resolve_interval(prev: Reading, nxt: Reading, capacity: int, max_rate_per_sec: int,
                     shifts: list[dict]) -> dict:
    started_at, ended_at = prev.read_at, nxt.read_at
    seconds = (ended_at - started_at).total_seconds()

    if seconds <= 0:
        return _pending('bad_interval', started_at, ended_at)
    if prev.total_good > prev.total_input or nxt.total_good > nxt.total_input:
        return _pending('bad_interval', started_at, ended_at)

    plausibility_cap = int(max_rate_per_sec * seconds)

    if nxt.meter_changed:
        hi, hg = nxt.handover_input, nxt.handover_good
        # 缺换表交接或交接值本身非法
        if hi is None or hg is None or not (0 <= hi < capacity and 0 <= hg < capacity) or hg > hi:
            return _pending('missing_handover', started_at, ended_at)
        old_input, old_good = hi - prev.total_input, hg - prev.total_good
        if old_input < 0 or old_good < 0:
            return _pending('missing_handover', started_at, ended_at)
        input_delta = old_input + nxt.total_input
        good_delta = old_good + nxt.total_good
        rollovers = 0
        if input_delta > plausibility_cap or good_delta > plausibility_cap:
            return _pending('rate_exceeded', started_at, ended_at)
    else:
        input_solutions = rollover_candidates(prev.total_input, nxt.total_input, capacity, plausibility_cap)
        good_solutions = rollover_candidates(prev.total_good, nxt.total_good, capacity, plausibility_cap)
        if len(input_solutions) > 1 or len(good_solutions) > 1:
            return _pending('rewind_ambiguous', started_at, ended_at)
        if not input_solutions or not good_solutions:
            return _pending('rate_exceeded', started_at, ended_at)
        input_delta, ri = input_solutions[0]
        good_delta, _rg = good_solutions[0]
        rollovers = ri

    if good_delta > input_delta:
        return _pending('bad_interval', started_at, ended_at)

    if crosses_shift_boundary(shifts, started_at, ended_at):
        return _pending('missing_boundary', started_at, ended_at)

    return {
        'started_at': started_at,
        'ended_at': ended_at,
        'input_delta': input_delta,
        'good_delta': good_delta,
        'rollovers': rollovers,
        'status': INTERVAL_CONFIRMED,
        'reason_code': None,
        'shift_name': shift_at(shifts, started_at),
    }
