#!/bin/bash

# CI/CD Pipeline Verification Script
# This script verifies that all CI/CD components are properly configured

set -e

echo "=================================="
echo "CI/CD Pipeline Verification Script"
echo "=================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0
WARN=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

echo "1. Checking Workflow Files..."
echo "------------------------------"

workflows=(
    ".github/workflows/ci.yml"
    ".github/workflows/docker.yml"
    ".github/workflows/lint.yml"
    ".github/workflows/security.yml"
    ".github/workflows/performance.yml"
    ".github/workflows/release.yml"
    ".github/workflows/validate.yml"
)

for workflow in "${workflows[@]}"; do
    if [ -f "$workflow" ]; then
        check_pass "$(basename $workflow)"
    else
        check_fail "$(basename $workflow) not found"
    fi
done

echo ""
echo "2. Checking Configuration Files..."
echo "-----------------------------------"

configs=(
    ".github/dependabot.yml"
    ".github/SECRETS_SETUP.md"
    ".github/PULL_REQUEST_TEMPLATE.md"
)

for config in "${configs[@]}"; do
    if [ -f "$config" ]; then
        check_pass "$(basename $config)"
    else
        check_fail "$(basename $config) not found"
    fi
done

echo ""
echo "3. Checking Issue Templates..."
echo "-------------------------------"

templates=(
    ".github/ISSUE_TEMPLATE/bug_report.md"
    ".github/ISSUE_TEMPLATE/feature_request.md"
    ".github/ISSUE_TEMPLATE/config.yml"
)

for template in "${templates[@]}"; do
    if [ -f "$template" ]; then
        check_pass "$(basename $template)"
    else
        check_fail "$(basename $template) not found"
    fi
done

echo ""
echo "4. Checking Documentation..."
echo "-----------------------------"

docs=(
    "README.md"
    "CI_CD_GUIDE.md"
    "CI_CD_QUICK_REFERENCE.md"
    "CI_CD_IMPLEMENTATION_COMPLETE.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        check_pass "$doc"
    else
        check_fail "$doc not found"
    fi
done

echo ""
echo "5. Validating YAML Syntax..."
echo "-----------------------------"

if command -v python3 &> /dev/null; then
    for workflow in .github/workflows/*.yml; do
        if python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
            check_pass "$(basename $workflow) - Valid YAML"
        else
            check_fail "$(basename $workflow) - Invalid YAML"
        fi
    done

    if python3 -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))" 2>/dev/null; then
        check_pass "dependabot.yml - Valid YAML"
    else
        check_fail "dependabot.yml - Invalid YAML"
    fi
else
    check_warn "Python3 not found - skipping YAML validation"
fi

echo ""
echo "6. Checking for Hardcoded Secrets..."
echo "-------------------------------------"

if grep -rE '(password|token|key|secret).*[:=].*["'"'"'][^$]' .github/workflows/*.yml 2>/dev/null; then
    check_fail "Potential hardcoded secrets found in workflows!"
else
    check_pass "No hardcoded secrets detected"
fi

echo ""
echo "7. Checking Required Files..."
echo "------------------------------"

required_files=(
    "requirements.txt"
    "Dockerfile"
    "docker-compose.yml"
    "alembic.ini"
    ".env.example"
    ".dockerignore"
    ".gitignore"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file"
    else
        check_warn "$file not found (may be optional)"
    fi
done

echo ""
echo "8. Checking Test Files..."
echo "--------------------------"

test_files=(
    "test_comprehensive.py"
    "test_auth.py"
    "test_rate_limiting.py"
    "test_query_performance.py"
)

for file in "${test_files[@]}"; do
    if [ -f "$file" ]; then
        check_pass "$file"
    else
        check_warn "$file not found"
    fi
done

echo ""
echo "9. Checking for .env File..."
echo "-----------------------------"

if [ -f ".env" ]; then
    check_warn ".env file exists (should not be committed to git)"

    if grep -q ".env" .gitignore 2>/dev/null; then
        check_pass ".env is in .gitignore"
    else
        check_fail ".env is NOT in .gitignore!"
    fi
else
    check_pass ".env file not present (good for git)"
fi

echo ""
echo "10. README Badge Check..."
echo "--------------------------"

if [ -f "README.md" ]; then
    if grep -q "github.com/taiyousan15/kindle-text-extraction/actions/workflows/ci.yml" README.md; then
        check_pass "CI Pipeline badge present"
    else
        check_warn "CI Pipeline badge not found in README"
    fi

    if grep -q "github.com/taiyousan15/kindle-text-extraction/actions/workflows/docker.yml" README.md; then
        check_pass "Docker Build badge present"
    else
        check_warn "Docker Build badge not found in README"
    fi
else
    check_fail "README.md not found"
fi

echo ""
echo "=================================="
echo "Verification Summary"
echo "=================================="
echo -e "${GREEN}Passed:${NC} $PASS"
echo -e "${RED}Failed:${NC} $FAIL"
echo -e "${YELLOW}Warnings:${NC} $WARN"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ CI/CD Pipeline is properly configured!${NC}"
    echo ""
    echo "Next Steps:"
    echo "1. Configure GitHub Secrets:"
    echo "   - Go to Settings → Secrets and variables → Actions"
    echo "   - Add ANTHROPIC_API_KEY"
    echo "   - (Optional) Add OPENAI_API_KEY"
    echo ""
    echo "2. Push to GitHub:"
    echo "   git add ."
    echo "   git commit -m 'ci: add comprehensive CI/CD pipeline'"
    echo "   git push origin main"
    echo ""
    echo "3. Monitor workflows:"
    echo "   - Go to Actions tab on GitHub"
    echo "   - Watch workflows execute"
    echo "   - Fix any issues that arise"
    echo ""
    exit 0
else
    echo -e "${RED}✗ CI/CD Pipeline has issues that need to be fixed${NC}"
    echo ""
    echo "Please review the failed checks above and fix them."
    echo ""
    exit 1
fi
