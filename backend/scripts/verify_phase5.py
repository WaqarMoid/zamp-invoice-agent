import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def post_json(path, data):
    req = urllib.request.Request(
        f"{BASE}{path}", data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def get_json(path, headers=None):
    req = urllib.request.Request(f"{BASE}{path}", headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def stream_events(path, last_event_id=None, timeout=30):
    headers = {"Accept": "text/event-stream"}
    if last_event_id is not None:
        headers["Last-Event-ID"] = str(last_event_id)
    req = urllib.request.Request(f"{BASE}{path}", headers=headers)
    events = []
    start = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        current_event = {}
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str:
                if current_event:
                    events.append(current_event)
                    if current_event.get("event") in ("run.completed", "run.failed"):
                        break
                    current_event = {}
                continue
            if line_str.startswith("id:"):
                current_event["id"] = int(line_str[3:].strip())
            elif line_str.startswith("event:"):
                current_event["event"] = line_str[6:].strip()
            elif line_str.startswith("data:"):
                current_event["data"] = json.loads(line_str[5:].strip())
            if time.time() - start > timeout:
                break
        if current_event and current_event not in events:
            events.append(current_event)
    return events


print("=== 1. POST /api/admin/reset ===")
status, res = post_json("/api/admin/reset", {"confirm": "RESET"})
print(f"Status: {status}, Response: {res}")

print("\n=== 2. POST /api/runs F01 -> APPROVE ===")
status, res = post_json("/api/runs", {"sample_id": "F01"})
run_f01 = res.get("run_id") or res.get("id")
print(f"Created run F01: {run_f01}")
evs_f01 = stream_events(f"/api/runs/{run_f01}/events")
print(f"Received {len(evs_f01)} events. Last event: {evs_f01[-1] if evs_f01 else None}")
# Verify run detail
status, detail_f01 = get_json(f"/api/runs/{run_f01}")
print(f"Run detail decision: {detail_f01['decision']}, label: {detail_f01['label']}")
print(f"Run headline: {detail_f01['headline']}")

print("\n=== 3. F02 -> REVIEW, F05 -> HOLD, F04 -> REJECT ===")
for sample_id, expected_dec in [("F02", "REVIEW"), ("F05", "HOLD"), ("F04", "REJECT")]:
    status, res = post_json("/api/runs", {"sample_id": sample_id})
    rid = res.get("run_id") or res.get("id")
    evs = stream_events(f"/api/runs/{rid}/events")
    status, detail = get_json(f"/api/runs/{rid}")
    print(f"Sample {sample_id} ({rid[:8]}): decision={detail['decision']}, events={len(evs)}")
    assert detail["decision"] == expected_dec, f"Expected {expected_dec}, got {detail['decision']}"

print("\n=== 4. Re-run F01 -> REJECT (exact duplicate) ===")
status, res = post_json("/api/runs", {"sample_id": "F01"})
run_f01_dup = res.get("run_id") or res.get("id")
evs_dup = stream_events(f"/api/runs/{run_f01_dup}/events")
status, detail_dup = get_json(f"/api/runs/{run_f01_dup}")
print(f"Re-run F01 decision: {detail_dup['decision']}")
print(f"Re-run headline: {detail_dup['headline']}")
assert detail_dup["decision"] == "REJECT", f"Expected REJECT, got {detail_dup['decision']}"

print("\n=== 5. GET /api/purchase-orders/PO-2026-0412 ===")
status, po_data = get_json("/api/purchase-orders/PO-2026-0412")
print(f"PO status: {po_data['status']}, billed_pct: {po_data['billed_pct']}")
assert po_data["billed_pct"] == 100 or po_data["billed_pct"] == 100.0, (
    f"Expected billed_pct 100, got {po_data['billed_pct']}"
)

print("\n=== 6. Reconnect test: start F03, connect after 2s with Last-Event-ID: 3 ===")
status, res = post_json("/api/runs", {"sample_id": "F03"})
run_f03 = res.get("run_id") or res.get("id")
time.sleep(2)
reconnect_evs = stream_events(f"/api/runs/{run_f03}/events", last_event_id=3)
print(f"Reconnected events count: {len(reconnect_evs)}")
ids = [e.get("id") for e in reconnect_evs]
print(f"Event IDs received: {ids}")
assert ids[0] == 4, f"Expected first reconnected event id=4, got {ids[0]}"
print("All event IDs contiguous:", ids == list(range(4, 4 + len(ids))))

print("\n=== All Phase 5 acceptance criteria successfully passed! ===")
