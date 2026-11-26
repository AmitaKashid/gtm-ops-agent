# GTM Ops Agent

An API and dashboard for experimenting with business operations workflows. The
application combines LangGraph workflows, rule-based CRM checks, optional n8n
orchestration, and PostgreSQL-backed onboarding state.

## Workflows

| Workflow | API | Current behavior |
| --- | --- | --- |
| Lead intelligence | `POST /leads/analyze` | Uses an LLM to describe, score, and draft outreach for a supplied lead. |
| Email triage | `POST /emails/triage` | Classifies an email, drafts a reply, and selects routing. |
| Meeting intelligence | `POST /meetings/analyze` | Extracts action items and prepares summary and task payloads. |
| CRM hygiene | `POST /crm/analyze` | Applies rules to deals supplied in the request. |
| Competitor intelligence | `POST /competitors/analyze` | Scrapes supplied URLs and compares with caller-supplied previous content. |
| HR onboarding | `POST /hr/onboard`, `POST /hr/provision` | Produces a plan, stores state and contains partial provisioning logic. |

## Run the API on Windows

From Command Prompt, create the environment and install dependencies:

```cmd
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
copy .env.example .env
.venv\Scripts\python.exe -m uvicorn api.main:app --env-file .env --reload --host 127.0.0.1 --port 8010
```

API documentation: <http://127.0.0.1:8010/docs>.
Configure a model provider in `.env` before LLM-based workflows. Leave Slack and
tracing disabled while testing with synthetic examples. The CRM route works
without an LLM. The health endpoint checks API responsiveness, not dependencies.

To serve the dashboard in a separate Command Prompt:

```cmd
.venv\Scripts\python.exe -m http.server 8080 --bind 127.0.0.1 --directory dashboard
```

Open <http://127.0.0.1:8080> and confirm its API URL. The default points to
local port 8010. If the API runs using Docker Compose, use port 8000 instead.

Run deterministic local tests:

```cmd
.venv\Scripts\python.exe -m pytest tests -v
```

The feature tests stub model calls, competitor HTTP requests, and database
writes. They do not prove a live provider or integration works.

For optional Docker services, create `.env`, then run `docker compose up -d --build`.
PostgreSQL initializes `supabase/schema.sql` only on a new data
volume. n8n workflow files need to be imported manually and configured with
your credentials; they are inactive on import. The `latest` n8n image should be
pinned to a tested release before relying on it.

## Current limitations

- Lead research uses the model and provided input; it does not retrieve web sources.
- CRM deals are provided in the request rather than fetched from a CRM.
- Competitor history is not persisted, and untrusted URLs are not restricted.
- The HR provisioning endpoint does not verify manager approval. Some HR
  provisioning steps are placeholders, and email-send status is unreliable.
- The dashboard renders data as HTML and requires output sanitization before
  use with untrusted data. Keep it on localhost with synthetic examples.
- Evaluation fixtures and reports are small; no production performance or
  accuracy claims are established by the included tests.

The code contains adaptations of an earlier MIT-licensed implementation. The
original copyright and permission notice is preserved in [LICENSE](LICENSE).
