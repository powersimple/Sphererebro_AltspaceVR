// A fake Creator SDK (BS) and in-memory IndexedDB for the tests, in Node 22.
// Each client is one player's page in its own VM context; clients on one network share space state and one-shots.
// It can't prove anything about the real app (UI, attachments, permissions); it catches logic errors before a Windows build.
import vm from 'node:vm';
import { build } from '../install.mjs';

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// The plugin exactly as install.mjs puts it into script.js.
export const scriptSource = () => build().join('\n') + '\n';

// ---- in-memory IndexedDB, just what the recorder uses ----
export function fakeIndexedDB(dbs = new Map()) {
  const later = (fn) => setTimeout(fn, 0);
  const keyOf = (path, v) => (Array.isArray(path) ? JSON.stringify(path.map((p) => v[p])) : v[path]);
  return {
    dbs,
    open(name) {
      const req = {};
      later(() => {
        let db = dbs.get(name);
        const fresh = !db;
        if (!db) dbs.set(name, (db = { stores: new Map() }));
        const api = {
          createObjectStore(n, { keyPath }) { db.stores.set(n, { keyPath, rows: new Map() }); },
          transaction(names) {
            const t = { objectStore(n) {
              const s = db.stores.get(n);
              return {
                put(v) { s.rows.set(keyOf(s.keyPath, v), structuredClone(v)); },
                delete(k) {
                  if (k && k.lower) { for (const [key, v] of s.rows) if (v.id === k.lower[0]) s.rows.delete(key); }
                  else s.rows.delete(k);
                },
                getAll() { const r = {}; later(() => { r.result = [...s.rows.values()].map((v) => structuredClone(v)); r.onsuccess?.(); }); return r; },
              };
            } };
            later(() => t.oncomplete?.());
            return t;
          },
        };
        req.result = api;
        if (fresh) req.onupgradeneeded?.();
        req.onsuccess?.();
      });
      return req;
    },
  };
}

// Put a recording straight into a device's store, as the recorder would have written it.
export function seedRecording(dbs, meta, lines, chunkCount = 2) {
  const db = { stores: new Map([['recordings', { keyPath: 'id', rows: new Map() }], ['chunks', { keyPath: ['id', 'seq'], rows: new Map() }]]) };
  dbs.set('xrtm', db);
  db.stores.get('recordings').rows.set(meta.id, meta);
  const text = lines.map((l) => JSON.stringify(l) + '\n');
  const per = Math.ceil(text.length / chunkCount);
  for (let seq = 0; seq * per < text.length; seq++) {
    db.stores.get('chunks').rows.set(JSON.stringify([meta.id, seq]), { id: meta.id, seq, text: text.slice(seq * per, (seq + 1) * per).join('') });
  }
}

// ---- the shared room ----
export function makeNetwork() {
  return { clients: [], users: {}, state: { public: {}, protected: {} } };
}

// ---- one player's fake BS ----
function makeBS(net, me, opts = {}) {
  const listeners = new Map();
  const ui = [];
  const objects = [];
  class Emitter { On(n, f) { (listeners.get(n) || listeners.set(n, []).get(n)).push(f); } Off(n, f) { const a = listeners.get(n) || []; const i = a.indexOf(f); if (i >= 0) a.splice(i, 1); } }
  const emit = (n, detail) => (listeners.get(n) || []).slice().forEach((f) => f({ detail }));
  class V { constructor(...a) { [this.x, this.y, this.z, this.w] = a; } }
  const vec = (a) => (a.length === 1 ? { x: a[0].x, y: a[0].y, z: a[0].z, w: a[0].w } : { x: a[0], y: a[1], z: a[2] });
  class GameObject {
    constructor(o) { Object.assign(this, { active: true }, o); this.comps = []; objects.push(this); }
    async AddComponent(c) { this.comps.push(c); c.go = this; return c; }
    async SetActive(v) { this.active = v; }
    async SetPosition(...a) { this.position = vec(a); }
    async SetRotation(...a) { this.rotation = vec(a); }
    async SetLocalScale() {}
    Destroy() { this.destroyed = true; }
    async WatchTransform(_p, cb) { this.watch = cb; }
  }
  class Component { constructor(o) { Object.assign(this, o); } }
  class UIPanel { constructor(o) { Object.assign(this, o); } SetBackgroundColor() {} }
  class El {
    constructor(panel, parent) { this.panel = panel; this.parent = parent; this.style = {}; this.visible = true; ui.push(this); }
    SetStyles(s) { Object.assign(this.style, s); } SetStyle() {}
    OnClick(f) { this.click = f; } OnChange(f) { this.change = f; } Destroy() { this.destroyed = true; }
    SetRange(min, max) { this.minValue = min; this.maxValue = max; } SetValue(v) { this.value = v; }
  }
  const found = new Map(); // scene objects by name, stable per player
  const scene = Object.assign(new Emitter(), {
    async WaitForUnityLoaded() {},
    async IsVR() { return false; },
    async Find(name) {
      if (name !== 'Trophy') return null;
      if (!found.has(name)) {
        const o = new GameObject({ name });
        o.position = { x: 0, y: 0.5, z: 0 };
        o.rotation = { x: 0, y: 0, z: 0, w: 1 };
        o.transform = { get position() { return o.position; }, get rotation() { return o.rotation; } };
        found.set(name, o);
      }
      return found.get(name);
    },
    async SpaceStateSet(path, value, opt) {
      if (opt?.protected && !me.owner) throw Object.assign(new Error('not authorized'), { code: 'not_authorized' });
      const scope = opt?.protected ? 'protected' : 'public';
      net.state[scope][path] = value;
      broadcast(net, (c) => c.emit('space-state', { full: false, changes: [{ path, value, scope }] }));
    },
    async SpaceStateDelete(path, opt) {
      if (!me.owner) throw Object.assign(new Error('not authorized'), { code: 'not_authorized' });
      // as in the app (Windows, 2026-10-30): a protected key is deleted only by a protected delete
      if (path in net.state.protected && !opt?.protected) throw Object.assign(new Error('protected path'), { code: 'protected_path' });
      delete net.state.protected[path];
      broadcast(net, (c) => c.emit('space-state', { full: false, changes: [{ path, deleted: true }] }));
    },
    async OneShot(data) {
      const text = typeof data === 'string' ? data : JSON.stringify(data);
      if (text.length > 4089) throw new Error('one-shot too big');
      net.oneShots = (net.oneShots || 0) + 1;
      broadcast(net, (c) => c !== client && c.emit('one-shot', { fromId: me.sid, fromAdmin: !!me.owner, data: text }));
    },
  });
  Object.defineProperties(scene, {
    users: { get: () => Object.fromEntries(Object.values(net.users).map((u) => [u.uid, { ...u, isLocal: u.uid === me.uid }])) },
    spaceStateJson: { get: () => net.state },
  });
  const client = { me, ui, objects, emit, scene, free: opts.free ?? 5e10, av: { starts: [], stops: 0, listeners: [] },
    listenerCount: () => [...listeners.values()].reduce((n, a) => n + a.length, 0) };
  scene.localUser = { uid: me.uid, id: me.sid, name: me.name, isLocal: true, state: {} };
  const BS = {
    Scene: { GetInstance: () => scene },
    PersistFileBridge: { info: async () => ({ canWrite: !!me.owner, worldId: 856, slug: 'thepolys', url: 'https://thepolys.worldspace.host' }) },
    GameObject, UIPanel, AttachedObject: Component,
    Sphere: Component, Box: Component, Material: Component, Text: Component,
    UIVisualElement: El, UILabel: El, UIButton: El, UITextField: El, UIScrollView: El, UISlider: El,
    Vector2: V, Vector3: V, Vector4: V, Quaternion: V,
    AvatarBoneName: { HEAD: 0 }, PN: { position: 'position', rotation: 'rotation' },
  };
  // The app's own video recorder, on this device. opts.av = false: not available (as in Play mode).
  if (opts.av !== 'missing') BS.Recording = {
    async info() { return opts.av === false ? { canRecord: false, reason: 'app_unavailable', recording: false, platform: 'windows' } : { canRecord: true, reason: null, recording: false, platform: opts.platform || 'windows' }; },
    async start(o) { client.av.starts.push(o); const takeId = `take${client.av.starts.length}`; client.av.listeners.forEach((f) => f({ state: 'Recording', takeId })); return { takeId }; },
    async stop() { client.av.stops++; client.av.listeners.forEach((f) => f({ state: 'Finalizing' })); },
    on(n, f) { client.av.listeners.push(f); return () => { client.av.listeners = client.av.listeners.filter((x) => x !== f); }; },
  };
  return { BS, client };
}

// Deliver to every client (or every other client) a moment later, as a network would.
function broadcast(net, fn) {
  setTimeout(() => net.clients.forEach(fn), 1);
}

// Join a player to the room and run the world script in their own page.
// One account can join twice (two devices): scene.users is keyed by account id, as in the SDK, so the second
// instance replaces the first's entry. me.sid tells the devices apart.
export async function joinClient(net, me, { config = {}, dbs = new Map(), fetch, free, av, platform, noIndexedDB } = {}) {
  net.users[me.uid] = { uid: me.uid, id: me.sid, name: me.name, state: {} };
  const { BS, client } = makeBS(net, me, { free, av, platform });
  for (const other of net.clients) other.emit('user-joined', net.users[me.uid]);
  net.clients.push(client);
  const winListeners = {};
  const ctx = vm.createContext({
    BS, console, performance, setTimeout, setInterval, clearTimeout, clearInterval, structuredClone,
    ...(noIndexedDB ? {} : { indexedDB: fakeIndexedDB(dbs) }),
    IDBKeyRange: { bound: (lower, upper) => ({ lower, upper }) },
    location: { origin: 'https://thepolys.worldspace.host', hostname: 'thepolys.worldspace.host' },
    navigator: { storage: { estimate: async () => ({ quota: client.free + 1e8, usage: 1e8 }) } },
    fetch: fetch || (async () => { throw new Error('no helper'); }),
    addEventListener: (n, f) => { winListeners[n] = f; },
    removeEventListener: (n, f) => { if (winListeners[n] === f) delete winListeners[n]; },
    XRTM_CONFIG: { log: process.env.XRTM_LOG ? (...a) => console.log("[XRTM]", ...a) : () => {}, ...config },
  });
  ctx.window = ctx;
  vm.runInContext(scriptSource(), ctx, { filename: 'xrtm-world.js' });
  await winListeners['bs-loaded']?.();
  Object.assign(client, { dbs, winListeners, ctx, get XRTM() { return ctx.XRTM; } });
  // Finders for the tests.
  client.button = (text) => client.ui.findLast((e) => e.click && !e.destroyed && (typeof text === 'function' ? text(String(e.text)) : String(e.text) === text));
  client.named = (name) => client.objects.findLast((o) => o.name === name && !o.destroyed);
  return client;
}

export function leaveClient(net, client) {
  if (net.users[client.me.uid]?.id === client.me.sid) delete net.users[client.me.uid];
  net.clients = net.clients.filter((c) => c !== client);
  for (const c of net.clients) c.emit('user-left', { uid: client.me.uid, id: client.me.sid });
}
