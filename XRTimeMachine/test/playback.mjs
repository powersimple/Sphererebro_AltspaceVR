// Playback test: the owner plays a recording from their device, and every player's page shows it in step.
// Three fake players share one room: Ben (world owner, has the recording), Guest (there from the start),
// and Late (arrives mid-playback). Load, play/pause, scrub, hh:mm:ss jump, chapter jump, end, stop.
// It can't prove anything about the real app (UI, attachments, permissions); it catches logic errors before a Windows build.
//   ~/.nvm/versions/node/v22.12.0/bin/node XRTimeMachine/test/playback.mjs
import assert from 'node:assert/strict';
import { makeNetwork, joinClient, leaveClient, seedRecording, sleep } from './fake-sdk.mjs';

// ---- a 4-second recording: the head walks along +x at 1 m/s, the trophy rises at 1 m/s ----
const id = 'thepolys-2026-10-27T10-00-00';
const lines = [
  { type: 'header', format: 'xrtm', version: 0, id, name: 'thepolys 2026-10-27 10:00', startedUtc: '2026-10-27T10:00:00.000Z', recorder: { by: 'Ben', app: 'xrtm-world.js', appVersion: '0.1.0' } },
  { t: 0, type: 'roster', users: [{ uid: 'u1', sid: 's1', name: 'Ben', local: true, state: {} }, { uid: 'u9', sid: 's9', name: 'Bob', state: {} }] },
  { t: 0, type: 'space_state', full: true, public: {}, protected: {} },
  { t: 0, type: 'object', name: 'Trophy', ref: { kind: 'scene', path: 'Trophy' } },
];
for (let t = 0; t <= 4000; t += 33) {
  const x = t / 1000;
  lines.push({ t, type: 'self_pose', uid: 'u1', head: { p: [x, 1.6, 0], r: [0, 0, 0, 1] }, left: { p: [x - 0.2, 1.2, 0.2], r: [0, 0, 0, 1] }, right: { p: [x + 0.2, 1.2, 0.2], r: [0, 0, 0, 1] } });
  if (t % 99 === 0) lines.push({ t, type: 'object_pose', name: 'Trophy', p: [0, 1 + x, 0], r: [0, 0, 0, 1] });
}
lines.push(
  { t: 1000, type: 'join', user: { uid: 'u3', sid: 's3', name: 'Ada', state: { avatar: 'Robot', config: 'x'.repeat(5000) } } },
  { t: 1000, type: 'chapter', label: 'Ada arrives' },
  { t: 1500, type: 'user_state', uid: 'u3', sid: 's3', full: false, changes: [{ path: 'handRaise', value: '1761559200000' }] },
  { t: 3000, type: 'chapter', label: 'Finale' },
  { t: 3500, type: 'leave', uid: 'u3', sid: 's3' },
  { t: 4000, type: 'end', endedUtc: '2026-10-27T10:00:04.000Z', durationMs: 4000 },
);
lines.sort((a, b) => (a.t ?? -1) - (b.t ?? -1));
const benDbs = new Map();
seedRecording(benDbs, { id, name: 'Rehearsal', startedUtc: '2026-10-27T10:00:00.000Z', status: 'complete', durationMs: 4000, chapters: 2 }, lines, 3);

const config = { trackObjects: ['Trophy'], pumpMs: 50, keyframeMs: 300, scrubDebounceMs: 50, playAheadMs: 600 };
const net = makeNetwork();
const ben = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { dbs: benDbs, config });
const guest = await joinClient(net, { uid: 'u2', sid: 's2', name: 'Guest' }, { config });
await sleep(30);

const near = (actual, expected, tol, what) => assert.ok(Math.abs(actual - expected) <= tol, `${what}: expected ~${expected}, got ${actual}`);
const playState = () => { const raw = net.state.protected['xrtm.play']; return raw && JSON.parse(raw); };
const headX = (c) => c.named('XRTM Stand-in Head')?.position?.x;
const label = (c) => c.named('XRTM Stand-in Label')?.comps.find((k) => 'rectTransformSizeDelta' in k)?.text || '';
const trophyY = async (c) => (await c.scene.Find('Trophy')).position.y;

// Only the owner gets a panel.
assert.ok(!guest.ui.some((e) => e.text === 'XR Time Machine'), 'guest has no panel');
ben.emit('key-press', { key: 290 });
await sleep(30);

// ---- load: Play on the library row ----
await ben.button('Play').click();
await sleep(30);
let s = playState();
assert.ok(s, 'playback announced in protected space state');
assert.equal(s.id, id);
assert.equal(s.playing, true);
assert.equal(s.durationMs, 4000);
assert.deepEqual(s.chapters.map((c) => c.label), ['Ada arrives', 'Finale']);
assert.equal(s.recordedBy, 'Ben');

await sleep(400);
for (const c of [ben, guest]) {
  const head = c.named('XRTM Stand-in Head');
  assert.ok(head?.active, `${c.me.name} sees the stand-in`);
  near(headX(c), 0.4, 0.2, `${c.me.name} stand-in follows the recorded head`);
  assert.ok(c.named('XRTM Stand-in Left Hand')?.active, `${c.me.name} sees the hands`);
  near(await trophyY(c), 1.4, 0.25, `${c.me.name} trophy follows the recording`);
}
near(Math.abs(headX(ben) - headX(guest)), 0, 0.1, 'Ben and Guest are in step');
assert.ok(net.oneShots > 0, 'lines went out as one-shots');

// ---- pause holds the frame ----
await ben.button('❚❚  Pause').click();
await sleep(40);
assert.equal(playState().playing, false);
const held = headX(guest);
await sleep(250);
assert.equal(headX(guest), held, 'paused: the stand-in stays put');

// ---- scrub: drag the slider to 2.5 s ----
const slider = ben.ui.find((e) => 'maxValue' in e && !e.destroyed);
assert.equal(slider.maxValue, 4, 'slider spans the recording in seconds');
const sessionBefore = playState().session;
slider.change({ value: 2.5 });
await sleep(200);
assert.ok(playState().session > sessionBefore, 'a jump starts a new session');
assert.equal(playState().atT, 2500);
near(headX(guest), 2.5, 0.05, 'scrub: Guest jumped to 2.5 s');
near(headX(ben), 2.5, 0.05, 'scrub: Ben jumped to 2.5 s');
near(await trophyY(guest), 3.5, 0.11, 'scrub: the trophy jumped too');

// ---- chapter jump ----
const finale = ben.button((t) => t.includes('Finale'));
assert.ok(finale, 'chapter list has Finale');
assert.ok(finale.text.startsWith('00:00:03'), 'chapter shows its time');
await finale.click();
await sleep(200);
near(headX(guest), 3.0, 0.05, 'chapter jump: Guest at the Finale');

// ---- hh:mm:ss jump, then play through the raised hand ----
const field = ben.ui.find((e) => e.value === '00:00:00');
field.change({ value: 'nonsense' });
await ben.button('Go to time').click();
assert.ok(ben.ui.some((e) => String(e.text).startsWith('Type a time')), 'bad time is refused');
field.change({ value: '00:00:01' });
await ben.button('Go to time').click();
await sleep(200);
near(headX(guest), 1.0, 0.05, 'jump field: Guest at 1 s');
assert.match(label(guest), /3 here/, 'caption counts who was there at 1 s (Ben, Bob, Ada)');
await ben.button('▶  Play').click();
await sleep(700);
assert.match(label(guest), /Ada raised a hand/, 'user_state shows as a caption');
near(headX(guest), 1.7, 0.25, 'playing again from 1 s');

// ---- someone arriving mid-playback catches up ----
const late = await joinClient(net, { uid: 'u4', sid: 's4', name: 'Late' }, { config });
await sleep(450);
assert.ok(late.named('XRTM Stand-in Head')?.active, 'late arrival sees the stand-in');
near(headX(late), headX(guest), 0.25, 'late arrival is in step');

// ---- the end pauses it ----
await ben.button((t) => t.includes('Finale')).click();
await sleep(1300);
assert.equal(playState().playing, false, 'reaching the end pauses');
assert.equal(playState().atT, 4000);
assert.match(label(guest), /Ada left/, 'leave shows as a caption');

// ---- one at a time: Ben can't be overridden by a guest, and a forged packet is ignored ----
guest.scene.OneShot({ xrtm: 'pb', id, s: playState().session, lines: [{ t: 0, type: 'self_pose', head: { p: [99, 0, 0] } }] });
await sleep(100);
assert.notEqual(headX(ben), 99, "only the conductor's packets count");

// ---- stop ----
await ben.button('■  Stop playback').click();
await sleep(100);
assert.equal(net.state.protected['xrtm.play'], undefined, 'playback cleared from space state');
for (const c of [ben, guest, late]) {
  assert.equal(c.named('XRTM Stand-in Head'), undefined, `${c.me.name}: stand-in removed`);
  assert.equal(await trophyY(c), 0.5, `${c.me.name}: trophy put back`);
}

// ---- the conductor leaving ends it for everyone ----
await ben.button('Play').click();
await sleep(200);
assert.ok(guest.named('XRTM Stand-in Head'), 'playing again');
leaveClient(net, ben);
await sleep(100);
assert.equal(guest.named('XRTM Stand-in Head'), undefined, 'conductor left: Guest stops showing it');

console.log(`ok: load, play/pause, scrub, jump, chapters, late arrival, end, stop; ${net.oneShots} one-shots`);
process.exit(0);
