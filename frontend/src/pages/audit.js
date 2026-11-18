import {heading} from '../components/common/header.js';
import {esc, time} from '../utils/format.js';

const ACTION_TEXT = {
  'device.create': '登记设备',
  'import.accepted': '接收入队',
  'import.completed': '核算完成',
  'import.failed': '核算失败',
  'import.recovered': '中断恢复',
};

export function audit(c, d) {
  return heading('AUDIT TRAIL / 06', '过程留痕',
    '设备登记、导入批次、失败与中断恢复均记录操作者与时间，便于追溯每一次差额切换。')
    + `<div class="report"><div class="table-wrap"><table><thead><tr>
      <th>时间</th><th>操作者</th><th>动作</th><th>对象</th><th>明细</th>
    </tr></thead><tbody>
    ${(d.audits || []).map(a => `<tr>
      <td>${time(a.at)}</td><td>${esc(a.actor)}</td>
      <td><span class="reason-tag">${esc(ACTION_TEXT[a.action] || a.action)}</span></td>
      <td>${esc(a.target || '')}</td><td>${esc(a.detail || '')}</td></tr>`).join('')
      || '<tr><td colspan="5" class="empty">暂无留痕。</td></tr>'}
    </tbody></table></div></div>`;
}
