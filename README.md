# Nexus — Reactive Social for Bharat Connect

An agentic prototype in two modules, merged into **one backend and one frontend**.

| Module | Name | What it does |
|---|---|---|
| **MOD03** | National Trend Radar | Finds what India is talking about, scores each trend for Bharat Connect (BBPS) relevance, and drafts a post + image. |
| **MOD02** | Persona Panel | Five synthetic Indian consumers vote APPROVE/REJECT on that draft. 3 of 5 passes. |

The two are joined by a **handoff**: a draft approved in the Radar is loaded
straight into the Panel for validation. That is the point of the merge — MOD03
writes the post, MOD02 decides whether it is safe to publish.

> **Nothing is ever published.** Every approve action is simulated end to end.
> There is no connection to any social platform's publishing API.

---

## Table of contents

1. [What this does, end to end](#1-what-this-does-end-to-end)
2. [Architecture](#2-architecture)
3. [Project layout](#3-project-layout)
4. [Prerequisites](#4-prerequisites)
5. [Setup — step by step](#5-setup--step-by-step)
6. [Running it](#6-running-it)
7. [Using the app](#7-using-the-app)
8. [API reference](#8-api-reference)
9. [Configuration](#9-configuration)
10. [How MOD03 works](#10-how-mod03-works)
11. [How MOD02 works](#11-how-mod02-works)
12. [Logging](#12-logging)
13. [Troubleshooting](#13-troubleshooting)
14. [Known limitations](#14-known-limitations)

---

## 1. What this does, end to end

```
  ┌─ MOD03 · TREND RADAR ─────────────────────────────────────────┐
  │  1. Scan          scrape live X/Twitter trends for India      │
  │  2. Block         drop politics / religion / protest /        │
  │                   security / competitor topics FIRST          │
  │  3. Score         0-100 BBPS relevance, sorted into bands     │
  │  4. Pick          a human chooses one trend worth posting     │
  │  5. Draft         LLM writes the post copy                    │
  │  6. Image         optional matching image + brand wordmark    │
  │  7. Approve       human approves the copy and image           │
  └───────────────────────────┬───────────────────────────────────┘
                              │  HANDOFF
                              │  the approved wording is loaded
                              │  into the panel automatically
                              ▼
  ┌─ MOD02 · PERSONA PANEL ───────────────────────────────────────┐
  │  8. Vote          5 personas each APPROVE or REJECT           │
  │  9. Tally         3 of 5 approvals passes                     │
  │ 10a. Passed       human makes the final call                  │
  │ 10b. Failed       Rework & run again → reviser rewrites from  │
  │                   the panel's feedback → panel votes again    │
  └───────────────────────────────────────────────────────────────┘
```

**Why two modules?** MOD03 optimises for *relevance* — is this trend worth
riding? MOD02 optimises for *safety and reception* — will an actual Indian
consumer find this trustworthy, clear, and useful? A post can be highly relevant
and still be rejected by the panel, which is exactly the check the pipeline
needs before anything reaches a real audience.

---

## 2. Architecture

**One FastAPI app, two routers.** Both modules previously ran their own server on
port 8000. They are now mounted under a single app with distinct prefixes:

```
                    ┌──────────────────────────────┐
  Browser :5173 ───▶│  Vite dev server             │
                    │  proxies /api and /generated │
                    └──────────────┬───────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │  FastAPI :8000               │
                    │    /api/health   (both)      │
                    │    /api/handoff  (bridge)    │
                    │    /api/radar/*  → MOD03     │
                    │    /api/panel/*  → MOD02     │
                    └───────┬──────────────┬───────┘
                            ▼              ▼
                    OpenRouter LLM     Groq LLM
                    + HuggingFace      (or Ollama /
                    (images)            Anthropic)
```

**Providers stay separate by design.** MOD03 uses OpenRouter (free NVIDIA
models); MOD02 uses Groq by default. Each module keeps its own `utils/config.py`.
Only **logging** is shared, in `backend/core/logging.py`.

**Python packages are namespaced.** Both modules originally had `agents/`,
`utils/`, and `prompts/` directories, which would collide. They now live under
`backend/mod02/` and `backend/mod03/`.

---

## 3. Project layout

```
nexus-ai-all/
├── backend/
│   ├── api.py                    # THE app: mounts both routers, /api/health, /api/handoff
│   ├── core/
│   │   └── logging.py            # unified logging, one file per run
│   │
│   ├── mod03/                    # ══ TREND RADAR ══
│   │   ├── router.py             # /api/radar/*
│   │   ├── trends_html.py        # scrapes trends24.in (no auth needed)
│   │   ├── agents/agent.py       # LCEL: prompt | ChatOpenAI | PydanticOutputParser
│   │   ├── prompts/prompts.py    # 5 editable prompt blocks
│   │   ├── services/
│   │   │   ├── scoring.py        # blocklist + 0-100 relevance + bands
│   │   │   ├── trend_service.py  # scrape + cache tier, honest freshness labels
│   │   │   └── imagegen.py       # FLUX via HuggingFace + brand wordmark
│   │   └── utils/
│   │       ├── config.py         # OpenRouter / HF settings
│   │       ├── schemas.py        # SocialPost, Draft, TrendFeed, ...
│   │       ├── categories.py     # topic categorisation
│   │       └── language.py       # script/language detection
│   │
│   └── mod02/                    # ══ PERSONA PANEL ══
│       ├── router.py             # /api/panel/*
│       ├── graph.py              # LangGraph: auto graph + manual (interrupt) graph
│       ├── pipeline.py           # CLI wrapper over the auto graph
│       ├── cli.py                # terminal runner
│       ├── agents/
│       │   ├── base.py           # PersonaAgent → structured PersonaVote
│       │   ├── panel.py          # VotingPanel: runs all 5, tallies
│       │   ├── reviser.py        # rewrites failed posts from feedback
│       │   └── {suresh,meena,arjun,kavya,ramesh}.py
│       ├── prompts/
│       │   ├── personas/*.md     # one file per persona (frontmatter + profile)
│       │   └── templates/*.md    # shared voting + reviser prompts
│       ├── model/factory.py      # Groq / Ollama / Anthropic factory
│       └── utils/
│           ├── config.py         # provider, thresholds, retry settings
│           ├── schemas.py        # PersonaVote, PanelResult, Persona
│           ├── voting.py         # tally_votes(), feedback summarisation
│           └── cache.py          # optional Redis vote cache
│
├── frontend/
│   ├── vite.config.js            # proxies /api and /generated → :8000
│   ├── tailwind.config.js        # union of both modules' design tokens
│   └── src/
│       ├── App.jsx               # shell: module switcher + handoff state
│       ├── views/
│       │   ├── TrendRadar.jsx    # MOD03 screen
│       │   └── PersonaPanel.jsx  # MOD02 screen
│       ├── components/
│       │   ├── radar/            # TrendFeed, DraftPanel, ScoreDial, ImagePanel, ...
│       │   ├── panel/            # PostConsole, VoteCard, RoundResults, Tally, ...
│       │   └── ui/               # GlassCard, Badge, ScoreRing (shared)
│       ├── hooks/usePanel.js     # panel session state
│       └── api/
│           ├── radarApi.js       # → /api/radar/*
│           └── panelApi.js       # → /api/panel/*
│
├── requirements.txt              # merged Python dependencies
├── .env.example                  # every setting, no secrets
└── README.md
```

---

## 4. Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | 3.12 tested |
| Node.js | 18+ | needed for the frontend only |
| OpenRouter API key | free | https://openrouter.ai/keys — MOD03 drafting |
| Groq API key | free | https://console.groq.com/keys — MOD02 voting |
| HuggingFace token | free, optional | https://huggingface.co/settings/tokens — images only |

Without the HF token everything works except image generation.

---

## 5. Setup — step by step

### 5.1 Get the code

```bash
git clone https://github.com/deepak10official/nexus-ai-all.git
cd nexus-ai-all
```

Confirm `backend/` and `frontend/` sit at the **root** of the folder. If you see
a nested `nexus/` directory, move its contents up one level — otherwise
`uvicorn backend.api:app` will not resolve.

### 5.2 Python dependencies

```bash
pip install -r requirements.txt
```

<details>
<summary>Optional: use a virtual environment</summary>

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux
pip install -r requirements.txt
```
</details>

### 5.3 Environment file

```bash
copy .env.example .env            # Windows
# cp .env.example .env            # macOS / Linux
```

Open `.env` and fill in **two keys minimum**:

```ini
OPENROUTER_API_KEY=sk-or-v1-...   # MOD03 drafting
GROQ_API_KEY=gsk_...              # MOD02 voting
HF_TOKEN=hf_...                   # optional, images only
```

`.env` is gitignored. **Never commit it.**

### 5.4 Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

Takes a minute or two the first time.

---

## 6. Running it

You need **two terminals**, both open at the project root.

### Terminal 1 — Backend

```bash
python -m uvicorn backend.api:app --reload --port 8000
```

> **Run this from the project root**, not from inside `backend/`. The dotted
> path `backend.api` is resolved relative to your current directory.
>
> Use `python -m uvicorn` rather than bare `uvicorn` — on locked-down Windows
> machines the `uvicorn.exe` launcher is often blocked by Application Control,
> while `python.exe` is not.

**Verify it started:** open http://127.0.0.1:8000/api/health

```json
{
  "ok": true,
  "radar": { "llm_configured": true, "model": "nvidia/nemotron-nano-9b-v2:free" },
  "panel": { "llm_configured": true, "model": "qwen/qwen3.6-27b" },
  "log_file": "/path/to/logs/2026-08-11_09-30-45.log"
}
```

Both `llm_configured` values should be `true`. If either is `false`, that
module's API key is missing from `.env`.

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**.

Vite proxies `/api` and `/generated` to port 8000, so both servers must stay
running. Interactive API docs are at http://127.0.0.1:8000/docs.

---

## 7. Using the app

The top bar switches between the two modules. Both keep their state, so you can
move back and forth freely.

### Trend Radar (MOD03)

1. **Scan now** — fetches live trends. The header labels the source honestly as
   `live` or `cache`.
2. **Read the feed** — every trend shows its score, band, and the reason. Blocked
   topics appear with their block reason rather than silently vanishing.
3. **Pick a trend** — only `auto_draft` (80-100) and `review` (60-79) bands are
   selectable. Lower bands are shown but cannot be drafted.
4. **Generate** — writes the post copy, with an angle, tone, and risk notes.
5. **Generate image** *(optional)* — creates a matching image with the
   "Bharat Connect" wordmark composited bottom-right.
6. **Approve** — the copy and the image are judged separately, so a good post is
   not thrown away because its image missed.

Approving the full draft **hands it off to the Persona Panel** and switches the
view automatically.

### Persona Panel (MOD02)

The handed-off post is already loaded in the text box.

1. **Run the panel** — all five personas vote. Each card shows the decision,
   confidence, reasoning, and any changes wanted.
2. **Read the tally** — 3 of 5 approvals passes.
3. If it fails, **Rework & run again** — the reviser rewrites the post using
   every objection, then the panel votes again. Round history stacks so you can
   see how the wording evolved.
4. **New draft** — clears everything and starts a fresh session.

You can also paste any post directly into the box and run the panel on it,
without going through the Radar.

---

## 8. API reference

### Shared

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Config + model readiness for both modules |
| `POST` | `/api/handoff` | Fetch a Radar draft's wording for panel validation |

### MOD03 — Trend Radar

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/radar/trends?refresh=false` | Scored trend feed |
| `GET` | `/api/radar/evaluate?name=<hashtag>` | Score a single trend |
| `POST` | `/api/radar/generate` | Draft a post for one hashtag |
| `POST` | `/api/radar/image` | Generate a branded image for a draft |
| `PATCH` | `/api/radar/draft/{draft_id}` | Hand-edit a draft |
| `POST` | `/api/radar/decision` | Record approve/reject (simulated) |
| `GET` | `/api/radar/log` | Decision audit trail |

### MOD02 — Persona Panel

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/panel/personas` | The five persona profiles |
| `GET` | `/api/panel/settings` | Provider, model, threshold, panel size |
| `GET` | `/api/panel/state?thread_id=` | Current session state (rounds, flags) |
| `POST` | `/api/panel/run` | Run the panel (fresh vote or re-vote) |
| `POST` | `/api/panel/rework` | Revise the post from panel feedback |
| `GET` | `/api/panel/debug/state` | Raw LangGraph state (troubleshooting) |
| `GET` | `/api/panel/debug/logfile` | Path of the active log file |

---

## 9. Configuration

Everything is environment variables in `.env`. See `.env.example` for the full list.

### MOD03 — Trend Radar

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | — | **Required.** Drafting. |
| `OPENROUTER_MODEL` | `nvidia/nemotron-nano-9b-v2:free` | Any OpenRouter model id. |
| `TREND_REGION` | `india` | Region for the trend scrape. |
| `TREND_CACHE_MINUTES` | `30` | How long a scrape stays fresh. |
| `HF_TOKEN` | — | Optional. Image generation. |
| `IMAGE_MODEL` | `black-forest-labs/FLUX.1-dev` | Use `FLUX.1-schnell` for a commercial-safe licence. |

### MOD02 — Persona Panel

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq` \| `ollama` \| `anthropic` |
| `GROQ_API_KEY` | — | **Required** when provider is groq. |
| `GROQ_MODEL` | `qwen/qwen3.6-27b` | Any Groq model id. |
| `GROQ_REASONING` | `false` | Leave off — thinking eats the token budget and votes come back empty. |
| `APPROVAL_THRESHOLD` | `3` | Approvals needed to pass. |
| `PANEL_SIZE` | `5` | Number of personas. |
| `MAX_REVISION_ROUNDS` | `2` | Revision budget (auto graph only). |
| `STRUCTURED_OUTPUT_METHOD` | `function_calling` | Set to `json_schema` if you hit `tool_use_failed`. |
| `PERSONA_MAX_ATTEMPTS` | `2` | Retries per persona on a malformed response. |
| `PANEL_PARALLEL` | `false` | `true` fans the five personas onto a thread pool — much faster, harder on rate limits. |

### Shared

| Variable | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `INFO` | `DEBUG` shows the full post text per vote. |
| `LOG_DIR` | `logs` | Resolved from the project root. |
| `LOG_TO_FILE` / `LOG_TO_CONSOLE` | `true` | Output toggles. |
| `FRONTEND_ORIGIN` | `http://localhost:5173,...` | CORS allowlist. |

### Choosing an OpenRouter model

Free NVIDIA models rotate in and out of availability. If generation fails with a
model error, browse https://openrouter.ai/models?q=nvidia, pick any entry ending
in `:free`, and update `OPENROUTER_MODEL`. No code change needed.

---

## 10. How MOD03 works

### Scoring bands

Every trend gets a 0-100 relevance score. The band decides what happens next:

| Score | Band | Action | Selectable? |
|---|---|---|---|
| 80-100 | `auto_draft` | Draft immediately | Yes |
| 60-79 | `review` | Draft, flag for human review | Yes |
| 40-59 | `monitor` | Monitor only, no draft | No |
| 0-39 | `ignore` | Below threshold | No |
| n/a | `blocked` | Off-limits, never drafted | No |

**The blocklist runs first**, before scoring. Political, religious, protest,
security, and competitor topics are removed and never reach the model. Blocked
trends still appear in the feed with their reason, so the decision is auditable.

**Dilution penalties** reduce the score for high-volume but low-relevance topics
(IPL, Bollywood, Bigg Boss, box office) that would otherwise rank well on raw
engagement alone.

### The prompt

Five editable blocks in `backend/mod03/prompts/prompts.py`:

1. **ROLE** — a senior social strategist for a regulated financial brand, known
   for knowing when a trend is *not* worth touching.
2. **CONTEXT** — `BRAND_CONTEXT` (what BBPS is, its voice) plus `TREND_CONTEXT`
   injected per call (hashtag, score, rationale, neighbouring trends).
3. **GOAL** — ride the trend with a genuine connection; explicitly licensed to
   say the link is weak rather than invent one.
4. **CONSTRAINTS** — under 260 characters, must include the trending hashtag and
   `#BharatConnect`, 2-4 hashtags, max one emoji, no politics/religion/protests,
   no competitor names, no market-share claims, Indian English.
5. **OUTPUT FORMAT** — JSON only, schema injected from the Pydantic model.

**Why `PydanticOutputParser` and not `.with_structured_output()`:** free-tier
models frequently lack reliable tool-calling, and native structured output fails
hard on them. Format instructions plus parse-and-retry works across far more
models — which matters when the free tier rotates.

---

## 11. How MOD02 works

### The panel

| Persona | Profile | Archetype |
|---|---|---|
| 🧓 Suresh Yadav | 58, Varanasi, retired clerk | Cash Guardian |
| 👩‍👧 Meena Krishnan | 44, Coimbatore, homemaker | Household CFO |
| 🛵 Arjun Kapoor | 26, Gurgaon, gig worker | Gig Native |
| 💳 Kavya Nair | 31, Bengaluru, UX designer | Fintech Champion |
| 🏪 Ramesh Borkar | 50, Nagpur, kirana owner | Pragmatic Merchant |

They span the digital-adoption spectrum deliberately, so disagreement is a
feature. A post that only Kavya likes is probably too jargon-heavy for Bharat.

### Orchestration

LangGraph state graph (`backend/mod02/graph.py`) with two compiled variants
sharing the same `vote` and `revise` nodes:

- **Manual graph** (the UI) — human-in-the-loop. After a failed vote the graph
  **pauses at an `interrupt()`** and waits. An in-memory checkpointer plus a
  per-session `thread_id` keeps every round's votes, feedback, and the evolving
  post across iterations.
- **Auto graph** (CLI) — loops `vote → revise → vote` unattended until the post
  passes or `MAX_REVISION_ROUNDS` is spent.

Inside a round: `VotingPanel` runs the five `PersonaAgent`s, each constrained to
the `PersonaVote` schema (decision, confidence, reasoning, suggested_changes).
The panel tallies; ≥3 APPROVE passes. On rework, `ReviserAgent` receives the
post, all feedback, and the *original* post as an anchor.

### Editing personas

All wording lives in Markdown — no code changes needed:

- **A persona's voice:** `backend/mod02/prompts/personas/<name>.md`. YAML
  frontmatter (name, archetype, tagline, emoji) drives the UI; the body is the
  profile injected into the prompt.
- **Shared voting instructions:** `prompts/templates/persona_system.md` and
  `persona_human.md`.
- **Reviser behaviour:** `prompts/templates/reviser_system.md` and
  `reviser_human.md`.

Restart the backend after editing so the new prompts load.

### Command line

```bash
python -m backend.mod02.cli "Your post text here"
echo "Get an instant loan, just share your OTP!" | python -m backend.mod02.cli
```

---

## 12. Logging

One timestamped file per run, under `logs/`:

```
logs/2026-08-11_09-30-45.log
```

Both modules write to the **same file**, so a full session — scan, score, draft,
handoff, every voting round — reads as one continuous trace.

```
2026-08-11 09:30:47 | INFO  | panel.agent.suresh | 🧓 Suresh Yadav -> REJECT (conf 0.85) in 4.2s
2026-08-11 09:30:47 | INFO  | panel.agent.suresh |     reasoning: This asks for an OTP, classic fraud.
2026-08-11 09:30:47 | INFO  | panel.agent.suresh |     wants: Remove the OTP instruction entirely.
```

A new file starts on each new draft, so filenames reflect when the work actually
happened rather than when the server booted. `logs/` is gitignored.

---

## 13. Troubleshooting

**`ModuleNotFoundError: No module named 'backend'`**
You are not at the project root. `cd` to the folder containing `backend/` and
`frontend/`, then re-run uvicorn.

**`npm error ENOENT ... package.json`**
`npm run dev` must run from `frontend/`, not the root.

**`'uvicorn' is not recognized` / "Application Control policy has blocked this file"**
Use `python -m uvicorn backend.api:app --reload --port 8000`.

**`'node' is not recognized` after installing Node**
PATH only applies to terminals opened *after* installation. Close all terminals
and VS Code, then reopen. As a temporary patch:
`$env:Path += ";C:\Program Files\nodejs"`.

**Frontend loads but shows "Couldn't reach the API"**
The backend is not running, or not on port 8000. Check
http://127.0.0.1:8000/api/health.

**`llm_configured: false` in health**
That module's API key is missing from `.env`. Note `.env` must be at the project
root, not inside `backend/`.

**`tool_use_failed` from a persona**
The model answered in prose instead of calling the vote function. It retries
automatically and salvages the answer. To reduce it at source, set
`STRUCTURED_OUTPUT_METHOD=json_schema` in `.env` and restart.

**Trend feed shows navigation links instead of trends**
The scraper selector has drifted. See Known limitations.

**Panel takes minutes to respond**
Votes run sequentially by default. Set `PANEL_PARALLEL=true` for roughly a 5×
speedup, at the cost of harder rate-limit pressure.

**Images 404**
Check the backend is running — `/generated` is proxied to it. Images are written
to `backend/mod03/generated/`.

---

## 14. Known limitations

Worth naming before a stakeholder demo, because a client will find them.

**The scraper selector is unverified.** `trends_html.parse_latest()` targets
`.trend-card__list` on trends24 with a whole-page anchor fallback. If the feed
looks like navigation links rather than trends, inspect the page and correct the
selector. The cache tier means a mid-demo failure degrades to the last good
result instead of an empty screen — and the UI labels which tier it is serving
rather than pretending.

**The blocklist is a first pass, not a compliance control.** Hashtags concatenate
words, so word boundaries often do not exist. The matcher uses boundaries plus a
leading-prefix allowance, which correctly blocks `#RamMandir` while leaving
`Naveed Akram` alone — but it is a heuristic. Government-programme hashtags sit
on a genuinely ambiguous line between civic and political and need an explicit
allowlist decision from the brand team.

**Scoring is keyword-based by design.** Auditable and explainable, which matters
more than sophistication for a first release. It will miss semantic relevance
that has no keyword overlap.

**The persona panel is a proxy, not research.** Five synthetic profiles are a
useful smoke test for tone and trust, not a substitute for real consumer
testing. Treat a pass as "no obvious red flags", not as validation.

**Salvaged votes are heuristic.** When a model returns prose instead of
structured output, the verdict is inferred from keywords. These are logged as
`(heuristic)` and held at lower confidence, but they are a rescue, not a
guarantee.

**Drafts and panel state are in-memory.** Restarting the backend clears them.
Intentional for a prototype — every demo starts clean.

**The 6-hour scan cadence undercuts a 5-minute draft SLA.** A trend breaking at
09:05 is not detected until 12:00, by which point many X trends have peaked. If
speed matters, shorten the scan interval — it is one HTTP GET — rather than
optimising draft latency.

---

## Security note

`.env` holds live API keys and is gitignored. If a key is ever committed or
shared, **rotate it immediately** at the provider — git history is very hard to
scrub after the fact.
