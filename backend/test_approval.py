"""
Phase 2 test script — verifies all three approval paths without n8n.
Run with the FastAPI server already up: uvicorn main:app --reload
"""
import os
import requests

SERVER = os.environ.get("SERVER", "http://127.0.0.1:8888")
SAMPLE_COPY = (
    "Exciting breakthroughs in AI are transforming social media automation. "
    "From intelligent content generation to human-in-the-loop review systems, "
    "modern workflows now blend machine speed with human judgment seamlessly."
)


def get_image_url() -> str:
    """Call /compose-image to get a real image_url for testing."""
    resp = requests.post(f"{SERVER}/compose-image", json={"title": "AI Trends 2024"})
    resp.raise_for_status()
    return resp.json()["image_url"]


def make_review(label: str) -> str:
    image_url = get_image_url()
    resp = requests.post(f"{SERVER}/request-approval", json={
        "copy": SAMPLE_COPY,
        "image_url": image_url,
        "resume_webhook_url": f"{SERVER}/test-webhook-sink",
    })
    resp.raise_for_status()
    data = resp.json()
    print(f"  review_id={data['review_id']}   review_url={data['review_url']}")
    return data["review_id"]


def verify_html(review_id: str) -> None:
    resp = requests.get(f"{SERVER}/review/{review_id}")
    resp.raise_for_status()
    html = resp.text
    assert "textarea" in html,                    "FAIL: no textarea"
    assert "Approve" in html,                     "FAIL: no Approve button"
    assert "Edit" in html,                        "FAIL: no Edit & Approve button"
    assert "Reject" in html,                      "FAIL: no Reject button"
    assert f"/review/{review_id}/image" in html,  "FAIL: no image src"
    print(f"  HTML OK: textarea + 3 buttons + image tag all present")


def verify_image(review_id: str) -> None:
    resp = requests.get(f"{SERVER}/review/{review_id}/image")
    resp.raise_for_status()
    assert "image/png" in resp.headers["content-type"], "FAIL: wrong content-type"
    print(f"  Image OK: {len(resp.content):,} bytes, content-type=image/png")


# ─── PATH 1: Approve (copy sent unchanged) ───────────────────────────────────
print("=" * 58)
print("PATH 1 — Approve (copy unchanged)")
print("=" * 58)
rid = make_review("approve")
verify_html(rid)
verify_image(rid)

resp = requests.post(f"{SERVER}/review/{rid}/decision",
                     json={"decision": "approved", "edited_copy": None})
resp.raise_for_status()
d = resp.json()
assert d["status"] == "approved",    f"FAIL: status={d['status']}"
assert d["callback_status"] == 200,  f"FAIL: callback_status={d['callback_status']}"
assert d["final_copy"] == SAMPLE_COPY, "FAIL: final_copy should equal original"
print(f"  status={d['status']}   callback_http={d['callback_status']}")
print(f"  final_copy (unchanged): \"{d['final_copy'][:70]}...\"")

# ─── PATH 2: Edit & Approve (human modifies copy) ────────────────────────────
print()
print("=" * 58)
print("PATH 2 — Edit & Approve (human modifies copy)")
print("=" * 58)
EDITED_COPY = (
    "HUMAN EDIT: AI-powered social media automation is revolutionizing "
    "brand content strategies. Teams can now review, approve, and refine "
    "AI-generated posts before they go live — ensuring quality at scale."
)
rid = make_review("edit-approve")
verify_html(rid)

resp = requests.post(f"{SERVER}/review/{rid}/decision",
                     json={"decision": "approved", "edited_copy": EDITED_COPY})
resp.raise_for_status()
d = resp.json()
assert d["status"] == "approved",      f"FAIL: status={d['status']}"
assert d["callback_status"] == 200,    f"FAIL: callback_status={d['callback_status']}"
assert d["final_copy"] == EDITED_COPY, f"FAIL: final_copy did not use edited text"
print(f"  status={d['status']}   callback_http={d['callback_status']}")
print(f"  final_copy (edited):   \"{d['final_copy'][:70]}...\"")

# ─── PATH 3: Reject ──────────────────────────────────────────────────────────
print()
print("=" * 58)
print("PATH 3 — Reject")
print("=" * 58)
rid = make_review("reject")
verify_html(rid)

resp = requests.post(f"{SERVER}/review/{rid}/decision",
                     json={"decision": "rejected", "edited_copy": None})
resp.raise_for_status()
d = resp.json()
assert d["status"] == "rejected",   f"FAIL: status={d['status']}"
assert d["callback_status"] == 200, f"FAIL: callback_status={d['callback_status']}"
print(f"  status={d['status']}   callback_http={d['callback_status']}")

print()
print("All 3 approval paths passed. Webhook callback fired correctly each time.")
