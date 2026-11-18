"""共享枚举与待确认原因口径。"""

# 导入批次状态：processing 可被启动恢复接管，completed 幂等重试直接返回
BATCH_PROCESSING = 'processing'
BATCH_COMPLETED = 'completed'
BATCH_FAILED = 'failed'
BATCH_STATUSES = (BATCH_PROCESSING, BATCH_COMPLETED, BATCH_FAILED)

# 区间状态：confirmed 计入班次良率；pending 暂不计件并登记原因
INTERVAL_CONFIRMED = 'confirmed'
INTERVAL_PENDING = 'pending'
INTERVAL_STATUSES = (INTERVAL_CONFIRMED, INTERVAL_PENDING)

# 待确认原因代码 -> 页面文案
REASONS = {
    'rewind_ambiguous': '回卷存在多个差额解，无法唯一还原',
    'rate_exceeded': '区间还原产量超过设备最大产速×时长',
    'missing_handover': '换表读数缺少旧表交接值，区间无法计件',
    'missing_boundary': '区间跨越班次边界且边界时刻缺读数',
    'bad_interval': '读数异常（同刻多值、合格大于投入或交接值非法）',
}

DEFAULT_SHIFTS = [
    {'name': '早班', 'start': '08:00', 'end': '16:00'},
    {'name': '中班', 'start': '16:00', 'end': '00:00'},
    {'name': '晚班', 'start': '00:00', 'end': '08:00'},
]
