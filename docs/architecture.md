# System Architecture

## Component map

```
┌─────────────────────────────────────────────────────────────────┐
│                        n8n Cloud                                │
│                                                                 │
│  Form Trigger ──► Generate Post Content (Code / Groq)           │
│       │                    │                                    │
│       │           (topic, scheduled_at, copy, wordCount)        │
│       │                    │                                    │
│       │            Compose Brand Image (HTTP POST)              │
│       │                    │                                    │
│       │           (image_url, image_path)                       │
│       │                    │                                    │
│       │           Request Human Approval (HTTP POST) ───────────┼──►  FastAPI
│       │                    │              resume_webhook_url    │      /request-approval
│       │                    │                                    │      /review/{id}
│       │            Wait for Human Decision ◄───────────────────┼────  POST resume_webhook_url
│       │                    │              (decision callback)   │
│       │             Was Approved? (IF)                          │
│       │            /              \                             │
│  Publish to Facebook    Rejected — Log and Stop                 │
│  Publish to Instagram                                           │
└─────────────────────────────────────────────────────────────────┘
           │  │  │
           ▼  ▼  ▼
        FastAPI (localhost:8888) ◄── ngrok HTTPS tunnel
           │
           ├── POST /compose-image      → Pillow compositing engine
           ├── GET  /output/{filename}  → serve PNG
           ├── POST /request-approval   → in-memory review store
           ├── GET  /review/{id}        → HTML reviewer dashboard
           ├── POST /review/{id}/decision → fires n8n resume webhook
           ├── POST /mock/facebook/post  → logs to console
           └── POST /mock/instagram/post → logs to console
```

---

## Data flow — step by step

### 1. Form submission
User submits the n8n Form Trigger with:
- `topic` — free-text post subject
- `scheduled_at` — ISO 8601 publish time

### 2. LLM content generation (n8n Code node)
- Calls Groq (Llama 3.3 70B) with a `system` message enforcing 90–150 words
- Counts words after each response; sends corrective multi-turn prompts on failure
- If still out of range after 5 attempts, the node throws — strict guarantee that no out-of-range post proceeds
- Outputs: `{ topic, scheduled_at, copy, wordCount, attempts, withinRange }`

### 3. Image compositing (n8n HTTP Request → FastAPI)
- n8n POSTs `{ title: topic }` to `POST /compose-image`
- FastAPI runs `compositing.py`: opens template PNG, pastes logo at fixed pixel coords, wraps and draws title text in the lower third
- Saves PNG to `backend/output/`, returns `{ image_url, image_path }`

### 4. HITL request (n8n HTTP Request → FastAPI)
- n8n POSTs `{ copy, image_url, resume_webhook_url }` to `POST /request-approval`
  - `resume_webhook_url = $execution.resumeUrl` — n8n's unique per-execution webhook
- FastAPI stores the review in `_reviews[review_id]` and returns `{ review_id, review_url }`

### 5. Workflow suspension (n8n Wait node)
- n8n serialises execution state and suspends — zero CPU usage
- Execution can wait indefinitely (or until a configured timeout)

### 6. Human review
- Reviewer opens `http://NGROK_URL/review/{review_id}` in a browser
- Dashboard shows: composited image, generated copy in an editable textarea, three buttons
- Reviewer clicks **Approve**, **Edit & Approve** (after modifying the copy), or **Reject**

### 7. Decision callback (FastAPI → n8n)
- FastAPI `POST /review/{id}/decision` fires `requests.post(resume_webhook_url, json={ decision, final_copy, review_id })`
- n8n receives the POST and resumes the paused execution
- The Wait node nests the POST payload under `$json.body`, so the Was Approved? IF node checks `$json.body.decision`

### 8. Publish or stop
- **Approved:** n8n POSTs to `/mock/facebook/post` then `/mock/instagram/post`; FastAPI logs the payload to the terminal
- **Rejected:** n8n runs the Set node, sets `status = "rejected"`, execution ends

---

## Why each boundary exists

| Boundary | Reason |
|----------|--------|
| n8n ↔ FastAPI over HTTP | n8n has no Python runtime; FastAPI gives pixel-level Pillow control |
| ngrok tunnel | n8n Cloud (hosted) cannot reach localhost directly |
| In-memory review store | Sufficient for demo scope; trivially replaceable with Redis/Postgres |
| `$execution.resumeUrl` pattern | The correct n8n primitive for async human-in-the-loop — no polling, no external state machine |
| Groq free tier | Zero cost; very fast inference (sub-second), generous free rate limits |

---

## Sequence diagram — approve path

```
Browser      n8n Cloud          FastAPI (local)        Human Reviewer
   │              │                    │                     │
   │──submit form─►│                   │                     │
   │              │──POST /compose-image►                    │
   │              │◄── { image_url } ──│                     │
   │              │──POST /request-approval (+ resumeUrl) ──►│ (stored)
   │              │◄── { review_id } ──│                     │
   │              │                    │                     │
   │              │  [SUSPENDED]       │◄──── opens /review/{id} ──┤
   │              │                    │──── HTML dashboard ─────►│
   │              │                    │◄──── POST /decision ─────┤
   │              │                    │                     │
   │              │◄── POST resumeUrl ─│                     │
   │              │  [RESUMED]         │                     │
   │              │──POST /mock/facebook/post ──────────────►│ (logged)
   │              │──POST /mock/instagram/post ─────────────►│ (logged)
   │              │                    │                     │
```
