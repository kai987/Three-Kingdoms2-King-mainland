import { build } from 'esbuild';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here=dirname(fileURLToPath(import.meta.url));
const target=resolve(here,'../../game/vendor');
const lockBytes=await readFile(resolve(here,'package-lock.json'));
const lock=JSON.parse(lockBytes);
const result=await build({absWorkingDir:here,entryPoints:['entry.js'],bundle:true,
  format:'iife',globalName:'GameSupabase',platform:'browser',target:'es2020',
  minify:true,legalComments:'eof',write:false,logLevel:'warning'});
const bundle=result.outputFiles[0].contents;
const sha=data=>createHash('sha256').update(data).digest('hex');
let licenses='Self-hosted Supabase browser SDK. Rebuild: npm ci --prefix tools/cloud-sdk --ignore-scripts && npm run build --prefix tools/cloud-sdk\n';
const packages={};
for(const [path,record] of Object.entries(lock.packages).sort(([a],[b])=>a.localeCompare(b,'en'))){
  if(!path||record.dev||record.optional)continue;
  const name=path.replace(/^node_modules\//,'');
  packages[name]=record.version;
  let source;
  for(const name of ['LICENSE','LICENSE.md','LICENSE.txt']){
    try{source=await readFile(resolve(here,path,name),'utf8');break;}catch(error){if(error.code!=='ENOENT')throw error;}
  }
  if(!source)throw new Error('Missing license: '+name);
  licenses+='\n\n=== '+name+' '+record.version+' ('+record.license+') ===\n'+source.trim()+'\n';
}
const manifest=JSON.stringify({schema:'tk2-self-hosted-cloud-sdk-v1',
  supabase_js:lock.packages['node_modules/@supabase/supabase-js'].version,
  esbuild:lock.packages['node_modules/esbuild'].version,lock_sha256:sha(lockBytes),
  bundle_sha256:sha(bundle),bundle_bytes:bundle.length,packages},null,2)+'\n';
const outputs={'supabase.min.js':bundle,'supabase-LICENSES.txt':licenses,'supabase-manifest.json':manifest};
await mkdir(target,{recursive:true});
for(const [name,content] of Object.entries(outputs)){
  const path=resolve(target,name),bytes=typeof content==='string'?Buffer.from(content):content;
  if(process.argv.includes('--check')){
    const existing=await readFile(path);
    if(!Buffer.from(bytes).equals(existing))throw new Error('Vendor output changed: '+name);
  }else await writeFile(path,bytes);
}
console.log('Supabase '+lock.packages['node_modules/@supabase/supabase-js'].version+' browser bundle: '+bundle.length+' bytes; '+(process.argv.includes('--check')?'verified':'built'));
