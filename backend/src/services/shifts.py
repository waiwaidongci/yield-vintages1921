"""班次窗口与跨班边界判定（Asia/Shanghai 朴素时间）。"""
from datetime import datetime, timedelta


def _parse_hm(value: str) -> int:
    hour, minute = value.split(':')
    return int(hour) * 60 + int(minute)


def _window_on_day(shift: dict, day: datetime):
    start_min = _parse_hm(shift['start'])
    end_min = _parse_hm(shift['end'])
    start = day.replace(hour=start_min // 60, minute=start_min % 60, second=0, microsecond=0)
    # end <= start 视为跨午夜班次（如 16:00-00:00、00:00-08:00 的衔接由相邻日窗口覆盖）
    end_day = start if end_min > start_min else start + timedelta(days=1)
    end = end_day.replace(hour=end_min // 60, minute=end_min % 60, second=0, microsecond=0)
    return start, end, shift['name']


def build_windows(shifts: list[dict], day: datetime):
    return [_window_on_day(sh, day) for sh in shifts]


def _all_windows(shifts: list[dict], around: datetime):
    base = around.replace(hour=0, minute=0, second=0, microsecond=0)
    windows = []
    for offset in (-1, 0, 1):
        windows.extend(build_windows(shifts, base + timedelta(days=offset)))
    return windows


def shift_at(shifts: list[dict], t: datetime):
    """时刻 t 所属班次名；班次定义未覆盖时返回 None。"""
    for start, end, name in _all_windows(shifts, t):
        if start <= t < end:
            return name
    return None


def crosses_shift_boundary(shifts: list[dict], started_at: datetime, ended_at: datetime) -> bool:
    """区间内部是否存在班次边界时刻（边界恰好落在端点不算跨越）。"""
    boundaries = set()
    for start, end, _name in _all_windows(shifts, started_at):
        boundaries.add(start)
        boundaries.add(end)
    return any(started_at < bnd < ended_at for bnd in boundaries)
