import {heading} from '../components/common/header.js';
import {esc, pct} from '../utils/format.js';

export function yields(c, d) {
  const rows = d.yields || [];
  return heading('SHIFT YIELD / 04', '班次良率',
    '良率 = 已计件合格差额合计 ÷ 已计件投入差额合计（按设备 × 日历日 × 班次）；待确认区间不计入分子分母。')
    + `<div class="report"><div class="report-top"><h2>班次良率 ${esc(rows.length)} 组</h2></div>
      <div class="table-wrap"><table><thead><tr>
        <th>设备编码</th><th>设备名称</th><th>日期</th><th>班次</th><th>投入合计</th><th>合格合计</th>
        <th>班次良率</th><th>已计件区间</th><th>待确认区间</th>
      </tr></thead><tbody>
      ${rows.map(y => `<tr class="${y.yield_rate == null ? 'row-pending' : ''}">
        <td>${esc(y.device_code)}</td><td>${esc(y.device_name)}</td><td>${esc(y.date)}</td>
        <td>${esc(y.shift_name)}</td><td>${esc(y.input_total)}</td><td>${esc(y.good_total)}</td>
        <td><b>${pct(y.yield_rate)}</b></td>
        <td>${esc(y.confirmed_intervals)}</td><td>${esc(y.pending_intervals)}</td></tr>`).join('')
        || '<tr><td colspan="9" class="empty">尚无核算结果。</td></tr>'}
      </tbody></table></div>
      <p class="rule-note">口径：只统计 confirmed 区间；pending 区间在“待确认区间”页列明原因，补读重算后一次性切换。</p>
      </div>`;
}
