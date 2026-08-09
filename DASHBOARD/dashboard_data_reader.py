"""
dashboard_data_reader.py
Reference pattern for the DASHBOARD to poll BOTH live data sources without
manual re-running:

  1. SIMULATION/data/debris_state.json   -- Sam's physics sandbox (synthetic
     debris, orbital mechanics, GNC, capture events)
  2. AI_Engine/telemetry/mission_decision.json + state_machine.json
     -- member 3's real decision pipeline, running on the actual debris
     catalog (COSMOS 2251-style named objects), completely independent of
     the simulation.

These are two PARALLEL feeds, not one chained into the other -- the
dashboard's job is to display them side by side, not merge them into one
"truth." Field names below match what's actually in the repo
(AI_Engine/telemetry/mission_decision.json and state_machine.json), not
guesses.

Solves Challenge 14 (poll at a fixed interval, don't stream every frame).
"""

import json
import os
import time

# adjust these two paths to wherever your dashboard script actually sits
# relative to the repo root
SIM_STATE_PATH = "../SIMULATION/data/debris_state.json"
AI_DECISION_PATH = "../AI_Engine/telemetry/mission_decision.json"
AI_STATE_MACHINE_PATH = "../AI_Engine/telemetry/state_machine.json"

POLL_INTERVAL_S = 1.5


def _load_json(path):
    """Defensive read: main.py/mission_report.py write atomically, but
    poll loops should never crash on a momentarily-missing or mid-write
    file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def load_simulation_state():
    """Sam's physics sandbox output. Key fields: timestamp_s,
    spacecraft.{total_mass_kg, remaining_delta_v_km_s, storage_full},
    tracked_debris[], mission_state, abort_log[]."""
    return _load_json(SIM_STATE_PATH)


def load_ai_decision():
    """Member 3's real decision output. Key fields: mission_id,
    tracking_id, target_name (real catalog name, e.g. 'COSMOS 2251'),
    risk_level, risk_score, capture_method, capture_feasible,
    decision ('ABORT'/'PROCEED'-style), reason, timestamp."""
    return _load_json(AI_DECISION_PATH)


def load_ai_state_machine():
    """Member 3's decision-engine FSM snapshot. Key fields: current_state
    (one of SEARCH/TRACK/APPROACH/ALIGN/CAPTURE/VERIFY/STORE/STABILIZE/
    DISPOSE/ABORT), allowed_transitions."""
    return _load_json(AI_STATE_MACHINE_PATH)


def poll_forever(interval_s=POLL_INTERVAL_S, on_update=None):
    """
    Polls all three files every interval_s seconds. Calls on_update(dict)
    only when something actually changed, so the dashboard doesn't
    re-render on every tick for no reason.

    on_update receives:
        {
          "simulation": <debris_state.json dict or None>,
          "ai_decision": <mission_decision.json dict or None>,
          "ai_state": <state_machine.json dict or None>,
        }
    """
    last_sim_t = None
    last_ai_t = None
    last_ai_state = None

    print(f"Dashboard polling every {interval_s}s. Ctrl+C to stop.")
    try:
        while True:
            sim = load_simulation_state()
            ai_decision = load_ai_decision()
            ai_state = load_ai_state_machine()

            sim_t = sim.get("timestamp_s") if sim else None
            ai_t = ai_decision.get("timestamp") if ai_decision else None
            ai_s = ai_state.get("current_state") if ai_state else None

            changed = (sim_t != last_sim_t) or (ai_t != last_ai_t) or (ai_s != last_ai_state)
            if changed and on_update:
                on_update({"simulation": sim, "ai_decision": ai_decision, "ai_state": ai_state})

            last_sim_t, last_ai_t, last_ai_state = sim_t, ai_t, ai_s
            time.sleep(interval_s)
    except KeyboardInterrupt:
        print("\nStopped.")


def _demo_print(update):
    sim = update["simulation"]
    ai = update["ai_decision"]
    ai_s = update["ai_state"]
    sim_line = f"sim: t={sim['timestamp_s']:.0f}s state={sim['mission_state']}" if sim else "sim: (no data yet)"
    ai_line = f"ai: target={ai['target_name']} decision={ai['decision']}" if ai else "ai: (no data yet)"
    ai_state_line = f"ai_fsm: {ai_s['current_state']}" if ai_s else "ai_fsm: (no data yet)"
    print(f"{sim_line}  |  {ai_line}  |  {ai_state_line}")


if __name__ == "__main__":
    poll_forever(on_update=_demo_print)
