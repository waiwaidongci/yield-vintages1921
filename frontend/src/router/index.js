export const pages = [
  ['overview', '业务总览'],
  ['devices', '设备台账'],
  ['import', '读数导入'],
  ['yields', '班次良率'],
  ['pending', '待确认区间'],
  ['audit', '过程留痕'],
];
export const currentPage = () => location.hash.slice(1) || 'overview';
