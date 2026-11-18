"""导入 CSV 解析：支持中英文表头，按设备编码分组。"""
import csv
import io
import uuid
from datetime import datetime

from fastapi import HTTPException

_HEADER_ALIASES = {
    'device_code': {'device_code', '设备编码', '设备编号', '设备'},
    'read_at': {'read_at', '时点', '读数时间', '时间', 'timestamp'},
    'total_input': {'total_input', '累计投入', '投入累计', '投入读数'},
    'total_good': {'total_good', '累计合格', '合格累计', '合格读数'},
    'meter_changed': {'meter_changed', '换表', '是否换表'},
    'handover_input': {'handover_input', '交接投入', '旧表投入'},
    'handover_good': {'handover_good', '交接合格', '旧表合格'},
}


def _normalize_header(name: str) -> str:
    token = name.strip().lower()
    for key, aliases in _HEADER_ALIASES.items():
        if token in {a.lower() for a in aliases}:
            return key
    return token


def parse_csv(content: bytes, idempotency_key: str | None = None, actor: str = 'operator') -> dict:
    text = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(422, 'CSV 缺少表头')
    headers = {}
    for h in reader.fieldnames:
        canonical = _normalize_header(h)
        if canonical in _HEADER_ALIASES:
            headers[canonical] = h
    required = ('device_code', 'read_at', 'total_input', 'total_good')
    missing = [h for h in required if h not in headers]
    if missing:
        raise HTTPException(422, f'CSV 缺少必需列: {", ".join(missing)}')

    readings, seen = [], set()
    for line_no, raw in enumerate(reader, start=2):
        try:
            item = {
                'device_code': raw[headers['device_code']].strip(),
                'read_at': _parse_dt(raw[headers['read_at']].strip()),
                'total_input': int(raw[headers['total_input']]),
                'total_good': int(raw[headers['total_good']]),
                'meter_changed': _parse_bool(raw.get(headers.get('meter_changed'), '')),
                'handover_input': _parse_opt_int(raw.get(headers.get('handover_input'), '')),
                'handover_good': _parse_opt_int(raw.get(headers.get('handover_good'), '')),
            }
        except (ValueError, KeyError) as exc:
            raise HTTPException(422, f'第 {line_no} 行解析失败: {exc}') from exc
        if not item['device_code']:
            raise HTTPException(422, f'第 {line_no} 行设备编码为空')
        dedup = (item['device_code'], item['read_at'])
        if dedup in seen:
            raise HTTPException(422, f'第 {line_no} 行与同文件内读数时点重复: {dedup}')
        seen.add(dedup)
        readings.append(item)

    if not readings:
        raise HTTPException(422, 'CSV 没有有效读数行')
    return {
        'idempotency_key': idempotency_key or f'csv-{uuid.uuid4().hex[:16]}',
        'actor': actor,
        'readings': readings,
    }


def _parse_dt(value: str) -> str:
    # 统一转 ISO 字符串交给 pydantic/datetime 处理
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            continue
    raise ValueError(f'无法识别时间 "{value}"')


def _parse_bool(value) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ('1', 'true', 'yes', 'y', '是', '换表')


def _parse_opt_int(value):
    if value is None or str(value).strip() == '':
        return None
    return int(value)
