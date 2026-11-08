// XR Time Machine adapter for Altspace worlds (Creator SDK world script). Everything that touches BS is here;
// the format, scheduling, storage budget and breaker are in xrtm-core.js. Built together into one block of the
// world's Assets/WebRoot/script.js by XRTimeMachine/install.mjs (see plugin.json).
//
// What it does
//   - World owners and moderators get a recorder panel: F9 on desktop, or the small REC button on the left wrist
//     in a headset. A recording belongs to the device it was started on: each device writes its own, so one
//     account in the space twice (two headsets, or a PC and a headset) can record on both at once.
//   - Each recording device announces itself in the protected key "xrtm.recs.<session id>"; everyone sees
//     "This session is being recorded by <name>" when it starts and when they arrive during one.
//   - What a world script can see is written on one clock from zero, in world coordinates: who's here, joins and
//     leaves, user-state and space-state changes, the recording player's own head and hands, tracked objects,
//     chapter markers. Lines are written to the device about once a second and dropped from memory:
//     IndexedDB always (Windows and Quest), plus the Windows helper when it's running, which writes .xrtm files
//     to Documents\AltspaceVR\XRTimeMachine\ on the PC's own drive.
//   - Video and sound: the app's own recorder (BS.Recording) on the same device, compressed MP4 straight to the
//     device's Videos folder (PC) or Movies folder (Quest), started and stopped with the recording. It never
//     passes through this page's memory. The .xrtm file notes when it started, so the two line up.
//   - Storage: a warning at the start under 3 GB free; under 1 GB a lasting warning with a countdown; at
//     100 MB the recording stops, so the device keeps room to work.
//   - Playback in the original location, seen by everyone present: the device that has the recording is the
//     conductor. The shared clock is the protected key "xrtm.play"; the lines stream in one-shots a couple of
//     seconds ahead, with keyframes for late arrivals. A stand-in head and hands, tracked objects moved,
//     joins/leaves/user-state as a caption. One playback at a time.
//
// Failing safely
//   - window.XRTM_CONFIG.enabled = false: does nothing at all.
//   - Missing SDK features: turns itself off for the visit, one log line.
//   - Five errors within a minute: removes everything it made, stops (saving what's recorded), stays off for the visit.
//   - The protected key "xrtm.off": the owner turns it off for everyone in the space at once, from the panel
//     or the browser console (XRTM.off() / XRTM.on()). It touches only "xrtm." keys and its own one-shots.

    const C = XRTMCore;

    const XRTM = {
        version: "0.4.0",
        enabled: true,
        helperUrl: "http://localhost:47800",   // xrtm-helper.ps1 on Windows
        toggleKeyCode: 290,                     // Unity KeyCode F9
        inHeadset: true,                        // false: no recorder panel or REC button in a headset (desktop only)
        wristButton: true,                      // false: no REC button on the forearm in a headset
        // The REC button: on this avatar bone, at this offset (metres) and turn (degrees); a disc this size; a tap from
        // the right hand counts on touchLayer (13, UserLayer9, the layer hands touch), at most once per touchMs.
        wrist: { bone: "LEFTARM_LOWER", position: [0, 0.03, 0], rotation: [0, 0, 0], radius: 0.035, thickness: 0.008, fontSize: 0.12, touchLayer: 13, touchMs: 800 },
        poseHz: 20,                             // most self and object poses per second (unchanged ones aren't written)
        flushMs: 1000,                          // lines wait in memory this long, then go to the device
        maxPendingWrites: 30,                   // writes waiting on a slow device before recording stops (memory guard)
        trackObjects: [],                       // object names to record, e.g. ["Poly Trophy Body"]
        storage: {
            warnBytes: 3e9,                     // warn at the start under this
            countdownBytes: 1e9,                // a lasting warning with the time left under this
            stopBytes: 1e8,                     // stop recording here: room for the device owner to work
            checkMs: 10000,
        },
        av: {
            enabled: true,                      // video and sound with each recording, by the app's own recorder
            preset: "Low",                      // "Low" 1280×720 30 fps: the smallest files
            bytesPerSec: 400000,                // expected MP4 size, for the countdown until measured; unverified
        },
        noticeSeconds: 5,
        allowInPlayMode: true,                  // Play mode can't check ownership; let the editor test the panel
        breaker: { max: 5, windowMs: 60000 },
        recKey: "xrtm.recs",                    // + ".<session id>", one per recording device
        heartbeatMs: 30000,                     // a recording refreshes its key this often; 3 missed and it's over
        playStateKey: "xrtm.play",
        offKey: "xrtm.off",
        playHz: 30,                             // how often each player's copy updates the stand-in
        pumpMs: 250,                            // how often the conductor sends the next lines
        playAheadMs: 2000,                      // how far ahead of the playhead lines are sent
        keyframeMs: 3000,                       // a full keyframe this often, for people who arrive mid-playback
        oneShotBytes: 3600,                     // one-shots are capped near 4 KB; leave room for the wrapper
        scrubDebounceMs: 250,                   // dragging the slider jumps once it settles
        ghostColor: [0.35, 0.8, 1, 0.55],       // the stand-in's tint, RGBA 0–1
        // Sizes, kept here because panel readability on a device is still unverified.
        ui: {
            panelScale: 0.1,                    // world size of the panel: 560 px wide = 0.56 m at 0.1
            anchor: null,                       // a scene object's name (a desk mount): the panel is built into it
                                                // there, opening on the Sequences tab, instead of in front of the player
            anchorScale: 0.06,                  // its size there: 560 px = 0.34 m
            panelWidth: 560,
            panelHeight: 960,
            fontScale: 1,                       // multiplies every font size on the panel
            listHeight: 220,                    // the recordings list
            chapterListHeight: 150,
            noticeSize: 0.11,
            ghostLabelFontSize: 1,
            ghostLabelHeight: 0.35,             // metres above the stand-in's head
        },
        log: (...a) => console.log("[XRTM]", ...a),
        state: "loading",                       // loading, on, off, tripped, disabled, unsupported
    };
    // The world's settings (the XR Time Machine config block above this one). Nested groups merge, so
    // { ui: { fontScale: 1.4 } } changes only that size.
    const config = window.XRTM_CONFIG || {};
    for (const [k, v] of Object.entries(config)) {
        XRTM[k] = v && typeof v === "object" && !Array.isArray(v) && XRTM[k] && typeof XRTM[k] === "object" ? { ...XRTM[k], ...v } : v;
    }
    window.XRTM = XRTM;

    if (XRTM.enabled === false) {
        XRTM.state = "disabled";
        XRTM.log("disabled in this world's config");
        return;
    }
    XRTM.log("loaded", XRTM.version);

    const log = (...a) => XRTM.log(...a);
    const brk = C.breaker({ ...XRTM.breaker, log, onTrip: () => down("tripped") });
    const guard = brk.guard;

    let scene = null;
    let life = null;        // everything the running plugin made, removed by down()

    window.addEventListener("bs-loaded", guard(async () => {
        if (typeof BS === "undefined" || !BS.Scene?.GetInstance) return unsupported("no Creator SDK");
        scene = BS.Scene.GetInstance();
        await scene.WaitForUnityLoaded();
        const missing = ["On", "SpaceStateSet", "SpaceStateDelete", "OneShot"].filter((f) => typeof scene[f] !== "function");
        if (missing.length) return unsupported(`missing ${missing.join(", ")}`);
        watchOffSwitch();
        if (offState()) await downTo("off"); else await up();
    }, "start"));

    function unsupported(why) {
        XRTM.state = "unsupported";
        log("off for this visit:", why);
    }

    // ---------- lifecycle ----------

    // Everything one run of the plugin makes, so it can all be removed: listeners, timers, scene objects.
    function newLife() {
        const offs = [];
        const timers = [];
        const objects = new Set();
        const stops = [];
        const l = {
            disposed: false,
            on(name, fn, where) {
                const g = guard((...a) => (l.disposed ? undefined : fn(...a)), where || name);
                scene.On(name, g);
                offs.push(() => scene.Off?.(name, g));
            },
            every(fn, ms, where) { const id = setInterval(guard(() => (l.disposed ? undefined : fn()), where), ms); timers.push(id); return id; },
            later(fn, ms, where) { const id = setTimeout(guard(() => (l.disposed ? undefined : fn()), where), ms); timers.push(id); return id; },
            obj(o) { objects.add(o); return o; },
            onDispose(fn) { stops.push(fn); },
            async dispose() {
                if (l.disposed) return;
                l.disposed = true;
                // What people see and what listens goes at once; then recordings and playback finish saving.
                for (const off of offs) { try { off(); } catch { /* gone already */ } }
                for (const id of timers) { clearInterval(id); clearTimeout(id); }
                for (const o of objects) { try { o.Destroy?.(); } catch { /* gone already */ } }
                for (const fn of stops.reverse()) { try { await fn(); } catch (e) { log("cleanup failed:", e); } }
            },
        };
        return l;
    }

    async function up() {
        if (brk.tripped || (life && !life.disposed && XRTM.state === "on")) return;
        await life?.dispose();
        life = newLife();
        XRTM.state = "on";
        try {
            await start(life);
        } catch (e) {
            brk.hit(e, "start");
        }
    }

    // down(): leave the world as it was. "tripped" stays down for the visit; "off" waits for the key to clear.
    let downing = null;
    function down(reason) {
        downing = downTo(reason);
        return downing;
    }
    async function downTo(reason) {
        XRTM.state = reason;
        const l = life;
        life = null;
        await l?.dispose();
        if (reason === "tripped") log("too many errors: XR Time Machine has removed itself for this visit");
        if (reason === "off") {
            log("turned off in this space");
            if (scene && await mayRecord() && !(await panelOffHere())) { life = newLife(); await offPanel(life).catch((e) => log("off panel failed:", e)); }
        }
    }

    function offState() {
        return readJson(XRTM.offKey);
    }

    // The off switch: one protected key. It outlives any run of the plugin, so it can bring it back.
    function watchOffSwitch() {
        scene.On("space-state", guard((e) => {
            if (brk.tripped) return;
            if (!e.detail.changes.some((c) => c.path === XRTM.offKey)) return;
            if (offState()) { if (XRTM.state !== "off") down("off"); }
            else if (XRTM.state === "off") up();
        }, "off switch"));
    }

    XRTM.off = async () => {
        await scene.SpaceStateSet(XRTM.offKey, JSON.stringify({ by: scene.localUser?.name || "someone", at: new Date().toISOString() }), { protected: true });
        if (XRTM.state !== "off") await down("off");
    };
    XRTM.on = async () => {
        await scene.SpaceStateDelete(XRTM.offKey, { protected: true });
        if (XRTM.state === "off") await up();
    };

    // ---------- shared state ----------

    function readJson(key) {
        const raw = scene?.spaceStateJson?.protected?.[key];
        if (raw == null) return null;
        try { return typeof raw === "string" ? JSON.parse(raw) : raw; } catch { return null; }
    }

    const myRecKey = () => `${XRTM.recKey}.${C.keyPart(scene.localUser?.id)}`;

    // Every recording in progress, one per device; stale ones (that device has gone) left out.
    function liveRecordings() {
        const all = scene.spaceStateJson?.protected || {};
        return Object.keys(all)
            .filter((k) => k.startsWith(`${XRTM.recKey}.`))
            .map((k) => ({ key: k, s: readJson(k) }))
            .filter(({ s }) => s && alive(s) && C.present(scene.users, s.bySid, s.byUid));
    }

    // A recording's key is refreshed every heartbeatMs while it records. Presence alone can't tell: the user list has
    // one entry per account, so the same account on another device kept a recording "live" that its own device had
    // left behind, and everyone kept being told they were recorded (The Polys, 2026-10-30).
    function alive(s) {
        const at = Date.parse(s.aliveUtc || s.startedUtc || "");
        return Number.isFinite(at) && Date.now() - at < XRTM.heartbeatMs * 3;
    }

    // "xrtm.play": { id, name, recordedBy, by, byUid, bySid, durationMs, chapters, session, playing, atT, atUtc }.
    function livePlayState() {
        const s = readJson(XRTM.playStateKey);
        return s && C.present(scene.users, s.bySid, s.byUid) ? s : null;
    }

    // ---------- storage ----------

    // IndexedDB: "recordings" holds each recording's summary, "chunks" its lines in order.
    const store = {
        db: null,
        async open() {
            if (this.db) return this.db;
            this.db = await new Promise((resolve, reject) => {
                const req = indexedDB.open("xrtm", 1);
                req.onupgradeneeded = () => {
                    const db = req.result;
                    db.createObjectStore("recordings", { keyPath: "id" });
                    db.createObjectStore("chunks", { keyPath: ["id", "seq"] });
                };
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
            return this.db;
        },
        async tx(stores, mode, fn) {
            const db = await this.open();
            return new Promise((resolve, reject) => {
                const t = db.transaction(stores, mode);
                let result;
                t.oncomplete = () => resolve(result);
                t.onerror = () => reject(t.error);
                t.onabort = () => reject(t.error);
                result = fn(t);
            });
        },
        putMeta(meta) {
            return this.tx(["recordings"], "readwrite", (t) => t.objectStore("recordings").put(meta));
        },
        appendChunk(id, seq, text) {
            return this.tx(["chunks"], "readwrite", (t) => t.objectStore("chunks").put({ id, seq, text }));
        },
        async list() {
            const db = await this.open();
            return new Promise((resolve, reject) => {
                const req = db.transaction("recordings").objectStore("recordings").getAll();
                req.onsuccess = () => resolve(req.result.sort((a, b) => (b.startedUtc || "").localeCompare(a.startedUtc || "")));
                req.onerror = () => reject(req.error);
            });
        },
        async load(id) {
            const db = await this.open();
            const chunks = await new Promise((resolve, reject) => {
                const req = db.transaction("chunks").objectStore("chunks").getAll(IDBKeyRange.bound([id, 0], [id, Infinity]));
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
            return C.parseLines(chunks.filter((c) => c.id === id).sort((a, b) => a.seq - b.seq).map((c) => c.text).join(""));
        },
        remove(id) {
            return this.tx(["recordings", "chunks"], "readwrite", (t) => {
                t.objectStore("recordings").delete(id);
                t.objectStore("chunks").delete(IDBKeyRange.bound([id, 0], [id, Infinity]));
            });
        },
    };

    // The Windows helper, when it's running. Every call is best effort: IndexedDB has the data regardless.
    const helper = {
        available: false,
        folder: null,
        free: null,             // free bytes on the drive it writes to
        async probe() {
            try {
                const r = await fetch(`${XRTM.helperUrl}/xrtm/ping`, { cache: "no-store" });
                const j = await r.json();
                this.available = !!j.ok;
                this.folder = j.folder || null;
                this.free = typeof j.free === "number" ? j.free : null;
            } catch {
                this.available = false;
                this.free = null;
            }
            return this.available;
        },
        async call(path, body, method = "POST") {
            if (!this.available) return false;
            try {
                const r = await fetch(`${XRTM.helperUrl}${path}`, { method, body, headers: { "Content-Type": "text/plain" } });
                return r.ok;
            } catch (e) {
                log("helper unreachable:", e.message);
                this.available = false;
                return false;
            }
        },
        append: (id, text) => helper.call(`/xrtm/append?id=${encodeURIComponent(id)}`, text),
        remove: (id) => helper.call(`/xrtm/delete?id=${encodeURIComponent(id)}`, "", "POST"),
    };

    // Free space where recordings go: the helper's drive (exact) on Windows, else what the app's storage allows.
    async function freeSpace() {
        await helper.probe();
        if (helper.free != null) return { free: helper.free, where: `${helper.folder} (this PC's drive)` };
        try {
            const { quota, usage } = await navigator.storage.estimate();
            return { free: quota - usage, where: "this device (app storage)" };
        } catch {
            return { free: null, where: "this device (app storage)" };
        }
    }

    // ---------- the recorder ----------

    function createRecorder(l, onChange) {
        let rec = null;          // the recording in progress
        let beat = null;         // its heartbeat timer (kept off rec, which is stored)
        let lines = [];          // buffered, flushed every flushMs and then dropped
        let seq = 0;
        let t0 = 0;
        let flushing = Promise.resolve();
        let pending = 0;         // writes not yet on the device
        let offs = [];
        let banner = null;
        let watch = null;
        const lastSample = new Map();
        let changed = C.changeFilter();

        const t = () => Math.round((performance.now() - t0) * 10) / 10; // ms, to 0.1 ms
        const write = (type, data) => lines.push(JSON.stringify({ t: t(), type, ...data }));
        const due = (key) => {
            const now = performance.now();
            if (now - (lastSample.get(key) || -1e9) < 1000 / XRTM.poseHz) return false;
            lastSample.set(key, now);
            return true;
        };

        function flush() {
            if (!rec || lines.length === 0) return flushing;
            if (pending >= XRTM.maxPendingWrites) {
                stop("This device isn't saving fast enough, so recording stopped before memory filled up.");
                return flushing;
            }
            const text = lines.join("\n") + "\n";
            lines = [];
            const n = seq++;
            const id = rec.id;
            rec.bytes += text.length;
            pending++;
            // Chained so chunks land in order; the text is released once both sinks have it.
            flushing = flushing.then(async () => {
                try { await store.appendChunk(id, n, text); } catch (e) { log("store write failed:", e); }
                await helper.append(id, text);
                pending--;
            });
            return flushing;
        }

        function userInfo(u) {
            return { uid: u.uid, sid: u.id, name: u.name, local: !!u.isLocal, state: u.state || {} };
        }

        let checking = false;
        async function checkStorage(first) {
            if (!rec || checking) return;
            checking = true;
            try { await storageCheck(first); } finally { checking = false; }
        }
        async function storageCheck(first) {
            const { free, where } = await freeSpace();
            if (!rec) return;
            const elapsed = Math.max(1, (performance.now() - t0) / 1000);
            const expected = rec.bytes / elapsed + (rec.av.ours ? XRTM.av.bytesPerSec : 0);
            const s = watch.update(free, performance.now(), expected);
            rec.storage = { ...s, where };
            if (s.level === "stop") {
                await stop(`Recording stopped: only ${C.bytes(free)} left on ${where}. Free up space to record again.`);
                return;
            }
            if (s.level === "countdown") {
                const text = `Storage low: ${C.bytes(free)} free · ${C.duration(s.secondsLeft)} of recording left`;
                if (banner) (await banner).set(text);
                else banner = headPanel(l, text, { y: -0.3, color: "#f9a825" });
            } else if (first && s.level === "low") {
                timedNotice(l, `Low storage: ${C.bytes(free)} free on ${where}`, "#f9a825");
            }
            onChange();
        }

        // Video and sound by the app's own recorder, on this device only.
        async function startAv() {
            const av = { ours: false, note: "" };
            if (!XRTM.av.enabled) { av.note = "Video and sound: off in this world's settings"; return av; }
            if (!BS.Recording?.info) { av.note = "Video and sound: not available in this app"; return av; }
            const info = await BS.Recording.info();
            if (!info.canRecord) {
                av.note = info.reason === "already_recording" ? "Video and sound: you're already recording video" : `Video and sound: not available here (${info.reason})`;
                write("av", { event: "unavailable", reason: info.reason });
                return av;
            }
            try {
                const off = BS.Recording.on?.("state", guard((s) => {
                    if (rec) write("av", { event: "state", state: s.state, takeId: s.takeId, error: s.error, durationSeconds: s.durationSeconds });
                }, "video state"));
                if (typeof off === "function") offs.push(off);
                const { takeId } = await BS.Recording.start({ preset: XRTM.av.preset, title: rec.name });
                write("av", { event: "start", takeId, preset: XRTM.av.preset, platform: info.platform });
                av.ours = true;
                av.takeId = takeId;
                av.note = `Video and sound: recording to this ${info.platform === "android" ? "headset's Movies" : "PC's Videos"} folder`;
            } catch (e) {
                av.note = `Video and sound: couldn't start (${e.code || e.message || e})`;
                write("av", { event: "failed", code: e.code || String(e) });
            }
            return av;
        }

        async function start(by) {
            if (rec) return rec;
            const first = await freeSpace();
            if (first.free != null && first.free <= XRTM.storage.stopBytes) {
                throw Object.assign(new Error(`Only ${C.bytes(first.free)} free on ${first.where}: not enough to record.`), { code: "storage" });
            }
            const world = await worldInfo();
            const startedUtc = new Date().toISOString();
            const me = scene.localUser || {};
            const id = C.recordingId(world.slug, startedUtc, me.id);
            rec = { id, name: `${world.slug || "world"} ${startedUtc.slice(0, 16).replace("T", " ")}`, world, startedUtc, by, bytes: 0, status: "recording", chapters: 0, av: { ours: false, note: "" } };
            t0 = performance.now();
            seq = 0;
            lines = [];
            changed = C.changeFilter();
            lastSample.clear();
            watch = C.storageWatch(XRTM.storage);

            const announced = { id, by, byUid: me.uid, bySid: me.id, startedUtc };
            try {
                await scene.SpaceStateSet(myRecKey(), JSON.stringify({ ...announced, aliveUtc: startedUtc }), { protected: true });
            } catch (e) {
                rec = null;
                throw Object.assign(new Error("You don't have permission to record in this world."), { code: e.code || "not_authorized" });
            }
            // The heartbeat: a key not refreshed for a while is a recording whose device went without stopping (see alive)
            beat = l.every(() => {
                if (rec?.id !== id) return;
                scene.SpaceStateSet(myRecKey(), JSON.stringify({ ...announced, aliveUtc: new Date().toISOString() }), { protected: true })
                    .catch((e) => log("heartbeat failed:", e.code || e));
            }, XRTM.heartbeatMs, "recording heartbeat");
            await store.putMeta(stored(rec));

            lines.push(JSON.stringify(C.header({
                id, name: rec.name, startedUtc, world, by, device: { sid: me.id },
                app: "xrtm (Altspace adapter)", appVersion: XRTM.version, poseHz: XRTM.poseHz, layers: ["world-script"],
            })));
            write("roster", { users: Object.values(scene.users || {}).map(userInfo) });
            write("space_state", { full: true, public: scene.spaceStateJson?.public || {}, protected: scene.spaceStateJson?.protected || {} });

            const on = (name, fn) => {
                const g = guard((e) => (rec ? fn(e) : undefined), `recording ${name}`);
                scene.On(name, g);
                offs.push(() => scene.Off?.(name, g));
            };
            on("user-joined", (e) => write("join", { user: userInfo(e.detail) }));
            on("user-left", (e) => write("leave", { uid: e.detail.uid, sid: e.detail.id }));
            on("user-state", (e) => write("user_state", { uid: e.detail.uid, sid: e.detail.id, full: !!e.detail.full, changes: e.detail.changes }));
            on("space-state", (e) => write("space_state", { full: !!e.detail.full, changes: e.detail.changes }));
            on("pose-update", (e) => {
                const { head, leftHand, rightHand } = e.detail;
                const pose = { head: C.quantize(head), left: C.quantize(leftHand), right: C.quantize(rightHand) };
                if (!due("self") || !changed("self", pose)) return;
                write("self_pose", { uid: scene.localUser?.uid, sid: scene.localUser?.id, ...pose });
            });
            for (const name of XRTM.trackObjects) {
                const obj = await scene.Find(name);
                if (!obj) { log("track: not found", name); continue; }
                write("object", { name, ref: { kind: "scene", path: name } });
                await obj.WatchTransform([BS.PN.position, BS.PN.rotation], guard((tr) => {
                    if (!rec) return;
                    const pose = C.quantize(tr);
                    if (pose && due(`obj:${name}`) && changed(`obj:${name}`, pose)) write("object_pose", { name, ...pose });
                }, "tracked object"));
            }

            rec.av = await startAv();
            const flushTimer = setInterval(guard(flush, "save"), XRTM.flushMs);
            const storageTimer = setInterval(guard(() => checkStorage(false), "storage check"), XRTM.storage.checkMs);
            offs.push(() => clearInterval(flushTimer), () => clearInterval(storageTimer));
            await checkStorage(true);
            onChange();
            log("recording", id, helper.available ? `(helper: ${helper.folder})` : "(device storage only)", rec.av.note);
            return rec;
        }

        async function chapter(label) {
            if (!rec) return;
            rec.chapters++;
            write("chapter", { label: label || `Chapter ${rec.chapters}` });
            onChange();
        }

        let stopping = null;
        function stop(reason) {
            if (!rec) return Promise.resolve(null);
            stopping ??= finish(reason).finally(() => { stopping = null; });
            return stopping;
        }
        async function finish(reason) {
            for (const off of offs.splice(0)) { try { off(); } catch { /* gone already */ } }
            const done = rec;
            clearInterval(beat);
            if (done.av.ours) await BS.Recording.stop().catch((e) => log("video stop failed:", e.code || e));
            const durationMs = t();
            write("end", { endedUtc: new Date().toISOString(), durationMs, ...(reason ? { reason } : {}) });
            await flush();
            rec = null; // after the flush: flush() needs it
            await flushing;
            const meta = { ...stored(done), status: "complete", durationMs, endedUtc: new Date().toISOString(), ...(reason ? { stoppedBecause: reason } : {}) };
            await store.putMeta(meta);
            await scene.SpaceStateDelete(myRecKey(), { protected: true }).catch((e) => log("clear state failed:", e.code || e));
            const b = banner;
            banner = null;
            b?.then((p) => p.close()).catch(() => {}); // shrinks away; stopping doesn't wait for it
            if (reason) {
                lastStop = reason;
                timedNotice(l, reason, "#e53935", 3);
            }
            onChange();
            log("stopped", done.id, `${Math.round(durationMs / 1000)} s, ${done.bytes} bytes`, reason || "");
            return meta;
        }
        let lastStop = "";

        // What goes in the library: the summary without the live parts.
        function stored(r) {
            const { av, storage, ...rest } = r;
            return { ...rest, ...(av?.takeId ? { videoTakeId: av.takeId } : {}) };
        }

        l.onDispose(() => stop());

        return {
            start, stop, chapter,
            get current() { return rec; },
            get lastStop() { return lastStop; },
            elapsedMs: () => (rec ? performance.now() - t0 : 0),
        };
    }

    async function worldInfo() {
        try {
            const info = await BS.PersistFileBridge.info(scene);
            return { id: info.worldId ?? null, slug: info.slug ?? null, url: info.url ?? location.origin };
        } catch {
            return { id: null, slug: location.hostname.split(".")[0] || null, url: location.origin };
        }
    }

    // ---------- who may record ----------

    async function mayRecord() {
        try {
            const info = await BS.PersistFileBridge.info(scene);
            if (info.canWrite) return true;                 // the world owner, signed in
            if (/not available in this build/i.test(info.reason || "")) return XRTM.allowInPlayMode;
        } catch { /* fall through */ }
        return !!scene.localUser?.isSpaceAdmin;
    }

    const v3of = (a) => new BS.Vector3(a[0], a[1], a[2]);
    const q4of = (a) => new BS.Quaternion(a[0], a[1], a[2], a[3]);

    // ---------- playback: every player's copy (the viewer) ----------

    function createViewer(l) {
        let state = null;           // the current "xrtm.play"
        let anchor = 0;             // performance.now() when the playhead was state.atT
        let buffer = [];            // { id, s, from, line } received and not yet shown
        let timer = null;
        let ghost = null;           // Promise of the stand-in's objects
        let labelText = "";
        let events = [];            // { text, until } for the caption
        const present = new Map();  // session id (or account id) -> name, from the recording
        const objects = new Map();  // name -> Promise<{ obj, home } | null>
        const who = (l) => l.sid || l.uid;

        function playhead() {
            if (!state) return 0;
            return Math.min(state.durationMs, state.atT + (state.playing ? performance.now() - anchor : 0));
        }

        // `live`: the change just happened. Otherwise this is the snapshot on arrival, so the clock is placed
        // from atUtc (the two devices' clocks may differ a little).
        function setState(next, live) {
            if (!next) return teardown();
            if (state && next.id === state.id && next.session === state.session && next.playing === state.playing && next.atT === state.atT) return;
            if (!state || state.id !== next.id) {
                teardown();
                ghost = buildGhost(l, next).catch((e) => { log("stand-in failed:", e); return null; });
                timer = setInterval(guard(render, "playback"), 1000 / XRTM.playHz);
            }
            state = next;
            anchor = live ? performance.now() : performance.now() - C.clamp(Date.now() - next.atUtc, 0, 6e4);
            buffer = buffer.filter((e) => e.id === next.id && e.s >= next.session && e.from === next.bySid);
        }

        // A packet from the conductor's one-shot (or straight from the conductor on its own device).
        function receive(p, from) {
            if (state && (p.id !== state.id || p.s < state.session || from !== state.bySid)) return;
            for (const line of p.lines || []) buffer.push({ id: p.id, s: p.s, from, line });
            if (buffer.length > 20000) buffer.splice(0, buffer.length - 20000);
        }

        function render() {
            if (!state) return;
            const now = playhead();
            const due = [];
            const keep = [];
            for (const e of buffer) {
                if (e.id !== state.id || e.s < state.session) continue;
                (e.s === state.session && e.line.t <= now ? due : keep).push(e);
            }
            buffer = keep;
            due.sort((a, b) => a.line.t - b.line.t);
            let pose = null;
            const moved = new Map();
            for (const { line } of due) {
                const name = (x) => present.get(who(x)) || "Someone";
                switch (line.type) {
                    case "self_pose": pose = line; break;
                    case "object_pose": moved.set(line.name, line); break;
                    case "roster":
                        present.clear();
                        for (const u of line.users || []) present.set(who(u), u.name);
                        break;
                    case "join":
                        present.set(who(line.user), line.user.name);
                        note(`${line.user.name} joined`);
                        break;
                    case "leave":
                        note(`${name(line)} left`);
                        present.delete(who(line));
                        break;
                    case "user_state":
                        for (const c of line.changes || []) note(`${name(line)} ${C.describeChange(c)}`);
                        break;
                    case "chapter": note(`Chapter: ${line.label}`); break;
                }
            }
            if (pose) queuePose(pose);
            for (const m of moved.values()) moveObject(m);
            updateLabel().catch((e) => brk.hit(e, "caption"));
        }

        function note(text) {
            events.push({ text, until: performance.now() + 5000 });
            if (events.length > 3) events.shift();
        }

        async function updateLabel() {
            const g = await ghost;
            if (!g || !state) return;
            const t = performance.now();
            events = events.filter((e) => e.until > t);
            const text = [`${state.recordedBy} (recorded)`, `${present.size} here`, ...events.map((e) => e.text)].join("\n");
            if (text !== labelText) { labelText = text; g.text.text = text; }
        }

        // One stand-in move at a time, and only the newest pose waits: a move is several calls to Unity, and teardown
        // destroying the stand-in partway through one made the app throw (SetJsTransform, Windows app 2026-10-30).
        let nextPose = null, posing = null;
        function queuePose(p) {
            nextPose = p;
            if (posing) return;
            posing = (async () => {
                while (nextPose) {
                    const q = nextPose;
                    nextPose = null;
                    await showPose(q).catch((e) => brk.hit(e, "stand-in pose"));
                }
                posing = null;
            })();
        }

        async function showPose(p) {
            const g = await ghost;
            if (!g || g.id !== state?.id) return;
            if (p.head?.p) {
                await g.head.SetPosition(v3of(p.head.p));
                if (p.head.r) await g.head.SetRotation(q4of(p.head.r));
                const f = forward(p.head.r && { x: p.head.r[0], y: p.head.r[1], z: p.head.r[2], w: p.head.r[3] });
                await g.tag.SetPosition(new BS.Vector3(p.head.p[0], p.head.p[1] + XRTM.ui.ghostLabelHeight, p.head.p[2]));
                await g.tag.SetRotation(yawRotation({ x: -f.x, z: -f.z })); // text reads from −Z: face whoever faces them
                if (!g.shown) { g.shown = true; await g.head.SetActive(true); await g.tag.SetActive(true); }
            }
            for (const side of ["left", "right"]) {
                const hand = g[side];
                const h = p[side];
                if (h?.p) {
                    await hand.SetPosition(v3of(h.p));
                    if (h.r) await hand.SetRotation(q4of(h.r));
                }
                if (!!h?.p !== g.handsOn[side]) { g.handsOn[side] = !!h?.p; await hand.SetActive(!!h?.p); }
            }
        }

        // Missing objects are skipped silently, as if they were never there (logged once).
        function moveObject(m) {
            let entry = objects.get(m.name);
            if (!entry) {
                entry = Promise.resolve(scene.Find(m.name)).then((obj) => {
                    if (!obj) { log("playback: object not in this world, skipped:", m.name); return null; }
                    const tr = obj.transform;
                    const home = tr?.position && tr?.rotation
                        ? { p: [tr.position.x, tr.position.y, tr.position.z], r: [tr.rotation.x, tr.rotation.y, tr.rotation.z, tr.rotation.w] }
                        : null;
                    return { obj, home };
                }).catch(() => null);
                objects.set(m.name, entry);
            }
            entry.then(async (o) => {
                if (!o || !state) return;
                await o.obj.SetPosition(v3of(m.p));
                if (m.r) await o.obj.SetRotation(q4of(m.r));
            }).catch((e) => log("playback: move failed:", m.name, e));
        }

        function teardown() {
            clearInterval(timer);
            timer = null;
            const old = state;
            state = null;
            const gone = ghost;
            ghost = null;
            nextPose = null;
            // after the move still on its way, if any (queuePose)
            Promise.resolve(posing).then(() => gone).then((g) => g?.parts.forEach((o) => o.Destroy?.()));
            // Put tracked objects back where they were before playback moved them.
            for (const entry of objects.values()) {
                entry.then(async (o) => {
                    if (!o?.home) return;
                    await o.obj.SetPosition(v3of(o.home.p));
                    await o.obj.SetRotation(q4of(o.home.r));
                }).catch(() => {});
            }
            objects.clear();
            present.clear();
            events = [];
            labelText = "";
            if (old) buffer = buffer.filter((e) => e.id !== old.id);
        }

        l.onDispose(teardown);
        return { setState, receive, playhead, get state() { return state; } };
    }

    // The stand-in for the person who recorded: a head with a visor (so you can see where they looked),
    // two hands, and a caption. Created inactive; shown on the first pose.
    async function buildGhost(l, state) {
        const tint = () => new BS.Material({ shaderName: "Unlit/DiffuseTransparent", color: new BS.Vector4(...XRTM.ghostColor) });
        const part = async (name, shape) => {
            const o = l.obj(new BS.GameObject({ name, active: false }));
            await o.AddComponent(shape);
            await o.AddComponent(tint());
            return o;
        };
        const head = await part("XRTM Stand-in Head", new BS.Sphere({ radius: 0.11 }));
        const visor = l.obj(new BS.GameObject({ name: "XRTM Stand-in Visor", parent: head, localPosition: new BS.Vector3(0, 0.02, 0.09) }));
        await visor.AddComponent(new BS.Box({ width: 0.16, height: 0.05, depth: 0.04 }));
        await visor.AddComponent(new BS.Material({ shaderName: "Unlit/Diffuse", color: new BS.Vector4(0.1, 0.1, 0.12, 1) }));
        const left = await part("XRTM Stand-in Left Hand", new BS.Sphere({ radius: 0.045 }));
        const right = await part("XRTM Stand-in Right Hand", new BS.Sphere({ radius: 0.045 }));
        const tag = l.obj(new BS.GameObject({ name: "XRTM Stand-in Label", active: false }));
        const text = await tag.AddComponent(new BS.Text({
            text: `${state.recordedBy} (recorded)`,
            fontSize: XRTM.ui.ghostLabelFontSize,
            color: new BS.Vector4(1, 1, 1, 1),
            horizontalAlignment: 1,  // Center
            verticalAlignment: 2,    // Bottom: grows upwards from just above the head
            rectTransformSizeDelta: new BS.Vector2(2, 1),
        }));
        return { id: state.id, head, left, right, tag, text, parts: [visor, head, left, right, tag], shown: false, handsOn: { left: false, right: false } };
    }

    function watchPlayState(l, viewer) {
        const check = (live) => viewer.setState(livePlayState(), live);
        l.on("space-state", (e) => {
            if (e.detail.changes.some((c) => c.path === XRTM.playStateKey)) check(!e.detail.full);
        });
        l.on("user-left", () => check(true)); // the conductor left: stop showing it
        l.on("one-shot", (e) => {
            let msg;
            try { msg = JSON.parse(e.detail.data); } catch { return; } // not one of ours
            if (msg?.xrtm === "pb") viewer.receive(msg, e.detail.fromId);
        });
        check(false); // arriving during a playback
    }

    // ---------- playback: the conductor (the device that has the recording) ----------

    function createConductor(l, viewer, onChange) {
        let cur = null;     // C.prepare(): { id, name, recordedBy, lines, durationMs, chapters }
        let clock = null;   // this device's copy of the shared clock: { playing, atT, atPerf }
        let session = 0;
        let sentT = 0;      // lines up to here have been sent
        let lastKey = 0;
        let pump = null;
        const me = () => scene.localUser || {};

        const position = () => (!cur ? 0 : Math.min(cur.durationMs, clock.atT + (clock.playing ? performance.now() - clock.atPerf : 0)));

        function publish() {
            return scene.SpaceStateSet(XRTM.playStateKey, JSON.stringify({
                id: cur.id, name: cur.name, recordedBy: cur.recordedBy,
                by: me().name || "someone", byUid: me().uid, bySid: me().id,
                durationMs: cur.durationMs, chapters: cur.chapters,
                session, playing: clock.playing, atT: Math.round(clock.atT), atUtc: Date.now(),
            }), { protected: true });
        }

        async function load(meta) {
            if (cur) await stop();
            cur = C.prepare(await store.load(meta.id), meta);
            session = 0;
            try {
                await go(0, true);
            } catch (e) {
                cur = null; clock = null;
                throw e;
            }
            pump = setInterval(guard(tick, "playback send"), XRTM.pumpMs);
            log("playing", cur.id, `${cur.lines.length} lines`);
        }

        // Move the shared clock. A new session means everyone drops what they'd buffered and waits for the keyframe.
        async function go(t, playing) {
            session++;
            t = C.clamp(t, 0, cur.durationMs);
            clock = { playing, atT: t, atPerf: performance.now() };
            sentT = t;
            lastKey = performance.now();
            await publish();
            send(C.keyframe(cur.lines, t));
            if (playing) sendUpTo(t + XRTM.playAheadMs);
            onChange();
        }

        // Play and pause keep the session: what's buffered is still good.
        async function setPlaying(playing) {
            if (!cur || clock.playing === playing) return;
            const t = position();
            if (playing && t >= cur.durationMs) return go(0, true);
            clock = { playing, atT: t, atPerf: performance.now() };
            await publish();
            onChange();
        }

        function tick() {
            if (!cur) return;
            const t = position();
            if (clock.playing) {
                sendUpTo(t + XRTM.playAheadMs);
                if (t >= cur.durationMs) { setPlaying(false).catch((e) => log("pause failed:", e)); return; }
            }
            if (performance.now() - lastKey >= XRTM.keyframeMs) {
                lastKey = performance.now();
                send(C.keyframe(cur.lines, t));
            }
        }

        function sendUpTo(limit) {
            const out = [];
            for (let i = C.firstAfter(cur.lines, sentT); i < cur.lines.length && cur.lines[i].t <= limit; i++) {
                const s = C.slim(cur.lines[i]);
                if (s) out.push(s);
            }
            sentT = Math.max(sentT, limit);
            send(out);
        }

        function send(lines) {
            for (const batch of C.pack(lines, XRTM.oneShotBytes, (x) => log("playback: line too big to send, skipped:", x.type))) {
                const p = { xrtm: "pb", id: cur.id, s: session, lines: batch };
                viewer.receive(p, me().id); // a one-shot never comes back to its sender
                Promise.resolve(scene.OneShot(p)).catch((e) => log("one-shot failed:", e));
            }
        }

        async function stop() {
            if (!cur) return;
            clearInterval(pump);
            const id = cur.id;
            cur = null;
            clock = null;
            await scene.SpaceStateDelete(XRTM.playStateKey, { protected: true }).catch((e) => log("clear playback failed:", e.code || e));
            onChange();
            log("playback stopped", id);
        }

        l.onDispose(stop);
        return {
            load, stop,
            play: () => setPlaying(true),
            pause: () => setPlaying(false),
            seek: (t) => (cur ? go(t, clock.playing) : undefined),
            get current() {
                return cur && { id: cur.id, name: cur.name, durationMs: cur.durationMs, chapters: cur.chapters, playing: clock.playing, position: position() };
            },
        };
    }

    // ---------- UI: panels in front of the player ----------

    // A small panel that follows the player's head: notices and warnings. set(text) changes it, close() removes it.
    async function headPanel(l, text, { y = -0.12, color = "#e53935" } = {}) {
        const obj = l.obj(new BS.GameObject({ name: "XRTM Notice", localScale: new BS.Vector3(0.001, 0.001, 0.001) }));
        const panel = await obj.AddComponent(new BS.UIPanel({ resolution: new BS.Vector2(560, 96) }));
        panel.SetBackgroundColor(new BS.Vector4(0.08, 0.08, 0.1, 0.85));
        const row = new BS.UIVisualElement(panel);
        row.SetStyles({ flexDirection: "row", alignItems: "center", justifyContent: "center", width: "100%", height: "100%" });
        const dot = new BS.UIVisualElement(panel, row);
        dot.SetStyles({ width: "22px", height: "22px", borderRadius: "11px", backgroundColor: color, marginRight: "14px" });
        const label = new BS.UILabel(panel, row);
        label.text = text;
        label.SetStyles({ fontSize: "24px", color: "#ffffff" });
        await obj.AddComponent(new BS.AttachedObject({
            uid: "me",
            avatarAttachmentPoint: BS.AvatarBoneName.HEAD,
            attachmentPosition: new BS.Vector3(0, y, 0.9),
            autoSync: false,
            autoAttach: true,
        }));
        const size = XRTM.ui.noticeSize; // 560 px at 100 px/m, scaled to about 0.6 m wide at 0.9 m
        const opening = animateScale(obj, 0, size, 250).catch(() => {}); // grows in; nothing waits for it
        let closed = false;
        return {
            label,
            set(next) { if (!closed) label.text = next; },
            async close() {
                if (closed) return;
                closed = true;
                await opening;
                await animateScale(obj, size, 0, 250).catch(() => {});
                obj.Destroy?.();
            },
        };
    }

    function timedNotice(l, text, color, times = 1) {
        headPanel(l, text, { color }).then((p) => l.later(() => p.close(), XRTM.noticeSeconds * 1000 * times, "notice"))
            .catch((e) => log("notice failed:", e));
    }

    async function animateScale(obj, from, to, ms) {
        const steps = 8;
        for (let i = 1; i <= steps; i++) {
            const k = from + (to - from) * easeOut(i / steps);
            await obj.SetLocalScale(new BS.Vector3(Math.max(k, 0.0001), Math.max(k, 0.0001), Math.max(k, 0.0001)));
            await new Promise((r) => setTimeout(r, ms / steps));
        }
    }
    const easeOut = (x) => 1 - (1 - x) ** 3;

    // Everyone: "This session is being recorded by …", once per recording, when it starts or on arrival.
    function watchRecordings(l) {
        const shown = new Set();
        const check = () => {
            for (const { key, s } of liveRecordings()) {
                if (shown.has(`${key} ${s.id}`)) continue;
                shown.add(`${key} ${s.id}`);
                timedNotice(l, `This session is being recorded by ${s.by}`, "#e53935");
            }
        };
        l.on("space-state", (e) => {
            if (e.detail.changes.some((c) => c.path.startsWith(`${XRTM.recKey}.`) || c.path === XRTM.recKey)) check();
        });
        check(); // arriving during a recording
    }

    // ---------- UI: the panel (permitted users only, local to their device) ----------

    async function buildPanel(l, recorder, conductor, show = null) {
        const U = XRTM.ui;
        const fs = (n) => `${Math.round(n * U.fontScale)}px`;
        // Built into the world (a desk) when ui.anchor names an object there; else it opens in front of the player.
        let anchor = null;
        if (U.anchor) { try { anchor = await scene.Find(U.anchor); } catch (e) { anchor = null; } }
        if (U.anchor && !anchor) log(`panel anchor "${U.anchor}" not found: the panel opens in front of you instead`);
        const size = anchor ? U.anchorScale : U.panelScale;
        const obj = l.obj(new BS.GameObject({ name: "XRTM Recorder Panel", localScale: new BS.Vector3(size, size, size),
            ...(anchor ? { parent: anchor, localPosition: new BS.Vector3(0, 0, 0) } : {}) }));
        const panel = await obj.AddComponent(new BS.UIPanel({ resolution: new BS.Vector2(U.panelWidth, U.panelHeight), enableHaptics: true }));
        panel.SetBackgroundColor(new BS.Vector4(0.07, 0.07, 0.09, 0.92));
        const root = new BS.UIVisualElement(panel);
        root.SetStyles({ width: "100%", height: "100%", padding: "24px", flexDirection: "column" });

        const el = (Type, styles, parent = root) => {
            const e = new Type(panel, parent);
            if (styles) e.SetStyles(styles);
            return e;
        };
        const button = (text, styles, parent) => {
            const b = el(BS.UIButton, { height: "52px", fontSize: fs(22), color: "#ffffff", backgroundColor: "#37474f", borderRadius: "10px", ...styles }, parent);
            b.text = text;
            return b;
        };
        const click = (b, fn, where) => b.OnClick(guard(fn, where));
        const title = el(BS.UILabel, { fontSize: fs(30), color: "#ffffff", marginBottom: "4px" });
        title.text = "XR Time Machine";
        const sub = el(BS.UILabel, { fontSize: fs(18), color: "#9aa0a6", marginBottom: "12px" });
        sub.text = `Spatial recorder prototype v${XRTM.version}`;

        const tabs = el(BS.UIVisualElement, { flexDirection: "row", marginBottom: "14px" });
        const tabShow = show ? button("Show", { flexGrow: "1", marginRight: "6px" }, tabs) : null;
        const tabSeq = button("Sequences", { flexGrow: "1", marginRight: "6px" }, tabs);
        const tabRec = button("Record", { flexGrow: "1", marginRight: "6px" }, tabs);
        const tabPlay = button("Playback", { flexGrow: "1" }, tabs);

        // --- the Show tab (v0.4): the presenter's cue controls. Only the presenter's device builds this panel, so
        // nothing here is ever seen by the audience. Round-ended pill keys (Ben: no square buttons). ---
        const showPane = el(BS.UIVisualElement, { flexDirection: "column" });
        const cueNow = el(BS.UILabel, { fontSize: fs(34), color: "#ffffff", marginBottom: "4px" }, showPane);
        const cueName = el(BS.UILabel, { fontSize: fs(26), color: "#f2c46b", marginBottom: "10px" }, showPane);
        const cueNext = el(BS.UILabel, { fontSize: fs(20), color: "#9aa0a6", marginBottom: "16px" }, showPane);
        const cueRow = el(BS.UIVisualElement, { flexDirection: "row", marginBottom: "10px" }, showPane);
        const cueBack = button("◀  Back", { flexGrow: "1", height: "96px", fontSize: fs(28), backgroundColor: "#37474f", borderRadius: "48px", marginRight: "8px" }, cueRow);
        const cueGo = button("Next  ▶", { flexGrow: "2", height: "96px", fontSize: fs(32), backgroundColor: "#b8860b", borderRadius: "48px" }, cueRow);
        const cueRow2 = el(BS.UIVisualElement, { flexDirection: "row", marginBottom: "10px" }, showPane);
        const cueHome = button("Cue 1", { flexGrow: "1", height: "56px", fontSize: fs(22), borderRadius: "28px", marginRight: "6px" }, cueRow2);
        const cueRehearse = button("Rehearse", { flexGrow: "1", height: "56px", fontSize: fs(22), borderRadius: "28px", marginRight: "6px" }, cueRow2);
        const cueHouse = button("End show", { flexGrow: "1", height: "56px", fontSize: fs(22), borderRadius: "28px", backgroundColor: "#3e2723" }, cueRow2);
        const cueHelp = el(BS.UILabel, { fontSize: fs(16), color: "#9aa0a6", marginBottom: "8px" }, showPane);
        cueHelp.text = "Next: A (right hand) or Right arrow.  Back: X (left hand) or Left arrow.  Home: cue 1.  R: rehearse (every 20 s).";
        const cueList = el(BS.UIScrollView, { height: `${U.panelHeight - 640}px`, width: "100%" }, showPane);
        cueList.horizontalScrolling = false;
        const cueRows = [];
        function refreshShow() {
            if (!show) return;
            const i = show.i, c = show.cue(i), n = show.cue(i + 1);
            cueNow.text = i === 0 ? "House" : `Cue ${c.id}  ·  ${i} of ${show.count}`;
            cueName.text = i === 0 ? "No show running. Next starts cue 1." : c.name;
            cueNext.text = i >= show.count ? "Last cue." : `Next: ${n.id}  ${n.name}`;
            cueRehearse.text = show.rehearsing ? "Stop rehearsal" : "Rehearse";
            cueRehearse.style.backgroundColor = show.rehearsing ? "#6a1b9a" : "#37474f";
            cueRows.forEach((b, k) => { b.style.backgroundColor = k + 1 === i ? "#b8860b" : "#263238"; });
        }
        if (show) {
            for (let k = 1; k <= show.count; k++) {
                const c = show.cue(k);
                const b = button(`${c.id}   ${c.name}`, { height: "44px", fontSize: fs(18), marginBottom: "4px", borderRadius: "22px", backgroundColor: "#263238" }, cueList);
                click(b, () => show.goto(k), "cue jump");
                cueRows.push(b);
            }
            click(cueGo, () => show.next(), "cue next");
            click(cueBack, () => show.back(), "cue back");
            click(cueHome, () => show.home(), "cue home");
            click(cueRehearse, () => show.rehearseToggle(), "cue rehearse");
            let houseArmed = false;
            click(cueHouse, () => {
                if (!houseArmed) { houseArmed = true; cueHouse.text = "Sure? Tap again"; l.later(() => { houseArmed = false; cueHouse.text = "End show"; }, 3000); return; }
                return show.house();
            }, "cue house");
            show.setUi(refreshShow);
        }

        // --- the Sequences tab: a presentation's sequences, one big button each (Sphererebro, 2026-11-07). A sequence        // is a recording on this device; a tap plays it for everyone, from the start. ---
        const seqTab = el(BS.UIVisualElement, { flexDirection: "column" });
        const seqNow = el(BS.UILabel, { fontSize: fs(22), color: "#e0e0e0", marginBottom: "8px" }, seqTab);
        const seqList = el(BS.UIScrollView, { height: `${U.panelHeight - 420}px`, width: "100%", marginBottom: "8px" }, seqTab);
        seqList.horizontalScrolling = false;
        const seqStop = button("■  Stop", { height: "56px", fontSize: fs(24), backgroundColor: "#455a64", marginBottom: "8px" }, seqTab);

        // --- the Record tab ---
        const recTab = el(BS.UIVisualElement, { flexDirection: "column" });
        const record = el(BS.UIButton, { height: "120px", fontSize: fs(34), color: "#ffffff", backgroundColor: "#c62828", borderRadius: "60px", marginBottom: "12px" }, recTab);
        const status = el(BS.UILabel, { fontSize: fs(22), color: "#e0e0e0", marginBottom: "8px" }, recTab);
        const chapterBtn = button("Add chapter marker", { marginBottom: "8px" }, recTab);
        const avLine = el(BS.UILabel, { fontSize: fs(18), color: "#9aa0a6", marginBottom: "4px" }, recTab);
        const storage = el(BS.UILabel, { fontSize: fs(18), color: "#9aa0a6", marginBottom: "14px" }, recTab);

        // --- the Playback tab ---
        const playTab = el(BS.UIVisualElement, { flexDirection: "column" });
        const nowPlaying = el(BS.UILabel, { fontSize: fs(22), color: "#ffffff", marginBottom: "4px" }, playTab);
        const time = el(BS.UILabel, { fontSize: fs(26), color: "#e0e0e0", marginBottom: "6px" }, playTab);
        const slider = el(BS.UISlider, { width: "100%", marginBottom: "10px" }, playTab);
        const transport = el(BS.UIVisualElement, { flexDirection: "row", marginBottom: "8px" }, playTab);
        const playBtn = button("▶  Play", { flexGrow: "1", height: "64px", fontSize: fs(26), backgroundColor: "#2e7d32", marginRight: "6px" }, transport);
        const stopBtn = button("■  Stop playback", { flexGrow: "1", height: "64px", fontSize: fs(22), backgroundColor: "#455a64" }, transport);
        const jumpRow = el(BS.UIVisualElement, { flexDirection: "row", alignItems: "center", marginBottom: "8px" }, playTab);
        // text fields draw dark text unless told otherwise: unreadable on this panel (Windows app, 2026-10-30)
        const jumpField = el(BS.UITextField, { flexGrow: "1", fontSize: fs(22), marginRight: "6px", color: "#ffffff", backgroundColor: "#37474f" }, jumpRow);
        jumpField.value = "00:00:00";
        const goBtn = button("Go to time", { width: "150px" }, jumpRow);
        const playStatus = el(BS.UILabel, { fontSize: fs(18), color: "#9aa0a6", marginBottom: "6px" }, playTab);
        const chapTitle = el(BS.UILabel, { fontSize: fs(20), color: "#ffffff", marginBottom: "4px" }, playTab);
        chapTitle.text = "Chapters";
        const chapList = el(BS.UIScrollView, { height: `${U.chapterListHeight}px`, width: "100%", marginBottom: "10px" }, playTab);
        chapList.horizontalScrolling = false;

        // --- the library, under both tabs ---
        const libTitle = el(BS.UILabel, { fontSize: fs(22), color: "#ffffff", marginBottom: "6px" });
        libTitle.text = "Recordings on this device";
        const list = el(BS.UIScrollView, { height: `${U.listHeight}px`, width: "100%", marginBottom: "10px" });
        list.horizontalScrolling = false;

        // --- the off switch, for everyone in the space ---
        const offBtn = button("Turn XR Time Machine off for everyone here", { height: "44px", fontSize: fs(17), backgroundColor: "#3e2723" });
        let offArmed = false;
        click(offBtn, async () => {
            if (!offArmed) {
                offArmed = true;
                offBtn.text = "Sure? Tap again to turn it off";
                l.later(() => { offArmed = false; offBtn.text = "Turn XR Time Machine off for everyone here"; }, 3000);
                return;
            }
            await XRTM.off();
        }, "off button");

        let tab = "record";
        function showTab(next) {
            tab = next;
            showPane.visible = tab === "show";
            seqTab.visible = tab === "seq";
            recTab.visible = tab === "record";
            playTab.visible = tab === "play";
            // the library and the off switch belong to Record and Playback; Sequences is just the buttons
            for (const e of [libTitle, list, offBtn]) e.visible = tab !== "seq" && tab !== "show";
            if (tabShow) tabShow.style.backgroundColor = tab === "show" ? "#b8860b" : "#37474f";
            if (tab === "show") refreshShow();
            tabSeq.style.backgroundColor = tab === "seq" ? "#6a1b9a" : "#37474f";
            tabRec.style.backgroundColor = tab === "record" ? "#c62828" : "#37474f";
            tabPlay.style.backgroundColor = tab === "play" ? "#2e7d32" : "#37474f";
            refresh();
        }
        if (tabShow) click(tabShow, () => showTab("show"), "tab");
        click(tabSeq, () => showTab("seq"), "tab");
        click(tabRec, () => showTab("record"), "tab");
        click(tabPlay, () => showTab("play"), "tab");
        click(seqStop, () => conductor.stop(), "sequence stop");

        let busy = false;
        let message = "";
        click(record, async () => {
            if (busy) return;
            busy = true;
            message = "";
            try {
                if (recorder.current) await recorder.stop();
                else await recorder.start(scene.localUser?.name || "someone");
            } catch (e) {
                log("couldn't record:", e.code || e);
                message = e.message || String(e);
            } finally {
                busy = false;
                refresh();
            }
        }, "record button");
        click(chapterBtn, () => recorder.chapter(), "chapter button");

        // --- playback controls ---
        // stay: started from the Sequences tab, which keeps showing (its line says what happened)
        async function startPlayback(item, stay = false) {
            if (!stay) showTab("play");
            const say = (t) => { playStatus.text = t; seqNow.text = t; };
            if (recorder.current?.id === item.id) { say("Stop recording before playing it."); return; }
            const other = livePlayState();
            if (other && other.bySid !== scene.localUser?.id) { say(`${other.by} is already playing a recording (one at a time).`); return; }
            say("Loading…");
            try {
                await conductor.load(item);
                say("");
            } catch (e) {
                log("playback failed:", e.code || e);
                say(e.code === "not_authorized" ? "You don't have permission to play back in this world." : `Couldn't play it: ${e.message || e.code || e}`);
            }
            refreshPlay();
        }
        click(playBtn, () => {
            const p = conductor.current;
            if (p) return p.playing ? conductor.pause() : conductor.play();
        }, "play button");
        click(stopBtn, () => conductor.stop(), "stop playback");
        let scrubTimer = null;
        let scrubbingUntil = 0;
        slider.OnChange(guard((e) => {
            scrubbingUntil = performance.now() + XRTM.scrubDebounceMs + 500; // don't move the slider under their finger
            clearTimeout(scrubTimer);
            scrubTimer = l.later(() => conductor.seek(Number(e.value) * 1000), XRTM.scrubDebounceMs, "scrub");
        }, "slider"));
        let jumpText = jumpField.value;
        jumpField.OnChange(guard((e) => { jumpText = String(e.value || ""); }, "time field"));
        click(goBtn, () => {
            if (!conductor.current) return;
            const ms = C.parseClock(jumpText);
            if (ms == null) { playStatus.text = "Type a time as hh:mm:ss, mm:ss or seconds."; return; }
            playStatus.text = "";
            return conductor.seek(ms);
        }, "go to time");

        const chapRows = [];
        let chaptersFor = null;
        let seqPlaying = null;
        function refreshChapters(p) {
            if ((p?.id || null) === chaptersFor) return;
            chaptersFor = p?.id || null;
            for (const r of chapRows.splice(0)) r.Destroy();
            for (const c of p?.chapters || []) {
                const b = button(`${C.clock(c.t)}   ${c.label}`, { height: "44px", fontSize: fs(18), marginBottom: "4px", backgroundColor: "#263238" }, chapList);
                click(b, () => conductor.seek(c.t), "chapter");
                chapRows.push(b);
            }
            if (p && !p.chapters.length) {
                const none = el(BS.UILabel, { fontSize: fs(18), color: "#9aa0a6" }, chapList);
                none.text = "No chapters in this recording.";
                chapRows.push(none);
            }
        }

        function refreshPlay() {
            const p = conductor.current;
            nowPlaying.text = p ? `Playing for everyone: ${p.name}` : "Nothing playing. Pick a recording below.";
            if (seqNow.text !== "Loading…") seqNow.text = p ? `▶ ${p.name}   ${C.clock(p.position)} / ${C.clock(p.durationMs)}` : "Tap a sequence to play it for everyone.";
            seqStop.visible = !!p;
            if ((p?.id || null) !== seqPlaying) { seqPlaying = p?.id || null; refreshList().catch((e) => log("list failed:", e)); }   // re-mark the playing one
            time.text = p ? `${C.clock(p.position)} / ${C.clock(p.durationMs)}` : "";
            playBtn.text = p?.playing ? "❚❚  Pause" : "▶  Play";
            for (const e of [slider, transport, jumpRow, chapTitle, chapList]) e.visible = !!p;
            if (p) {
                if (slider.maxValue !== p.durationMs / 1000) slider.SetRange(0, Math.max(p.durationMs / 1000, 0.001));
                if (performance.now() > scrubbingUntil) slider.SetValue(p.position / 1000);
            }
            refreshChapters(p);
        }

        const rows = [];
        let listDraws = 0;
        async function refreshList() {
            // Only the latest call draws: two at once each cleared the list, waited, then both drew it (every recording
            // twice, Windows app 2026-10-30).
            const draw = ++listDraws;
            const items = await store.list().catch(() => []);
            if (draw !== listDraws) return;
            for (const r of rows.splice(0)) r.Destroy();
            // the Sequences tab: finished recordings, oldest first (the order they were rehearsed), one button each
            const seqs = items.filter((i) => i.status === "complete").sort((a, b) => String(a.startedUtc || "").localeCompare(String(b.startedUtc || "")));
            seqs.forEach((item, n) => {
                const playingThis = conductor.current?.id === item.id;
                const b = button(`${n + 1}.  ${item.name}   ${C.clock(item.durationMs)}`, { height: "72px", fontSize: fs(24), marginBottom: "8px",
                    backgroundColor: playingThis ? "#6a1b9a" : "#263238" }, seqList);
                click(b, () => startPlayback(item, true), "play sequence");
                rows.push(b);
            });
            if (seqs.length === 0) {
                const none = el(BS.UILabel, { fontSize: fs(20), color: "#9aa0a6" }, seqList);
                none.text = "No sequences yet: record each part of the presentation on the Record tab.";
                rows.push(none);
            }
            for (const item of items) {
                const row = el(BS.UIVisualElement, { flexDirection: "row", alignItems: "center", marginBottom: "6px" }, list);
                rows.push(row);
                const name = el(BS.UITextField, { flexGrow: "1", fontSize: fs(18), marginRight: "6px", color: "#ffffff", backgroundColor: "#37474f" }, row);
                name.value = item.name;
                name.OnChange(guard(async (e) => {
                    const next = String(e.value || "").trim().slice(0, 80);
                    if (!next || next === item.name) return;
                    item.name = next;
                    await store.putMeta(item);
                }, "rename"));
                const info = el(BS.UILabel, { fontSize: fs(16), color: "#9aa0a6", width: "90px" }, row);
                info.text = item.status === "complete" ? C.clock(item.durationMs) : item.status;
                const play = button("Play", { width: "70px", height: "36px", fontSize: fs(16), backgroundColor: "#2e7d32", borderRadius: "8px", marginRight: "6px" }, row);
                click(play, () => startPlayback(item), "play recording");
                const del = button("Delete", { width: "80px", height: "36px", fontSize: fs(16), backgroundColor: "#5d4037", borderRadius: "8px" }, row);
                let armed = false;
                click(del, async () => {
                    if (recorder.current?.id === item.id || conductor.current?.id === item.id) return;
                    if (!armed) { armed = true; del.text = "Sure?"; l.later(() => { armed = false; del.text = "Delete"; }, 3000); return; }
                    await store.remove(item.id);
                    await helper.remove(item.id);
                    await refreshList();
                }, "delete recording");
            }
            if (items.length === 0) {
                const none = el(BS.UILabel, { fontSize: fs(18), color: "#9aa0a6" }, list);
                none.text = "None yet.";
                rows.push(none);
            }
        }

        async function refreshStorage() {
            const s = recorder.current?.storage;
            const { free, where } = s || await freeSpace();
            const level = free == null ? "" : free < XRTM.storage.countdownBytes ? "Storage low: " : free < XRTM.storage.warnBytes ? "Low storage: " : "";
            storage.text = free == null ? `Saving to ${where}` : `${level}${C.bytes(free)} free on ${where}`;
        }

        function statusText() {
            const rec = recorder.current;
            if (rec) return `Recording on this device ${C.clock(recorder.elapsedMs())}  ·  ${rec.chapters} chapters`;
            return message || recorder.lastStop || "Ready. Records on this device only.";
        }

        function refresh() {
            const rec = recorder.current;
            record.text = rec ? "■  Stop" : "●  Record";
            record.style.backgroundColor = rec ? "#455a64" : "#c62828";
            chapterBtn.visible = !!rec;
            status.text = statusText();
            avLine.text = rec ? rec.av.note : XRTM.av.enabled ? "Video and sound: recorded with each recording, on this device" : "Video and sound: off";
            refreshPlay();
            refreshList().catch((e) => log("list failed:", e));
            refreshStorage().catch((e) => log("storage check failed:", e));
        }
        let open = false;
        l.every(() => {
            if (recorder.current) status.text = statusText();
            if (open && (tab === "play" || tab === "seq") && conductor.current) refreshPlay();
        }, 250, "panel clock");

        await obj.SetLocalScale(new BS.Vector3(0, 0, 0));   // hidden by size, not SetActive: see placeInFront
        const onToggle = (isOpen) => { open = isOpen; if (open) refresh(); };
        // built in: it stays where its anchor is and just shows and hides (still by size)
        const toggle = anchor
            ? async () => { open = !open; onToggle(open); const s = open ? size : 0; await obj.SetLocalScale(new BS.Vector3(s, s, s)); }
            : await placeInFront(l, obj, size, onToggle);
        showTab(show ? "show" : anchor ? "seq" : "record");
        return { toggle, refresh, refreshPlay };
    }

    // Shows and hides a panel in front of the player, facing them, at chest height. Two things the Windows app showed
    // (2026-10-30), which together kept the panel from ever being seen:
    //  - A UIPanel switched off and on again with SetActive is never drawn again. Panels hide by shrinking to nothing
    //    and show by growing back to `size`.
    //  - Where the player is comes from pose-update, which only arrives while they move: at a PC, standing still, it
    //    never came, and the panel opened at the world's origin. With no pose in the last second the panel goes on the
    //    player's head instead, where it lands in front of their eyes, and is let go there.
    async function placeInFront(l, obj, size, onToggle) {
        let head = null, headAt = 0;
        let open = false;
        l.on("pose-update", (e) => { head = e.detail?.head; headAt = performance.now(); }, "panel follow");
        return async () => {
            open = !open;
            const posed = head && performance.now() - headAt < 1000;
            if (open && posed) {
                const p = head.position;
                const f = forward(head.rotation);
                await obj.SetPosition(p.x + f.x * 1.1, p.y - 0.25, p.z + f.z * 1.1);
                await obj.SetRotation(yawRotation(f));
            }
            if (open && !posed) await placeOnHead(obj);
            onToggle(open);
            const s = open ? size : 0;
            await obj.SetLocalScale(new BS.Vector3(s, s, s));
        };
    }

    // Attach to the head 1.1 m out and 0.25 m down, then let go: the panel stays put there, facing the player.
    async function placeOnHead(obj) {
        if (!obj.xrtmHead) obj.xrtmHead = await obj.AddComponent(new BS.AttachedObject({
            avatarAttachmentPoint: BS.AvatarBoneName.HEAD,
            attachmentPosition: new BS.Vector3(0, -0.25, 1.1),
            attachmentRotation: new BS.Quaternion(0, 0, 0, 1),
            autoSync: false,
        }));
        const a = obj.xrtmHead;
        if (typeof a.Attach !== "function") return;
        await a.Attach(scene.localUser.uid);
        await a.Detach();
    }

    // While turned off: owners get one button (F9 or the wrist button) to turn it back on.
    async function offPanel(l) {
        const obj = l.obj(new BS.GameObject({ name: "XRTM Off Panel", localScale: new BS.Vector3(XRTM.ui.panelScale, XRTM.ui.panelScale, XRTM.ui.panelScale) }));
        const panel = await obj.AddComponent(new BS.UIPanel({ resolution: new BS.Vector2(XRTM.ui.panelWidth, 200), enableHaptics: true }));
        panel.SetBackgroundColor(new BS.Vector4(0.07, 0.07, 0.09, 0.92));
        const b = new BS.UIButton(panel);
        b.text = "XR Time Machine is off here. Turn it back on";
        b.SetStyles({ width: "100%", height: "100%", fontSize: "24px", color: "#ffffff", backgroundColor: "#2e7d32" });
        b.OnClick(guard(() => XRTM.on(), "turn on"));
        await obj.SetLocalScale(new BS.Vector3(0, 0, 0));   // hidden by size, not SetActive: see placeInFront
        const toggle = await placeInFront(l, obj, XRTM.ui.panelScale, () => {});
        await openers(l, toggle);
    }

    // F9 on desktop; the small REC button on the left wrist in a headset.
    async function openers(l, toggle) {
        XRTM.toggle = guard(toggle, "toggle"); // from the console too: key-press doesn't fire in Play mode
        l.on("key-press", (e) => { if (e.detail.key === XRTM.toggleKeyCode) return toggle(); }, "F9");
        if (XRTM.wristButton !== false && await scene.IsVR()) await buildWristButton(l, toggle);
    }

    function forward(q) {
        if (!q) return { x: 0, z: 1 };
        // Unity forward (0,0,1) rotated by q, flattened to the floor.
        const x = 2 * (q.x * q.z + q.w * q.y);
        const z = 1 - 2 * (q.x * q.x + q.y * q.y);
        const len = Math.hypot(x, z) || 1;
        return { x: x / len, z: z / len };
    }
    function yawRotation(f) {
        const yaw = Math.atan2(f.x, f.z) / 2;
        return new BS.Quaternion(0, Math.sin(yaw), 0, Math.cos(yaw));
    }

    // The wrist button in a headset, only on permitted players' devices: a small red REC disc on the forearm, pressed by
    // pointing and clicking or by a tap from the right hand. Until 0.3.1 it was a UIPanel on the hand, attached with
    // uid "me", and a press never reached it in the app (Quest, 2026-10-30). Where it sits: XRTM.wrist.
    async function buildWristButton(l, onPress) {
        const w = XRTM.wrist;
        const press = guard((how) => { log("wrist button pressed by", how); return onPress(); }, "wrist button");
        const obj = l.obj(new BS.GameObject({ name: "XRTM Wrist Button", layer: 5 }));   // 5, UI: the layer clicks look at
        await obj.Async?.();
        await obj.AddComponent(new BS.Cylinder({ radiusTop: w.radius, radiusBottom: w.radius, height: w.thickness }));
        await obj.AddComponent(new BS.Material({ color: new BS.Vector4(0.75, 0.05, 0.05, 1) }));
        await obj.AddComponent(new BS.BoxCollider({ isTrigger: true, size: new BS.Vector3(w.radius * 2.6, w.thickness * 4, w.radius * 2.6) }));
        // the caption lies on the top face, reading from above (text reads from its back, so it points down)
        const label = new BS.GameObject({ name: "XRTM Wrist Label", localPosition: new BS.Vector3(0, w.thickness / 2 + 0.001, 0), localEulerAngles: new BS.Vector3(90, 0, 0) });
        await label.Async?.();
        await label.SetParent(obj, false);
        await label.AddComponent(new BS.Text({
            text: "REC", color: new BS.Vector4(1, 1, 1, 1), fontSize: w.fontSize,
            horizontalAlignment: BS.HorizontalAlignment.Center, verticalAlignment: BS.VerticalAlignment.Center,
            richText: false, enableWordWrapping: false, rectTransformSizeDelta: new BS.Vector2(w.radius * 2, w.radius),
        }));
        obj.On("click", () => press("click"));
        // The tap: a trigger over the disc on the layer the hands touch. Not the left hand: it's right next to it.
        const touch = new BS.GameObject({ name: "XRTM Wrist Touch", layer: w.touchLayer });
        await touch.Async?.();
        await touch.SetParent(obj, false);
        await touch.AddComponent(new BS.BoxCollider({ isTrigger: true, size: new BS.Vector3(w.radius * 2.4, w.thickness * 8, w.radius * 2.4) }));
        await touch.AddComponent(new BS.ColliderEvents());
        let lastTouch = 0;
        touch.On("trigger-enter", (e) => {
            if (e.detail?.tag !== "BSLocalCharacterRightHand" || Date.now() - lastTouch < w.touchMs) return;
            lastTouch = Date.now();
            press("touch");
        });
        const attached = await obj.AddComponent(new BS.AttachedObject({
            avatarAttachmentPoint: BS.AvatarBoneName[w.bone],
            attachmentPosition: new BS.Vector3(...w.position),
            attachmentRotation: eulerQuaternion(w.rotation),
        }));
        await attached.Attach(scene.localUser.uid);
        log("wrist button on", w.bone);
    }

    // Euler angles in degrees to a quaternion, in Unity's order (Z, X, Y).
    function eulerQuaternion([x, y, z]) {
        const r = Math.PI / 360, hx = x * r, hy = y * r, hz = z * r;
        return new BS.Quaternion(
            Math.sin(hx) * Math.cos(hy) * Math.cos(hz) + Math.cos(hx) * Math.sin(hy) * Math.sin(hz),
            Math.cos(hx) * Math.sin(hy) * Math.cos(hz) - Math.sin(hx) * Math.cos(hy) * Math.sin(hz),
            Math.cos(hx) * Math.cos(hy) * Math.sin(hz) - Math.sin(hx) * Math.sin(hy) * Math.cos(hz),
            Math.cos(hx) * Math.cos(hy) * Math.cos(hz) + Math.sin(hx) * Math.sin(hy) * Math.sin(hz));
    }

    // ---------- the show: cue-by-cue staging (v0.4, Sphererebro talk, 2026-11-08) ----------
    //
    // A world gives XRTM a show (XRTM_CONFIG.show): a list of CUES and the ELEMENTS they bring on and take off. Every
    // element is a set of scene objects the world built ("twins"): `play` (its Animator plays the entrance whenever it is
    // switched on), `hold` (the final pose, still), and optionally `exit` (its Animator plays the way out). The motion is
    // all Unity's (the SDK: per-frame motion belongs in Unity); the show only switches objects, so it costs nothing per frame.
    // The presenter (owner or moderator) steps through it from the Show tab, the arrow keys, or A / X on the controllers;
    // the cue is the protected key "xrtm.show" {i, at, by}, so everyone in the space sees the same cue, and late arrivals
    // see where the show is (in its held pose). Going back, or jumping, shows each live element's held pose at once.
    // Cue 0 is "house": the world as it is without the show.
    function createShow(l) {
        const S = XRTM.show;
        if (!S || !Array.isArray(S.cues) || !S.elements) return null;
        const key = "xrtm.show";
        const objs = {};                    // name -> BS.GameObject
        let ready = false, rootObj = null;
        let shown = new Map();              // element -> "play" | "hold" | "exit"
        let applied = -1, appliedAt = 0;
        const timers = [];
        const exitTimers = {}, swapTimers = {};
        const clearTimers = () => { for (const t of timers.splice(0)) clearTimeout(t); };
        const later = (fn, ms) => timers.push(l.later(fn, ms, "show timer"));

        // which elements are live after cue i (cue 1 .. i applied in order)
        function liveAt(i) {
            const live = new Set();
            for (let k = 0; k < Math.min(i, S.cues.length); k++) {
                for (const e of S.cues[k].off || []) live.delete(e);
                for (const e of S.cues[k].on || []) live.add(e);
            }
            return live;
        }
        // the video after cue i: the last cue at or before i that says something about video
        function videoAt(i) {
            let v = null;
            for (let k = 0; k < Math.min(i, S.cues.length); k++) {
                const c = S.cues[k].video;
                if (c === "stop") v = null; else if (c && c.clip) v = { ...c, cue: k + 1 };
            }
            return v;
        }
        const nameOf = (e, kind) => S.elements[e]?.[kind];
        async function set(name, on) {
            const o = name && objs[name];
            if (!o) return;
            if (o._xrtmOn === on) return;
            o._xrtmOn = on;
            await o.SetActive(on);
        }
        async function setRestart(name) {      // switch off and on again: its Animator plays from the start
            const o = name && objs[name];
            if (!o) return;
            if (o._xrtmOn) { await o.SetActive(false); }
            o._xrtmOn = true;
            await o.SetActive(true);
        }

        async function init() {
            const names = [S.root, ...S.videos || []];
            for (const e of Object.keys(S.elements)) for (const k of ["play", "hold", "exit"]) if (S.elements[e][k]) names.push(S.elements[e][k]);
            const found = await Promise.all(names.map((n) => scene.Find(n).catch(() => null)));
            names.forEach((n, i) => { if (found[i]) objs[n] = found[i]; });
            const missing = names.filter((n) => !objs[n]);
            if (missing.length) log(`show: ${missing.length} objects not in the scene (first: ${missing.slice(0, 4).join(", ")})`);
            rootObj = objs[S.root];
            // everything off, then the root comes home from where it waits (10 km below the world)
            for (const n of names) if (n !== S.root && objs[n]) { objs[n]._xrtmOn = true; await set(n, false); }
            if (rootObj) await rootObj.SetPosition(new BS.Vector3(...(S.home || [0, 0, 0])));
            ready = true;
            log(`show ready: ${S.cues.length} cues, ${Object.keys(S.elements).length} elements`);
            await apply(read(), true);
        }

        function read() {
            const s = readJson(key);
            return s && Number.isFinite(s.i) ? s : { i: 0, at: 0 };
        }

        // the heart: make the scene match cue `i` (from `prev`)
        async function apply(state, arriving = false) {
            if (!ready) return;
            const i = Math.max(0, Math.min(S.cues.length, state.i | 0));
            // the echo of our own write (and repeats): already there, leave every running entrance alone
            if (i === applied && !arriving) { ui?.(); return; }
            const prev = applied;
            const fresh = !arriving && prev >= 0 && i === prev + 1 && Date.now() - (state.at || 0) < 4000;
            const now = liveAt(i), before = prev >= 0 ? liveAt(prev) : new Set();
            clearTimers();
            for (const e of Object.keys(S.elements)) {
                const el = S.elements[e];
                const isLive = now.has(e), wasLive = before.has(e);
                if (fresh) {
                    if (isLive && !wasLive) {                           // enters: its entrance plays
                        clearTimeout(exitTimers[e]); delete exitTimers[e];
                        await setRestart(el.play); await set(el.hold, false); await set(el.exit, false);
                        shown.set(e, "play");
                        // once the entrance ends, the identical held pose takes over (merged by the builder: fewer draw calls)
                        if (el.swap) {
                            clearTimeout(swapTimers[e]);
                            swapTimers[e] = l.later(async () => {
                                delete swapTimers[e];
                                if (shown.get(e) !== "play") return;
                                await set(el.hold, true); await set(el.play, false); shown.set(e, "hold");
                            }, (el.playDur || 0) * 1000 + 600, "show swap");
                        }
                    } else if (!isLive && wasLive) {                    // leaves: its exit plays, then it is gone
                        clearTimeout(swapTimers[e]); delete swapTimers[e];
                        await set(el.play, false); await set(el.hold, false);
                        if (el.exit) {
                            await setRestart(el.exit); shown.set(e, "exit");
                            // not cleared by the next cue: a quick double press must still switch the exit off
                            clearTimeout(exitTimers[e]);
                            exitTimers[e] = l.later(() => { delete exitTimers[e]; set(el.exit, false); if (shown.get(e) === "exit") shown.delete(e); }, (el.exitDur || 0) * 1000 + 300, "show exit");
                        } else shown.delete(e);
                    }
                    // staying: left exactly as it is (an entrance still running keeps running)
                } else {
                    // going back, jumping, arriving: every live element in its final pose, at once
                    clearTimeout(exitTimers[e]); delete exitTimers[e]; clearTimeout(swapTimers[e]); delete swapTimers[e];
                    await set(el.play, false); await set(el.exit, false);
                    await set(el.hold, isLive);
                    if (isLive) shown.set(e, "hold"); else shown.delete(e);
                }
            }
            applied = i; appliedAt = Date.now();
            await applyVideo(i, fresh, state);
            // the world can make room for the show (Sphererebro hides its dome shells and lattice while a show runs)
            try { window.dispatchEvent(new CustomEvent("xrtm-show", { detail: { i, cue: i ? S.cues[i - 1].id : "0" } })); } catch (e) { }
            ui?.();
        }

        let videoNow = null;
        async function applyVideo(i, fresh, state) {
            const v = videoAt(i);
            const want = v ? `Talk_Video_${v.surface}_${v.layout || "mono"}` : null;
            for (const n of S.videos || []) if (n !== want) await set(n, false);
            if (!v) { videoNow = null; return; }
            const url = /^https?:/.test(v.clip) ? v.clip : (S.mediaBase || "") + v.clip;
            const surfaceEl = Object.keys(S.elements).find((e) => S.elements[e].video?.surface === v.surface);
            const delay = fresh && v.cue === i && surfaceEl && S.cues[i - 1].on?.includes(surfaceEl) ? (S.elements[surfaceEl].video.delay || 0) * 1000 : 0;
            const start = async () => {
                await set(want, true);
                const o = objs[want]; if (!o) return;
                const vp = o.GetComponent?.(BS.CT.VideoPlayer);
                if (!vp) { log("show: no video player on", want); return; }
                if (videoNow === url + "|" + want + "|" + v.cue) return;      // the same clip, still playing: leave it
                videoNow = url + "|" + want + "|" + v.cue;
                vp.loop = false; vp.volume = 1; vp.url = url;
                // late arrivals (and a jump back to a video cue) pick up where the clip is (once it has loaded)
                if (!fresh && v.cue === i && state.at) {
                    const into = (Date.now() - state.at) / 1000;
                    if (into > 2) l.later(() => { try { vp.time = into + 1; } catch (e) { } }, 1000, "video seek");
                }
            };
            if (delay > 0) later(start, delay); else await start();
        }

        // presenter
        const may = { known: false, yes: false };
        async function canDrive() { if (!may.known) { may.yes = await mayRecord(); may.known = true; } return may.yes; }
        async function go(i) {
            if (!(await canDrive())) return;
            i = Math.max(0, Math.min(S.cues.length, i));
            const state = { i, at: Date.now(), by: scene.localUser?.name || "presenter" };
            await scene.SpaceStateSet(key, JSON.stringify(state), { protected: true });
            await apply(state);
        }
        let rehearse = null;
        const ctl = {
            get i() { return applied < 0 ? read().i : applied; },
            get count() { return S.cues.length; },
            cue: (i) => (i >= 1 && i <= S.cues.length ? S.cues[i - 1] : { id: "0", name: "House (no show)" }),
            next: () => go(ctl.i + 1),
            back: () => go(ctl.i - 1),
            home: () => go(1),
            house: () => { ctl.stopRehearsal(); return go(0); },
            goto: (i) => go(i),
            get rehearsing() { return !!rehearse; },
            rehearseToggle() {
                if (rehearse) return ctl.stopRehearsal();
                const secs = S.rehearsalSeconds || 20;
                if (ctl.i === 0 || ctl.i >= S.cues.length) go(1);
                rehearse = l.every(() => {
                    if (ctl.i >= S.cues.length) { ctl.stopRehearsal(); return; }
                    go(ctl.i + 1);
                }, secs * 1000, "rehearsal");
                ui?.();
            },
            stopRehearsal() { if (rehearse) { clearInterval(rehearse); rehearse = null; } ui?.(); },
            elements: () => Object.fromEntries(shown),
            onChange: null,
        };
        let ui = null;
        ctl.setUi = (fn) => { ui = fn; };

        l.on("space-state", (e) => { if (e.detail.changes.some((c) => c.path === key)) apply(read()); }, "show cue");
        // presenter inputs: arrows / Home / R on a keyboard; A (right) next and X (left) back while a show is running
        l.on("key-press", async (e) => {
            const k = e.detail.key;
            const KC = BS.KeyCode || {};
            if (!(await canDrive())) return;
            if (k === (KC.RightArrow ?? 275)) ctl.next();
            else if (k === (KC.LeftArrow ?? 276)) ctl.back();
            else if (k === (KC.Home ?? 278)) ctl.home();
            else if (k === (KC.R ?? 114)) ctl.rehearseToggle();
        }, "show keys");
        l.on("button-pressed", async (e) => {
            if (ctl.i === 0) return;          // only while a show is running: A and X do their usual jobs otherwise
            const d = e.detail || {};
            if (d.button !== BS.ButtonType?.PRIMARY) return;
            if (!(await canDrive())) return;
            if (d.side === BS.HandSide?.RIGHT) ctl.next(); else if (d.side === BS.HandSide?.LEFT) ctl.back();
        }, "show buttons");
        XRTM.showControl = ctl;
        init().catch((e) => log("show init failed:", e));
        return ctl;
    }

    // ---------- start ----------

    async function start(l) {
        watchRecordings(l); // everyone: the notice
        const viewer = createViewer(l);
        watchPlayState(l, viewer); // everyone: playback
        const show = createShow(l); // everyone: the show's cues

        // Permitted players clear a recording or playback left behind by a device that left without stopping.
        l.on("user-left", async (e) => {
            const gone = e.detail.id;
            const stale = liveKeysBy(gone);
            if (stale.length && await mayRecord()) for (const key of stale) scene.SpaceStateDelete(key, { protected: true }).catch(() => {});
        });

        if (!(await mayRecord())) return;
        // Keys left by a device that went while nobody who could clear them was here: cleared on arrival.
        for (const key of staleKeys()) scene.SpaceStateDelete(key, { protected: true }).catch(() => {});
        if (await panelOffHere()) return;
        if (typeof indexedDB === "undefined") { log("no device storage here: recording is off, playback still shows"); return; }

        let ui;
        const recorder = createRecorder(l, () => ui?.refresh());
        const conductor = createConductor(l, viewer, () => ui?.refreshPlay());
        ui = await buildPanel(l, recorder, conductor, show);
        await openers(l, ui.toggle);

        // Leaving the space ends the recording and the playback cleanly.
        const leave = guard(() => { recorder.stop(); conductor.stop(); }, "leaving");
        window.addEventListener("pagehide", leave);
        l.onDispose(() => window.removeEventListener?.("pagehide", leave));
        log("recorder ready: F9 or the wrist button");
    }

    // XRTM.inHeadset false: no panel or REC button in a headset; recording and its controls are for the desktop app.
    // Everyone, headset or not, still sees the notices and playback. (The Polys, 2026-10-30: the panel opened in the floor.)
    async function panelOffHere() {
        if (XRTM.inHeadset !== false || !(await scene.IsVR())) return false;
        log("no recorder controls in a headset here (inHeadset: false)");
        return true;
    }

    // The recording and playback keys whose device isn't in the space.
    function staleKeys() {
        const all = scene.spaceStateJson?.protected || {};
        return Object.keys(all).filter((k) => {
            if (k !== XRTM.playStateKey && !k.startsWith(`${XRTM.recKey}.`)) return false;
            const s = readJson(k);
            return !s || !C.present(scene.users, s.bySid, s.byUid) || (k !== XRTM.playStateKey && !alive(s));
        });
    }

    // The shared keys a device that just left was holding.
    function liveKeysBy(sid) {
        const all = scene.spaceStateJson?.protected || {};
        return Object.keys(all).filter((k) => {
            if (k !== XRTM.playStateKey && !k.startsWith(`${XRTM.recKey}.`)) return false;
            return readJson(k)?.bySid === sid;
        });
    }
