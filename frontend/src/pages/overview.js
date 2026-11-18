import {heading} from '../components/common/header.js';
import {esc, pct} from '../utils/format.js';

export function overview(c, d) {
  const o = d.overview || {};
  const cards = [
    ['设备数', o.device_count ?? 0],
    ['累计读数', o.reading_count ?? 0],
    ['已计件区间', o.confirmed_interval_count ?? 0],
    ['待确认区间', o.pending_interval_count ?? 0],
  ];
  const queue = d.queue || {};
  return heading('WORKSHOP OVERVIEW / 01', '设备读数计件总览',
    '设备仅上报累计投入与合格数；系统按计数上限与最大产速还原相邻读数差额，待确认区间暂不计件。')
    + `<div class="overview"><div class="overview-counts">${cards.map(([k, v]) =>
      `<div class="overview-count"><b>${esc(v)}</b><p>${esc(k)}</p></div>`).join('')}</div>
      <div class="report">
        <div class="report-top"><h2>核算队列</h2></div>
        <p>队列后端：${queue.redis_configured ? 'Redis' : '内存降级（单进程）'} · 待处理任务 ${esc(queue.depth ?? 0)}</p>
        <p class="rule-note">回卷多解、缺换表交接、跨班缺边界读数的区间进入待确认，不进入班次良率分母。</p>
        <h2>班次良率速览</h2>
        <div class="table-wrap"><table><thead><tr><th>设备</th><th>日期</th><th>班次</th><th>投入</th><th>合格</th><th>良率</th><th>待确认区间</th></tr></thead><tbody>
        ${(d.yields || []).slice(0, 8).map(y => `<tr><td>${esc(y.device_code)}</td><td>${esc(y.date)}</td><td>${esc(y.shift_name)}</td>
          <td>${esc(y.input_total)}</td><td>${esc(y.good_total)}</td><td>${pct(y.yield_rate)}</td><td>${esc(y.pending_intervals)}</td></tr>`).join('')}
        </tbody></table></div>
      </div></div>`;
}
