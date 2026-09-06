import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, resolve } from 'node:path';

const TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
};

const CONTROL_PAGES = {
  '/__gama-vitals-finalize.html': '<!doctype html><meta charset="utf-8"><title>Finalize metrics</title>',
  '/control-missing.html': `<!doctype html>
    <meta charset="utf-8"><title>Missing INP control</title>
    <main><h1>Missing input control</h1><p>No interaction is performed.</p></main>`,
  '/control-layout.html': `<!doctype html>
    <meta charset="utf-8"><title>Layout shift control</title>
    <style>body{margin:0;font:24px sans-serif}#spacer{height:0;background:#ddd}main{height:600px;padding:16px}</style>
    <div id="spacer"></div><main><h1>Layout shift control</h1><button id="control">Trusted click</button></main>
    <script>addEventListener('load',()=>setTimeout(()=>{const spacer=document.querySelector('#spacer');spacer.style.height='420px';spacer.dataset.shifted='true'},100))</script>`,
  '/control-slow.html': `<!doctype html>
    <meta charset="utf-8"><title>Slow input control</title>
    <main><h1>Slow input control</h1><button id="control">Block main thread</button><output id="done"></output></main>
    <script>document.querySelector('#control').addEventListener('click',()=>{const start=performance.now();while(performance.now()-start<260){}document.querySelector('#done').textContent='done'})</script>`,
  '/adapter-react.html': `<!doctype html>
    <meta charset="utf-8"><title>React adapter control</title>
    <nav><button type="button" onclick="location.hash='contact'">Kontakt</button></nav>
    <main><h1>React adapter</h1><section id="contact">
      <form><label>Imię i nazwisko <input name="name"></label><label>E-mail <input name="email"></label>
      <label>Telefon <input name="phone"></label><label>Wiadomość <textarea name="message"></textarea></label>
      <button type="submit">Wyślij wiadomość</button></form>
    </section></main><script>globalThis.__gamaFormSubmitted=false;document.querySelector('form').addEventListener('submit',event=>{event.preventDefault();globalThis.__gamaFormSubmitted=true})</script>`,
  '/adapter-wordpress.html': `<!doctype html>
    <meta charset="utf-8"><title>WordPress adapter control</title>
    <nav><a href="#contact">Kontakt</a></nav>
    <main><h1>WordPress adapter</h1><section id="contact">
      <form><label>Imię i nazwisko <input name="name"></label><label>E-mail <input name="email"></label>
      <label>Telefon <input name="phone"></label><label>Wiadomość <textarea name="message"></textarea></label>
      <button type="submit">Wyślij wiadomość</button></form>
    </section></main><script>globalThis.__gamaFormSubmitted=false;document.querySelector('form').addEventListener('submit',event=>{event.preventDefault();globalThis.__gamaFormSubmitted=true})</script>`,
};

export async function startStaticServer({ root, port }) {
  const staticRoot = root ? resolve(root) : null;
  const server = createServer((request, response) => {
    const pathname = new URL(request.url, `http://${request.headers.host}`).pathname;
    response.setHeader('Cache-Control', 'no-store');
    response.setHeader('X-Content-Type-Options', 'nosniff');
    if (CONTROL_PAGES[pathname]) {
      response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      response.end(CONTROL_PAGES[pathname]);
      return;
    }
    if (!staticRoot) {
      response.writeHead(404);
      response.end('Not found');
      return;
    }
    const relative = pathname === '/' ? 'index.html' : normalize(pathname).replace(/^\/+/, '');
    const path = resolve(join(staticRoot, relative));
    if (!path.startsWith(`${staticRoot}/`) || !existsSync(path) || !statSync(path).isFile()) {
      response.writeHead(404);
      response.end('Not found');
      return;
    }
    response.writeHead(200, {
      'Content-Type': TYPES[extname(path)] ?? 'application/octet-stream',
    });
    createReadStream(path).pipe(response);
  });
  await new Promise((resolveReady, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolveReady);
  });
  return {
    server,
    close: () => new Promise((resolveClose, reject) => server.close((error) => (error ? reject(error) : resolveClose()))),
  };
}
