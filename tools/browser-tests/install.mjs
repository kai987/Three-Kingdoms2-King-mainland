#!/usr/bin/env node
/* Install the pinned full browser that channel:'chromium' actually exercises.
 * Ubuntu runners normally already provide its shared libraries. Avoid an
 * unconditional apt update/install of unrelated font packages on every run.
 */
import {access,constants} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const cli=fileURLToPath(new URL('node_modules/playwright/cli.js',import.meta.url));
function runOfficial(...args){
 const result=spawnSync(process.execPath,[cli,...args],{stdio:'inherit'});
 if(result.error)throw result.error;
 if(result.status!==0)throw new Error(`Pinned Playwright ${args.join(' ')} failed (${result.signal||result.status})`);
}

export function probeDependencies(executable,probe=spawnSync){
 const result=probe('ldd',[executable],{encoding:'utf8',timeout:30_000,maxBuffer:1024*1024});
 if(result.error)throw new Error(`Cannot verify Chromium dependencies with ldd: ${result.error.message}`);
 const output=[result.stdout||'',result.stderr||''].join('\n').trim();
 if(result.status!==0)throw new Error(`ldd could not inspect Chromium (${result.signal||result.status}):\n${output}`);
 return output.split('\n').filter(line=>/\bnot found\b/.test(line)).map(line=>line.trim());
}

export async function installBrowser(){
 // No headless-shell download: tests explicitly use the checked full Chromium.
 runOfficial('install','--no-shell','chromium');
 const executable=chromium.executablePath();
 await access(executable,constants.X_OK);
 console.log('Checking pinned full Chromium:',executable);
 if(process.platform!=='linux'){
  console.log('Official browser install completed; Linux ldd/apt probe is not applicable on',process.platform);
  return;
 }
 let missing=probeDependencies(executable);
 if(missing.length){
  console.log('Chromium shared libraries are missing:\n'+missing.join('\n'));
  runOfficial('install-deps','chromium');
  missing=probeDependencies(executable);
  if(missing.length)throw new Error('Chromium still has missing shared libraries after install-deps:\n'+missing.join('\n'));
 }
 console.log('ldd verified all shared libraries; actual Chromium acceptance remains mandatory.');
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{await installBrowser();}
 catch(error){console.error(error.stack||error.message);process.exitCode=1;}
}
