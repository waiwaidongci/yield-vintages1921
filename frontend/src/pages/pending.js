import {heading} from '../components/common/header.js';
import {INTERVAL_STATUS, REASON_COLORS, REASON_TEXT} from '../constants/enums.js';
import {esc, pct, time} from '../utils/format.js';

export function pending(c, d) {
  const rows = d.pending || [];
  return heading('PENDING INTERVALS / 05', '待确认区间与原因',
    '回卷多解、缺换表交接、跨班缺边界、超速等区间暂不计件，补全读数后重新导入即自动重算。')
    + `<div class="report"><div class="report-top"><h2>待确认 ${esc(rows.length)} 段</h2>
        <span class="status pending">不进入班次良率</span></div>
      <div class="table-wrap"><table><thead><tr>
        <th>设备</th><th>开始</th><th>结束</th><th>原因代码</th><th>待确认原因</th><th>前读数(投/合)</th><th>后读数(投/合)</th><th>批次</th>
      </tr></thead><tbody>
      ${rows.map(x => `<tr>
        <td>${esc(x.device_code)}<br><small>${esc(x.device_name)}</small></td>
        <td>${time(x.started_at)}</td><td>${time(x.ended_at)}</td>
        <td><span class="reason-tag ${esc(REASON_COLORS[x.reason_code] || '')}">${esc(x.reason_code)}</span></td>
        <td>${esc(x.reason_text || REASON_TEXT[x.reason_code] || x.reason_code)}</td>
        <td>${esc(x.prev_input)} / ${esc(x.prev_good)}</td>
        <td>${esc(x.next_input)} / ${esc(x.next_good)}</td>
        <td>${esc(x.import_batch_id)}</td></tr>`).join('')
        || '<tr><td colspan="8" class="empty">没有待确认区间，全部相邻读数均已计件。</td></tr>'}
      </tbody></table></div>
      <h2>全部区间（含已计件）</h2>
      <div class="table-wrap"><table><thead><tr>
        <th>设备</th><th>开始</th><th>结束</th><th>状态</th><th>投入差额</th><th>合格差额</th><th>回卷次数</th><th>班次</th>
      </tr></thead><tbody>
      ${(d.intervals || []).map(x => `<tr>
        <td>${esc(x.device_code)}</td><td>${time(x.started_at)}</td><td>${time(x.ended_at)}</td>
        <td><span class="status ${esc(x.status)}">${esc(INTERVAL_STATUS[x.status] || x.status)}</span></td>
        <td>${esc(x.input_delta ?? '—')}</td><td>${esc(x.good_delta ?? '—')}</td>
        <td>${esc(x.rollovers)}</td><td>${esc(x.shift_name || '跨班/未归属')}</td></tr>`).join('')}
      </tbody></table></div></div>`;
}
