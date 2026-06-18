"""
Phase 3 test script — calls both mock publish endpoints directly.
Run with the FastAPI server already up: uvicorn main:app --reload --port 8888
"""
import os
import requests

SERVER = os.environ.get("SERVER", "http://127.0.0.1:8888")

PAYLOAD = {
    "image_url": "http://127.0.0.1:8888/review/test123/image",
    "description": "AI is transforming how brands create and schedule social media content. "
                   "Human-in-the-loop workflows ensure quality before every post goes live.",
    "scheduled_at": "2026-06-21T10:00:00Z",
}

print("Testing POST /mock/facebook/post ...")
resp = requests.post(f"{SERVER}/mock/facebook/post", json=PAYLOAD)
resp.raise_for_status()
fb = resp.json()
assert fb["status"] == "scheduled", f"FAIL: {fb}"
assert fb["post_id"].startswith("fb_"), f"FAIL: unexpected post_id format: {fb['post_id']}"
print(f"  post_id : {fb['post_id']}")
print(f"  status  : {fb['status']}")
print(f"  platform: {fb['platform']}")

print()
print("Testing POST /mock/instagram/post ...")
resp = requests.post(f"{SERVER}/mock/instagram/post", json=PAYLOAD)
resp.raise_for_status()
ig = resp.json()
assert ig["status"] == "scheduled", f"FAIL: {ig}"
assert ig["post_id"].startswith("ig_"), f"FAIL: unexpected post_id format: {ig['post_id']}"
print(f"  post_id : {ig['post_id']}")
print(f"  status  : {ig['status']}")
print(f"  platform: {ig['platform']}")

print()
print("Both mock publish endpoints responded correctly.")
