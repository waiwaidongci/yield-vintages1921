from datetime import datetime, timedelta

from src.constants.enums import INTERVAL_CONFIRMED, INTERVAL_PENDING
from src.services.intervals import Reading, resolve_interval, rollover_candidates
from src.constants.enums import DEFAULT_SHIFTS

T0 = datetime(2026, 11, 18, 8, 0, 0)
CAP = 10000
RATE = 2  # 件/秒


def rd(minutes, ti, tg, **kw):
    return Reading(T0 + timedelta(minutes=minutes), ti, tg, **kw)


def test_monotonic_unique_delta():
    out = resolve_interval(rd(0, 100, 95), rd(60, 1300, 1240), CAP, RATE, DEFAULT_SHIFTS)
    assert out['status'] == INTERVAL_CONFIRMED
    assert (out['input_delta'], out['good_delta'], out['rollovers']) == (1200, 1145, 0)
    assert out['shift_name'] == '早班'


def test_rollover_single_solution():
    # 60 分钟产能 7200；倒退解 k=1 可行（投入370/合格358），k=2 的 10370 超产能 → 唯一解
    out = resolve_interval(rd(0, 9950, 9700), rd(60, 320, 58), CAP, RATE, DEFAULT_SHIFTS)
    assert out['status'] == INTERVAL_CONFIRMED
    assert (out['input_delta'], out['good_delta'], out['rollovers']) == (370, 358, 1)


def test_rollover_multiple_solutions_pending():
    # 120 分钟产能 14400；k=1(110) 与 k=2(10110) 均可行 → 多解
    out = resolve_interval(rd(0, 9950, 9700), rd(120, 60, 58), CAP, RATE, DEFAULT_SHIFTS)
    assert out['status'] == INTERVAL_PENDING and out['reason_code'] == 'rewind_ambiguous'
    assert out['input_delta'] is None


def test_rate_exceeded_pending():
    out = resolve_interval(rd(0, 1000, 960), rd(1, 1300, 1250), CAP, RATE, DEFAULT_SHIFTS)
    assert out['status'] == INTERVAL_PENDING and out['reason_code'] == 'rate_exceeded'


def test_meter_change_with_handover():
    prev = rd(0, 300, 290)
    nxt = rd(1, 100, 95, meter_changed=True, handover_input=300, handover_good=290)
    out = resolve_interval(prev, nxt, CAP, RATE, DEFAULT_SHIFTS)
    assert out['status'] == INTERVAL_CONFIRMED
    assert (out['input_delta'], out['good_delta']) == (100, 95)


def test_meter_change_missing_handover():
    prev = rd(0, 500, 470)
    nxt = rd(1, 80, 70, meter_changed=True)
    out = resolve_interval(prev, nxt, CAP, RATE, DEFAULT_SHIFTS)
    assert out['status'] == INTERVAL_PENDING and out['reason_code'] == 'missing_handover'


def test_cross_shift_missing_boundary():
    # 15:55 -> 16:10 跨过 16:00 班次边界，内部没有读数
    prev = Reading(datetime(2026, 11, 18, 15, 55), 200, 190)
    nxt = Reading(datetime(2026, 11, 18, 16, 10), 900, 850)
    out = resolve_interval(prev, nxt, CAP, RATE, DEFAULT_SHIFTS)
    assert out['status'] == INTERVAL_PENDING and out['reason_code'] == 'missing_boundary'


def test_cross_shift_with_boundary_reading_splits():
    # 边界点本身有读数：两段都不“跨越”边界
    prev = Reading(datetime(2026, 11, 18, 15, 55), 200, 190)
    mid = Reading(datetime(2026, 11, 18, 16, 0), 300, 280)
    nxt = Reading(datetime(2026, 11, 18, 16, 10), 900, 850)
    out1 = resolve_interval(prev, mid, CAP, RATE, DEFAULT_SHIFTS)
    out2 = resolve_interval(mid, nxt, CAP, RATE, DEFAULT_SHIFTS)
    assert out1['status'] == INTERVAL_CONFIRMED and out1['shift_name'] == '早班'
    assert out2['status'] == INTERVAL_CONFIRMED and out2['shift_name'] == '中班'


def test_same_timestamp_bad_interval():
    out = resolve_interval(rd(0, 100, 90), rd(0, 200, 180), CAP, RATE, DEFAULT_SHIFTS)
    assert out['status'] == INTERVAL_PENDING and out['reason_code'] == 'bad_interval'


def test_candidate_list_helpers():
    assert rollover_candidates(50, 80, 100, 1000) == [(30, 0)]
    # 倒退：产能 250 内只有 k=1(70)；k=2(170) 也在内 → 两个候选
    assert rollover_candidates(70, 40, 100, 250) == [(70, 1), (170, 2)]
    # 倒退且全部超产能 → 空
    assert rollover_candidates(70, 40, 100, 50) == []
