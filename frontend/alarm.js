() => {
    // GrandmaCare client-side voice + alarm engine.
    // Loaded once via gr.Blocks(js=...). Cards carry only plain markup with
    // data-gc-* attributes; everything here is driven by event delegation, so
    // it works regardless of how Gradio sanitizes the card HTML blob.
    if (window.__gcAlarmReady) return;
    window.__gcAlarmReady = true;

    const STORE_KEY = "gc_alarms";
    let primedAudio = null;       // unlocked on first user gesture
    let lastFiredMinute = {};     // medName -> "HH:MM" already rung this minute

    const loadAlarms = () => {
        try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; }
        catch (e) { return {}; }
    };
    const saveAlarms = (alarms) => {
        try { localStorage.setItem(STORE_KEY, JSON.stringify(alarms)); }
        catch (e) { /* localStorage full or blocked; alarm still rings this session */ }
    };

    const nowHHMM = () => {
        const d = new Date();
        const p = (n) => String(n).padStart(2, "0");
        return p(d.getHours()) + ":" + p(d.getMinutes());
    };

    // Prime audio on a real user gesture so the scheduled (gestureless) ring
    // is not blocked by the browser's autoplay policy.
    const primeFrom = (src) => {
        try {
            if (!primedAudio) primedAudio = new Audio();
            if (src) primedAudio.src = src;
            primedAudio.muted = true;
            const p = primedAudio.play();
            if (p && p.then) p.then(() => { primedAudio.pause(); primedAudio.muted = false; }).catch(() => {});
        } catch (e) {}
    };

    const playSrc = (src) => {
        if (!src) { beep(); return; }
        try {
            const a = new Audio(src);
            const p = a.play();
            if (p && p.catch) p.catch(() => beep());
        } catch (e) { beep(); }
    };

    // Fallback chime when no clip is available or audio is blocked.
    const beep = () => {
        try {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            const ctx = new Ctx();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.frequency.value = 880; gain.gain.value = 0.2;
            osc.start();
            osc.stop(ctx.currentTime + 0.6);
        } catch (e) {}
    };

    const banner = () => {
        let el = document.getElementById("gc-alarm-banner");
        if (!el) {
            el = document.createElement("div");
            el.id = "gc-alarm-banner";
            el.className = "alarm-banner";
            el.addEventListener("click", () => { el.style.display = "none"; });
            document.body.appendChild(el);
        }
        return el;
    };

    const ring = (medName, src) => {
        playSrc(src);
        const el = banner();
        el.textContent = "🔔 Time to take " + medName + "  (tap to dismiss)";
        el.style.display = "block";
        try {
            if (window.Notification && Notification.permission === "granted") {
                new Notification("GrandmaCare", { body: "Time to take " + medName });
            }
        } catch (e) {}
    };

    // Re-apply saved alarm times to inputs after any re-render (view toggle,
    // new analyze). Runs on a MutationObserver + initial pass.
    const syncInputs = () => {
        const alarms = loadAlarms();
        document.querySelectorAll("[data-gc-card]").forEach((card) => {
            const med = card.getAttribute("data-gc-card");
            const input = card.querySelector("[data-gc-alarm-input]");
            const status = card.querySelector("[data-gc-alarm-status]");
            const saved = alarms[med];
            if (input && saved && saved.time && !input.value) input.value = saved.time;
            if (status) status.textContent = saved && saved.time ? "Alarm set for " + saved.time : "";
        });
    };

    document.addEventListener("click", (ev) => {
        const playBtn = ev.target.closest("[data-gc-play]");
        if (playBtn) {
            const src = playBtn.getAttribute("data-gc-src");
            primeFrom(src);
            playSrc(src);
            return;
        }

        const setBtn = ev.target.closest("[data-gc-alarm-set]");
        if (setBtn) {
            const med = setBtn.getAttribute("data-gc-med");
            const actions = setBtn.closest("[data-gc-card]");
            const input = actions && actions.querySelector("[data-gc-alarm-input]");
            const status = actions && actions.querySelector("[data-gc-alarm-status]");
            const time = input && input.value;
            if (!time) { if (status) status.textContent = "Please choose a time first."; return; }
            const card = setBtn.closest(".medicine-card");
            const soundBtn = card && card.querySelector("[data-gc-play]");
            const src = soundBtn ? soundBtn.getAttribute("data-gc-src") : "";
            const alarms = loadAlarms();
            alarms[med] = { time: time, audio: src || "" };
            saveAlarms(alarms);
            primeFrom(src);
            try { if (window.Notification && Notification.permission === "default") Notification.requestPermission(); } catch (e) {}
            if (status) status.textContent = "Alarm set for " + time;
            return;
        }

        const clearBtn = ev.target.closest("[data-gc-alarm-clear]");
        if (clearBtn) {
            const med = clearBtn.getAttribute("data-gc-med");
            const actions = clearBtn.closest("[data-gc-card]");
            const input = actions && actions.querySelector("[data-gc-alarm-input]");
            const status = actions && actions.querySelector("[data-gc-alarm-status]");
            const alarms = loadAlarms();
            delete alarms[med];
            saveAlarms(alarms);
            if (input) input.value = "";
            if (status) status.textContent = "";
            return;
        }
    });

    const tick = () => {
        const current = nowHHMM();
        const alarms = loadAlarms();
        Object.keys(alarms).forEach((med) => {
            const a = alarms[med];
            if (!a || a.time !== current) return;
            if (lastFiredMinute[med] === current) return;
            lastFiredMinute[med] = current;
            ring(med, a.audio);
        });
    };

    const observer = new MutationObserver(() => syncInputs());
    observer.observe(document.body, { childList: true, subtree: true });
    syncInputs();
    setInterval(tick, 20000);
    tick();
}
