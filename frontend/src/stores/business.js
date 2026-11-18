import {request} from '../api/client.js';

export const store = {
  data: {
    overview: {}, devices: [], readings: [], intervals: [], pending: [],
    yields: [], imports: [], audits: [], queue: {},
  },
  selectedDevice: '',
};

export async function reload() {
  const dev = store.selectedDevice ? `?device_code=${encodeURIComponent(store.selectedDevice)}` : '';
  const [overview, devices, readings, intervals, pending, yields, imports, audits, queueInfo] = await Promise.all([
    request('/overview'),
    request('/devices'),
    request('/readings' + dev),
    request('/intervals' + dev),
    request('/intervals/pending' + dev),
    request('/shift-yields' + dev),
    request('/imports'),
    request('/audits'),
    request('/queue/info'),
  ]);
  store.data = {overview, devices, readings, intervals, pending, yields, imports, audits, queue: queueInfo};
}
