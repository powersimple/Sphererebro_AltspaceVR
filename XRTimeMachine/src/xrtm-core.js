// XR Time Machine core: platform-agnostic and world-agnostic. Plain JavaScript, no libraries.
// Knows the .xrtm line format, time, poses, playback scheduling, the storage budget and the error breaker.
// Knows nothing about Altspace, Unity or any world: a platform adapter (src/adapter-*.js) supplies all of that.
// Runs in a world page, a browser or Node.
//
// Format: .xrtm v0 is newline-delimited JSON, one record per line, append-only (crash-safe: every line
// written before a crash is readable). First line is the header; every other line has t, milliseconds since
// the header's startedUtc. Readers key on "format" and "version"; it will move to the MCAP container in PLAN.md.
const XRTMCore = (() => {
    "use strict";

    const FORMAT = "xrtm";
    const FORMAT_VERSION = 0;

    const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));
    const round = (n, d) => Math.round(n * 10 ** d) / 10 ** d;

    // ---------- poses ----------

    // Millimetres and 4-place rotations: finer than any headset tracks, and about half the bytes of raw floats.
    function quantize(tr) {
        if (!tr?.position) return null;
        const p = tr.position;
        const q = tr.rotation;
        return {
            p: [round(p.x, 3), round(p.y, 3), round(p.z, 3)],
            ...(q ? { r: [round(q.x, 4), round(q.y, 4), round(q.z, 4), round(q.w, 4)] } : {}),
        };
    }

    // Remembers the last thing written per key, so a pose that hasn't changed isn't written again.
    function changeFilter() {
        const last = new Map();
        return (key, value) => {
            const text = JSON.stringify(value);
            if (last.get(key) === text) return false;
            last.set(key, text);
            return true;
        };
    }

    // ---------- recordings ----------

    // World, start time and device: two devices can start in the same second, even on one PC (one helper folder).
    function recordingId(slug, startedUtc, device) {
        const dev = String(device || "").replace(/[^A-Za-z0-9]/g, "").slice(-6) || "dev";
        return `${String(slug || "world").replace(/[^A-Za-z0-9_-]/g, "")}-${startedUtc.replace(/[:.]/g, "-").slice(0, 19)}-${dev}`;
    }

    function header({ id, name, startedUtc, world, by, device, app, appVersion, poseHz, layers }) {
        return {
            type: "header", format: FORMAT, version: FORMAT_VERSION, id, name, startedUtc,
            world, recorder: { by, device, app, appVersion },
            coordinates: "world space: metres, Y up, left-handed (Unity); relative to the world origin",
            clock: "t = milliseconds since startedUtc (0.1 ms)", poseHz,
            precision: "positions to 1 mm, rotations to 4 places; a pose is written only when it changes",
            layers,
        };
    }

    // Text to lines. A last line cut short by a crash is skipped.
    function parseLines(text) {
        const lines = [];
        for (const l of String(text).split("\n")) {
            if (!l) continue;
            try { lines.push(JSON.parse(l)); } catch { /* cut short */ }
        }
        return lines;
    }

    // Ready to play: the header checked, the body in time order, the length and the chapters.
    function prepare(lines, meta = {}) {
        const head = lines[0];
        if (head?.format !== FORMAT || head.version !== FORMAT_VERSION) throw new Error("not an .xrtm v0 recording");
        const body = lines.slice(1).filter((l) => typeof l.t === "number").sort((a, b) => a.t - b.t);
        const end = body.find((l) => l.type === "end");
        return {
            id: meta.id || head.id,
            name: String(meta.name || head.name || head.id).slice(0, 80),
            recordedBy: String(head.recorder?.by || "someone").slice(0, 60),
            lines: body,
            durationMs: Math.round(end?.durationMs ?? (body.length ? body[body.length - 1].t : 0)),
            chapters: body.filter((l) => l.type === "chapter").slice(0, 100).map((l) => ({ t: Math.round(l.t), label: String(l.label || "").slice(0, 60) })),
        };
    }

    // ---------- playback scheduling ----------

    // Index of the first line after time t (lines sorted by t).
    function firstAfter(lines, t) {
        let lo = 0;
        let hi = lines.length;
        while (lo < hi) {
            const mid = (lo + hi) >> 1;
            if (lines[mid].t <= t) lo = mid + 1; else hi = mid;
        }
        return lo;
    }

    // Everything true at time t, stamped t: who's here, the latest self pose, the latest object poses.
    function keyframe(lines, t) {
        const present = new Map();
        const objs = new Map();
        let pose = null;
        for (const l of lines) {
            if (l.t > t) break;
            if (l.type === "roster") { present.clear(); for (const u of l.users || []) present.set(u.sid || u.uid, u); }
            else if (l.type === "join") present.set(l.user.sid || l.user.uid, l.user);
            else if (l.type === "leave") present.delete(l.sid || l.uid);
            else if (l.type === "self_pose") pose = l;
            else if (l.type === "object_pose") objs.set(l.name, l);
        }
        return [
            { t, type: "roster", users: [...present.values()].slice(0, 60).map((u) => ({ uid: u.uid, sid: u.sid, name: u.name })) },
            pose && { ...pose, t },
            ...[...objs.values()].map((l) => ({ ...l, t })),
        ].filter(Boolean);
    }

    // Only what playback shows, small enough to send.
    function slim(l) {
        switch (l.type) {
            case "self_pose": case "object_pose": case "leave": return l;
            case "join": return { t: l.t, type: "join", user: { uid: l.user.uid, sid: l.user.sid, name: l.user.name } };
            case "user_state": return {
                t: l.t, type: "user_state", uid: l.uid, sid: l.sid,
                changes: (l.changes || []).map((c) => ({ path: c.path, deleted: !!c.deleted, value: JSON.stringify(c.value ?? null).length < 200 ? c.value : true })),
            };
            case "chapter": return { t: l.t, type: "chapter", label: l.label };
            default: return null;
        }
    }

    // Lines into batches of at most maxChars of JSON each. A line too big on its own is dropped (and reported).
    function pack(lines, maxChars, onTooBig) {
        const out = [];
        let batch = [];
        let size = 0;
        for (const l of lines) {
            const n = JSON.stringify(l).length + 1;
            if (n > maxChars) { onTooBig?.(l); continue; }
            if (size + n > maxChars && batch.length) { out.push(batch); batch = []; size = 0; }
            batch.push(l);
            size += n;
        }
        if (batch.length) out.push(batch);
        return out;
    }

    function describeChange(c) {
        const off = c.deleted || !c.value || c.value === "0" || c.value === "false";
        if (c.path === "handRaise") return off ? "lowered their hand" : "raised a hand";
        if (/mute/i.test(c.path)) return off ? "unmuted" : "muted";
        if (/avatar|persona/i.test(c.path)) return "changed avatar";
        return `changed ${c.path}`;
    }

    // ---------- who's here ----------

    // A state written by a device is live while that device is present. Devices are told apart by session id,
    // because one account can be in the space twice (two headsets, or a PC and a headset); the account id is
    // a fallback for platforms whose user list keeps one entry per account.
    function present(users, sid, uid) {
        const list = Object.values(users || {});
        return list.some((u) => u.id === sid || u.sid === sid) || (!!uid && list.some((u) => u.uid === uid));
    }

    // A session id made safe as one part of a shared-state path.
    const keyPart = (s) => String(s || "unknown").replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 40);

    // ---------- storage budget ----------

    // Watches free space while recording. Levels:
    //   ok, low (under warnBytes: warn at the start), countdown (under countdownBytes: a lasting warning with
    //   the time left), stop (at stopBytes: stop, so the device keeps room to work).
    // Time left comes from how fast free space is actually falling, or from the expected write rate until
    // there are two readings to go on.
    function storageWatch({ warnBytes, countdownBytes, stopBytes }) {
        let last = null;
        let rate = 0; // bytes per second, smoothed
        return {
            update(free, nowMs, expectedRate = 0) {
                if (free == null) return { level: "unknown", free: null, secondsLeft: null };
                if (last && nowMs > last.at) {
                    const r = (last.free - free) / ((nowMs - last.at) / 1000);
                    if (r > 0) rate = rate ? rate * 0.7 + r * 0.3 : r;
                }
                last = { free, at: nowMs };
                const use = Math.max(rate, expectedRate);
                const secondsLeft = use > 0 ? Math.max(0, (free - stopBytes) / use) : null;
                const level = free <= stopBytes ? "stop" : free < countdownBytes ? "countdown" : free < warnBytes ? "low" : "ok";
                return { level, free, secondsLeft, rate: use };
            },
        };
    }

    function bytes(n) {
        if (n == null) return "?";
        if (n >= 1e9) return `${(n / 1e9).toFixed(1)} GB`;
        return `${Math.max(0, Math.round(n / 1e6))} MB`;
    }

    function duration(seconds) {
        if (seconds == null) return "unknown time";
        const m = Math.floor(seconds / 60);
        if (m < 1) return "under a minute";
        if (m < 60) return `about ${m} min`;
        return `about ${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min`;
    }

    // ---------- the error breaker ----------

    // Counts errors from everything the plugin runs; too many in a short time and it trips once.
    function breaker({ max, windowMs, onTrip, log }) {
        let hits = [];
        let tripped = false;
        function hit(e, where) {
            log?.(`error${where ? ` in ${where}` : ""}:`, e);
            if (tripped) return;
            const now = Date.now();
            hits = hits.filter((t) => now - t < windowMs);
            hits.push(now);
            if (hits.length >= max) {
                tripped = true;
                try { onTrip(e); } catch (err) { log?.("shutting down failed:", err); }
            }
        }
        // Wraps a callback: what it throws, or rejects with, is counted instead of reaching the world's code.
        function guard(fn, where) {
            return function guarded(...args) {
                if (tripped) return undefined;
                try {
                    const r = fn.apply(this, args);
                    if (r && typeof r.then === "function") return r.catch((e) => hit(e, where));
                    return r;
                } catch (e) {
                    hit(e, where);
                    return undefined;
                }
            };
        }
        return { hit, guard, get tripped() { return tripped; }, reset() { hits = []; tripped = false; } };
    }

    // ---------- time ----------

    function clock(ms) {
        const s = Math.floor((ms || 0) / 1000);
        return [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60].map((n) => String(n).padStart(2, "0")).join(":");
    }

    // "1:02:03", "02:03" or "123" (seconds) to milliseconds; null if it isn't a time.
    function parseClock(text) {
        const s = String(text || "").trim();
        if (!/^\d+(\.\d+)?(:\d+(\.\d+)?){0,2}$/.test(s)) return null;
        return s.split(":").reduce((acc, n) => acc * 60 + Number(n), 0) * 1000;
    }

    return {
        FORMAT, FORMAT_VERSION, clamp, round,
        quantize, changeFilter, recordingId, header, parseLines, prepare,
        firstAfter, keyframe, slim, pack, describeChange,
        present, keyPart, storageWatch, bytes, duration, breaker, clock, parseClock,
    };
})();
