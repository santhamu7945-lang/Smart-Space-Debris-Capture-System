
// ============================================================
// ADCS-01 | SHARED WEBSITE BEHAVIOUR
// AUTONOMOUS SPACE DEBRIS MONITORING AND CAPTURE SYSTEM
// ============================================================

(() => {
  "use strict";

  const ADCS = window.ADCS = window.ADCS || {};

  ADCS.config = {
    project: "AUTONOMOUS SPACE DEBRIS MONITORING AND CAPTURE SYSTEM",
    missionCode: "ADCS-01",
    storageKey: "adcsMissionCase",
    eventStorageKey: "adcsMissionEvents",
    syncEvent: "adcs:mission-case-changed",
    eventLimit: 80
  };

  ADCS.cases = {
    CAPTURE: {
      id: "CAPTURE",
      number: "01",
      label: "CAPTURE",
      title: "Capture sequence authorized",
      description:
        "The capture scenario is selected. Target assessment, safe-approach gates and mechanism readiness must still be satisfied before physical capture begins.",
      status: "CAPTURE SELECTED",
      tone: "capture"
    },
    HOLD: {
      id: "HOLD",
      number: "02",
      label: "HOLD",
      title: "Relative-motion hold",
      description:
        "Capture actuation is inhibited. The servicer maintains the hold scenario while target motion and relative geometry continue to be monitored.",
      status: "HOLD ACTIVE",
      tone: "hold"
    },
    ABORT: {
      id: "ABORT",
      number: "03",
      label: "ABORT",
      title: "Capture sequence inhibited",
      description:
        "Capture actuation is inhibited. The scenario enters its abort state and requires safe separation or a defined recovery procedure in the simulation.",
      status: "ABORT ACTIVE",
      tone: "abort"
    }
  };

  // ----------------------------------------------------------
  // SAFE STORAGE HELPERS
  // ----------------------------------------------------------

  function readJSON(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : fallback;
    } catch (error) {
      console.warn("[ADCS] Could not read local storage.", error);
      return fallback;
    }
  }

  function writeJSON(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.warn("[ADCS] Could not write local storage.", error);
      return false;
    }
  }

  function validCase(value) {
    return Object.prototype.hasOwnProperty.call(ADCS.cases, value);
  }

  function getCurrentCase() {
    try {
      const saved = localStorage.getItem(ADCS.config.storageKey);
      return validCase(saved) ? saved : "CAPTURE";
    } catch (_) {
      return "CAPTURE";
    }
  }

  // ----------------------------------------------------------
  // MISSION EVENT LOG
  // ----------------------------------------------------------

  function utcTimestamp() {
    return new Date().toISOString();
  }

  function createEventId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }

    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function getEvents() {
    const value = readJSON(ADCS.config.eventStorageKey, []);
    return Array.isArray(value) ? value : [];
  }

  function recordEvent(event) {
    const entry = {
      id: createEventId(),
      time: utcTimestamp(),
      page: document.body?.dataset.page || "unknown",
      type: "INFO",
      message: "",
      state: getCurrentCase(),
      ...event
    };

    const events = getEvents();
    events.push(entry);

    writeJSON(
      ADCS.config.eventStorageKey,
      events.slice(-ADCS.config.eventLimit)
    );

    window.dispatchEvent(
      new CustomEvent("adcs:mission-event", { detail: entry })
    );

    return entry;
  }

  ADCS.events = {
    getAll: getEvents,
    record: recordEvent,
    clear() {
      writeJSON(ADCS.config.eventStorageKey, []);
      window.dispatchEvent(new CustomEvent("adcs:mission-events-cleared"));
    }
  };

  // ----------------------------------------------------------
  // SYNCHRONIZED CASE AUTHORITY
  // ----------------------------------------------------------

  function dispatchCaseChange(previousCase, nextCase, source) {
    const detail = {
      previousCase,
      case: nextCase,
      definition: ADCS.cases[nextCase],
      source: source || "local",
      timestamp: utcTimestamp()
    };

    window.dispatchEvent(
      new CustomEvent(ADCS.config.syncEvent, { detail })
    );

    window.dispatchEvent(
      new CustomEvent("adcs:mission-case-changed", { detail })
    );

    return detail;
  }

  function setCurrentCase(nextCase, options = {}) {
    if (!validCase(nextCase)) {
      console.warn(`[ADCS] Ignored invalid mission case: ${nextCase}`);
      return false;
    }

    const previousCase = getCurrentCase();

    try {
      localStorage.setItem(ADCS.config.storageKey, nextCase);
    } catch (error) {
      console.warn("[ADCS] Mission case could not be persisted.", error);
    }

    updateCaseControls(nextCase);
    updateCaseReadouts(nextCase);

    if (previousCase !== nextCase && options.log !== false) {
      recordEvent({
        type: nextCase === "ABORT" ? "ALERT" : "STATE",
        message: `Mission case changed from ${previousCase} to ${nextCase}.`,
        state: nextCase
      });
    }

    dispatchCaseChange(
      previousCase,
      nextCase,
      options.source || "local"
    );

    return true;
  }

  function updateCaseControls(caseName) {
    document.querySelectorAll("[data-case]").forEach((control) => {
      const value = String(control.dataset.case || "").toUpperCase();
      const selected = value === caseName;

      control.classList.toggle("is-active", selected);
      control.setAttribute("aria-pressed", selected ? "true" : "false");
    });

    document.querySelectorAll("[data-current-case]").forEach((element) => {
      element.textContent = ADCS.cases[caseName].label;
    });
  }

  function updateCaseReadouts(caseName) {
    const definition = ADCS.cases[caseName];

    document.querySelectorAll("[data-case-title]").forEach((element) => {
      element.textContent = definition.title;
    });

    document.querySelectorAll("[data-case-description]").forEach((element) => {
      element.textContent = definition.description;
    });

    document.querySelectorAll("[data-case-status]").forEach((element) => {
      element.textContent = definition.status;
      element.dataset.tone = definition.tone;
    });

    document.querySelectorAll("[data-mission-state]").forEach((element) => {
      element.textContent = caseName;
      element.dataset.state = caseName;
    });

    document.documentElement.dataset.missionCase = caseName.toLowerCase();
  }

  function bindCaseControls() {
    document.querySelectorAll("[data-case]").forEach((control) => {
      if (control.dataset.adcsCaseBound === "true") return;

      control.dataset.adcsCaseBound = "true";

      control.addEventListener("click", () => {
        const requestedCase = String(control.dataset.case || "").toUpperCase();
        setCurrentCase(requestedCase, { source: "page-control" });
      });
    });
  }

  function listenForExternalCaseChanges() {
    window.addEventListener("storage", (event) => {
      if (event.key !== ADCS.config.storageKey) return;

      const incoming = event.newValue;

      if (!validCase(incoming)) return;

      updateCaseControls(incoming);
      updateCaseReadouts(incoming);

      dispatchCaseChange(
        event.oldValue || "CAPTURE",
        incoming,
        "another-tab"
      );
    });

    window.addEventListener(ADCS.config.syncEvent, (event) => {
      const caseName = event.detail?.case;

      if (!validCase(caseName)) return;

      updateCaseControls(caseName);
      updateCaseReadouts(caseName);
    });
  }

  ADCS.mission = {
    cases: ADCS.cases,
    getCase: getCurrentCase,
    setCase: setCurrentCase,
    onCaseChange(callback) {
      if (typeof callback !== "function") return () => {};

      const listener = (event) => callback(event.detail);

      window.addEventListener(ADCS.config.syncEvent, listener);

      return () => {
        window.removeEventListener(ADCS.config.syncEvent, listener);
      };
    }
  };

  // ----------------------------------------------------------
  // PAGE NAVIGATION
  // ----------------------------------------------------------

  function setupNavigation() {
    const toggle = document.querySelector("[data-nav-toggle]");
    const nav = document.querySelector("[data-site-nav]");

    if (toggle && nav) {
      toggle.setAttribute("aria-expanded", "false");

      toggle.addEventListener("click", () => {
        const open = nav.classList.toggle("is-open");

        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        toggle.setAttribute(
          "aria-label",
          open ? "Close navigation" : "Open navigation"
        );
      });

      nav.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
          nav.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
        });
      });

      document.addEventListener("click", (event) => {
        if (!nav.classList.contains("is-open")) return;

        if (!nav.contains(event.target) && !toggle.contains(event.target)) {
          nav.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
        }
      });
    }

    const currentFile = (
      window.location.pathname.split("/").pop() || "index.html"
    ).toLowerCase();

    document.querySelectorAll("[data-site-nav] a[href]").forEach((link) => {
      const destination = link.getAttribute("href");
      if (!destination) return;

      const file = destination.split("/").pop().split("#")[0].toLowerCase();

      if (file && file === currentFile) {
        link.setAttribute("aria-current", "page");
        link.classList.add("is-active");
      } else {
        link.removeAttribute("aria-current");
        link.classList.remove("is-active");
      }
    });
  }

  // ----------------------------------------------------------
  // SCROLL REVEAL
  // ----------------------------------------------------------

  function setupRevealAnimations() {
    const elements = document.querySelectorAll("[data-reveal]");

    if (!elements.length) return;

    if (
      !("IntersectionObserver" in window) ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      elements.forEach((element) => element.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries, activeObserver) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;

          entry.target.classList.add("is-visible");
          activeObserver.unobserve(entry.target);
        });
      },
      {
        threshold: 0.08,
        rootMargin: "0px 0px -35px 0px"
      }
    );

    elements.forEach((element) => observer.observe(element));
  }

  // ----------------------------------------------------------
  // TIMESTAMPS
  // ----------------------------------------------------------

  function formatUTC(date) {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    }).format(date);
  }

  function formatUTCDate(date) {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC",
      day: "2-digit",
      month: "short",
      year: "numeric"
    }).format(date);
  }

  function setupClocks() {
    const update = () => {
      const now = new Date();

      document.querySelectorAll("[data-clock-utc]").forEach((element) => {
        element.textContent = formatUTC(now);
      });

      document.querySelectorAll("[data-date-utc]").forEach((element) => {
        element.textContent = formatUTCDate(now);
      });

      document.querySelectorAll("[data-iso-time]").forEach((element) => {
        element.textContent = now.toISOString();
      });
    };

    update();
    window.setInterval(update, 1000);
  }

  // ----------------------------------------------------------
  // EVENT LOG RENDERER
  // ----------------------------------------------------------

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      };

      return map[character];
    });
  }

  function renderEventLog(container) {
    if (!container) return;

    const events = getEvents().slice().reverse();

    if (!events.length) {
      container.innerHTML = `
        <div class="event-log__row">
          <span class="event-log__time">--:--:--</span>
          <span class="event-log__message">No mission events recorded in this browser session.</span>
          <span class="event-log__state">STANDBY</span>
        </div>
      `;
      return;
    }

    container.innerHTML = events.map((event) => {
      const date = new Date(event.time);
      const time = Number.isNaN(date.getTime())
        ? "--:--:--"
        : formatUTC(date);

      return `
        <div class="event-log__row">
          <span class="event-log__time">${escapeHTML(time)} UTC</span>
          <span class="event-log__message">${escapeHTML(event.message || "Mission event")}</span>
          <span class="event-log__state">${escapeHTML(event.state || "INFO")}</span>
        </div>
      `;
    }).join("");
  }

  function setupEventLog() {
    const containers = document.querySelectorAll("[data-event-log]");

    if (!containers.length) return;

    const renderAll = () => {
      containers.forEach(renderEventLog);
    };

    renderAll();

    window.addEventListener("adcs:mission-event", renderAll);
    window.addEventListener("adcs:mission-events-cleared", renderAll);
  }

  // ----------------------------------------------------------
  // STANDARD LEGAL FOOTER
  // ----------------------------------------------------------

  const legalNotice =
    "Academic simulation and research demonstrator only. This project is not flight-qualified hardware, an operational spacecraft, or a live mission-control service. Telemetry, orbital states, risk scores and capture outcomes shown on this website may be simulated or illustrative and must not be treated as verified live data. No operational authorization or flight-safety assurance is implied. Third-party assets and libraries remain subject to their respective licenses.";

  function ensureLegalFooter() {
    const footer = document.querySelector("[data-legal-footer]");

    if (!footer) return;

    const notice = footer.querySelector("[data-legal-notice]");

    if (notice && !notice.textContent.trim()) {
      notice.textContent = legalNotice;
    }

    const year = footer.querySelector("[data-footer-year]");

    if (year) {
      year.textContent = String(new Date().getUTCFullYear());
    }
  }

  ADCS.legalNotice = legalNotice;

  // ----------------------------------------------------------
  // EXTERNAL COMPONENT HOOKS
  // ----------------------------------------------------------

  function setupCustomControls() {
    document.querySelectorAll("[data-action]").forEach((control) => {
      if (control.dataset.adcsActionBound === "true") return;

      control.dataset.adcsActionBound = "true";

      control.addEventListener("click", () => {
        const action = control.dataset.action;

        if (action === "clear-event-log") {
          ADCS.events.clear();
          ADCS.events.record({
            type: "INFO",
            message: "Event log cleared by the user."
          });
        }

        if (action === "reset-mission-case") {
          ADCS.mission.setCase("CAPTURE");
        }

        if (action === "scroll-top") {
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      });
    });
  }

  // ----------------------------------------------------------
  // INITIALIZATION
  // ----------------------------------------------------------

  function initialize() {
    setupNavigation();
    setupRevealAnimations();
    setupClocks();
    setupEventLog();
    ensureLegalFooter();
    setupCustomControls();

    bindCaseControls();
    listenForExternalCaseChanges();

    const currentCase = getCurrentCase();
    updateCaseControls(currentCase);
    updateCaseReadouts(currentCase);

    if (!sessionStorage.getItem("adcsPageInitialized")) {
      recordEvent({
        type: "SYSTEM",
        message: `ADCS-01 interface initialized on ${document.body?.dataset.page || "page"}.`,
        state: currentCase
      });

      try {
        sessionStorage.setItem("adcsPageInitialized", "true");
      } catch (_) {
        // The interface remains usable if session storage is unavailable.
      }
    }

    document.documentElement.classList.add("adcs-ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();