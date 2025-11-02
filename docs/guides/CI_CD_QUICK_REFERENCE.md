# CI/CD Quick Reference

## Workflow Status Dashboard

View all workflows: https://github.com/taiyousan15/kindle-text-extraction/actions

## Workflows at a Glance

| Workflow | Trigger | Purpose | Runtime |
|----------|---------|---------|---------|
| **CI Pipeline** | Push to main/develop, PRs | Run comprehensive tests | ~5-10 min |
| **Docker Build** | Push to main, tags | Build & push Docker images | ~10-15 min |
| **Code Quality** | Push, PRs | Linting and formatting checks | ~2-3 min |
| **Security Scan** | Push, PRs, weekly | Security vulnerability scanning | ~5-8 min |
| **Performance** | Push to main, weekly | Performance benchmarks | ~5-7 min |
| **Release** | Version tags (v*.*.*) | Create GitHub releases | ~3-5 min |
| **Validate** | PR to workflows | Validate workflow syntax | ~1 min |

## Common Commands

### Trigger Workflows Manually

```bash
# Via GitHub UI: Actions → Workflow → Run workflow

# Via gh CLI
gh workflow run ci.yml
gh workflow run docker.yml
gh workflow run security.yml
```

### View Workflow Runs

```bash
# List recent runs
gh run list

# View specific run
gh run view <run-id>

# Watch live run
gh run watch

# Download artifacts
gh run download <run-id>
```

### Create Release

```bash
# Create and push tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Release workflow triggers automatically
```

## Status Badges

Add to README.md:

```markdown
[![CI Pipeline](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/ci.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/ci.yml)
[![Docker Build](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/docker.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/docker.yml)
[![Code Quality](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/lint.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/lint.yml)
[![Security Scan](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/security.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/security.yml)
```

## Quick Fixes

### Workflow Fails: Missing Secret

```bash
# 1. Go to Settings → Secrets and variables → Actions
# 2. Add required secret
# 3. Re-run workflow
```

### Workflow Fails: Test Failures

```bash
# Run tests locally first
pytest test_comprehensive.py -v

# Fix issues, commit, push
git add .
git commit -m "fix: resolve test failures"
git push
```

### Workflow Fails: Linting Errors

```bash
# Auto-fix formatting
black app/
isort app/

# Commit fixes
git add .
git commit -m "style: fix formatting"
git push
```

### Docker Build Fails

```bash
# Test build locally
docker build -t kindle-ocr:test .

# Check .dockerignore
cat .dockerignore

# Fix and push
git push
```

## Secret Configuration

Required secrets:
- `ANTHROPIC_API_KEY` - For LLM tests (required)
- `OPENAI_API_KEY` - For OpenAI tests (optional)

See [SECRETS_SETUP.md](.github/SECRETS_SETUP.md) for detailed setup.

## Pull Request Checklist

Before creating PR:
- [ ] Tests pass locally: `pytest test_comprehensive.py -v`
- [ ] Code formatted: `black app/ && isort app/`
- [ ] No linting errors: `flake8 app/ --max-line-length=120`
- [ ] Type checking: `mypy app/ --ignore-missing-imports`
- [ ] Branch up to date with main

After creating PR:
- [ ] CI Pipeline passes
- [ ] Code Quality passes
- [ ] Security Scan passes
- [ ] No merge conflicts
- [ ] Review approved

## Release Checklist

- [ ] All tests passing on main
- [ ] Version updated in relevant files
- [ ] CHANGELOG updated
- [ ] Create tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
- [ ] Push tag: `git push origin v1.0.0`
- [ ] Verify release workflow succeeds
- [ ] Check GitHub Release page
- [ ] Verify Docker image: `docker pull ghcr.io/taiyousan15/kindle-text-extraction:v1.0.0`

## Rollback Procedures

### Rollback Git Tag
```bash
# Delete local tag
git tag -d v1.0.0

# Delete remote tag
git push origin :refs/tags/v1.0.0
```

### Rollback Docker Image
```bash
# Use previous version
docker pull ghcr.io/taiyousan15/kindle-text-extraction:v0.9.0
```

### Rollback Code
```bash
# Revert last commit
git revert HEAD
git push
```

## Monitoring

### GitHub Actions Dashboard
https://github.com/taiyousan15/kindle-text-extraction/actions

### Workflow Insights
- Actions → Insights → View workflow details
- See success rates, run times, costs

### Email Notifications
- Settings → Notifications → Actions
- Configure when to receive emails

## Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| CI Pipeline | < 10 min | ~5-10 min |
| Docker Build | < 15 min | ~10-15 min |
| Code Quality | < 5 min | ~2-3 min |
| Security Scan | < 10 min | ~5-8 min |
| Test Success Rate | > 95% | TBD |

## Troubleshooting

### Common Errors

**Error: Secret not found**
- Solution: Add secret in Settings → Secrets and variables

**Error: Database connection failed**
- Solution: Check service health in workflow logs

**Error: Docker build timeout**
- Solution: Increase timeout or optimize Dockerfile

**Error: Rate limit exceeded**
- Solution: Check API usage, add delays

### Getting Help

1. Check [CI_CD_GUIDE.md](CI_CD_GUIDE.md) for detailed docs
2. Review workflow logs in Actions tab
3. Search GitHub Issues
4. Create new issue with logs

## Best Practices

### Commit Messages
```
feat: add new feature
fix: bug fix
docs: documentation
style: formatting
refactor: code restructure
test: add tests
chore: maintenance
```

### Branch Naming
```
feature/feature-name
bugfix/issue-description
hotfix/critical-fix
release/v1.0.0
```

### Testing
- Always test locally before pushing
- Run full test suite for main/develop
- Add tests for new features
- Maintain > 80% code coverage

### Security
- Never commit secrets
- Use GitHub Secrets for sensitive data
- Rotate API keys regularly
- Monitor security scan results

## Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Hub](https://hub.docker.com/)
- [GitHub Container Registry](https://ghcr.io)
- [Project Documentation](CI_CD_GUIDE.md)

## Quick Links

- [Actions Dashboard](https://github.com/taiyousan15/kindle-text-extraction/actions)
- [Secrets Configuration](https://github.com/taiyousan15/kindle-text-extraction/settings/secrets/actions)
- [Releases](https://github.com/taiyousan15/kindle-text-extraction/releases)
- [Container Registry](https://github.com/taiyousan15/kindle-text-extraction/pkgs/container/kindle-text-extraction)
- [Issues](https://github.com/taiyousan15/kindle-text-extraction/issues)

---

**Last Updated**: 2024-10-29
