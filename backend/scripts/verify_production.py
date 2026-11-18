import json
import time
import urllib.request
import urllib.error

RENDER_URL = "https://zamp-invoice-agent-api.onrender.com"

def post_json(path: str, data: dict):
    req = urllib.request.Request(
        f"{RENDER_URL}{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def get_json(path: str):
    req = urllib.request.Request(f"{RENDER_URL}{path}")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def stream_events(path: str, timeout: int = 45):
    headers = {"Accept": "text/event-stream"}
    req = urllib.request.Request(f"{RENDER_URL}{path}", headers=headers)
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

def run_sample(sample_id: str, use_cache: bool = True):
    print(f"\n--- Running sample {sample_id} (cache={use_cache}) ---")
    status, run_init = post_json("/api/runs", {"sample_id": sample_id, "use_cache": use_cache})
    run_id = run_init.get("run_id") or run_init.get("id")
    print(f"Created run: {run_id}")
    
    events = stream_events(f"/api/runs/{run_id}/events")
    print(f"Streamed {len(events)} events over SSE")
    
    status, run = get_json(f"/api/runs/{run_id}")
    decision = run.get("decision")
    label = run.get("label")
    headline = run.get("headline")
    print(f"Result -> Status: {run['status']}, Decision: {decision}, Label: {label}")
    print(f"Headline: {headline}")
    return run

def main():
    print("=== 1. Health check ===")
    status, health = get_json("/api/health")
    print("Health:", status, health)
    assert health["status"] == "ok"
    assert health["db"] == "ok"
    assert health["llm_configured"] is True

    print("\n=== 2. Admin Reset ===")
    status, reset_res = post_json("/api/admin/reset", {"confirm": "RESET"})
    print("Reset:", status, reset_res)

    print("\n=== 3. Run F01 (Happy Path -> APPROVE) ===")
    run_f01 = run_sample("F01")
    assert run_f01["decision"] == "APPROVE"
    assert "Approved" in run_f01["label"]

    print("\n=== 4. Run F02 (Price variance & tax discrepancy -> REVIEW) ===")
    run_f02 = run_sample("F02")
    assert run_f02["decision"] == "REVIEW"

    print("\n=== 5. Run F05 (Bank detail mismatch -> HOLD) ===")
    run_f05 = run_sample("F05")
    assert run_f05["decision"] == "HOLD"
    assert "hold" in run_f05["label"].lower()

    print("\n=== 6. Run F04 (Buyer GSTIN mismatch -> REJECT) ===")
    run_f04 = run_sample("F04")
    assert run_f04["decision"] == "REJECT"

    print("\n=== 7. Run F03 with cache=False (Scanned vision extraction in prod -> REVIEW) ===")
    run_f03 = run_sample("F03", use_cache=False)
    assert run_f03["decision"] == "REVIEW"
    assert run_f03["status"] == "COMPLETED"

    print("\n=== 8. Duplicate check: Re-run F01 -> REJECT ===")
    run_f01_dup = run_sample("F01")
    assert run_f01_dup["decision"] == "REJECT"
    assert "Duplicate" in run_f01_dup["headline"]

    print("\n=== 9. Final Reset so reviewers start clean ===")
    status, reset_final = post_json("/api/admin/reset", {"confirm": "RESET"})
    print("Final Reset:", status, reset_final)

    print("\n=============================================")
    print("ALL PRODUCTION ACCEPTANCE CHECKS PASSED 100%!")
    print("=============================================")

if __name__ == "__main__":
    main()
