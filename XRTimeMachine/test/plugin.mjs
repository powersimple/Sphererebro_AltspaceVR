// Plugin test: what makes XR Time Machine safe to bake into a world.
// Recording per device (one account on two devices), video and sound per device, storage warnings and the stop
// at 100 MB, slimmer poses, the off switch, the error breaker, switched off in the config, missing features,
// and the installer leaving the world's own code untouched.
//   node XRTimeMachine/test/plugin.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { makeNetwork, joinClient, leaveClient, sleep } from './fake-sdk.mjs';
import { install, parse, status, build, manifest, pluginDir } from '../install.mjs';

const config = { flushMs: 40, storage: { checkMs: 40 }, noticeSeconds: 0.2 };
// What's on screen: labels whose panel's object hasn't been destroyed.
const texts = (c) => c.ui.filter((e) => !e.destroyed && !e.panel?.go?.destroyed && e.text != null).map((e) => String(e.text));
const linesOf = (c) => {
  const db = c.dbs.get('xrtm');
  const byId = new Map();
  for (const ch of [...db.stores.get('chunks').rows.values()].sort((a, b) => a.seq - b.seq)) byId.set(ch.id, (byId.get(ch.id) || '') + ch.text);
  return [...byId.values()].map((t) => t.trim().split('\n').map((l) => JSON.parse(l)));
};
const metas = (c) => [...c.dbs.get('xrtm').stores.get('recordings').rows.values()];
const pose = (x) => ({ head: { position: { x, y: 1.6, z: 0 }, rotation: { x: 0, y: 0, z: 0, w: 1 } } });

// ---- one account on two devices: each records on its own ----
{
  const net = makeNetwork();
  const pc = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { config });
  const quest = await joinClient(net, { uid: 'u1', sid: 's5', name: 'Ben', owner: true }, { config, platform: 'android' });
  const guest = await joinClient(net, { uid: 'u2', sid: 's2', name: 'Guest' }, { config });
  await sleep(20);
  assert.equal(pc.XRTM.state, 'on');
  assert.equal(pc.XRTM.version, manifest.version, 'plugin.json and the code agree on the version');
  for (const c of [pc, quest]) { c.emit('key-press', { key: 290 }); await sleep(10); await c.button('●  Record').click(); }
  await sleep(40);
  assert.ok(net.state.protected['xrtm.recs.s1'], 'PC announced its recording');
  assert.ok(net.state.protected['xrtm.recs.s5'], 'headset announced its own, at the same time');
  assert.equal(texts(guest).filter((t) => t.startsWith('This session is being recorded by Ben')).length, 2, 'guest told about both');

  // Video and sound on each device by the app's recorder, smallest preset.
  assert.equal(pc.av.starts.length, 1);
  assert.equal(pc.av.starts[0].preset, 'Low');
  assert.equal(quest.av.starts.length, 1);
  assert.ok(texts(quest).some((t) => t.includes("headset's Movies folder")), 'headset says where its video goes');

  // Slimmer poses: rounded to the millimetre, and the same pose isn't written twice.
  for (let i = 0; i < 6; i++) { pc.emit('pose-update', pose(1.23456)); await sleep(60); }
  pc.emit('pose-update', pose(2));
  await sleep(60);

  await pc.button('■  Stop').click();
  await sleep(60);
  assert.equal(net.state.protected['xrtm.recs.s1'], undefined, "PC's announcement cleared");
  assert.ok(net.state.protected['xrtm.recs.s5'], "headset's still recording");
  assert.equal(pc.av.stops, 1, 'video stopped with the recording');
  const [pcLines] = linesOf(pc);
  const selfPoses = pcLines.filter((l) => l.type === 'self_pose');
  assert.equal(selfPoses.length, 2, 'six identical poses written once, then the new one');
  assert.deepEqual(selfPoses[0].head.p, [1.235, 1.6, 0], 'positions to the millimetre');
  assert.equal(selfPoses[0].sid, 's1', 'pose says which device');
  assert.ok(pcLines.some((l) => l.type === 'av' && l.event === 'start' && l.takeId === 'take1'), 'the .xrtm notes when the video started');
  assert.equal(pcLines[0].recorder.device.sid, 's1');
  assert.equal(metas(pc).length, 1, 'PC has its recording');
  assert.equal(metas(quest).length, 1, 'headset has its own (still going)');

  // The PC leaving doesn't touch the headset's recording.
  leaveClient(net, pc);
  await sleep(40);
  assert.ok(net.state.protected['xrtm.recs.s5']);
  await quest.button('■  Stop').click();
  await sleep(60);
  assert.equal(metas(quest)[0].status, 'complete');
  console.log('ok: two devices, one account: separate recordings, video per device, slim poses');
}

// ---- storage: warn under 3 GB, countdown under 1 GB, stop at 100 MB ----
{
  const net = makeNetwork();
  const ben = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { config, free: 2.5e9 });
  ben.emit('key-press', { key: 290 });
  await sleep(10);
  await ben.button('●  Record').click();
  await sleep(30);
  assert.ok(texts(ben).some((t) => t.startsWith('Low storage: 2.5 GB free')), 'warned at the start');
  ben.free = 9e8;
  await sleep(100);
  ben.free = 8e8;
  await sleep(100);
  const banner = texts(ben).find((t) => t.endsWith('of recording left'));
  assert.ok(banner, 'lasting warning under 1 GB');
  assert.match(banner, /800 MB free · .* of recording left/, `countdown shown: ${banner}`);
  ben.free = 9e7;
  await sleep(700); // the warning shrinks away
  assert.equal(net.state.protected['xrtm.recs.s1'], undefined, 'stopped at 100 MB');
  const meta = metas(ben)[0];
  assert.equal(meta.status, 'complete', 'what was recorded is kept');
  assert.match(meta.stoppedBecause, /only 90 MB left/);
  assert.equal(ben.av.stops, 1, 'video stopped too');
  assert.ok(!texts(ben).some((t) => t.endsWith('of recording left')), 'countdown removed');
  // And it won't start again with no room.
  await ben.button('●  Record').click();
  await sleep(30);
  assert.ok(texts(ben).some((t) => /not enough to record/.test(t)), 'refuses to start under 100 MB');
  assert.equal(metas(ben).length, 1);
  console.log('ok: storage warning, countdown, stop at 100 MB');
}

// ---- no video recorder here (Play mode): records data anyway ----
{
  const net = makeNetwork();
  const ben = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { config, av: false });
  ben.emit('key-press', { key: 290 });
  await sleep(10);
  await ben.button('●  Record').click();
  await sleep(30);
  assert.ok(texts(ben).some((t) => t.includes('not available here (app_unavailable)')));
  await ben.button('■  Stop').click();
  await sleep(60);
  assert.ok(linesOf(ben)[0].some((l) => l.type === 'av' && l.event === 'unavailable'));
  console.log('ok: no video recorder: data only, and it says so');
}

// ---- the off switch: everyone, at once, and back ----
{
  const net = makeNetwork();
  const ben = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { config });
  const guest = await joinClient(net, { uid: 'u2', sid: 's2', name: 'Guest' }, { config });
  await sleep(20);
  ben.emit('key-press', { key: 290 });
  await sleep(10);
  await ben.button('●  Record').click();
  await sleep(30);
  const off = () => ben.button((t) => t.startsWith('Turn XR Time Machine off') || t.startsWith('Sure? Tap again'));
  await off().click();
  await off().click();
  await sleep(60);
  assert.ok(net.state.protected['xrtm.off'], 'off is in shared state');
  assert.equal(ben.XRTM.state, 'off');
  assert.equal(guest.XRTM.state, 'off', 'off for everyone in the space');
  assert.equal(metas(ben)[0].status, 'complete', 'the recording was saved first');
  assert.equal(ben.named('XRTM Recorder Panel'), undefined, 'panel removed');
  assert.ok(ben.named('XRTM Off Panel'), 'owner gets the turn-back-on button');
  const late = await joinClient(net, { uid: 'u3', sid: 's3', name: 'Late' }, { config });
  assert.equal(late.XRTM.state, 'off', 'arriving while off stays off');
  ben.emit('key-press', { key: 290 });
  await sleep(10);
  await ben.button((t) => t.startsWith('XR Time Machine is off here')).click();
  await sleep(60);
  assert.equal(net.state.protected['xrtm.off'], undefined);
  for (const c of [ben, guest, late]) assert.equal(c.XRTM.state, 'on', `${c.me.name} back on`);
  assert.ok(ben.named('XRTM Recorder Panel'), 'panel back');
  assert.equal(ben.named('XRTM Off Panel'), undefined);
  console.log('ok: off switch for everyone, and back on');
}

// ---- the breaker: five errors in a minute and it removes itself ----
{
  const net = makeNetwork();
  const ben = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { config });
  const before = ben.listenerCount();
  ben.emit('key-press', { key: 290 });
  await sleep(10);
  await ben.button('●  Record').click();
  await sleep(30);
  for (let i = 0; i < 5; i++) ben.emit('pose-update', null); // a broken event: throws inside the plugin
  await sleep(10);
  assert.equal(ben.named('XRTM Recorder Panel'), undefined, 'panel removed at once');
  await sleep(150);
  assert.equal(ben.XRTM.state, 'tripped');
  assert.equal(net.state.protected['xrtm.recs.s1'], undefined, 'announcement cleared');
  assert.equal(metas(ben)[0].status, 'complete', 'what it recorded is saved');
  assert.equal(ben.listenerCount(), 1, `only the off-switch listener is left (had ${before})`);
  for (let i = 0; i < 5; i++) ben.emit('pose-update', null); // nothing reaches the world's code
  console.log('ok: breaker trips, cleans up, saves');
}

// ---- switched off in the config, or missing pieces ----
{
  const net = makeNetwork();
  const ben = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { config: { ...config, enabled: false } });
  await sleep(20);
  assert.equal(ben.XRTM.state, 'disabled');
  assert.equal(ben.listenerCount(), 0, 'not even listening');
  assert.equal(ben.objects.length, 0, 'made nothing');
  const noDb = await joinClient(net, { uid: 'u4', sid: 's4', name: 'Mod', owner: true }, { config, noIndexedDB: true });
  await sleep(20);
  assert.equal(noDb.XRTM.state, 'on', 'still shows playback');
  assert.equal(noDb.named('XRTM Recorder Panel'), undefined, 'no device storage: no recorder');
  const noVideo = await joinClient(net, { uid: 'u5', sid: 's6', name: 'Old', owner: true }, { config, av: 'missing' });
  noVideo.emit('key-press', { key: 290 });
  await sleep(10);
  await noVideo.button('●  Record').click();
  await sleep(30);
  assert.ok(net.state.protected['xrtm.recs.s6'], 'records without BS.Recording');
  console.log('ok: disabled in config; missing storage or video handled');
}

// ---- a recording left behind by a device that went without stopping (The Polys, 2026-10-30) ----
{
  const net = makeNetwork();
  const long = new Date(Date.now() - 10 * 60000).toISOString();
  net.state.protected['xrtm.recs.s9'] = JSON.stringify({ id: 'old', by: 'Ben', byUid: 'u1', bySid: 's9', startedUtc: long, aliveUtc: long });
  const guest = await joinClient(net, { uid: 'u2', sid: 's2', name: 'Guest' }, { config });
  // the same account, on another device: the user list has one entry per account, so presence alone can't tell
  const ben = await joinClient(net, { uid: 'u1', sid: 's1', name: 'Ben', owner: true }, { config });
  await sleep(30);
  assert.equal(texts(guest).filter((t) => t.startsWith('This session is being recorded')).length, 0, 'no notice for a recording nobody is making');
  assert.equal(net.state.protected['xrtm.recs.s9'], undefined, 'the owner arriving clears it');
  ben.emit('key-press', { key: 290 }); await sleep(10); await ben.button('●  Record').click(); await sleep(30);
  assert.ok(JSON.parse(net.state.protected['xrtm.recs.s1']).aliveUtc, 'a live recording carries its heartbeat');
  assert.equal(texts(guest).filter((t) => t.startsWith('This session is being recorded by Ben')).length, 1, 'a real recording still tells everyone');
  await ben.button('■  Stop').click(); await sleep(30);
  console.log('ok: a recording left behind shows no notice and is cleared; a real one still does');
}

// ---- the installer: the world's own code untouched ----
{
  const script = readFileSync(join(pluginDir, manifest.target), 'utf8');
  const world = parse(script).own.join('\n') + '\n';
  assert.ok(!world.includes('XRTM'), "the world's own code has no XR Time Machine in it");
  const once = install(world);
  assert.deepEqual(status(once), { installed: true, current: true, enabled: true });
  assert.equal(install(once), once, 'installing twice changes nothing');
  assert.equal(install(once, { uninstall: true }), world, 'uninstall gives back the world byte-for-byte');
  const off = install(once, { enabled: false });
  assert.equal(status(off).enabled, false);
  const edited = off.replace('trackObjects: [],', 'trackObjects: ["Poly Trophy Body"],');
  const again = install(edited, { enabled: true });
  assert.ok(again.includes('trackObjects: ["Poly Trophy Body"],'), 'reinstall keeps your config');
  assert.equal(status(again).enabled, true);
  const crlf = world.replace(/\n/g, '\r\n');
  assert.equal(install(install(crlf), { uninstall: true }), crlf, 'Windows line endings kept');
  // A Windows checkout (core.autocrlf) has CRLF on disk; `world` was joined with LF above.
  const eol = script.includes('\r\n') ? '\r\n' : '\n';
  assert.equal(install(script, { uninstall: true }), world.replace(/\n/g, eol), 'an older install is recognised and removed');
  assert.deepEqual(status(script), { installed: true, current: status(script).current, enabled: status(script).enabled });
  const block = build().join('\n');
  console.log(`ok: installer round trip; plugin block ${(block.length / 1024).toFixed(1)} KB`);
}

process.exit(0);
