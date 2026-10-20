// Use REA's public MCP operations in one persistent, local Ghidra session.
import { Client } from '../tools/rea/node_modules/@modelcontextprotocol/client/dist/index.mjs';
import { StdioClientTransport } from '../tools/rea/node_modules/@modelcontextprotocol/client/dist/stdio.mjs';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import assert from 'node:assert/strict';

const root = fileURLToPath(new URL('..', import.meta.url));
const out = resolve(root, 'analysis/rea/mcp');
await mkdir(resolve(out, 'functions'), { recursive: true });
const client = new Client({ name: 'nes-6502-investigation', version: '1' });
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [resolve(root, 'tools/rea/scripts/rea.mjs'), 'mcp'],
  env: {
    PATH: process.env.PATH ?? '/usr/bin:/bin',
    REA_LOG_LEVEL: 'silent',
    GHIDRA_INSTALL_DIR: resolve(root, '.toolchain/ghidra_12.1.4_PUBLIC'),
    REA_GHIDRA_SEED_FILE: resolve(root, 'analysis/rea/fixed-bank-seeds.tsv'),
    ...(process.env.JAVA_HOME ? { JAVA_HOME: process.env.JAVA_HOME } : {}),
  },
  stderr: 'pipe',
});
let errors = '', opened = false;
transport.stderr?.on('data', (x) => { errors += x.toString(); });

async function call(name, args = {}, basename = name) {
  const result = await client.callTool({ name, arguments: args }, { timeout: 330000 });
  await writeFile(resolve(out, basename + '.json'), JSON.stringify(result, null, 2) + '\n');
  if (result.isError) throw new Error(name + ': ' + JSON.stringify(result));
  const data = result.structuredContent ?? JSON.parse(result.content.find(x => x.type === 'text').text);
  return data.normalized_result ?? data.result ?? data;
}

try {
  await client.connect(transport);
  const catalog = await client.listTools();
  await writeFile(resolve(out, 'catalog.json'), JSON.stringify(catalog, null, 2) + '\n');
  await call('open_binary', {
    path: resolve(root, 'analysis/rom/prg-banks/bank-31.bin'), format: 'raw-binary',
    architecture: '6502', entry_point: '0xe000', provider_id: 'ghidra',
  });
  opened = true;
  const image = await call('inspect_native_load_image');
  assert.equal(image.status, 'verified', JSON.stringify(image));
  console.log('REA verified the complete fixed-bank load image.');
  const procedures = await call('list_procedures');
  const index = [];
  let combined = '// Ghidra-generated 6502 pseudocode. Not original source or compilable game code.\n';
  for (const p of procedures) {
    const address = p.address;
    const id = address.replace(/[^a-zA-Z0-9_-]/g, '_');
    const info = await call('procedure_info', { procedure: address }, 'functions/' + id + '-info');
    const assembly = await call('procedure_assembly', { procedure: address }, 'functions/' + id + '-assembly');
    const pseudocode = await call('procedure_pseudo_code', { procedure: address }, 'functions/' + id + '-pseudocode');
    index.push({ address, name: p.value, info, has_pseudocode: pseudocode !== null });
    await writeFile(resolve(out, 'functions/' + id + '.asm'), typeof assembly === 'string' ? assembly : JSON.stringify(assembly, null, 2));
    await writeFile(resolve(out, 'functions/' + id + '.c'), typeof pseudocode === 'string' ? pseudocode : JSON.stringify(pseudocode, null, 2));
    combined += '\n/* ' + address + ' ' + p.value + ' */\n' + (typeof pseudocode === 'string' ? pseudocode : JSON.stringify(pseudocode)) + '\n';
  }
  await writeFile(resolve(out, 'procedure-index.json'), JSON.stringify(index, null, 2) + '\n');
  await writeFile(resolve(out, 'fixed-bank-pseudocode.c'), combined);
  await call('export_evidence_bundle', { path: resolve(out, 'evidence-bundle.json'), overwrite: true });
  await call('close_binary', { snapshot_path: resolve(out, 'snapshot.json'), overwrite: true });
  opened = false;
  console.log('Exported ' + index.length + ' analyzed procedures, assembly, pseudocode, and REA Evidence.');
} finally {
  if (opened) {
    try { await client.callTool({ name: 'close_binary', arguments: {} }, { timeout: 60000 }); }
    catch (e) { errors += '\n' + String(e); }
  }
  await client.close();
  await writeFile(resolve(out, 'stderr.log'), errors);
}
