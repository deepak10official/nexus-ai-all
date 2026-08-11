# Nexus — Trend Radar (MOD03) + Persona Panel (MOD02)

Two agentic modules, one backend and one frontend.

**MOD03 — National Trend Radar.** Scrapes live X/Twitter trends for India, scores
each against Bharat Connect (BBPS) relevance, and drafts a post (plus an
optional image) for human approval.

**MOD02 — Persona Panel.** Five synthetic Indian consumer personas each vote
APPROVE/REJECT on that draft. Three of five approvals passes. On failure a
reviser rewrites it from the panel's feedback and the panel votes again.

**The handoff:** a draft approved in the Radar is loaded straight into the Panel
for validation. That is the whole point of the merge.

**Nothing is ever published.** Every approval is simulated end to end.

---

## Layout

```
nexus/
├── backend/
│   ├── api.py                  # ONE FastAPI app: mounts both routers + /api/handoff
│   ├── core/
│   │   └── logging.py          # unified logging (both modules' APIs kept)
│   ├── mod03/                  # Trend Radar
│   │   ├── router.py           # /api/radar/*
│   │   ├── trends_html.py      # trend scraper
│   │   ├── agents/agent.py     # LCEL: prompt | llm | PydanticOutputParser
│   │   ├── prompts/prompts.py
│   │   ├── services/           # scoring, trend_service, imagegen
│   │   └── utils/              # config (OpenRouter), schemas, categories, language
│   └── mod02/                  # Persona Panel
│       ├── router.py           # /api/panel/*
│       ├── graph.py            # LangGraph auto + manual graphs
│       ├── agents/             # base, panel, reviser, 5 personas
│       ├── prompts/            # personas/*.md + templates/*.md
│       ├── model/factory.py    # Groq / Ollama / Anthropic
│       └── utils/              # config, schemas, voting, cache
└── frontend/
    └── src/
        ├── App.jsx             # shell: module switcher + handoff state
        ├── views/              # TrendRadar.jsx, PersonaPanel.jsx
        ├── components/         # radar/, panel/, ui/
        ├── hooks/usePanel.js
        └── api/                # radarApi.js, panelApi.js
```

## Routes

| Route | Module |
|---|---|
| `GET /api/health` | both (single, aggregated) |
| `GET /api/radar/trends` · `/evaluate` · `/log` | MOD03 |
| `POST /api/radar/generate` · `/image` · `/decision` | MOD03 |
| `PATCH /api/radar/draft/{id}` | MOD03 |
| `GET /api/panel/personas` · `/settings` · `/state` | MOD02 |
| `POST /api/panel/run` · `/rework` | MOD02 |
| `POST /api/handoff` | the bridge |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in OPENROUTER_API_KEY and GROQ_API_KEY
```

Two terminals, both from the project root:

```bash
# 1 — backend
python -m uvicorn backend.api:app --reload --port 8000

# 2 — frontend
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 and check http://127.0.0.1:8000/api/health — both
`radar.llm_configured` and `panel.llm_configured` should be `true`.

## The flow

```
  MOD03: scan -> score -> pick a trend -> generate draft (+ image)
    │
    ├─ human approves the draft
    │
    ▼
  handoff  (App.jsx switches view; the wording is loaded into the panel)
    │
    ▼
  MOD02: five personas vote -> 3/5 passes
    ├─ passed  -> human makes the final call
    └─ failed  -> Rework & run again -> revise -> re-vote
```

## Notes from the merge

- **Providers are unchanged.** MOD03 still uses OpenRouter, MOD02 still uses
  Groq/Ollama/Anthropic. Each module keeps its own `utils/config.py`; only
  logging is shared.
- **Structured output differs by design.** MOD03 uses `PydanticOutputParser`
  because free-tier models have unreliable tool-calling; MOD02 uses
  `with_structured_output` with retry + salvage. MOD02 can be switched to raw
  JSON with `STRUCTURED_OUTPUT_METHOD=json_schema` if `tool_use_failed` recurs.
- **One log file per run**, under `logs/`, shared by both modules.
- **Generated images** are written to `backend/mod03/generated/` and served at
  `/generated/*`.
- **Drafts are in-memory.** Restarting the backend clears them.
