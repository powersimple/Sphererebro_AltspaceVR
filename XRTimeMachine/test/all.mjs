// Runs every test, each in its own Node process, and checks script.js has the current build.
//   node XRTimeMachine/test/all.mjs
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { pluginDir, manifest, status } from '../install.mjs';

let failed = 0;
for (const t of ['smoke.mjs', 'playback.mjs', 'plugin.mjs']) {
  const r = spawnSync(process.execPath, [join(pluginDir, 'test', t)], { encoding: 'utf8' });
  process.stdout.write(r.stdout);
  if (r.status !== 0) { failed++; console.error(`FAILED: ${t}\n${r.stderr}`); }
}
const s = status(readFileSync(join(pluginDir, manifest.target), 'utf8'));
if (!s.installed) console.log('note: not installed in script.js yet (node XRTimeMachine/install.mjs)');
else if (!s.current) { failed++; console.error('FAILED: script.js has an old build: run node XRTimeMachine/install.mjs'); }
else console.log(`ok: script.js has the current build (${s.enabled ? 'on' : 'off'})`);
process.exit(failed ? 1 : 0);
