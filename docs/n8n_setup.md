# n8n Workflow Walkthrough — Beginner Guide

This guide walks you through setting up the HITL Social Media Automation workflow in n8n Cloud, step by step, assuming you have the n8n editor open and have never built a workflow like this before.

---

## Before you start — what you need running

1. **ngrok tunnel** — open a terminal and run:
   ```
   ngrok http 8888
   ```
   You'll get a URL like `https://abc123.ngrok-free.app`. Copy it. This is your `NGROK_URL`.

2. **FastAPI server** — in VS Code terminal, from the `backend/` folder:
   ```
   uvicorn main:app --reload --port 8888
   ```
   Leave it running. All n8n HTTP calls go through ngrok to this server.

3. **Your Groq API key** — get a free key at https://console.groq.com → API Keys. You'll paste it directly inside the Code node in Step 2 below (no environment variables needed).

> **Important:** The free ngrok URL changes every time you restart the tunnel. If you restart ngrok, you must update every `REPLACE_WITH_NGROK_URL` in the workflow nodes.

---

## Step 1 — Import the workflow JSON

1. In n8n Cloud, click **Workflows** in the left sidebar.
2. Click the **+** button (or **New Workflow**) to open an empty canvas.
3. In the top-right area of the canvas, click the **three-dot menu** (⋮) or the **...** icon.
4. Click **Import from file**.
5. Select `workflow.json` from the root of this repository.
6. The workflow will appear on the canvas with all 9 nodes connected.

If you don't see an import option, try: **Settings icon → Import** or look for a JSON import button in the node panel.

---

## Step 2 — Paste your Groq API key into the Code node

The "Generate Post Content" Code node calls the Groq API (Llama 3.3 70B, free tier). On the free n8n Cloud plan, environment variables are an Enterprise feature, so the key is pasted directly inside the Code node.

1. Get a free key: go to https://console.groq.com → click **API Keys** → **Create API Key**. Copy it — it starts with `gsk_`.

2. In n8n, click the **Generate Post Content** node on the canvas to open it.

3. Inside the code editor, find this line near the top:
   ```
   const apiKey = 'PASTE_YOUR_GROQ_API_KEY_HERE';
   ```

4. Replace `PASTE_YOUR_GROQ_API_KEY_HERE` with your actual key:
   ```
   const apiKey = 'PASTE_YOUR_GROQ_API_KEY_HERE';
   ```

5. Click **Back** or close the node panel. The key is now saved in the workflow.

> The node will throw a clear error message if you forget to replace the placeholder, so you can't accidentally run it with a missing key.

---

## Step 3 — Replace NGROK_URL in every HTTP Request node

There are **6 places** containing `REPLACE_WITH_NGROK_URL`. You need to update each one with your actual ngrok URL (e.g. `https://abc123.ngrok-free.app`).

Click each node listed below and update the field(s):

| Node | Field | What to change |
|---|---|---|
| **Compose Brand Image** | URL | `REPLACE_WITH_NGROK_URL/compose-image` |
| **Request Human Approval** | URL | `REPLACE_WITH_NGROK_URL/request-approval` |
| **Publish to Facebook** | URL | `REPLACE_WITH_NGROK_URL/mock/facebook/post` |
| **Publish to Facebook** | Body → image_url | `'REPLACE_WITH_NGROK_URL' + ...` |
| **Publish to Instagram** | URL | `REPLACE_WITH_NGROK_URL/mock/instagram/post` |
| **Publish to Instagram** | Body → image_url | `'REPLACE_WITH_NGROK_URL' + ...` |

To edit a node: **click the node** → the settings panel opens on the right. Find the field containing `REPLACE_WITH_NGROK_URL` and replace the placeholder with your ngrok URL (no trailing slash).

---

## Step 4 — Understand the Wait node

The "Wait for Human Decision" node is the core of the Human-in-the-Loop mechanism. Here's what it does in plain terms:

- When n8n reaches this node, it **completely pauses** the workflow execution. The execution is saved to disk. No CPU is used. Nothing is polling.
- n8n generates a **unique webhook URL** for this exact execution (accessible via `$execution.resumeUrl`). This URL was already passed to your FastAPI server in the previous step ("Request Human Approval").
- When the human opens the approval dashboard and clicks Approve/Edit/Reject, FastAPI POSTs the decision to that unique URL.
- n8n receives the POST, **wakes up the execution**, and the POST payload (`{ decision, final_copy, review_id }`) becomes the input to the next node, **nested under `$json.body`** (so the IF node reads `$json.body.decision`).

**Two settings matter in the Wait node:** `Resume` = `On webhook call`, and `HTTP Method` = `POST`. The POST method is essential — FastAPI sends the callback as a POST, and if the Wait node is left on the default GET it rejects the callback with a 404 and the workflow stays stuck. The webhook URL itself is generated automatically by n8n per execution.

**How to find the resume URL (for debugging):**
1. Run the workflow once.
2. In n8n, go to **Executions** (left sidebar).
3. Open the running execution.
4. Click on the "Wait for Human Decision" node.
5. You'll see the resume webhook URL displayed there. This is the same URL that was sent to FastAPI.

---

## Step 5 — Activate the workflow

For the Form Trigger to actually listen for form submissions, the workflow must be **activated** (not just saved).

1. In the top-right of the n8n canvas, find the toggle switch that says **Inactive**.
2. Click it to turn it **Active**.
3. The Form Trigger node will now be listening at its webhook URL.

**To find your form URL:**
1. Click on the "Form Trigger" node.
2. In the settings panel, look for **Test URL** (for testing) or **Production URL** (when active).
3. The production URL looks like: `https://your-n8n-instance.app.n8n.cloud/webhook/hitl-social-media-form`
4. Open that URL in a browser — you'll see the form with two fields: `topic` and `scheduled_at`.

> **Test vs Production — important:** The Human-in-the-Loop Wait/resume callback only works reliably when the workflow is **Active** and submitted through the **Production URL**. In Test mode the resume webhook expires immediately and FastAPI's callback returns a 404 ("no waiting webhook with a matching path"). Always run the full demo via the **Production URL** with the workflow **Active**.

---

## Step 6 — Node-by-node walkthrough

Here's what each node does and why it's there:

### 1. Form Trigger
**What it does:** Serves a web form that accepts two inputs: a post topic and a scheduled publish time.
**Why it's there:** This is the entry point. A human (or you during the demo) fills in the form to kick off the workflow.
**Output:** `{ topic: "...", scheduled_at: "..." }`

### 2. Generate Post Content (Code node)
**What it does:** Calls the Groq API (Llama 3.3 70B, free tier) up to 5 times, checking whether the generated copy is between 90 and 150 words each time. If an attempt is out of range, it sends a corrective prompt with the word count and asks for a rewrite. If it still can't hit the range after 5 tries, the node throws and the workflow stops.
**Why it's there:** The brief requires strict word count enforcement without truncation. Measuring and regenerating (rather than cutting) keeps the copy coherent; the hard stop guarantees no out-of-range post is ever published.
**Output:** `{ topic, scheduled_at, copy, wordCount, attempts, withinRange }`

### 3. Compose Brand Image (HTTP Request)
**What it does:** POSTs the topic text to `POST /compose-image` on your FastAPI server. FastAPI uses Pillow to overlay the text onto the brand card template at fixed pixel coordinates.
**Why it's there:** n8n can't do precise pixel placement. Delegating to a Python backend gives full control over the layout.
**Output:** `{ image_url: "/output/abc123.png", image_path: "..." }`

### 4. Request Human Approval (HTTP Request)
**What it does:** POSTs to `POST /request-approval` with the generated copy, the image URL, and — most importantly — `$execution.resumeUrl`. FastAPI stores these and serves the review dashboard at `/review/{id}`.
**Why it's there:** The human needs a page to see the image and copy, and a way to send their decision back to n8n.
**Output:** `{ review_id: "...", review_url: "/review/..." }`

### 5. Wait for Human Decision (Wait node)
**What it does:** Pauses the workflow execution indefinitely (or until a timeout if configured). The execution is stored. When FastAPI POSTs the decision to `$execution.resumeUrl`, n8n wakes up. Set `HTTP Method` = `POST` so it accepts FastAPI's callback.
**Why it's there:** This is how n8n natively implements "pause until a human responds." It's not polling — it's a true webhook-based resume.
**Output (after resume):** the payload arrives nested under `body`: `$json.body = { decision: "approved"|"rejected", final_copy: "...", review_id: "..." }`

### 6. Was Approved? (IF node)
**What it does:** Checks whether `$json.body.decision == "approved"`. Routes to the publish nodes (true) or the rejection node (false).
**Why it's there:** The workflow needs to branch based on the human's decision.

### 7. Publish to Facebook (HTTP Request)
**What it does:** POSTs to `POST /mock/facebook/post` with the final copy (which may be human-edited), the image URL, and the scheduled time. The FastAPI server logs this clearly to the console.
**Why it's there:** Simulates the real Facebook publishing step. The console logs are what you'll show in the demo video.

### 8. Publish to Instagram (HTTP Request)
**What it does:** Same as Facebook, but targets `POST /mock/instagram/post`. Runs after Facebook in sequence.

### 9. Rejected — Log and Stop (Set node)
**What it does:** Sets a `status = "rejected"` field and stops. No publish action is taken.
**Why it's there:** The workflow needs a clear endpoint for the rejection path so the execution history shows what happened.

---

## Step 7 — Run your first test

1. Make sure the workflow is **Active**, then open the Form Trigger's **Production URL** in a browser. (The HITL resume only works in Active/Production mode — see the note in Step 5.)
2. Fill in:
   - topic: `How AI is changing social media marketing`
   - scheduled_at: `2026-06-21T10:00:00Z`
3. Submit.
4. Watch the n8n execution panel — the workflow runs through nodes 1-4, then **pauses at node 5**.
5. **Look at your FastAPI terminal.** When the approval is requested, the server prints a banner with the full clickable review link:
   ```
   ========================================================================
     ACTION REQUIRED - HUMAN APPROVAL NEEDED
     Review post [a1b2c3d4] and approve / edit / reject here:
     https://abc123.ngrok-free.app/review/a1b2c3d4
   ========================================================================
   ```
   This is the evaluator notification — copy that URL into a browser. (You can also find the same URL by clicking the "Wait for Human Decision" node in the execution panel.)
6. You'll see the composited image and the generated copy. Click **Approve**, **Edit & Approve**, or **Reject**.
7. Watch n8n resume: the IF node runs, and either the mock publish nodes fire (check your FastAPI terminal for the logs) or the rejection node runs.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "replace PASTE_YOUR_GROQ_API_KEY_HERE" error in Code node | Open the Generate Post Content node, find the `apiKey` line, and paste your real key from https://console.groq.com (starts with `gsk_`) |
| HTTP Request to ngrok fails with connection error | Your ngrok tunnel isn't running, or you've restarted it and need to update the URL in all nodes |
| Review dashboard shows "Review not found" | The FastAPI server was restarted (in-memory store was cleared). Re-run the workflow from the start |
| Wait node never resumes / stuck in human node | (1) Wait node `HTTP Method` must be `POST`. (2) Workflow must be **Active** and submitted via the **Production URL** — Test mode returns a 404 on the resume callback. Check the `[CALLBACK]` lines in the FastAPI logs for the status n8n returned |
| Approve always routes to Reject | The IF node must check `{{ $json.body.decision }}` (note the `.body.`), not `{{ $json.decision }}` |
| Publish node sends literal `{{ ... }}` text | That field is in Fixed mode — toggle it to **Expression** mode (you should see a live preview under the field) |
| Form Trigger not showing the form | Make sure the workflow is **Active** (toggle in top-right of canvas) |
