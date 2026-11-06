// Smoke test: runs the plugin (as install.mjs builds it) against a fake Creator SDK (BS) and an in-memory IndexedDB, in Node 22.
// It can't prove anything about the real app (UI, attachments, permissions); it catches logic errors before a Windows build.
//   node XRTimeMachine/test/smoke.mjs
import assert from 'node:assert/strict';
import { makeNetwork, joinClient, sleep } from './fake-sdk.mjs';

// ---- run ----
const fetched = [];
const fetch = async (url, opts = {}) => {
  fetched.push({ url, body: opts.body });
  if (url.endsWith('/xrtm/ping')) return { ok: true, json: async () => ({ ok: true, folder: 'C:\\Users\\ben\\Documents\\AltspaceVR\\XRTimeMachine' }) };
  return { ok: true, json: async () => ({ ok: true }) };
};
const net = makeNetwork();
const dbs = new Map();
const ben = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { dbs, fetch, config: { trackObjects: ['Trophy'], flushMs: 50 } });
const { scene, emit, ui } = ben;
await sleep(20);

const button = (text) => ben.button(text);
emit('key-press', { key: 290 });                      // F9 opens the panel
await sleep(20);
const rec = button('●  Record');
assert.ok(rec, 'record button exists');
await rec.click();
await sleep(20);
assert.ok(scene.spaceStateJson.protected['xrtm.recs.s1'], 'recording announced in protected space state');
const announced = JSON.parse(scene.spaceStateJson.protected['xrtm.recs.s1']);
assert.equal(announced.by, 'Ben');
assert.ok(ui.some((e) => String(e.text).startsWith('This session is being recorded by Ben')), 'notice shown');

// Things happen.
emit('user-joined', { uid: 'u3', id: 's3', name: 'Ada', state: { avatar: 'Robot' } });
emit('user-state', { uid: 'u3', id: 's3', full: false, changes: [{ path: 'handRaise', value: String(Date.now()) }] });
emit('pose-update', { head: { position: { x: 1, y: 1.6, z: 2 }, rotation: { x: 0, y: 0, z: 0, w: 1 } } });
(await scene.Find('Trophy')).watch({ position: { x: 0, y: 1, z: 0 }, rotation: { x: 0, y: 0, z: 0, w: 1 } });
await button('Add chapter marker').click();
emit('user-left', { uid: 'u3', id: 's3' });
await sleep(120);                                     // at least one flush
await button('■  Stop').click();
await sleep(50);
assert.equal(scene.spaceStateJson.protected['xrtm.recs.s1'], undefined, 'state cleared on stop');

// What was written.
const db = dbs.get('xrtm');
const chunks = [...db.stores.get('chunks').rows.values()].sort((a, b) => a.seq - b.seq);
const lines = chunks.map((c) => c.text).join('').trim().split('\n').map((l) => JSON.parse(l));
const types = lines.map((l) => l.type);
for (const t of ['header', 'roster', 'space_state', 'join', 'user_state', 'self_pose', 'object', 'object_pose', 'chapter', 'leave', 'end']) {
  assert.ok(types.includes(t), `wrote ${t}`);
}
assert.equal(lines[0].format, 'xrtm');
assert.ok(lines.slice(1).every((l, i, a) => i === 0 || l.t >= a[i - 1].t), 'times only go forward');
const meta = [...db.stores.get('recordings').rows.values()][0];
assert.equal(meta.status, 'complete');
const appended = fetched.filter((f) => f.url.includes('/xrtm/append')).map((f) => f.body).join('');
assert.equal(appended, chunks.map((c) => c.text).join(''), 'helper got exactly what the device store got');

console.log(`ok: ${lines.length} lines, ${types.filter((t) => t === 'self_pose').length} self poses, helper and device store match`);
process.exit(0);
