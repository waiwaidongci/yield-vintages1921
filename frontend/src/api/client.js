export async function request(path, method = 'GET', data) {
  const r = await fetch('/api' + path, {
    method,
    headers: {'Content-Type': 'application/json'},
    ...(data ? {body: JSON.stringify(data)} : {}),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({detail: '请求失败'}));
    throw Error(typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail));
  }
  return r.json();
}

export async function upload(path, formData) {
  const r = await fetch('/api' + path, {method: 'POST', body: formData});
  if (!r.ok) {
    const e = await r.json().catch(() => ({detail: '上传失败'}));
    throw Error(typeof e.detail === 'string' ? e.detail : JSON.stringify(e.detail));
  }
  return r.json();
}
