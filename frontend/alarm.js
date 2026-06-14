() => {
    // GrandmaCare client-side voice + alarm engine.
    // Loaded once via demo.load(js=...). Cards carry only plain markup with
    // data-gc-* attributes; everything here runs by event delegation, so it
    // works regardless of how Gradio sanitizes the card HTML blob.
    if (window.__gcAlarmReady) return;
    window.__gcAlarmReady = true;

    const STORE_KEY = "gc_alarms";
    let audioCtx = null;
    const lastFiredMinute = {};   // medName -> "HH:MM" already rung this minute

    const loadAlarms = () => {
        try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; }
        catch (e) { return {}; }
    };
    const saveAlarms = (alarms) => {
        try { localStorage.setItem(STORE_KEY, JSON.stringify(alarms)); } catch (e) {}
    };

    const nowHHMM = () => {
        const d = new Date();
        const p = (n) => String(n).padStart(2, "0");
        return p(d.getHours()) + ":" + p(d.getMinutes());
    };

    // --- Bridge to the server: set a hidden Gradio textbox, click its button.
    const setGradioText = (rootId, value) => {
        const el = document.querySelector(rootId + " textarea") ||
                   document.querySelector(rootId + " input");
        if (!el) return false;
        const proto = el.tagName === "TEXTAREA"
            ? window.HTMLTextAreaElement.prototype
            : window.HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
        setter.call(el, value);
        el.dispatchEvent(new Event("input", { bubbles: true }));
        return true;
    };
    const speak = (text) => {
        if (!text) return;
        if (!setGradioText("#gc-tts-text", text)) return;
        // Let Gradio register the new value before firing the click.
        setTimeout(() => {
            const btn = document.querySelector("#gc-tts-trigger button") ||
                        document.querySelector("#gc-tts-trigger");
            if (btn) btn.click();
        }, 80);
    };

    // Short fallback chime so the alarm is audible even before TTS arrives.
    const beep = () => {
        try {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            if (!audioCtx) audioCtx = new Ctx();
            if (audioCtx.state === "suspended") audioCtx.resume();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain); gain.connect(audioCtx.destination);
            osc.frequency.value = 880; gain.gain.value = 0.2;
            osc.start();
            osc.stop(audioCtx.currentTime + 0.6);
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

    const ring = (medName, sayText) => {
        beep();
        speak(sayText);
        const el = banner();
        el.textContent = "🔔 Time to take " + medName + "  (tap to dismiss)";
        el.style.display = "block";
        try {
            if (window.Notification && Notification.permission === "granted") {
                new Notification("GrandmaCare", { body: "Time to take " + medName });
            }
        } catch (e) {}
    };

    // Re-apply saved alarm times/status to inputs after any re-render.
    const syncInputs = () => {
        const alarms = loadAlarms();
        document.querySelectorAll("[data-gc-card]").forEach((card) => {
            const med = card.getAttribute("data-gc-card");
            const input = card.querySelector("[data-gc-alarm-input]");
            const status = card.querySelector("[data-gc-alarm-status]");
            const saved = alarms[med];
            if (input && saved && saved.time && !input.value) input.value = saved.time;
            if (status) status.textContent = saved && saved.time ? "⏰ Alarm set for " + saved.time : "";
        });
    };

    document.addEventListener("click", (ev) => {
        const playBtn = ev.target.closest("[data-gc-play]");
        if (playBtn) {
            // Unlock audio on this user gesture so the later alarm beep is allowed.
            beep();
            speak(playBtn.getAttribute("data-gc-say"));
            return;
        }

        const setBtn = ev.target.closest("[data-gc-alarm-set]");
        if (setBtn) {
            const med = setBtn.getAttribute("data-gc-med");
            const card = setBtn.closest("[data-gc-card]");
            const input = card && card.querySelector("[data-gc-alarm-input]");
            const status = card && card.querySelector("[data-gc-alarm-status]");
            const time = input && input.value;
            if (!time) { if (status) status.textContent = "Please choose a time first."; return; }
            const playBtn = card && card.querySelector("[data-gc-play]");
            const say = playBtn ? playBtn.getAttribute("data-gc-say") : "";
            const alarms = loadAlarms();
            alarms[med] = { time: time, say: say || "" };
            saveAlarms(alarms);
            beep();   // also unlocks audio for the scheduled ring
            try {
                if (window.Notification && Notification.permission === "default") {
                    Notification.requestPermission();
                }
            } catch (e) {}
            if (status) status.textContent = "⏰ Alarm set for " + time;
            return;
        }

        const clearBtn = ev.target.closest("[data-gc-alarm-clear]");
        if (clearBtn) {
            const med = clearBtn.getAttribute("data-gc-med");
            const card = clearBtn.closest("[data-gc-card]");
            const input = card && card.querySelector("[data-gc-alarm-input]");
            const status = card && card.querySelector("[data-gc-alarm-status]");
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
            ring(med, a.say);
        });
    };

    new MutationObserver(() => syncInputs())
        .observe(document.body, { childList: true, subtree: true });
    syncInputs();
    setInterval(tick, 15000);
    tick();
}
