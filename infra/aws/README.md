# Regulatory Assistant — AWS deployment (TIME_build pattern)

This mirrors **[TIME_build](https://github.com/rohanbhutkar/TIME_build)** (Psidium): **ACM → EKS Fargate → ALB Ingress → ECR images → optional CloudFront + WAF**.

Differences from TIME:

| Topic | TIME | Regulatory Assistant |
|--------|------|------------------------|
| Frontend | Static `out/` → **S3** | **Next.js container** on EKS (WebSockets + SSR) |
| CloudFront default origin | S3 | Same **ALB** as API |
| Backend port | 8000 | **8001** |
| Workloads | `time-dev` namespace | **`regulatory-dev`** |
| Runtime data init | S3 hydrate → `/mnt/time-data` | **None** (extend later if needed) |
| Secrets Manager placeholders | OpenAI + OncoKB | **Removed** — use GitHub → **Kubernetes Secret** `regulatory-backend-env` |

Default hostnames (override in workflow `env:` if needed):

- App: `regulatory-assistant.lotorlab.com`
- API facade (same CloudFront): `api.regulatory-assistant.lotorlab.com`
- ALB origin (DNS only): `origin-api.regulatory-assistant.lotorlab.com`

---

## 1. Prerequisites

- AWS account + admin (or equivalent) for CloudFormation, EKS, ECR, ACM, CloudFront, WAF.
- GitHub repo (e.g. [regulatory_assistant](https://github.com/rohanbhutkar/regulatory_assistant)).
- DNS control for **`lotorlab.com`** (ACM DNS validation + app CNAMEs).

Regions (same as TIME):

- **App:** `us-east-2` — VPC, EKS, ECR, regional ACM cert, ALB.
- **Edge:** `us-east-1` — CloudFront ACM cert + distribution + WAF.

---

## 2. GitHub OIDC bootstrap (once)

Deploy **`infra/cloudformation/bootstrap-github-oidc.yml`** (repo root has a copy under **`infra/cloudformation/`**).

```bash
export AWS_PROFILE=<your-profile>
export APP_REGION=us-east-2

aws cloudformation deploy \
  --region "$APP_REGION" \
  --stack-name lotor-regulatory-assistant-bootstrap-github-oidc \
  --template-file infra/cloudformation/bootstrap-github-oidc.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    ProjectName=lotor-regulatory-assistant \
    GitHubOrg=rohanbhutkar \
    GitHubRepo=regulatory_assistant \
    GitHubBranch=main
```

### If deploy fails or “stack does not exist”

1. **`APP_REGION` must be set** (e.g. `export APP_REGION=us-east-2`). If it’s empty, the CLI uses your profile default region — **`describe-stack-events` must use the same `--region`** as `deploy`.

2. **`describe-stack-events` after rollback:** Failed creates often end in **`ROLLBACK_COMPLETE`**. The stack **still exists** until you delete it:
   ```bash
   aws cloudformation describe-stacks --region us-east-2 \
     --stack-name lotor-regulatory-assistant-bootstrap-github-oidc
   aws cloudformation describe-stack-events --region us-east-2 \
     --stack-name lotor-regulatory-assistant-bootstrap-github-oidc
   ```
   If you want to retry cleanly:
   ```bash
   aws cloudformation delete-stack --region us-east-2 \
     --stack-name lotor-regulatory-assistant-bootstrap-github-oidc
   aws cloudformation wait stack-delete-complete --region us-east-2 \
     --stack-name lotor-regulatory-assistant-bootstrap-github-oidc
   ```

   **`ROLLBACK_COMPLETE`:** the stack still exists but **cannot be updated**. You **must** `delete-stack` + `wait stack-delete-complete`, then run `deploy` again (same template + parameters).

3. **GitHub OIDC provider already exists** (common if **`TIME_build`** or another stack created `token.actions.githubusercontent.com` in this account). You cannot create a second provider for the same URL. List providers:
   ```bash
   aws iam list-open-id-connect-providers
   ```
   Copy the ARN that ends with **`token.actions.githubusercontent.com`** / looks like **`arn:aws:iam::047492347168:oidc-provider/token.actions.githubusercontent.com`** — note **`https://`** must **not** be part of the CLI ARN.

   Redeploy **referencing the existing provider** (omit creating a duplicate):

   ```bash
   aws cloudformation deploy \
     --region "$APP_REGION" \
     --stack-name lotor-regulatory-assistant-bootstrap-github-oidc \
     --template-file infra/cloudformation/bootstrap-github-oidc.yml \
     --capabilities CAPABILITY_NAMED_IAM \
     --parameter-overrides \
       ProjectName=lotor-regulatory-assistant \
       GitHubOrg=rohanbhutkar \
       GitHubRepo=regulatory_assistant \
       GitHubBranch=main \
       ExistingGitHubOidcProviderArn=arn:aws:iam::047492347168:oidc-provider/token.actions.githubusercontent.com
   ```

   Replace the ARN if your account ID differs.

After a successful deploy, copy output **`GitHubDeployRoleArn`** into GitHub → **Settings → Secrets and variables → Actions → Variables:**

- `AWS_ROLE_TO_ASSUME` = that ARN  

Create a **`dev`** GitHub Environment (optional protection rules).

---

## 3. GitHub Actions secrets (environment `dev`)

In GitHub: **Settings → Secrets and variables → Actions**.

- Put **`AWS_ROLE_TO_ASSUME`** under **Variables** (repository variable is fine; it’s not a password).
- Put everything below under **Secrets** for the **`dev`** environment (recommended) or repository secrets.

| Name | Required when | Purpose |
|------|----------------|---------|
| `DEV_BASIC_AUTH_HEADER` | `deploy_edge=true` | Full **`Authorization`** header value CloudFront checks (HTTP Basic). |
| `DEV_ORIGIN_VERIFY_HEADER` | Deploy applies Kubernetes manifests | Must match **`X-Origin-Verify`** CloudFront adds for ALB; backend rejects traffic without it when set. |
| `REGULATORY_LLM_PROVIDER` | Always for LLM | `anthropic` or `openai` (must match how you set keys). |
| `REGULATORY_ANTHROPIC_API_KEY` | LLM_PROVIDER=anthropic | API key from Anthropic Console. |
| `REGULATORY_OPENAI_API_KEY` | LLM_PROVIDER=openai | API key from OpenAI Platform. |
| `BIOONTOLOGY_API_KEY` | BioPortal / BioOntology API usage | From [BioOntology account](https://bioportal.bioontology.org/account); optional if unused. |
| `OPENFDA_API_KEY` | Higher OpenFDA rate limits | [openFDA API key](https://open.fda.gov/apis/authentication/) (optional). |
| `GOOGLE_API_KEY` | Custom Search agent | Google Cloud API key with Custom Search API enabled. |
| `GOOGLE_SEARCH_ENGINE_ID` | Custom Search agent | Programmable Search Engine **cx** ID. |
| `AACT_DB_USERNAME` | AACT Postgres | CTTI AACT cloud DB username. |
| `AACT_DB_PASSWORD` | AACT Postgres | CTTI AACT cloud DB password. |

These map through **`kubectl create secret … regulatory-backend-env`** into pod env (same names as **`backend/.env.example`**). Empty secrets omit capability but won’t break the deploy.

### How to generate values

**`DEV_BASIC_AUTH_HEADER` (Basic Auth)** — value must be the full HTTP header **value**: **`Basic `** + base64(**`username:password`**) with no newline.

One-shot (prints the entire secret to paste into GitHub):

```bash
USER="lotor-dev"
PASS="$(openssl rand -base64 24)"
printf 'Basic %s' "$(printf '%s:%s' "$USER" "$PASS" | base64 | tr -d '\n')"
echo ""
```

On **GNU/Linux**, if `base64` wraps lines, use: `... | base64 -w0`.

Save **`USER`** / **`PASS`** in your password manager; browsers will prompt for them when CloudFront returns **401**.

**Manual check:**

```bash
printf '%s:%s' "$USER" "$PASS" | base64 | tr -d '\n'   # must equal part after "Basic "
```

Smoke tests and `curl` need: `-H "Authorization: Basic …"` (same string as the GitHub secret).

**`DEV_ORIGIN_VERIFY_HEADER`** — long random string (CloudFront → ALB shared secret):

```bash
openssl rand -base64 48 | tr -d '\n'
```

Paste the **entire** line into the GitHub secret (no `Basic ` prefix).

**`REGULATORY_LLM_PROVIDER`** — plain text, e.g.:

```text
anthropic
```

**`REGULATORY_ANTHROPIC_API_KEY` / `REGULATORY_OPENAI_API_KEY`** — create keys in the vendor console ([Anthropic](https://console.anthropic.com/), [OpenAI](https://platform.openai.com/api-keys)). Paste the full secret string; rotate there if leaked.

**Vendor keys** (`BIOONTOLOGY_API_KEY`, `OPENFDA_API_KEY`, **`GOOGLE_API_KEY`** / **`GOOGLE_SEARCH_ENGINE_ID`**, **`AACT_*`**): create or copy from each provider’s console; paste into GitHub **Secrets** with **exactly** those names so Actions can inject them.

For more variables (Redis, `AACT_DB_SSL_CAFILE`, etc.), add GitHub secrets and extra **`--from-literal=...`** lines next to the existing block in **`.github/workflows/deploy-aws-dev.yml`**.

---

## 4. First workflow run (certificates + platform only)

Actions → **Deploy AWS Dev (EKS)**:

- `deploy_edge`: **false**
- `run_smoke_tests`: **false**

Workflow creates:

- `infra/aws/cloudformation/certificates-dev.yml` stacks (edge + regional)
- `infra/aws/cloudformation/platform-dev.yml` — VPC, **EKS 1.34**, Fargate profiles, **dual ECR** repos (backend + frontend), ALB SG, IRSA role for backend S3 read on `runtime-data/*` (optional future use)

### ACM DNS validation

Add every **CNAME** ACM prints (edge `us-east-1` + regional `us-east-2`) at your DNS provider.

Re-run the workflow until **Check certificate issuance** passes (`ISSUED` for both).

---

## 5. Second run — images + EKS

Same inputs (`deploy_edge`: false). After certs are **ISSUED**, the job:

1. Builds/pushes **Docker** images to ECR (`:${GITHUB_SHA}`).
2. Configures `kubectl`, patches **CoreDNS** (Fargate), installs **AWS Load Balancer Controller** (`infra/helm/aws-load-balancer-controller-values.yaml`).
3. Applies **`infra/aws/k8s/dev/regulatory-app.yaml`** (patched in CI).

### Origin DNS

When ingress is ready, the workflow prints:

```text
Create DNS: origin-api.regulatory-assistant.lotorlab.com CNAME <alb-xxxx.elb.amazonaws.com>
```

Add that **CNAME** at your DNS host. Wait for propagation before enabling CloudFront.

---

## 6. Third run — CloudFront edge

Actions → same workflow:

- `deploy_edge`: **true**
- `run_smoke_tests`: **false** (until viewer DNS exists)

Deploys **`infra/aws/cloudformation/edge-regulatory-dev.yml`** (CloudFront + WAF, single **ALB** origin).

### Viewer DNS

Point:

- `regulatory-assistant.lotorlab.com` → CloudFront domain (`dxxxx.cloudfront.net`)
- `api.regulatory-assistant.lotorlab.com` → **same** CloudFront domain

---

## 7. Smoke tests

After viewer DNS propagates:

- `deploy_edge`: **true**
- `run_smoke_tests`: **true**

---

## 8. Files reference

| Path | Role |
|------|------|
| `infra/aws/cloudformation/platform-dev.yml` | VPC, EKS, Fargate, ECR ×2, buckets, IRSA |
| `infra/aws/cloudformation/certificates-dev.yml` | ACM + DNS validation helper Lambda |
| `infra/aws/cloudformation/edge-regulatory-dev.yml` | CloudFront + WAF (ALB-only origin) |
| `infra/aws/k8s/dev/regulatory-app.yaml` | Namespace, backend + frontend Deployments, grouped Ingresses |
| `infra/helm/aws-load-balancer-controller-values.yaml` | Helm values; `${CLUSTER_NAME}` etc. substituted in workflow |
| `.github/workflows/deploy-aws-dev.yml` | Pipeline |

---

## 9. Backend behaviour behind CloudFront

- **`REGULATORY_ORIGIN_VERIFY_HEADER_VALUE`** — set from `DEV_ORIGIN_VERIFY_HEADER` in-cluster; rejects requests without **`X-Origin-Verify`** when set (health paths exempt).
- **`REGULATORY_CORS_ORIGINS`** — comma-separated extra origins (workflow sets app + API hosts).
- **`/alb-health`** — lightweight probe for ALB target groups.

---

## 10. Operational notes

- **WebSockets** via CloudFront have **idle/origin read limits**; very long silent connections may drop — tune ALB/CloudFront if needed.
- **Costs:** NAT Gateway + EKS + Fargate + CloudFront — track in AWS Cost Explorer.
- **Same AWS account as TIME:** VPC CIDR here is **`10.71.0.0/16`** to avoid colliding with TIME’s `10.70.0.0/16`.

For Psidium-specific naming and screenshots, see **`TIME_build/infra/README.md`** as a parallel runbook.
