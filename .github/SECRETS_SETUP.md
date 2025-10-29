# GitHub Secrets Setup Guide

This guide explains how to configure GitHub Secrets for the CI/CD pipeline.

## Required Secrets

### 1. ANTHROPIC_API_KEY

**Purpose**: Required for RAG and LLM-based features in tests

**How to obtain**:
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create new API key
5. Copy the key (starts with `sk-ant-`)

**How to set in GitHub**:
1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `ANTHROPIC_API_KEY`
5. Value: Paste your API key
6. Click **Add secret**

**Required**: Yes (for comprehensive tests)

---

### 2. OPENAI_API_KEY

**Purpose**: Optional, for OpenAI-based tests and fallback LLM

**How to obtain**:
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create new API key
5. Copy the key (starts with `sk-`)

**How to set in GitHub**:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `OPENAI_API_KEY`
4. Value: Paste your API key
5. Click **Add secret**

**Required**: No (optional)

---

## Automatic Secrets

### GITHUB_TOKEN

**Purpose**: Used for Docker image push to GitHub Container Registry

**How to obtain**: Automatically provided by GitHub Actions (no setup needed)

**Permissions**: Read/write access to packages

**Configuration**: Already configured in workflows

---

## Optional Secrets (for Docker Hub)

If you want to push to Docker Hub instead of/in addition to GitHub Container Registry:

### DOCKERHUB_USERNAME

**Purpose**: Docker Hub username

**How to obtain**: Your Docker Hub username

**How to set**:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `DOCKERHUB_USERNAME`
4. Value: Your Docker Hub username
5. Click **Add secret**

### DOCKERHUB_TOKEN

**Purpose**: Docker Hub access token

**How to obtain**:
1. Go to https://hub.docker.com/
2. Log in
3. Go to **Account Settings** → **Security**
4. Click **New Access Token**
5. Copy the token

**How to set**:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `DOCKERHUB_TOKEN`
4. Value: Paste your access token
5. Click **Add secret**

**Note**: Update `.github/workflows/docker.yml` to use Docker Hub registry

---

## Verifying Secrets

After setting up secrets, verify they work:

1. **Trigger a workflow**:
   - Push a commit to `main` or `develop`
   - Or manually trigger via **Actions** → **Workflow** → **Run workflow**

2. **Check workflow run**:
   - Go to **Actions** tab
   - Click on the workflow run
   - Check each job's logs
   - Ensure no "secret not found" errors

3. **Test specific workflows**:
   - **CI Pipeline**: Push to any branch
   - **Docker Build**: Push to `main` or create a tag
   - **Security Scan**: Should run automatically

---

## Security Best Practices

### Do's
- ✅ Rotate API keys regularly
- ✅ Use minimum required permissions
- ✅ Monitor API usage
- ✅ Delete unused secrets
- ✅ Use different keys for dev/prod

### Don'ts
- ❌ Never commit secrets to repository
- ❌ Don't share secrets in logs or comments
- ❌ Don't use production keys in CI
- ❌ Don't copy secrets to public places

---

## Troubleshooting

### Secret Not Available in Workflow

**Symptom**: Workflow fails with "secret not found" or empty value

**Solutions**:
1. Verify secret name matches exactly (case-sensitive)
2. Check secret is set in repository (not organization)
3. Ensure workflow has permission to access secrets
4. Forks don't have access to repository secrets (add secrets to your fork)

### API Key Errors

**Symptom**: Tests fail with "invalid API key" or "unauthorized"

**Solutions**:
1. Verify API key is valid and not expired
2. Check API key has correct permissions
3. Ensure billing is set up for API provider
4. Test API key locally first:
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   pytest test_comprehensive.py -k "test_llm"
   ```

### Rate Limit Errors

**Symptom**: Tests fail with "rate limit exceeded"

**Solutions**:
1. Check API quota/limits on provider dashboard
2. Reduce test frequency
3. Add delays between tests
4. Use separate test API key with higher limits

---

## Environment-Specific Configuration

### Development Environment

Create `.env` file locally (not committed):
```bash
ANTHROPIC_API_KEY=sk-ant-your-dev-key
OPENAI_API_KEY=sk-your-dev-key
DATABASE_URL=postgresql://localhost/kindle_ocr_dev
```

### CI Environment

Configured via GitHub Secrets (as described above)

### Production Environment

Use environment variables in deployment platform:
- Docker: Set in `docker-compose.prod.yml` or runtime
- Kubernetes: Use Secrets or ConfigMaps
- Cloud: Use secret management services (AWS Secrets Manager, etc.)

---

## Monitoring Secrets Usage

### GitHub Actions Usage

1. Go to **Settings** → **Billing and plans**
2. View **Actions & Packages** usage
3. Monitor workflow run minutes

### API Usage

**Anthropic**:
1. Go to https://console.anthropic.com/
2. Check **Usage** dashboard
3. Monitor token consumption

**OpenAI**:
1. Go to https://platform.openai.com/usage
2. Check API usage and costs
3. Set usage limits if needed

---

## Rotating Secrets

### When to Rotate
- Regularly (every 90 days recommended)
- After team member departure
- If secret potentially compromised
- After security incident

### How to Rotate

1. **Generate new API key** at provider
2. **Update GitHub Secret**:
   - Go to **Settings** → **Secrets and variables** → **Actions**
   - Click on secret name
   - Click **Update**
   - Paste new value
   - Click **Update secret**
3. **Update local `.env`** if applicable
4. **Test workflow** to ensure new key works
5. **Revoke old key** at provider

---

## Support

If you encounter issues:

1. **Check workflow logs**: Actions → Failed workflow → View logs
2. **Verify secret setup**: Settings → Secrets and variables
3. **Test locally**: Use same secret values in local `.env`
4. **Create issue**: Include error message (redact secrets!)

---

## Quick Setup Checklist

- [ ] Create Anthropic account and get API key
- [ ] Add `ANTHROPIC_API_KEY` to GitHub Secrets
- [ ] (Optional) Create OpenAI account and get API key
- [ ] (Optional) Add `OPENAI_API_KEY` to GitHub Secrets
- [ ] Verify secrets in Settings → Secrets and variables
- [ ] Trigger test workflow to verify
- [ ] Check Actions tab for successful run
- [ ] Document secret rotation schedule

---

**Last Updated**: 2024-10-29
