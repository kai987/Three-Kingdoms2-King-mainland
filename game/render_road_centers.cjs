#!/usr/bin/env node
'use strict';
// Repaint reviewed road corridors once at native resolution. No campaign, RNG,
// save, historical development page or network input is read by this compiler.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name));
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const json = name => JSON.parse(read(name));
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;');
const data = name => 'data:image/png;base64,' + read(name).toString('base64');

async function main() {
  const source = json('game/config/road-centers.json');
  const shared = json('game/config/campaigns/shared.json');
  const presentation = json('game/config/map-source.json').presentation;
  const positions = Object.fromEntries(shared.catalog.cities.map(city => [city.id, city.position]));
  const baseline = 'game/assets/map-navigation.png', ground = 'game/map-source/road-ground.png';
  if (sha(read(baseline)) !== source.provenance.baseline_navigation_sha256 || sha(read(ground)) !== source.ground.sha256)
    throw Error('Approved terrain or navigation source hash differs');
  const geometry = JSON.parse(execFileSync('python3', ['-B', '-c',
    "import json,sys;sys.path.insert(0,'game');from road_centers import build;s=json.load(open('game/config/road-centers.json'));c=json.load(open('game/config/campaigns/shared.json'));print(json.dumps(build(s,{v['id']:v['position'] for v in c['catalog']['cities']})))"
  ], {cwd: root, encoding: 'utf8'}));
  // Preserve the opaque native castle pixels; a rectangular exclusion would
  // retain the old fork in transparent corners of the 32 x 32 castle sprite.
  const pixels = [...presentation.castle_fill_pixels, ...presentation.castle_outline_pixels];
  const castles = Object.values(positions).flatMap(([cx, cy]) => pixels.map(([x, y]) =>
    `<rect x="${cx+x}" y="${cy+y}" width="4" height="4" fill="black"/>`)).join('');
  const maskPath = escape(geometry.mask_d), paintPath = escape(geometry.paint_d);
  const crossings = geometry.crossings.map(c => `<path d="${escape(c.d)}" stroke="${escape(c.stroke)}" stroke-width="${c.width}"/>`).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1352" height="1024" viewBox="0 0 1352 1024">
    <defs>
      <mask id="repair" maskUnits="userSpaceOnUse" x="0" y="0" width="1352" height="1024">
        <path d="${maskPath}" stroke="white" stroke-width="6.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        <g shape-rendering="crispEdges">${castles}</g>
      </mask>
      <mask id="road-crossings" maskUnits="userSpaceOnUse" x="0" y="0" width="1352" height="1024">
        <path d="${paintPath}" stroke="white" stroke-width="5.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </mask>
    </defs>
    <image href="${data(baseline)}" width="1352" height="1024"/>
    <g mask="url(#repair)">
      <image href="${data(ground)}" width="1352" height="1024"/>
      <g fill="none" stroke-linecap="round" stroke-linejoin="round" shape-rendering="geometricPrecision">
        <path d="${paintPath}" stroke="#e4b45e" stroke-width="4.1"/>
        <path d="${paintPath}" stroke="#704518" stroke-width="1.9"/>
        <g mask="url(#road-crossings)">${crossings}</g>
      </g>
    </g>
  </svg>`;
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    const page = await browser.newPage({viewport: {width:1352, height:1024}, deviceScaleFactor:1});
    await page.setContent('<html><style>html,body{margin:0;padding:0;overflow:hidden}svg{display:block}</style><body>'+svg+'</body></html>');
    await page.evaluate(async () => Promise.all([...document.images].map(i => i.decode())));
    // Embedded SVG images are not in document.images. Wait for the SVG itself
    // to decode before the native-resolution screenshot.
    await page.evaluate(async () => {const img = new Image(); img.src = 'data:image/svg+xml;base64,' + btoa(new XMLSerializer().serializeToString(document.querySelector('svg'))); await img.decode();});
    await page.screenshot({path:path.join(root, 'game/assets/map-road-centers.png')});
  } finally { await browser.close(); }
  const canonicalPositions = execFileSync('python3', ['-B', '-c',
    "import json; c=json.load(open('game/config/campaigns/shared.json'));print(json.dumps({v['id']:v['position'] for v in c['catalog']['cities']},sort_keys=True,separators=(',',':'),ensure_ascii=False),end='')"
  ], {cwd:root});
  const manifest = {
    schema:'tk2-road-center-render-v1', source_sha256:sha(read('game/config/road-centers.json')),
    positions_sha256:sha(canonicalPositions), baseline_sha256:sha(read(baseline)),
    ground_sha256:sha(read(ground)), output_sha256:sha(read('game/assets/map-road-centers.png'))
  };
  fs.writeFileSync(path.join(root, 'game/map-source/road-centers-render.json'), JSON.stringify(manifest, null, 2)+'\n');
  console.log(JSON.stringify({output:'game/assets/map-road-centers.png', changed_segments:geometry.changes.length, ...manifest}, null, 2));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
