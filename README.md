# Assessment 1 — AI Agent Workflow Automation (n8n + Human-in-the-Loop)

AI-driven social media automation workflow with brand-consistent image compositing, LLM content generation, and a human approval gate before publishing.

---

## What this does

1. A web form accepts a **post topic** and **scheduled publish time**.
2. Groq (Llama 3.3 70B) generates social media copy, enforcing a strict **90–150 word** count with a retry loop.
3. A FastAPI/Pillow backend composites a **1080×1080 brand card** — logo pinned top-right, topic text centred in the lower third — at fixed pixel coordinates every time.
4. The workflow **pauses** and sends the copy + image to a human reviewer via a webhook dashboard.
5. The reviewer clicks **Approve**, **Edit & Approve**, or **Reject**.
6. On approval the workflow resumes and publishes to mock Facebook and Instagram endpoints.

---

## Repository layout

```
.
├── workflow.json                  # n8n workflow export (import this into n8n Cloud)
├── backend/
│   ├── main.py                    # FastAPI app — all endpoints
│   ├── compositing.py             # Pillow image compositing engine
│   ├── requirements.txt
│   ├── test_flow.py               # Phase 1 tests (image compositing)
│   ├── test_approval.py           # Phase 2 tests (all 3 HITL paths)
│   └── test_mock_publish.py       # Phase 3 tests (mock publish endpoints)
└── docs/
    ├── n8n_setup.md                      # Step-by-step n8n Cloud setup guide
    ├── n8n_build_guide.md                # Manual node-by-node build guide (fallback if import fails)
    ├── architecture.md                   # System architecture and data flow
    ├── explain.md                        # Must Explain answers (brief requirement)
    └── demo_script.md                    # Spoken script for the demo video
```

---

## Quick start — local FastAPI server

**Requirements:** Python 3.11+, Windows/Mac/Linux

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8888
```

The server starts at `http://127.0.0.1:8888`. Swagger UI is at `/docs`.

**Run the test suite** (server must be running):

```bash
# Phase 1 — image compositing
python test_flow.py

# Phase 2 — HITL approval flow (all 3 paths)
python test_approval.py

# Phase 3 — mock publish endpoints
python test_mock_publish.py
```

---

## n8n Cloud setup

Full walkthrough: [`docs/n8n_setup.md`](docs/n8n_setup.md)

Short version:

1. **Expose local server via ngrok:**
   ```
   ngrok http 8888
   ```
   Copy the HTTPS URL (e.g. `https://abc123.ngrok-free.app`).

2. **Import `workflow.json`** into n8n Cloud (Workflows → + → Import from file).

3. **Add your Groq API key** — open the **Generate Post Content** Code node and replace the placeholder line:
   ```js
   const apiKey = 'PASTE_YOUR_GROQ_API_KEY_HERE';
   ```
   with your key from https://console.groq.com (starts with `gsk_`).
   (The free n8n Cloud plan has no environment variables, so the key is pasted directly into the node.)

4. **Replace `REPLACE_WITH_NGROK_URL`** with your ngrok URL in these 6 spots:
   - Compose Brand Image → URL
   - Request Human Approval → URL
   - Publish to Facebook → URL **and** image_url value
   - Publish to Instagram → URL **and** image_url value

5. **Activate** the workflow (toggle top-right of canvas).

6. Open the Form Trigger's **Production URL** in a browser and submit a topic.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/compose-image` | Composite brand card, returns `{ image_url, image_path }` |
| `GET` | `/output/{filename}` | Serve generated image |
| `POST` | `/request-approval` | Register pending review, returns `{ review_id, review_url }` |
| `GET` | `/review/{id}` | HTML approval dashboard |
| `GET` | `/review/{id}/image` | Redirect to composited image |
| `POST` | `/review/{id}/decision` | Submit human decision, fires n8n resume webhook |
| `POST` | `/mock/facebook/post` | Mock Facebook publish (logs to console) |
| `POST` | `/mock/instagram/post` | Mock Instagram publish (logs to console) |

---

## Demo video

[Insert Loom / YouTube / Drive link here]

The video covers:
- 3 separate topic submissions (proving brand card consistency)
- Approve path (copy published unchanged)
- Edit & Approve path (human rewrites copy before publish)
- Reject path (workflow stops, no publish)

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Workflow orchestration | n8n Cloud |
| LLM | Groq — Llama 3.3 70B Versatile (free tier) |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Image compositing | Pillow (PIL) |
| Tunnel (local → cloud) | ngrok |
| Mock social platforms | FastAPI endpoints (Facebook, Instagram) |
