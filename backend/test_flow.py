"""
Phase 1 test script — calls /compose-image with 3 titles and saves PNGs.
Run with the FastAPI server already up: uvicorn main:app --reload
"""
import os
import requests

SERVER_URL = os.environ.get("SERVER", "http://127.0.0.1:8888")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TITLES = [
    ("short",  "AI Trends 2024"),
    ("medium", "How Artificial Intelligence Is Changing the Way We Work and Live Every Day"),
    ("long",   "The Complete Guide to Understanding How Modern Machine Learning Models Are "
               "Transforming Every Industry From Healthcare to Finance to Creative Arts and "
               "Why You Should Care About This Revolution Right Now Before It Is Too Late"),
]

for label, title in TITLES:
    print(f"[{label}] Sending: {title[:70]}{'...' if len(title) > 70 else ''}")
    resp = requests.post(f"{SERVER_URL}/compose-image", json={"title": title})
    resp.raise_for_status()
    data = resp.json()                          # now returns JSON, not raw PNG
    image_url = data["image_url"]               # e.g. /output/abc123.png
    # Download the PNG from the serve endpoint
    img_resp = requests.get(f"{SERVER_URL}{image_url}")
    img_resp.raise_for_status()
    out_path = os.path.join(OUTPUT_DIR, f"test_{label}.png")
    with open(out_path, "wb") as fh:
        fh.write(img_resp.content)
    size_kb = len(img_resp.content) // 1024
    print(f"  image_url: {image_url}")
    print(f"  Saved -> {out_path}  ({size_kb} KB)\n")

print("All 3 images generated. Open backend/test_output/ to inspect them.")
