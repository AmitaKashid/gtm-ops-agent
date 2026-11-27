# Deploy a limited public demo on Render

This setup uses GitHub Pages for the dashboard and Render for the API.
It is a portfolio demo, not a production security boundary.

## Public demo limitations

Set `PUBLIC_DEMO=true` on Render. In this mode competitor scanning is
disabled because it accepts URLs, and all HR endpoints are disabled because
they handle employee information and may contact external services.
Provisioning is already disabled in the application. Do not configure Slack
credentials for the demo or submit real personal or confidential data.

The process limits POST requests to 60 per hour across all visitors and rejects
requests larger than 32 KiB. This is an in-memory limit, resets on restart,
and is not shared between instances. It does not guarantee protection against
abuse or provider quota exhaustion. Do not enable paid provider billing without
separate controls. Render's free service may sleep, restart, or suspend.
Database persistence, workflow integrations, and full production security are
not included.

## Configure Render

1. In Render create a **Web Service** connected to this repository and branch
   `main`. Select **Docker** and the **Free** instance.
2. Add environment variables in Render:
   - `PUBLIC_DEMO=true`
   - `CORS_ALLOWED_ORIGINS=https://amitakashid.github.io`
   - `DEFAULT_LLM_PROVIDER=groq`
   - `GROQ_MODEL=openai/gpt-oss-20b` (or another model your account can use)
   - `GROQ_API_KEY`: enter your own key privately in Render.
3. Deploy, then open the service's HTTPS address with `/health` appended.
   Startup can take time on the free tier. Check Render logs for errors.
4. Set `window.GTM_API_URL` in `docs/api-config.js` to your actual Render
   HTTPS address, without a trailing slash. Optionally match
   `dashboard/api-config.js` for local dashboard use. Commit and push both.
   Wait for GitHub Pages to rebuild.
5. Open your GitHub Pages site on a second device and check the API health
   indicator, then test lead, email, meeting, and CRM using sample data.
   Competitor and HR endpoints intentionally return 503 in this mode.

Never put your Groq API key into the dashboard, config JavaScript, git history,
or a public issue. CORS is a browser restriction and is not authentication.
