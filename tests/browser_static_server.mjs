#!/usr/bin/env node
/* Test-only hosting at the same project subpath as GitHub Pages. No API. */
import {createReadStream} from 'node:fs';
import {lstat,realpath} from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';

const root=await realpath(path.resolve(process.argv[2]||'build/web'));
const prefix='/Three-Kingdoms2-King-mainland/';
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.css':'text/css; charset=utf-8','.wasm':'application/wasm','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.webp':'image/webp','.woff2':'font/woff2','.ogg':'audio/ogg','.mp3':'audio/mpeg','.gz':'application/octet-stream','.zip':'application/zip'};
const server=http.createServer(async(req,res)=>{
 try{
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405).end();return;}
  const pathname=decodeURIComponent(new URL(req.url,'http://127.0.0.1:18917').pathname);
  if(pathname==='/favicon.ico'||pathname===prefix+'favicon.ico'){res.writeHead(204).end();return;}
  if(!pathname.startsWith(prefix)||pathname.includes('\0')){res.writeHead(404).end();return;}
  const relative=pathname.slice(prefix.length)||'index.html',target=path.resolve(root,relative);
  if(!target.startsWith(root+path.sep)){res.writeHead(404).end();return;}
  const info=await lstat(target),resolved=await realpath(target);
  if(!info.isFile()||info.isSymbolicLink()||!resolved.startsWith(root+path.sep)){res.writeHead(404).end();return;}
  res.writeHead(200,{'Content-Type':types[path.extname(target)]||'application/octet-stream','Content-Length':info.size,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
  if(req.method==='HEAD')res.end();else createReadStream(target).pipe(res);
 }catch{if(!res.headersSent)res.writeHead(404);res.end();}
});
server.listen(18917,'127.0.0.1',()=>console.log('Test-only Pages host: http://127.0.0.1:18917'+prefix));
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>server.close(()=>process.exit(0)));
