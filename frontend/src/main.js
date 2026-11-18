import {request, upload} from './api/client.js';
import {store, reload} from './stores/business.js';
import {pages, currentPage} from './router/index.js';
import {esc} from './utils/format.js';
import {action} from './hooks/action.js';
import {overview} from './pages/overview.js';
import {devices} from './pages/devices.js';
import {importPage} from './pages/import.js';
import {yields} from './pages/yields.js';
import {pending} from './pages/pending.js';
import {audit} from './pages/audit.js';

const c = await (await fetch('/project.json')).json();
const app = document.querySelector('#app');
const renderers = {overview, devices, import: importPage, yields, pending, audit};
let timer = null;

function render() {
  const page = currentPage();
  app.innerHTML = `<div class="shell"><aside class="sidebar">
    <a href="#overview" class="brand">${esc(c.title.slice(0, 2))}<small>设备累计读数<br>差额还原计件</small></a>
    <nav>${pages.map(([id, title], i) =>
      `<a class="${page === id ? 'active' : ''}" href="#${id}"><span>0${i + 1}</span>${esc(title)}</a>`).join('')}</nav>
    <footer>砚泉车间计件台<br><b>只读/录入一体化</b><br><button id="refresh">刷新数据</button></footer>
  </aside><main class="workspace">
    <div class="topline"><span>${esc(c.title)}</span><span id="queue-pill"></span></div>
    <div id="notice" role="status"></div>
    ${(renderers[page] || overview)(c, store.data)}
  </main></div>`;
  bind();
}

function notice(msg, isError) {
  const box = document.querySelector('#notice');
  box.textContent = msg;
  box.classList.toggle('error', !!isError);
}

function bind() {
  document.querySelector('#refresh').onclick = () => action(async () => { await reload(); render(); });
  const pill = document.querySelector('#queue-pill');
  if (pill) pill.textContent = `队列待处理 ${store.data.queue?.depth ?? 0}`;

  const select = document.querySelector('#device-select');
  if (select) {
    select.value = store.selectedDevice;
    select.onchange = () => action(async () => { store.selectedDevice = select.value; await reload(); render(); });
  }
  const recover = document.querySelector('#recover-btn');
  if (recover) recover.onclick = () => action(async () => {
    const r = await request('/imports/recover', 'POST', {});
    await reload(); render();
    notice(`已恢复批次：${r.recovered_batch_ids.join(', ') || '无中断批次'}`);
  });

  const df = document.querySelector('#device-form');
  if (df) df.onsubmit = e => {
    e.preventDefault();
    action(async () => {
      const b = Object.fromEntries(new FormData(df));
      await request('/devices', 'POST', {
        code: b.code.trim(), name: b.name.trim(),
        counter_capacity: Number(b.counter_capacity),
        max_rate_per_sec: Number(b.max_rate_per_sec),
      });
      await reload(); render();
    });
  };

  const df2 = document.querySelector('#import-json-form');
  const fillKey = document.querySelector('#fill-key');
  if (fillKey) fillKey.onclick = () => {
    df2.idempotency_key.value = 'ui-' + crypto.randomUUID().slice(0, 12);
  };
  if (df2) df2.onsubmit = e => {
    e.preventDefault();
    action(async () => {
      const b = Object.fromEntries(new FormData(df2));
      const reading = {
        read_at: b.read_at.length === 16 ? b.read_at + ':00' : b.read_at,
        total_input: Number(b.total_input),
        total_good: Number(b.total_good),
        meter_changed: !!b.meter_changed,
        handover_input: b.handover_input === '' ? null : Number(b.handover_input),
        handover_good: b.handover_good === '' ? null : Number(b.handover_good),
      };
      const payload = {
        idempotency_key: b.idempotency_key.trim(),
        device_code: b.device_code.trim(),
        readings: [reading],
      };
      const r = await request(`/readings/import?async_mode=${!!b.async_mode}`, 'POST', payload);
      await reload(); render();
      notice(`批次 #${r.id} 状态：${r.status === 'completed' ? '已完成并切换' : '已入队'}`);
    });
  };

  const cf = document.querySelector('#import-csv-form');
  if (cf) cf.onsubmit = e => {
    e.preventDefault();
    action(async () => {
      const fd = new FormData(cf);
      const asyncMode = fd.get('async_mode');
      fd.delete('async_mode');
      const r = await upload(`/readings/import-csv?async_mode=${!!asyncMode}`, fd);
      await reload(); render();
      notice(`CSV 批次 #${r.id} 状态：${r.status === 'completed' ? '已完成并切换' : '已入队'}`);
    });
  };
}

window.addEventListener('hashchange', render);
await reload();
render();
// 轮询：存在核算中批次或队列任务时自动刷新
timer = setInterval(async () => {
  const busy = (store.data.imports || []).some(b => b.status === 'processing') || (store.data.queue?.depth ?? 0) > 0;
  if (busy) { try { await reload(); render(); } catch { /* 忽略瞬时失败 */ } }
}, 2500);
