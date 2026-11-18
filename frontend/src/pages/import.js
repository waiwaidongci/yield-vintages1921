import {heading} from '../components/common/header.js';
import {BATCH_STATUS} from '../constants/enums.js';
import {store} from '../stores/business.js';
import {esc, time} from '../utils/format.js';

export function importPage(c, d) {
  const options = (d.devices || []).map(x =>
    `<option value="${esc(x.code)}"${store.selectedDevice === x.code ? ' selected' : ''}>${esc(x.code)} ${esc(x.name)}</option>`).join('');
  return heading('METER IMPORT / 03', '带时点设备读数导入',
    '只上报累计投入与累计合格。同批补读以幂等键去重，重试不重复入账；并发补读只重算受影响的前后区间。')
    + `<div class="report">
      <div class="inline-form">
        <label>选择设备<select id="device-select">${'<option value="">全部设备</option>' + options}</select></label>
        <button id="recover-btn" type="button">恢复中断批次</button>
        <span class="rule-note" id="queue-hint">队列：${esc((d.queue || {}).redis_configured ? 'Redis' : '内存降级')} · 待处理 ${esc((d.queue || {}).depth ?? 0)}</span>
      </div>

      <details open><summary>单条 / 批量 JSON 录入</summary>
        <form id="import-json-form">
          <div class="form-grid">
            <label>设备编码<input name="device_code" required list="device-codes" placeholder="选择或输入设备编码">
              <datalist id="device-codes">${(d.devices || []).map(x => `<option value="${esc(x.code)}">`).join('')}</datalist></label>
            <label>幂等键（同批补读保持不变）<input name="idempotency_key" required></label>
            <label class="weekday"><input name="async_mode" type="checkbox"> 异步排队（worker 消费）</label>
            <label>读数时点<input name="read_at" type="datetime-local" step="1" required></label>
            <label>累计投入<input name="total_input" type="number" min="0" required></label>
            <label>累计合格<input name="total_good" type="number" min="0" required></label>
            <label class="weekday"><input name="meter_changed" type="checkbox"> 换表后首读数</label>
            <label>旧表交接投入（换表必填）<input name="handover_input" type="number" min="0"></label>
            <label>旧表交接合格（换表必填）<input name="handover_good" type="number" min="0"></label>
          </div>
          <button type="submit">提交读数</button>
          <button type="button" id="fill-key">生成幂等键</button>
        </form>
      </details>

      <details><summary>CSV 文件导入（表头支持中文）</summary>
        <form id="import-csv-form">
          <div class="form-grid">
            <label>CSV 文件<input type="file" name="file" accept=".csv" required></label>
            <label>幂等键（留空自动生成）<input name="idempotency_key"></label>
            <label class="weekday"><input name="async_mode" type="checkbox"> 异步排队</label>
          </div>
          <p class="rule-note">列：设备编码、时点、累计投入、累计合格、换表(是/否)、交接投入、交接合格。时点支持 2026-11-18 08:00:00。</p>
          <button type="submit">上传并核算</button>
        </form>
      </details>

      <h2>最近导入批次</h2>
      <div class="table-wrap"><table><thead><tr>
        <th>#</th><th>幂等键</th><th>读数</th><th>设备数</th><th>状态</th><th>异步</th><th>错误</th><th>创建</th><th>完成</th>
      </tr></thead><tbody>
      ${(d.imports || []).slice(0, 15).map(b => `<tr class="batch-${esc(b.status)}">
        <td>${esc(b.id)}</td><td>${esc(b.idempotency_key)}</td><td>${esc(b.reading_count)}</td>
        <td>${esc(b.device_count)}</td><td><span class="status ${esc(b.status)}">${esc(BATCH_STATUS[b.status] || b.status)}</span></td>
        <td>${b.async_mode ? '是' : '否'}</td><td>${esc(b.error || '')}</td>
        <td>${time(b.created_at)}</td><td>${time(b.finished_at)}</td></tr>`).join('') || '<tr><td colspan="9" class="empty">尚无导入批次</td></tr>'}
      </tbody></table></div>

      <h2>设备读数明细</h2>
      <div class="table-wrap"><table><thead><tr>
        <th>设备</th><th>时点</th><th>累计投入</th><th>累计合格</th><th>换表</th><th>交接投入</th><th>交接合格</th><th>批次</th>
      </tr></thead><tbody>
      ${(d.readings || []).map(r => `<tr><td>${esc(r.device_code)}</td><td>${time(r.read_at)}</td>
        <td>${esc(r.total_input)}</td><td>${esc(r.total_good)}</td>
        <td>${r.meter_changed ? '是' : '否'}</td><td>${esc(r.handover_input ?? '')}</td><td>${esc(r.handover_good ?? '')}</td>
        <td>${esc(r.import_batch_id)}</td></tr>`).join('') || '<tr><td colspan="8" class="empty">暂无读数</td></tr>'}
      </tbody></table></div>
    </div>`;
}
