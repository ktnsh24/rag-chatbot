# CI/CD Pipeline — GitHub Actions

## Overview

Three workflows:

| Workflow | Trigger | What it does |
| --- | --- | --- |
| `ci.yml` | Push to main/develop, PRs | Lint → Test → Build Docker image |
| `deploy-aws.yml` | Manual (workflow_dispatch) | Build → Push to ECR → Terraform → Update ECS |
| `deploy-azure.yml` | Manual (workflow_dispatch) | Build → Push to ACR → Terraform → Update Container App |

## CI Pipeline (ci.yml)

```
Push/PR → Lint (Ruff) → Unit Tests (Pytest) → Build Docker Image
```

### Job 1: Lint

Runs `ruff check` and `ruff format --check`. Catches:

- Import errors, unused variables
- Code style violations
- Formatting inconsistencies

### Job 2: Test

Runs `pytest` with coverage. Reports:

- Test pass/fail status
- Code coverage percentage
- Coverage report uploaded as artifact

### Job 3: Build

Builds the Docker image to ensure:

- All dependencies install correctly
- The application starts without errors
- No missing files

## Deploy Pipeline

Both deploy workflows:

1. Authenticate to cloud (OIDC for AWS, Service Principal for Azure)
2. Build Docker image with commit SHA tag
3. Push to container registry (ECR/ACR)
4. Run Terraform apply (infrastructure changes)
5. Update the running service (ECS/Container Apps)

### Required GitHub Secrets

| Secret | AWS | Azure |
| --- | --- | --- |
| `AWS_ROLE_ARN` | IAM role ARN for OIDC | - |
| `AZURE_CLIENT_ID` | - | Service Principal client ID |
| `AZURE_TENANT_ID` | - | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | - | Subscription ID |
| `ACR_NAME` | - | Container Registry name |

## Running locally

You can test the CI pipeline locally:

```bash
# Lint
poetry run ruff check src/ tests/
poetry run ruff format --check src/ tests/

# Test
poetry run pytest -v --cov=src

# Build
docker build -t rag-chatbot:local .
```
