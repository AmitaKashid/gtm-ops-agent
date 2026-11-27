# GTM Ops Agent

A demonstration workspace for lead analysis, email triage, meeting summaries, and CRM hygiene. A FastAPI service runs the workflows and serves a dashboard; a separate GitHub Pages copy can connect to the same service.

- [Open the dashboard](https://gtm-ops-agent.onrender.com/)
- [Open the GitHub Pages dashboard](https://amitakashid.github.io/gtm-ops-agent/)
- [Deployment guide](DEPLOYMENT.md)

## Try the demo

Use fictional information only. Review generated output before relying on it. The free service may take a minute to wake after inactivity, and usage may be limited.

| Workflow | Demo behavior |
| --- | --- |
| Lead analysis | Accepts manually entered details, generates a score and draft. Company research is model-generated; it is not verified web research. |
| Email triage | Classifies manually entered email content and may draft a reply. It does not send the reply. |
| Meeting intelligence | Analyzes a pasted transcript and prepares a summary and action items. It does not create tasks in external systems by itself. |
| CRM hygiene | Scans sample deals supplied by the dashboard using deterministic rules. It does not connect the demo to a CRM. |
| Competitor intelligence | Disabled in the public demo. |
| HR onboarding | Disabled in the public demo. Provisioning is disabled until authenticated approval is implemented. |

The demo is not a production system: there is no user authentication or tenant isolation, the request limit is in memory, and external provider access can fail or run out of quota. Do not submit personal, confidential, or customer information.

## Run locally on Windows

Requires Python 3.13 and a configured model provider. In Command Prompt:

```cmd
cd C:\Users\User\gtm-ops-agent
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
copy .env.example .env
```

Edit `.env` privately with your provider configuration. Keep `.env` and API keys out of Git and public messages. Set `GROQ_MODEL` to a model your account can access. Then:

```cmd
.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8010
```

Open `http://127.0.0.1:8010/` for the dashboard, `/docs` for the API reference, and `/health` for a basic process health check. A healthy response does not verify every provider or workflow.

## Test

```cmd
.venv\Scripts\python.exe -m pytest tests -q
```

Automated tests include mocked providers; a passing test suite alone does not establish that external services are configured or that generated content is accurate.

## n8n workflows

`n8n/workflows/` contains five inactive templates. A running n8n instance, import, credentials, reachable API URL, and published triggers are required. Templates contain example inputs and must be reviewed before activation; changing a JSON field in Git does not start n8n. The public demo blocks competitor and HR requests.

## Licensing

See [LICENSE](LICENSE) for license terms and notices.
