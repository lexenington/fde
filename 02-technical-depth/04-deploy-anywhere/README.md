# 02/04 — Deploy anywhere

**Prove it (skip if yes):** Can you take a containerised app and, using only Terraform, deploy it into an AWS account you don't own, in a private subnet with no public IP, reaching an LLM API through a controlled egress path, with secrets in a secrets manager, logs and metrics shipped somewhere the customer can see, and a runbook their on-call can follow at 3am?

## Why this matters for FDEs

Railway and your own AWS account are easy mode. At an enterprise customer:
- It runs in **their** cloud account, which you get via a role they create, with permissions they review.
- **No public ingress.** Users reach it over VPN/private link. Outbound internet may be allow-listed to specific domains (e.g. `api.anthropic.com`) or not allowed at all.
- Every change goes through **their change process**: a PR to their infra repo, approval by their platform team, and a deploy window.
- When you leave, **their team runs it**. If it isn't observable and documented, it gets switched off.

LLM-specific wrinkle: customers increasingly want models served through *their* cloud contract, i.e. Claude via Amazon Bedrock, Google Vertex AI or Microsoft Foundry, so data stays in their cloud boundary and spend lands on existing commitments. Know how to switch an app between the first-party API and those providers (the Anthropic SDK ships a dedicated client for each).

**When the customer can't call any external model API** (air-gapped, regulator says no, data residency with no in-country region), your options are, in order of preference: (1) a frontier model through their cloud provider inside their boundary; (2) an open-weight model self-hosted on their GPUs (vLLM, Ollama, TGI), accepting the quality gap; (3) reduce the AI to the parts that can run locally and route the rest to humans. Your eval harness is how you show the customer the quality cost of each option, in numbers. Check which cloud regions currently exist in or near West Africa (and which models each offers there), because it changes the answer.

## Concepts to learn

| Area | Must know |
|---|---|
| **Terraform** | Modules, remote state + locking, workspaces/environments, `plan` as a review artifact, importing existing resources |
| **Networking** | VPC, public/private subnets, NAT gateway, security groups vs NACLs, VPC endpoints / PrivateLink, egress proxies & domain allow-lists, DNS |
| **Identity for infra** | Cross-account IAM roles, least-privilege policies, OIDC from CI to cloud (no long-lived keys) |
| **Compute choices** | ECS Fargate vs EKS vs a single VM: pick the one *their* team can operate. You know K8s; know when not to use it |
| **Secrets** | AWS Secrets Manager / SSM / Vault, rotation, never in env files in the repo |
| **Observability** | Structured logs, metrics (RED: rate/errors/duration), traces (OpenTelemetry), dashboards + alerts the customer owns. LLM traces: prompt, tokens, latency, tool calls |
| **Delivery** | CI/CD with environments, blue/green or rolling deploys, DB migrations that are backward-compatible, rollback plan |
| **Constrained environments** | Air-gapped installs (vendored images, offline package mirrors), on-prem K8s, and low-bandwidth edge sites. Your EatryCloud offline-first experience applies directly here |
| **Multi-tenant vs single-tenant** | Why big customers demand dedicated deployments, and what that costs you operationally |
| **Azure & GCP equivalents** | The lab is AWS, but many enterprises (banks and telcos especially) are Microsoft shops. Be able to translate the lab into Azure (Entra ID, VNet + Private Endpoints, Key Vault, Container Apps or AKS, Azure Monitor, Claude via Microsoft Foundry) and GCP (VPC + Private Service Connect, Secret Manager, Cloud Run or GKE, Cloud Logging, Claude via Vertex AI). Terraform providers differ; the shape of the design doesn't |
| **Self-hosted models & inference optimisation** | When option (2) above is the only option: serving open-weight models with vLLM/TGI, GPU sizing, quantisation (quality vs memory trade-off), distillation, batching and response caching. Measure tokens/sec, p95 latency and cost per task, and always put the eval score next to them |
| **MLOps & managed ML services** | Some customers already have an ML platform (SageMaker, Vertex AI, Azure ML) and want your work to live in it. Know the vocabulary: model registry, versioned data and models, training vs inference pipelines, drift monitoring. You don't need to train models; you need to deploy into *their* platform without fighting it |

## Lab: deploy the invoice extractor "into the customer's account"

1. Create a second AWS account (AWS Organizations, free) to play the **customer**. Your main account plays the **vendor**.
2. In the customer account, create a role the vendor account can assume, with a *written* least-privilege policy. Write it the way you'd send it to a customer's security team.
3. Terraform (in `lab/infra/`):
   - VPC with private subnets only for compute; NAT or egress proxy allowing *only* `api.anthropic.com` (or use Bedrock via a VPC endpoint, which is the stretch variant).
   - ECS Fargate service running the invoice extractor from 02/03 behind an **internal** ALB.
   - RDS Postgres for the review queue; credentials in Secrets Manager.
   - CloudWatch log group, a dashboard (requests, error rate, p95 latency, tokens/day, review-queue depth) and two alarms.
4. GitHub Actions deploying via OIDC → role assumption. No AWS keys in GitHub.
5. **Tear it down and bring it back up from zero** in under 30 minutes. Time it.
6. Write `RUNBOOK.md`: how to deploy, roll back, rotate the API key, read the dashboard, and what each alarm means and what to do about it.
7. Write `HANDOVER.md`: what the customer's team owns now, what they need to learn, open risks.

### Stretch
- **Azure variant (paper or real):** write `AZURE.md` mapping every resource in your Terraform to its Azure equivalent, with the one or two places the design has to change. If you have credits, deploy it.
- **Self-hosted fallback:** run an open-weight model with vLLM or Ollama, point the extractor at it, and re-run the 02/03 eval. Write the table a customer would need: quality, latency and cost per 1,000 invoices vs Claude in their cloud boundary. Then try a quantised variant and add a row.

**Cost guard:** NAT gateways and ALBs cost money even when idle. Run `terraform destroy` at the end of every session, and set an AWS Budget alert at $20 before you start.
