from fastapi import FastAPI, Request
from fastapi.responses import Response, HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, ConfigDict
from pathlib import Path
import uuid
import requests as req_lib

from compositing import compose_image

app = FastAPI(title="Social Media Automation Backend")

# ── Persistent image output directory ────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── In-memory review store ────────────────────────────────────────────────────
_reviews: dict[str, dict] = {}


# ── Phase 1: Image compositing ────────────────────────────────────────────────

class ComposeRequest(BaseModel):
    title: str

@app.post("/compose-image")
def compose(req: ComposeRequest):
    """
    Composite title onto brand card. Saves PNG to output/ and returns JSON
    with image_url (served by this server) and image_path (absolute disk path).
    n8n uses image_url; local scripts can use image_path.
    """
    png_bytes = compose_image(req.title)
    filename = f"{uuid.uuid4().hex}.png"
    save_path = OUTPUT_DIR / filename
    save_path.write_bytes(png_bytes)
    return {
        "image_url": f"/output/{filename}",
        "image_path": str(save_path),
    }

@app.get("/output/{filename}")
def serve_output_image(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return Response(status_code=404)
    return FileResponse(str(path), media_type="image/png")


# ── Phase 2: Approval flow ────────────────────────────────────────────────────

class ApprovalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    post_copy: str = Field(alias="copy")   # JSON key stays "copy"
    image_url: str                          # URL served by this FastAPI server
    resume_webhook_url: str

class DecisionRequest(BaseModel):
    decision: str           # "approved" | "rejected"
    edited_copy: str | None = None


@app.post("/request-approval")
def request_approval(body: ApprovalRequest, request: Request):
    review_id = uuid.uuid4().hex[:8]
    _reviews[review_id] = {
        "copy": body.post_copy,
        "image_url": body.image_url,
        "resume_webhook_url": body.resume_webhook_url,
        "status": "pending",
    }

    # Build an absolute, clickable review URL. Behind ngrok the request host is
    # the public tunnel domain; ngrok terminates TLS so force https for it.
    base = str(request.base_url).rstrip("/")
    if "ngrok" in base and base.startswith("http://"):
        base = "https://" + base[len("http://"):]
    review_url = f"{base}/review/{review_id}"

    # Notify the evaluator: print a prominent banner the reviewer can act on.
    print("\n" + "=" * 72)
    print("  ACTION REQUIRED - HUMAN APPROVAL NEEDED")
    print(f"  Review post [{review_id}] and approve / edit / reject here:")
    print(f"  {review_url}")
    print("=" * 72 + "\n")

    return {"review_id": review_id, "review_url": review_url}


@app.get("/review/{review_id}", response_class=HTMLResponse)
def review_page(review_id: str):
    record = _reviews.get(review_id)
    if not record:
        return HTMLResponse("<h1>Review not found</h1>", status_code=404)

    copy = record["copy"]
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Review Post &mdash; {review_id}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; max-width: 860px; margin: 40px auto;
            padding: 0 20px; color: #222; background: #f9f9f9; }}
    h2   {{ border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
    img  {{ max-width: 100%; border: 1px solid #ccc; border-radius: 6px; margin-top: 8px; }}
    label {{ font-weight: bold; display: block; margin-top: 22px; font-size: 15px; }}
    textarea {{ width: 100%; height: 160px; font-size: 14px; padding: 10px;
                border: 1px solid #ccc; border-radius: 4px; margin-top: 6px;
                resize: vertical; background: #fff; }}
    .buttons {{ display: flex; gap: 12px; margin-top: 18px; flex-wrap: wrap; }}
    button   {{ padding: 11px 28px; font-size: 15px; font-weight: bold;
                cursor: pointer; border: none; border-radius: 5px; }}
    .approve      {{ background: #28a745; color: #fff; }}
    .edit-approve {{ background: #0069d9; color: #fff; }}
    .reject       {{ background: #dc3545; color: #fff; }}
    #status {{ margin-top: 18px; font-size: 15px; padding: 10px; border-radius: 4px; }}
    .ok  {{ background: #d4edda; color: #155724; }}
    .err {{ background: #f8d7da; color: #721c24; }}
  </style>
</head>
<body>
  <h2>Human Review &mdash; Post ID: <code>{review_id}</code></h2>
  <img src="/review/{review_id}/image" alt="Composited post card">
  <label for="copy">Post Copy <span style="font-weight:normal;color:#666">(edit the text below if needed, then click Edit &amp; Approve)</span></label>
  <textarea id="copy">{copy}</textarea>
  <div class="buttons">
    <button class="approve"      onclick="decide('approved', false)">Approve</button>
    <button class="edit-approve" onclick="decide('approved', true)">Edit &amp; Approve</button>
    <button class="reject"       onclick="decide('rejected', false)">Reject</button>
  </div>
  <p id="status"></p>
  <script>
    function decide(decision, useEdit) {{
      const editedCopy = useEdit ? document.getElementById('copy').value.trim() : null;
      fetch('/review/{review_id}/decision', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ decision, edited_copy: editedCopy }})
      }})
      .then(r => r.json())
      .then(d => {{
        const el = document.getElementById('status');
        el.className = 'ok';
        el.textContent = 'Submitted: ' + d.status +
          (d.final_copy ? ' | copy: "' + d.final_copy.slice(0, 70) + '..."' : '');
        document.querySelectorAll('button').forEach(b => b.disabled = true);
      }})
      .catch(e => {{
        const el = document.getElementById('status');
        el.className = 'err';
        el.textContent = 'Error: ' + e;
      }});
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/review/{review_id}/image")
def review_image(review_id: str):
    record = _reviews.get(review_id)
    if not record:
        return Response(status_code=404)
    # image_url is like "/output/abc123.png" — redirect to the output endpoint
    return RedirectResponse(url=record["image_url"])


@app.post("/review/{review_id}/decision")
def decision(review_id: str, body: DecisionRequest):
    record = _reviews.get(review_id)
    if not record:
        return JSONResponse({"error": "review not found"}, status_code=404)

    final_copy = (body.edited_copy or "").strip() or record["copy"]

    callback_payload = {
        "decision": body.decision,
        "final_copy": final_copy,
        "review_id": review_id,
    }

    resume_url = record["resume_webhook_url"]
    print(f"[CALLBACK] Firing resume webhook: {resume_url}")
    try:
        cb = req_lib.post(resume_url, json=callback_payload, timeout=10)
        callback_status = cb.status_code
        print(f"[CALLBACK] n8n responded with status: {callback_status}")
        if callback_status != 200:
            print(f"[CALLBACK] Response body: {cb.text[:300]}")
    except Exception as exc:
        callback_status = f"error: {exc}"
        print(f"[CALLBACK] ERROR calling resume webhook: {exc}")

    record["status"] = body.decision
    return JSONResponse({
        "status": body.decision,
        "callback_status": callback_status,
        "final_copy": final_copy,
    })


# ── Phase 3: Mock publish endpoints ──────────────────────────────────────────

class PublishRequest(BaseModel):
    image_url: str
    description: str
    scheduled_at: str


@app.post("/mock/facebook/post")
def mock_facebook(body: PublishRequest):
    post_id = f"fb_{uuid.uuid4().hex[:10]}"
    print(f"[MOCK FACEBOOK] post_id={post_id}")
    print(f"  image_url    : {body.image_url}")
    print(f"  description  : {body.description[:120]}")
    print(f"  scheduled_at : {body.scheduled_at}")
    return {"post_id": post_id, "platform": "facebook", "status": "scheduled"}


@app.post("/mock/instagram/post")
def mock_instagram(body: PublishRequest):
    post_id = f"ig_{uuid.uuid4().hex[:10]}"
    print(f"[MOCK INSTAGRAM] post_id={post_id}")
    print(f"  image_url    : {body.image_url}")
    print(f"  description  : {body.description[:120]}")
    print(f"  scheduled_at : {body.scheduled_at}")
    return {"post_id": post_id, "platform": "instagram", "status": "scheduled"}


# ── Test helper: webhook sink ─────────────────────────────────────────────────

@app.post("/test-webhook-sink")
async def test_webhook_sink(request: Request):
    payload = await request.json()
    print(f"[webhook-sink] Received: {payload}")
    return {"received": True, "payload": payload}
