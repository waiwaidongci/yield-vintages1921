"""HTTP API 端到端：设备登记、JSON/CSV 导入、幂等、恢复、查询。"""


def _device_payload(code='API-01'):
    return {'code': code, 'name': '接口测试机', 'counter_capacity': 10000, 'max_rate_per_sec': 2}


def test_device_and_json_import_flow(client):
    r = client.post('/devices', json=_device_payload())
    assert r.status_code == 201
    assert r.json()['code'] == 'API-01'
    r = client.post('/devices', json=_device_payload())
    assert r.status_code == 409  # 编码唯一

    payload = {
        'idempotency_key': 'api-k-1',
        'device_code': 'API-01',
        'actor': 'tester',
        'readings': [
            {'read_at': '2026-11-18T08:00:00', 'total_input': 100, 'total_good': 95},
            {'read_at': '2026-11-18T09:00:00', 'total_input': 1300, 'total_good': 1240},
        ],
    }
    r = client.post('/readings/import', json=payload)
    assert r.status_code == 200 and r.json()['status'] == 'completed'

    # 同键重试：不重复入账
    client.post('/readings/import', json=payload)
    assert len(client.get('/readings').json()) == 2
    assert len(client.get('/intervals').json()) == 1

    yields = client.get('/shift-yields').json()
    assert yields[0]['yield_rate'] == round(1145 * 100 / 1200, 2)
    overview = client.get('/overview').json()
    assert overview['reading_count'] >= 2 and overview['confirmed_interval_count'] >= 1


def test_csv_import_and_pending_reasons(client):
    client.post('/devices', json=_device_payload('CSV-01'))
    csv_text = (
        '设备编码,时点,累计投入,累计合格,换表,交接投入,交接合格\n'
        'CSV-01,2026-11-18 08:00:00,100,95,0,,\n'
        'CSV-01,2026-11-18 09:00:00,1300,1240,0,,\n'
        'CSV-01,2026-11-18 09:01:00,80,70,1,,\n'          # 缺交接 -> pending
    )
    r = client.post('/readings/import-csv',
                    files={'file': ('r.csv', csv_text.encode('utf-8'), 'text/csv')},
                    data={'idempotency_key': 'csv-k-1'})
    assert r.status_code == 200
    pending = client.get('/intervals/pending').json()
    assert any(x['device_code'] == 'CSV-01' and x['reason_code'] == 'missing_handover' for x in pending)
    # 页面需要的待确认原因文案
    assert all(x['reason_text'] for x in pending)


def test_recover_endpoint_and_audits(client):
    client.post('/devices', json=_device_payload('AUD-01'))
    client.post('/readings/import', json={
        'idempotency_key': 'audit-k-1', 'device_code': 'AUD-01',
        'readings': [
            {'read_at': '2026-11-18T08:00:00', 'total_input': 100, 'total_good': 95},
            {'read_at': '2026-11-18T09:00:00', 'total_input': 1300, 'total_good': 1240},
        ],
    })
    r = client.post('/imports/recover')
    assert r.status_code == 200 and 'recovered_batch_ids' in r.json()
    audits = client.get('/audits').json()
    assert any(a['action'] == 'import.completed' for a in audits)


def test_health_and_meta(client):
    assert client.get('/health').json()['status'] == 'healthy'
    assert client.get('/meta').json()['title']
