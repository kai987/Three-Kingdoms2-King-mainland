#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { decodePng, encodePng } = require('./prepare_enhanced.cjs');
const eyeRegions = require('./white-eye-regions.json');
const inkRepairs = require('./white-ink-repairs.json');
const individualRedraws = require('./white-individual-redraws.json');

const root = path.resolve(__dirname, '../..');
const directory = path.join(root, 'game/assets/portraits/white');
const manifestPath = path.join(root, 'game/config/portrait-white.json');
const approved = new Set([
  'san14-candidate-0042', // 王允
  'san14-candidate-0123', // 夏侯德
  'san14-candidate-0223', // 金旋
  'san14-candidate-0304', // 顧譚
]);
const targetedRedraws = new Set([
  ...Object.keys(individualRedraws),
  'san14-candidate-0041', // 王異
  'san14-candidate-0406', // 鍾會
  'san14-candidate-0440', // 諸葛亮
  'san14-candidate-0449', // 徐盛
  'san14-candidate-0463', // 申耽
  'san14-candidate-0521', // 曹操
  'san14-candidate-0565', // 孫尚香
  'san14-candidate-0596', // 趙雲
  'san14-candidate-0640', // 貂蟬
  'san14-candidate-0962', // 劉曄
  'historical-lu-xing',
  'historical-li-wenhou',
  'historical-xiahou-bo',
  'historical-xue-yong',
  'historical-yuan-chen',
  'historical-liu-yan-shu',
  'historical-gongsun-heng',
  'historical-sun-xiang',
  'historical-expansion-0001',
  'historical-expansion-0002',
  'historical-expansion-0003',
  'historical-expansion-0004',
  'historical-expansion-0008',
  'historical-expansion-0014',
  'san14-candidate-0024',
  'san14-candidate-0026',
  'san14-candidate-0027',
  'san14-candidate-0099',
  'san14-candidate-0116',
  'san14-candidate-0120',
  'san14-candidate-0141',
  'san14-candidate-0170',
  'san14-candidate-0174',
  'san14-candidate-0213',
  'san14-candidate-0372',
  'san14-candidate-0385',
  'san14-candidate-0477',
  'san14-candidate-0546',
  'san14-candidate-0556',
  'san14-candidate-0562',
  'san14-candidate-0673',
  'san14-candidate-0772',
  'san14-candidate-0826',
  'san14-candidate-0857',
  'san14-candidate-0909',
  'san14-candidate-0911',
  'san14-candidate-0993',
]);
const width = 512;
const height = 640;
const scale = 4;
const white = 0xffffffff;
const black = 0x000000ff;
const atlasPalette = [
  black, white, 0xe2e2deff, 0xbcbdb9ff, 0xf8f0dcff, 0xffda80ff, 0xffbb59ff,
  0xf7a247ff, 0xdf7922ff, 0xc66312ff, 0xb9550aff, 0x9e4100ff, 0x8e3800ff, 0x6c2e07ff,
];
const batchSize = 128;
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

function paletteGroup(pixel) {
  if (pixel === black) return 0;
  const r = pixel >>> 24;
  const g = (pixel >>> 16) & 255;
  const b = (pixel >>> 8) & 255;
  return Math.max(r, g, b) - Math.min(r, g, b) < 15 ? 1 : 2;
}

function isPaper(pixel) {
  return ((pixel >>> 8) & 255) >= 208 && paletteGroup(pixel) === 1;
}

// In the original black display both alpha-zero and opaque black can represent
// background or ink. Build the outside edge from the visible colored shapes.
// Treating opaque black as a different material produces stripes on some art.
function scanPortrait(source, w, h) {
  const rows = [];
  for (let y = 0; y < h; y++) {
    let left = w;
    let right = -1;
    let leftPaper = 0;
    let rightPaper = 0;
    for (let x = 0; x < w; x++) {
      const pixel = source[y * w + x];
      if (!(pixel & 255) || pixel === black) continue;
      left = Math.min(x, left);
      right = x;
      if (isPaper(pixel)) {
        if (x < w * .23) leftPaper++;
        if (x >= w * .77) rightPaper++;
      }
    }
    rows.push({ left, right, leftPaper, rightPaper });
  }
  return rows;
}

function containsWhiteMatte(rows, w, h, top) {
  const field = rows.slice(Math.max(top + Math.round(h * .065), Math.round(h * .07)), Math.round(h * .67));
  const crown = rows.slice(top, top + Math.round(h * .11));
  const hasSidePaper = row => row.leftPaper >= w * .09 && row.rightPaper >= w * .09;
  const sidePaperRows = field.filter(hasSidePaper).length;
  const upperPaperRows = crown.filter(hasSidePaper).length;
  return sidePaperRows >= field.length * .41 ||
    (sidePaperRows >= field.length * .24 && upperPaperRows >= crown.length * .45);
}

function applyWhiteMatte(source, w, h) {
  const rows = scanPortrait(source, w, h);
  const top = rows.findIndex(row => row.right >= 0);
  const bottom = rows.findLastIndex(row => row.right >= 0);
  if (top < 0) throw new Error('Portrait has no visible detail');
  const paper = containsWhiteMatte(rows, w, h, top);
  const rim = paper ? 0 : Math.max(1, Math.round(w / 64));
  const look = Math.round(w / 64);
  const reach = Math.round(w * 1.5 / 128);
  const edges = rows.map(({ left, right }) => [left, right]);
  for (let y = top + 1; y < bottom; y++) {
    if (rows[y].right >= 0) continue;
    // A blank band inside a hat or collar is black in the source display.
    let next = y + 1;
    while (rows[next].right < 0) next++;
    edges[y] = edges[y - 1].map((edge, side) =>
      Math.round(edge + (edges[next][side] - edge) / (next - y + 1)));
  }
  const silhouette = paper ? edges : closeInkGaps(edges, w, top, bottom);
  const result = new Uint32Array(source.length);
  for (let y = 0; y < h; y++) {
    const row = Math.max(top, Math.min(bottom, y));
    const [originalLeft, originalRight] = silhouette[row];
    let left = originalLeft;
    let right = originalRight;
    if (rim) {
      for (const nearby of [Math.max(top, row - look), Math.min(bottom, row + look)]) {
        left = Math.max(originalLeft - reach, Math.min(left, edges[nearby][0]));
        right = Math.min(originalRight + reach, Math.max(right, edges[nearby][1]));
      }
    }
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const pixel = source[i];
      if ((pixel & 255) && pixel !== black) result[i] = pixel;
      else if (y >= top - rim && y <= bottom && x >= left - rim && x <= right + rim) result[i] = black;
      else result[i] = white;
    }
  }
  return result;
}

function closeInkGaps(edges, w, top, bottom) {
  const depth = Math.max(3, Math.round(w * .065));
  const maximum = Math.round(w * .12);
  return edges.map(([left, right], y) => {
    if (y <= top || y >= bottom) return [left, right];
    let aboveLeft = left, belowLeft = left, aboveRight = right, belowRight = right;
    for (let step = 1; step <= depth; step++) {
      const inset = Math.round(step * .28);
      if (y - step >= top) {
        aboveLeft = Math.min(aboveLeft, edges[y - step][0] + inset);
        aboveRight = Math.max(aboveRight, edges[y - step][1] - inset);
      }
      if (y + step <= bottom) {
        belowLeft = Math.min(belowLeft, edges[y + step][0] + inset);
        belowRight = Math.max(belowRight, edges[y + step][1] - inset);
      }
    }
    // A dark notch between two visible stretches is part of the outline.
    // Require evidence on both sides of the row to keep open side gaps open.
    return [Math.max(left - maximum, aboveLeft, belowLeft),
      Math.min(right + maximum, aboveRight, belowRight)];
  });
}

function atlasShade(r, g, b) {
  if (Math.max(r, g, b) < 33) return black;
  let selected = black;
  let nearest = Infinity;
  for (const color of atlasPalette) {
    const distance = (r - (color >>> 24)) ** 2
      + (g - ((color >>> 16) & 255)) ** 2
      + (b - ((color >>> 8) & 255)) ** 2;
    if (distance < nearest) {
      nearest = distance;
      selected = color;
    }
  }
  return selected;
}

function drawAtlasPortrait(atlas, record, study) {
  const [cellLeft, cellTop, cellRight, cellBottom] = record.source_cell_box;
  const [left, top, right, bottom] = record.source_visible_box;
  const pad = Math.round((right - left) * .045);
  const x0 = Math.max(cellLeft, left - pad);
  const y0 = Math.max(cellTop, top - pad);
  const w = Math.min(cellRight, right + pad) - x0;
  const h = Math.min(cellBottom, bottom + pad) - y0;
  const raw = new Uint32Array(w * h);
  const [fitLeft, fitTop, fitRight, fitBottom] = record.native_fitted_box.map(value => value * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = ((y0 + y) * atlas.width + x0 + x) * 4;
      let shade = atlasShade(atlas.rgba[i], atlas.rgba[i + 1], atlas.rgba[i + 2]);
      const u = (x0 + x + .5 - left) / (right - left);
      const v = (y0 + y + .5 - top) / (bottom - top);
      if (paletteGroup(shade) === 2 && u >= 0 && u < 1 && v >= 0 && v < 1) {
        const sx = Math.floor(fitLeft + u * (fitRight - fitLeft));
        const sy = Math.floor(fitTop + v * (fitBottom - fitTop));
        const color = study.rgba.readUInt32BE((sy * study.width + sx) * 4);
        // Keep the later skin and garment color study only over matching
        // materials. The uncompressed cell owns the silhouette and all ink.
        if ((color & 255) && paletteGroup(color) === 2 &&
            Math.abs(((shade >>> 16) & 255) - ((color >>> 16) & 255)) <= 60) {
          shade = atlasShade(color >>> 24, (color >>> 16) & 255, (color >>> 8) & 255);
        }
      }
      raw[y * w + x] = shade;
    }
  }
  const art = refineEdges(applyWhiteMatte(raw, w, h), w, h);
  const fitted = fitArt(art, w * scale, h * scale);
  reconnectOuterInk(fitted);
  return fitted;
}

function reconnectOuterInk(pixels) {
  const at = (x, y) => pixels.readUInt32BE((y * width + x) * 4);
  const limit = 9;
  const repairs = [];
  for (let y = 10 + limit; y < Math.floor(height * .70); y++) {
    for (const direction of [1, -1]) {
      const start = direction === 1 ? 6 : width - 7;
      const stop = direction === 1 ? Math.floor(width * .35) : Math.ceil(width * .65);
      for (let x = start; x !== stop && at(x, y) === white; x += direction) {
        let above = 1, below = 1;
        while (above < limit && at(x, y - above) === white) above++;
        if (above === limit) continue;
        while (above + below <= limit && at(x, y + below) === white) below++;
        if (above + below > limit) continue;
        // Bridge a narrow slit in the outer edge only when ink meets it
        // above and below. Enclosed whites (eyes, ornaments, ribbons) stay.
        const upper = at(x, y - above), lower = at(x, y + below);
        if ((upper === black && paletteGroup(lower) !== 1) ||
            (lower === black && paletteGroup(upper) !== 1)) {
          repairs.push((y * width + x) * 4);
        }
      }
    }
  }
  for (const offset of repairs) pixels.writeUInt32BE(black, offset);
}

function fitArt(art, w, h) {
  let left = w, right = -1, top = h, bottom = -1;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (art[y * w + x] === white) continue;
      left = Math.min(left, x);
      right = Math.max(right, x);
      top = Math.min(top, y);
      bottom = Math.max(bottom, y);
    }
  }
  assert(top <= bottom && left <= right, 'Atlas cell has no drawable figure');
  const artHeight = bottom - top + 1;
  const center = (left + right + 1) / 2;
  let radius = 0;
  for (let y = top; y < top + Math.ceil(artHeight * .76); y++) {
    for (let x = left; x <= right; x++) {
      if (art[y * w + x] !== white) radius = Math.max(radius, Math.abs(x + .5 - center));
    }
  }
  const ratio = Math.min(614 / artHeight, 250 / radius);
  const fitted = Buffer.alloc(width * height * 4, 255);
  for (let y = 0; y < Math.floor(artHeight * ratio); y++) {
    const sy = top + Math.floor((y + .5) / ratio);
    for (let x = 6; x < width - 6; x++) {
      const sx = Math.floor(center + (x + .5 - width / 2) / ratio);
      if (sx < left || sx > right) continue;
      fitted.writeUInt32BE(art[sy * w + sx], ((y + 10) * width + x) * 4);
    }
  }
  verifyWhiteMargin(fitted);
  return fitted;
}

function protectedFace(x, y, w, h) {
  return x >= w * .25 && x < w * .75 && y >= h * .29 && y < h * .73;
}

// Subdivide diagonal edges using only existing neighboring palette colors.
// Preserve the centers of the source pixels. Inside the face, subdivide only
// the warm shading and keep the ink, eyes and other neutral detail in place.
function refineEdges(data, w, h) {
  const palette = [...new Set(data)];
  const colorIds = new Map(palette.map((color, i) => [color, i]));
  const source = Uint8Array.from(data, color => colorIds.get(color));
  const groups = palette.map(paletteGroup);
  const output = new Uint32Array(w * h * scale * scale);
  const scores = new Float64Array(palette.length);
  const votes = new Float64Array(3);
  const radius = 2;
  const sigma = .76;
  const kernel = Array.from({ length: scale }, (_, subpixel) => {
    const position = (subpixel + .5) / scale - .5;
    return Array.from({ length: radius * 2 + 1 }, (_, offset) => {
      const delta = offset - radius - position;
      return Math.exp(-delta * delta / (2 * sigma * sigma));
    });
  });
  const patch = new Uint8Array((radius * 2 + 1) ** 2);
  const at = (x, y) => source[Math.max(0, Math.min(h - 1, y)) * w + Math.max(0, Math.min(w - 1, x))];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const original = at(x, y);
      let n = 0;
      let uniform = true;
      for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
          const color = at(x + dx, y + dy);
          patch[n++] = color;
          uniform &&= color === original;
        }
      }
      const face = protectedFace(x, y, w, h);
      const fixed = uniform || (face && groups[original] !== 2) || y >= h - 4;
      for (let py = 0; py < scale; py++) {
        for (let px = 0; px < scale; px++) {
          const index = (y * scale + py) * w * scale + x * scale + px;
          if (fixed || (px > 0 && px < 3 && py > 0 && py < 3)) {
            output[index] = palette[original];
            continue;
          }
          scores.fill(0);
          votes.fill(0);
          let k = 0;
          let total = 0;
          for (const yWeight of kernel[py]) {
            for (const xWeight of kernel[px]) {
              const color = patch[k++];
              const weight = xWeight * yWeight;
              scores[color] += weight;
              votes[groups[color]] += weight;
              total += weight;
            }
          }
          const sx = px < 2 ? -1 : 1;
          const sy = py < 2 ? -1 : 1;
          const allowed = [original, at(x + sx, y), at(x, y + sy), at(x + sx, y + sy)];
          let bestGroup = groups[original];
          let bestGroupScore = votes[bestGroup] + .015 * total;
          for (const color of allowed) {
            const group = groups[color];
            if (!face && votes[group] > bestGroupScore) {
              bestGroup = group;
              bestGroupScore = votes[group];
            }
          }
          let best = original;
          let bestScore = -1;
          for (const color of allowed) {
            if (groups[color] !== bestGroup) continue;
            const stability = color === original ? .035 * votes[bestGroup] : 0;
            if (scores[color] + stability > bestScore) {
              best = color;
              bestScore = scores[color] + stability;
            }
          }
          output[index] = palette[best];
        }
      }
    }
  }
  return output;
}

function verifyWhiteMargin(rgba) {
  const pixel = (x, y) => rgba.readUInt32BE((y * width + x) * 4);
  for (let x = 0; x < width; x++) {
    assert(pixel(x, 0) === white && pixel(x, height - 1) === white, 'Portrait has a nonwhite horizontal margin');
  }
  for (let y = 0; y < height; y++) {
    assert(pixel(0, y) === white && pixel(width - 1, y) === white, 'Portrait has a nonwhite vertical margin');
  }
}

function renderWhite(raw) {
  const { width: w, height: h, rgba } = decodePng(raw);
  assert((w === 128 || w === width) && h === w * 5 / 4, 'Unexpected source dimensions');
  const source = Uint32Array.from({ length: w * h }, (_, i) => rgba.readUInt32BE(i * 4));
  const matte = applyWhiteMatte(source, w, h);
  const output = w === width ? matte : refineEdges(matte, w, h);
  const factor = width / w;
  const offset = Math.floor(factor / 2);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const color = source[i];
      const anchor = (y * factor + offset) * width + x * factor + offset;
      const expected = (color & 255) && color !== black ? color : matte[i];
      assert.equal(output[anchor], expected);
      if (protectedFace(x, y, w, h)) {
        for (let dy = 0; dy < factor; dy++) {
          for (let dx = 0; dx < factor; dx++) {
            const subpixel = output[(y * factor + dy) * width + x * factor + dx];
            if (paletteGroup(matte[i]) === 2) assert.equal(paletteGroup(subpixel), 2);
            else assert.equal(subpixel, matte[i]);
          }
        }
      }
    }
  }
  const pixels = Buffer.alloc(output.length * 4);
  output.forEach((pixel, i) => pixels.writeUInt32BE(pixel, i * 4));
  verifyWhiteMargin(pixels);
  return pixels;
}

function correctEyeWhites(pixels, regions) {
  const at = (x, y) => pixels.readUInt32BE((y * width + x) * 4);
  const isDark = color => (color >>> 24) < 160;
  const isWarm = color => paletteGroup(color) === 2 && (color >>> 24) >= 195;
  for (const [left, top, right, bottom] of regions) {
    const span = right - left;
    const eyeHeight = bottom - top;
    const candidates = [];
    for (let y = top + Math.round(eyeHeight * .35); y <= bottom; y++) {
      for (let x = left + 3; x <= right - 3; x++) {
        if (!isWarm(at(x, y))) continue;
        const position = (x - left) / span;
        if (position > .43 && position < .57) continue;
        const side = position < .5 ? 1 : -1;
        let lid = 1;
        let iris = 1;
        while (lid <= 16 && !isDark(at(x, y - lid))) lid++;
        while (iris <= 20 && !isDark(at(x + side * iris, y))) iris++;
        if (lid > 16 || iris > 20) continue;
        const edge = Math.min(position, 1 - position);
        const score = Math.abs(edge - .23) * 20 + Math.abs((y - top) / eyeHeight - .63) * 12
          + Math.abs(lid - 8) * .22 + Math.abs(iris - 5) * .4;
        candidates.push({ x, y, score });
      }
    }
    assert(candidates.length > 20, 'No sclera region below the eyelid');
    const allowed = new Map(candidates.map(point => [point.y * width + point.x, point]));
    candidates.sort((a, b) => a.score - b.score);
    const visited = new Set();
    const maxPixels = Math.round(span * eyeHeight * .026);
    let corrected = false;
    for (const seed of candidates) {
      const key = seed.y * width + seed.x;
      if (visited.has(key)) continue;
      const shape = [key];
      visited.add(key);
      for (const index of shape) {
        for (const neighbor of [index - 1, index + 1, index - width, index + width]) {
          const point = allowed.get(neighbor);
          if (!point || visited.has(neighbor)) continue;
          if (Math.hypot((point.x - seed.x) / 9, (point.y - seed.y) / 6) > 1) continue;
          visited.add(neighbor);
          shape.push(neighbor);
        }
      }
      if (shape.length < Math.min(30, maxPixels)) continue;
      shape.sort((a, b) => {
        const distance = index => Math.hypot((index % width - seed.x) / 9,
          (Math.floor(index / width) - seed.y) / 6);
        return distance(a) - distance(b);
      });
      for (const [i, index] of shape.slice(0, maxPixels).entries()) {
        pixels.writeUInt32BE(i < maxPixels * .8 ? white : 0xe2e2deff, index * 4);
      }
      corrected = true;
      break;
    }
    assert(corrected, 'No contiguous sclera region');
  }
}

function fitPortraitFrame(pixels) {
  const topMargin = 10;
  const bottomMargin = 16;
  const sideMargin = 6;
  const rows = [];
  let left = width;
  let right = -1;
  for (let y = 0; y < height; y++) {
    let first = width;
    let last = -1;
    for (let x = 0; x < width; x++) {
      if (pixels.readUInt32BE((y * width + x) * 4) === white) continue;
      first = Math.min(x, first);
      last = x;
    }
    rows.push({ first, last });
    left = Math.min(left, first);
    right = Math.max(right, last);
  }
  const top = rows.findIndex(row => row.last >= 0);
  const bottom = rows.findLastIndex(row => row.last >= 0);
  assert(top >= 0, 'Cannot frame an empty portrait');
  if (top <= 14) return pixels;

  const figureHeight = bottom - top + 1;
  const center = (left + right + 1) / 2;
  // Fit the bust by height. Where a wide silhouette needs to trim, keep
  // every visible part of the head, headgear and upper torso in the frame.
  const protectedRows = rows.slice(top, top + Math.ceil(figureHeight * .76));
  const protectedRadius = Math.max(...protectedRows.map(({ first, last }) =>
    Math.max(center - first, last + 1 - center)));
  const ratio = Math.min((height - topMargin - bottomMargin) / figureHeight,
    (width / 2 - sideMargin) / protectedRadius);
  const fittedHeight = Math.floor(figureHeight * ratio);
  const framed = Buffer.alloc(pixels.length, 255);
  const sourceColumns = Array.from({ length: width }, (_, x) =>
    Math.floor(center + (x + .5 - width / 2) / ratio));
  for (let y = 0; y < fittedHeight; y++) {
    const sy = top + Math.floor((y + .5) / ratio);
    for (let x = sideMargin; x < width - sideMargin; x++) {
      const sx = sourceColumns[x];
      if (sx < left || sx > right) continue;
      const pixel = pixels.readUInt32BE((sy * width + sx) * 4);
      framed.writeUInt32BE(pixel, ((y + topMargin) * width + x) * 4);
    }
  }
  assert(framed.subarray(topMargin * width * 4, (topMargin + 1) * width * 4)
    .some(channel => channel !== 255), 'Top of the portrait was lost during framing');
  verifyWhiteMargin(framed);
  return framed;
}

function refineMaterialShading(pixels) {
  const source = Uint32Array.from({ length: width * height }, (_, i) => pixels.readUInt32BE(i * 4));
  const palette = new Set(source);
  for (const shade of atlasPalette) {
    if (palette.size >= 16) break;
    palette.add(shade);
  }
  const warm = [...palette].filter(color => paletteGroup(color) === 2);
  const lightness = color => ((color >>> 16) & 255) * 2 + (color >>> 24);
  const warmColors = new Set(warm);
  const pairs = new Map();
  for (const color of warm) {
    const transitions = new Map();
    for (const other of warm) {
      // Build a short intermediate shade from this portrait's palette.
      const red = ((color >>> 24) + (other >>> 24)) / 2;
      const green = (((color >>> 16) & 255) + ((other >>> 16) & 255)) / 2;
      const blue = (((color >>> 8) & 255) + ((other >>> 8) & 255)) / 2;
      const low = Math.min(lightness(color), lightness(other));
      const high = Math.max(lightness(color), lightness(other));
      let closest = color;
      let best = Infinity;
      for (const candidate of warm) {
        const level = lightness(candidate);
        if (level <= low || level >= high || Math.abs(level - lightness(color)) > 85) continue;
        const distance = ((candidate >>> 24) - red) ** 2
          + (((candidate >>> 16) & 255) - green) ** 2
          + (((candidate >>> 8) & 255) - blue) ** 2;
        if (distance < best) {
          best = distance;
          closest = candidate;
        }
      }
      transitions.set(other, closest);
    }
    pairs.set(color, transitions);
  }

  const shaded = Buffer.from(pixels);
  const directions = [[-1, -width, 1], [-width, -1, 1], [1, width, -1], [width, 1, -1]];
  for (let y = 12; y < height - 12; y++) {
    const garments = y >= height * .70;
    const radius = garments ? 7 : 5;
    for (let x = 12; x < width - 12; x++) {
      const i = y * width + x;
      const color = source[i];
      if (!warmColors.has(color)) continue;
      const level = lightness(color);
      let bestScore = 0;
      let result = color;
      for (const [across, along, direction] of directions) {
        const near = source[i + across * 2];
        const other = source[i + across * radius];
        if (!warmColors.has(near) || !warmColors.has(other)) continue;
        const score = (lightness(other) - level) * direction;
        if (score < 58 || score <= bestScore) continue;
        const shade = pairs.get(color).get(other);
        if (shade === color) continue;
        // Use an existing edge with length along the surface. This avoids
        // single-pixel speckles around the pupils and cloth stitching.
        if (source[i + across * radius + along * 2] !== other &&
            source[i + across * radius - along * 2] !== other) continue;
        bestScore = score;
        result = shade;
      }
      if (result !== color) shaded.writeUInt32BE(result, i * 4);
    }
  }
  return shaded;
}

function restoreInk(pixels, bands) {
  for (const [top, bottom, left, right] of bands) {
    assert(top > 0 && top <= bottom && bottom < height - 1);
    assert(left > 0 && left < right && right < width);
    for (let y = top; y <= bottom; y++) {
      for (let x = left; x < right; x++) {
        const offset = (y * width + x) * 4;
        assert.equal(pixels.readUInt32BE(offset), white, 'Ink repair no longer matches the white seam');
        pixels.writeUInt32BE(black, offset);
      }
    }
  }
}

function build(check) {
  const read = name => JSON.parse(fs.readFileSync(path.join(root, 'game/config', name), 'utf8'));
  const enhanced = read('portrait-enhanced.json').people;
  const refined = read('portrait-refined.json').people;
  const generated = read('portrait-generated.json').by_person_id;
  const female = Object.entries(generated)
    .filter(([id, portrait]) => portrait.gender_design === 'female' && !targetedRedraws.has(id))
    .map(([id]) => id).sort();
  assert.deepEqual(Object.keys(eyeRegions).sort(), female);
  const atlases = new Map();
  let atlasPortraits = 0;
  const people = {};
  const ids = Object.keys(enhanced).sort();
  if (!check) fs.mkdirSync(directory, { recursive: true });
  for (let start = 0; start < ids.length; start += batchSize) {
    const batch = ids.slice(start, start + batchSize);
    for (const id of batch) {
      assert.match(id, /^[a-z0-9-]{1,128}$/);
      const file = path.join(directory, id + '.png');
      const sourcePath = refined[id]
        ? '/assets/portraits/refined/' + id + '.png'
        : enhanced[id].path;
      const source = fs.readFileSync(path.join(root, 'game', sourcePath));
      const sourceHash = sha(source);
      assert.equal(sourceHash, refined[id]?.png_sha256 ?? enhanced[id].sha256, id);
      let png;
      let pixels;
      let method;
      const authored = approved.has(id) || targetedRedraws.has(id);
      const truecolor = individualRedraws[id]?.truecolor_export;
      const hairRedraw = individualRedraws[id]?.black_hair_redraw;
      try {
        if (authored) {
          png = fs.readFileSync(file);
          const image = decodePng(png);
          assert.deepEqual([image.width, image.height], [width, height]);
          verifyWhiteMargin(image.rgba);
          pixels = image.rgba;
          if (hairRedraw || truecolor) {
            if (truecolor) assert.equal(generated[id]?.gender_design, 'female');
            assert.equal(sha(png), (hairRedraw || truecolor).output_sha256, 'Portrait differs from the approved export');
            for (let offset = 3; offset < pixels.length; offset += 4) assert.equal(pixels[offset], 255);
            method = hairRedraw ? 'black_hair_redraw' : 'truecolor_redraw';
          } else {
            method = approved.has(id) && !individualRedraws[id] ? 'approved_redraw' : 'targeted_redraw';
          }
        } else if (generated[id]?.source_atlas?.startsWith('art/portraits/source-atlases/')) {
          const record = generated[id];
          const atlasPath = record.source_atlas;
          if (!atlases.has(atlasPath)) {
            const rawAtlas = fs.readFileSync(path.join(root, atlasPath));
            assert.equal(sha(rawAtlas), record.source_atlas_sha256, atlasPath);
            atlases.set(atlasPath, decodePng(rawAtlas));
          }
          pixels = drawAtlasPortrait(atlases.get(atlasPath), record, decodePng(source));
          if (eyeRegions[id]) correctEyeWhites(pixels, eyeRegions[id]);
          method = eyeRegions[id] ? 'targeted_repair' : 'white_matte_contour';
          atlasPortraits++;
        } else {
          pixels = renderWhite(source);
          method = 'white_matte_contour';
        }
        const framed = hairRedraw || truecolor ? pixels : fitPortraitFrame(pixels);
        if (!authored) {
          pixels = refineMaterialShading(framed);
          if (inkRepairs[id]) {
            restoreInk(pixels, inkRepairs[id]);
            method = 'targeted_repair';
          }
          png = encodePng(width, height, pixels);
        } else if (framed !== pixels) {
          pixels = framed;
          png = encodePng(width, height, pixels);
        }
        if (check) assert(fs.readFileSync(file).equals(png), 'Output differs');
        else fs.writeFileSync(file, png);
      } catch (error) {
        throw new Error(id + ': ' + error.message, { cause: error });
      }
      people[id] = { source_sha256: sourceHash, png_sha256: sha(png), rgba_sha256: sha(pixels), method };
    }
    console.log('White portraits:', start + 1, '–', start + batch.length, '/', ids.length);
  }
  console.log('White portraits recovered from pre-quantization atlas cells:', atlasPortraits);
  const manifest = JSON.stringify({ schema: 'tk2-white-portraits-v1', width, height, people }) + '\n';
  if (check) assert.equal(fs.readFileSync(manifestPath, 'utf8'), manifest);
  else fs.writeFileSync(manifestPath, manifest);
}

if (require.main === module) build(process.argv.includes('--check'));
module.exports = { renderWhite, drawAtlasPortrait, correctEyeWhites, refineMaterialShading };
