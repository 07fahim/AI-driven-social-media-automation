# Demo Video Script — AI Agent Workflow Automation (n8n + HITL)

**Target length: 4–6 minutes**

Read the **SAY** lines aloud; the **SHOW** lines tell you what to have on screen.

---

## 0. Setup before you hit record (don't film this)

- FastAPI running: `uvicorn main:app --reload --port 8888`
- ngrok running: `ngrok http 8888`
- n8n workflow **Active**, Groq key + ngrok URL filled in
- Browser tabs ready: (1) n8n canvas, (2) Form Production URL, (3) a blank tab for the review page
- Terminal visible (you'll switch to it to show publish logs)

---

## 1. Intro — 20 sec

**SHOW:** Your face cam or the n8n canvas with all 9 nodes visible.

**SAY:**
> "Hi, this is my submission for Assessment 1 — an AI agent workflow that automates social media post creation with a human-in-the-loop approval step. It's built in n8n, with a Python FastAPI backend for image compositing and mock publishing. Let me walk you through the architecture, then run three live scenarios: approve, edit-and-approve, and reject."

---

## 2. Architecture overview — 45 sec

**SHOW:** Slowly pan/point across the n8n canvas, left to right.

**SAY:**
> "The flow starts with a form that takes a post topic and a scheduled time. That goes to a Code node, which calls the Groq Llama 3.3 70B model to generate the copy. It strictly enforces a 90 to 150 word count — if the model goes out of range, it sends a corrective prompt and retries up to five times, and hard-stops if it still can't comply, so a non-compliant post can never get through.
>
> Next, the topic is sent to my FastAPI backend, which uses Pillow to composite a branded 1080-by-1080 card — logo top-right, title in the lower third, at fixed pixel coordinates every time.
>
> Then the workflow **pauses** at this Wait node and sends the copy and image to a human review dashboard. Based on the reviewer's decision, it either publishes to mock Facebook and Instagram endpoints, or stops."

---

## 3. Scenario 1 — APPROVE — 90 sec

**SHOW:** The form Production URL tab.

**SAY:**
> "Let's run the first scenario. I'll submit a topic: 'How AI is revolutionizing healthcare in 2026', scheduled for June 21st."

**SHOW:** Type it in, click Submit.

**SAY:**
> "The workflow is now running. Switching to n8n, you can see it generated the copy, built the image, and is now paused at the Wait node — waiting for human input."

**SHOW:** Switch to n8n executions — point at the spinning Wait node.

**SAY:**
> "My FastAPI server prints an 'Action Required' banner with a review link. Let me open it."

**SHOW:** Switch to terminal, show the `ACTION REQUIRED` banner, copy the URL into the browser.

**SAY:**
> "Here's the review dashboard. It shows the composited brand card — notice the logo placement and the title — and the generated copy, which is within the 90 to 150 word limit. For this first run I'll click **Approve** to publish it as-is."

**SHOW:** Click **Approve**. Switch back to n8n — show nodes turning green through the True branch.

**SAY:**
> "n8n resumed, the 'Was Approved' condition routed to the publish path, and both Facebook and Instagram nodes ran. Let me confirm in the backend logs."

**SHOW:** Switch to terminal — point at `[MOCK FACEBOOK]` and `[MOCK INSTAGRAM]` log blocks.

**SAY:**
> "Both mock endpoints received the post — the image URL, the approved copy, and the scheduled time. That's the approve path complete."

---

## 4. Scenario 2 — EDIT & APPROVE — 75 sec

**SHOW:** Form tab again.

**SAY:**
> "Second scenario — editing before approval. I'll submit a different topic: '5 productivity habits of successful remote teams.'"

**SHOW:** Submit, open the new review URL from the terminal banner.

**SAY:**
> "This time, before approving, I'll edit the copy directly in this text box — say I want to tweak the opening line."

**SHOW:** Edit a sentence in the textarea. Then click **Edit & Approve**.

**SAY:**
> "I clicked **Edit and Approve**. The dashboard sends my edited version back to n8n as the final copy."

**SHOW:** Terminal — point at the publish logs.

**SAY:**
> "And you can see in the publish logs — the description now contains my **edited** text, not the original. This proves the human's edits flow all the way through to publishing."

---

## 5. Scenario 3 — REJECT — 45 sec

**SHOW:** Form tab.

**SAY:**
> "Final scenario — rejection. I'll submit one more topic and this time reject it."

**SHOW:** Submit, open review URL, click **Reject**.

**SAY:**
> "I clicked **Reject**. Back in n8n, the condition routed to the **false** branch — the 'Rejected, Log and Stop' node ran, and importantly, **no** publish nodes fired."

**SHOW:** n8n execution — point at the rejected branch being green and the publish nodes untouched. Then terminal — show there are NO new publish logs.

**SAY:**
> "The terminal confirms it — no Facebook or Instagram calls were made. The post was correctly stopped before publishing."

---

## 6. Closing — 20 sec

**SHOW:** Back to the full n8n canvas.

**SAY:**
> "So that's all three paths: approve, edit-and-approve, and reject — with strict word-count enforcement, deterministic brand image compositing, and a true webhook-based human-in-the-loop pause. The code, workflow, and full setup docs are in the linked GitHub repo. Thanks for watching."

---

## Quick reference — topics for each run

| Run | Topic | Action |
|-----|-------|--------|
| 1 | How AI is revolutionizing healthcare in 2026 | Approve |
| 2 | 5 productivity habits of successful remote teams | Edit & Approve |
| 3 | Why sustainable fashion is the future of retail | Reject |

---

## Recording tips

- Pre-generate run 1 once before recording so you know the copy lands in range (avoids dead air during retries).
- Keep the terminal font large so logs are readable.
- If a run hits a retry, just wait — it's fast with Groq (sub-second per call).
