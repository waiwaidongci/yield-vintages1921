// 本地联调用静态服务器：等价于 nginx 的 try_files 与 /api/ 剥前缀代理，无第三方依赖
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const PORT = Number(process.env.FRONT_PORT || 18080);
const BACKEND = process.env.BACKEND || 'http://127.0.0.1:19099';
const TYPES = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json'};

http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) {
    const target = BACKEND + req.url.slice(4);
    const proxy = http.request(target, {method: req.method, headers: req.headers}, pr => {
      res.writeHead(pr.statusCode, pr.headers);
      pr.pipe(res);
    });
    proxy.on('error', () => res.writeHead(502).end('backend unavailable'));
    return req.pipe(proxy);
  }
  let urlPath = req.url.split('?')[0];
  let file = path.join(ROOT, urlPath === '/' ? 'index.html' : urlPath);
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(ROOT, 'index.html');
  res.writeHead(200, {'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream'});
  fs.createReadStream(file).pipe(res);
}).listen(PORT, () => console.log('frontend on', PORT));
