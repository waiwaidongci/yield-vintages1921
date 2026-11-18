export const BATCH_STATUS = {processing: '核算中', completed: '已完成', failed: '失败'};
export const INTERVAL_STATUS = {confirmed: '已计件', pending: '待确认'};
export const REASON_TEXT = {
  rewind_ambiguous: '回卷存在多个差额解，无法唯一还原',
  rate_exceeded: '区间还原产量超过设备最大产速×时长',
  missing_handover: '换表读数缺少旧表交接值，区间无法计件',
  missing_boundary: '区间跨越班次边界且边界时刻缺读数',
  bad_interval: '读数异常（同刻多值、合格大于投入或交接值非法）',
};
export const REASON_COLORS = {
  rewind_ambiguous: 'reason-ambiguous',
  rate_exceeded: 'reason-rate',
  missing_handover: 'reason-handover',
  missing_boundary: 'reason-boundary',
  bad_interval: 'reason-bad',
};
