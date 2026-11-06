// Installs XR Time Machine into this Unity project's world script, on any OS with Node 22.
// The Builder uploads only Assets/WebRoot/script.js (with index.html and the scene), so the plugin is built from
// src/ (see plugin.json) into one marked block at the end of script.js. Two blocks, both marked:
//   config  window.XRTM_CONFIG: yours to edit. Created once; install never overwrites it.
//   plugin  the built code. Replaced on every install; also written to dist/xrtm.js.
// Nothing else in script.js is touched, and --uninstall leaves it exactly as it was before.
//
//   node XRTimeMachine/install.mjs              install or update
//   node XRTimeMachine/install.mjs --off        keep it installed but switched off (enabled: false)
//   node XRTimeMachine/install.mjs --on         switch it back on
//   node XRTimeMachine/install.mjs --status     installed? up to date? on or off?
//   node XRTimeMachine/install.mjs --uninstall  remove both blocks
//   add --target <path to script.js> for another world
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const pluginDir = dirname(fileURLToPath(import.meta.url));
export const manifest = JSON.parse(readFileSync(join(pluginDir, 'plugin.json'), 'utf8'));
const M = manifest.markers;

const DEFAULT_CONFIG = [
  'window.XRTM_CONFIG = {',
  '    enabled: true,          // false: XR Time Machine does nothing in this world (or: node XRTimeMachine/install.mjs --off)',
  '    trackObjects: [],       // object names to record and replay, e.g. ["Poly Trophy Body"]',
  '};',
];

const lines = (text) => text.replace(/\r\n/g, '\n').replace(/\n$/, '').split('\n');

// The plugin's code: every source in plugin.json, in one function so nothing leaks into the world's code.
export function build() {
  const out = ['(function () {', '"use strict";'];
  for (const src of manifest.sources) out.push(...lines(readFileSync(join(pluginDir, src), 'utf8')));
  out.push('})();');
  return out;
}

const begin = () => `${M.begin} v${manifest.version} (built by XRTimeMachine/install.mjs from XRTimeMachine/src; edit those, not this block)`;
const configBegin = () => `${M.configBegin} (yours to edit: install keeps it; install.mjs --off / --on set "enabled")`;

// Splits script.js into the world's own lines and the two blocks.
export function parse(text) {
  const own = [];
  let config = null;
  let plugin = null;
  let cur = null;
  for (const l of lines(text)) {
    if (l.startsWith(M.configBegin)) { cur = config = []; continue; }
    if (l.startsWith(M.begin)) { cur = plugin = []; continue; }
    if (cur && (l === M.configEnd || l === M.end)) { cur = null; continue; }
    (cur || own).push(l);
  }
  while (own.length && own[own.length - 1].trim() === '') own.pop();
  return { own, config, plugin };
}

export function install(text, { uninstall = false, enabled } = {}) {
  const eol = text.includes('\r\n') ? '\r\n' : '\n';
  const { own, config } = parse(text);
  if (uninstall) return own.join(eol) + eol;
  let cfg = config || [...DEFAULT_CONFIG];
  if (enabled !== undefined) cfg = setEnabled(cfg, enabled);
  return [...own, '', configBegin(), ...cfg, M.configEnd, '', begin(), ...build(), M.end].join(eol) + eol;
}

function setEnabled(cfg, on) {
  let found = false;
  // the top-level one only (a line that starts with it): a group can have its own, like av: { enabled: false }
  const out = cfg.map((l) => l.replace(/^(\s*enabled\s*:\s*)(true|false)/, (_, a) => { found = true; return a + on; }));
  if (!found) {
    const i = out.findIndex((l) => /XRTM_CONFIG\s*=\s*\{/.test(l));
    if (i < 0) throw new Error('The XR Time Machine config block has no window.XRTM_CONFIG = { … }; fix it by hand.');
    out.splice(i + 1, 0, `    enabled: ${on},`);
  }
  return out;
}

export function status(text) {
  const { config, plugin } = parse(text);
  const cfg = (config || []).join('\n');
  return {
    installed: !!plugin,
    current: !!plugin && plugin.join('\n') === build().join('\n'),
    enabled: !config ? null : !/^\s*enabled\s*:\s*false/m.test(cfg),
  };
}

function main(argv) {
  const flag = (f) => argv.includes(f);
  const ti = argv.indexOf('--target');
  const target = ti >= 0 ? resolve(argv[ti + 1]) : resolve(pluginDir, manifest.target);
  let text;
  try { text = readFileSync(target, 'utf8'); } catch { console.error(`Not found: ${target}`); process.exit(1); }
  if (flag('--status')) {
    const s = status(text);
    console.log(!s.installed ? `Not installed in ${target}` : `Installed in ${target}: v${manifest.version} build ${s.current ? 'up to date' : 'OUT OF DATE (run install again)'}, ${s.enabled ? 'on' : 'off'}`);
    process.exit(s.installed && !s.current ? 2 : 0);
  }
  const uninstall = flag('--uninstall');
  const enabled = flag('--off') ? false : flag('--on') ? true : undefined;
  writeFileSync(target, install(text, { uninstall, enabled }));
  if (!uninstall) {
    mkdirSync(join(pluginDir, dirname(manifest.dist)), { recursive: true });
    writeFileSync(join(pluginDir, manifest.dist), build().join('\n') + '\n');
  }
  const s = status(readFileSync(target, 'utf8'));
  console.log(uninstall ? `Removed XR Time Machine from ${target}` : `XR Time Machine v${manifest.version} installed in ${target} (${s.enabled ? 'on' : 'off'})`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) main(process.argv.slice(2));
