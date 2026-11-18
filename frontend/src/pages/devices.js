import {heading} from '../components/common/header.js';
import {esc, time} from '../utils/format.js';

export function devices(c, d) {
  return heading('DEVICE LEDGER / 02', '设备台账',
    '每台设备登记计数上限（回卷/换表基准）与最大产速（件/秒），班次窗口用于跨班缺边界判定。')
    + `<div class="report">
      <div class="report-top"><h2>已登记设备 ${esc((d.devices || []).length)}</h2></div>
      <div class="table-wrap"><table><thead><tr>
        <th>设备编码</th><th>名称</th><th>计数上限</th><th>最大产速(件/秒)</th><th>班次</th><th>登记时间</th>
      </tr></thead><tbody>
      ${(d.devices || []).map(x => `<tr><td>${esc(x.code)}</td><td>${esc(x.name)}</td>
        <td>${esc(x.counter_capacity)}</td><td>${esc(x.max_rate_per_sec)}</td>
        <td>${(x.shifts || []).map(s => esc(`${s.name} ${s.start}-${s.end}`)).join('；')}</td>
        <td>${time(x.created_at)}</td></tr>`).join('') || '<tr><td colspan="6" class="empty">尚无设备</td></tr>'}
      </tbody></table></div>
      <details open><summary>登记新设备</summary>
        <form id="device-form" class="form-grid">
          <label>设备编码<input name="code" required placeholder="如 CNT-03"></label>
          <label>设备名称<input name="name" required placeholder="如 冲压三号机"></label>
          <label>计数上限<input name="counter_capacity" type="number" min="1" required placeholder="如 10000"></label>
          <label>最大产速（件/秒）<input name="max_rate_per_sec" type="number" min="1" required placeholder="如 2"></label>
          <div style="grid-column:1/-1"><button type="submit">登记设备</button></div>
        </form>
        <p class="rule-note">班次默认 早班08:00-16:00 / 中班16:00-24:00 / 晚班00:00-08:00，可后续扩展为按设备配置。</p>
      </details></div>`;
}
