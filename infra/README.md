# Deploying Regulatory Assistant (Lotor Lab)

Target site: **`https://regulatory_assistant.lotorlab.com`**.

This repo borrows the **deployment ideas** from the **TIME_build** repository (same layout under your `Documents updated` tree): GitHub Actions → container images, TLS at the edge, reverse proxy for API + WebSocket + Next.js, and an optional **AWS OIDC bootstrap** CloudFormation stack. It does **not** copy the full EKS / CloudFront / S3 stack by default—that path is large and account-specific; see [Full AWS (TIME_build–style)](#optional-full-aws-time_buildstyle) below.

---

## What gets exposed

| Path | Backend |
|------|---------|
| `/api/*` | FastAPI (`main_complete.py`) |
| `/ws/*` | Multi-agent WebSocket |
| `/health` | Health check |
| `/`, pages | Next.js (port 3000) |

Production frontend must be built with **`NEXT_PUBLIC_API_URL`** and **`NEXT_PUBLIC_AGENT_WS_URL`** pointing at the **public** origin (same host behind Caddy, or a dedicated API subdomain). Defaults are set in `frontend/Dockerfile` and overridable in CI.

---

## Path A — Recommended: GHCR + VM + Caddy (single host)

### A1. DNS (at `lotorlab.com`)

Create a record (name depends on your DNS UI; values illustrative):

| Type | Host / name | Value |
|------|----------------|--------|
| `A` or `CNAME` | `regulatory_assistant` | Your server’s public IP or hostname |

Use the exact hostname your users will open: `regulatory_assistant.lotorlab.com`.

### A2. GitHub Container Registry

Workflow: **`.github/workflows/deployment_GHCR.yml`**

1. In GitHub: **Actions → Deploy to GHCR → Run workflow**.
2. Optionally set inputs to override the baked-in public URLs (defaults match `regulatory_assistant.lotorlab.com`).
3. On the deploy host, log in to GHCR and pull:

```bash
echo <GITHUB_PAT> | docker login ghcr.io -u <github-username> --password-stdin
docker pull ghcr.io/<org>/<repo>/backend:latest
docker pull ghcr.io/<org>/<repo>/frontend:latest
```

(Lowercase `ghcr.io/<owner>/<repo>` as enforced in the workflow.)

### A3. Runtime secrets on the server

Create a file **only on the server** (not in git), e.g. `/opt/regulatory-assistant/.env`, with at least:

- `LLM_PROVIDER`, API keys, `AACT_*`, etc., mirroring `backend/.env.example`.

The backend container must receive these (Compose `env_file` or `--env-file`).

### A4. Docker Compose on the server

From the repo (or a deploy bundle), run the same topology as root `docker-compose.yml`:

- Backend **listens on `0.0.0.0:8001`** (image CMD uses `uvicorn` with proxy headers).
- Frontend on **3000**, with **runtime** env only if you need overrides; API URLs are already baked at **image build** time.

Bind ports to **localhost** and put **Caddy** in front (see `infra/proxy/Caddyfile.example`).

```bash
docker compose --env-file /opt/regulatory-assistant/.env up -d
```

### A5. Caddy (TLS)

1. Install [Caddy](https://caddyserver.com/) on the host.
2. Copy `infra/proxy/Caddyfile.example` to e.g. `/etc/caddy/Caddyfile` and fix upstreams if your compose binds differently.
3. Ensure DNS points to this host, then `caddy reload` (Caddy will obtain Let’s Encrypt certs automatically).

Smoke checks:

```bash
curl -fsS https://regulatory_assistant.lotorlab.com/health
curl -fsSI https://regulatory_assistant.lotorlab.com/
```

---

## Path B — Optional: GitHub OIDC → AWS (bootstrap only)

If you later add an ECR/EKS/CloudFront workflow similar to `TIME_build`, create a one-time deploy role:

```bash
export AWS_PROFILE=<your-profile>
export APP_REGION=us-east-2   # or your chosen region

aws cloudformation deploy \
  --region "$APP_REGION" \
  --stack-name lotor-regulatory-assistant-bootstrap-github-oidc \
  --template-file infra/cloudformation/bootstrap-github-oidc.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=lotor-regulatory-assistant \
    GitHubOrg=<your-github-org-or-user> \
    GitHubRepo=<this-repo-name> \
    GitHubBranch=main
```

Copy output **`GitHubDeployRoleArn`** into GitHub → **Settings → Secrets and variables → Actions → Variables**:

- `AWS_ROLE_TO_ASSUME` = that ARN  

Then wire a new workflow with `aws-actions/configure-aws-credentials` + OIDC (`id-token: write`), following `.github/workflows/deploy-dev.yml` in `TIME_build`.

---

## Optional: full AWS (TIME_build–style)

`TIME_build` adds:

- ACM certificates (edge `us-east-1` + regional ALB cert)
- CloudFormation platform stack (EKS, ECR, S3, …)
- Helm AWS Load Balancer Controller
- `infra/k8s/dev/backend.yaml` patched with image URI + secrets
- CloudFront + WAF in front of S3 static site + API origin

To reuse that pattern for Lotor:

1. Copy `TIME_build/infra/` (CloudFormation + Helm + k8s) into this repo under `infra/aws/` (or keep a submodule).
2. Global replace project identifiers (`psidium-time` → `lotor-regulatory-assistant`, domains → `regulatory_assistant.lotorlab.com` / API hostnames you choose).
3. Change the **backend image build** to this repo’s Dockerfile (`backend/Dockerfile`, port **8001**, `uvicorn main_complete:app`).
4. Change **frontend build** from static `out/` export to either:
   - **Container on EKS** for Next.js, or  
   - **Amplify / Vercel** for Next and keep only API on EKS, or  
   - **Next `output: 'export'`** only if you drop non-static features (WebSockets need a live Next server or same-origin proxy).

The regulatory app relies on **WebSockets** and **many dynamic routes**; a plain S3-only static export is usually **not** enough without architectural changes.

---

## Checklist for `regulatory_assistant.lotorlab.com`

- [ ] DNS `A`/`CNAME` → server or load balancer  
- [ ] GHCR images built with correct `NEXT_PUBLIC_*` (workflow inputs or Dockerfile defaults)  
- [ ] Server `.env` with production secrets; never commit `.env`  
- [ ] Caddy (or nginx) routes `/api`, `/ws`, `/health` → backend; `/` → Next  
- [ ] Backend CMD uses `--proxy-headers` (already in `backend/Dockerfile`) so `X-Forwarded-*` is trusted  

For issues, compare with the runbook in `TIME_build/infra/README.md` (Psidium-specific names and domains).
