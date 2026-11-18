export const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));
export const fmt = v => typeof v === 'number'
  ? v.toLocaleString('zh-CN', {maximumFractionDigits: 4})
  : esc(v == null ? '—' : typeof v === 'object' ? JSON.stringify(v) : v);
export const time = v => v
  ? new Date(v.replace(' ', 'T')).toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', hour12: false})
  : '—';
export const pct = v => v == null ? '不计件' : v.toFixed(2) + '%';
