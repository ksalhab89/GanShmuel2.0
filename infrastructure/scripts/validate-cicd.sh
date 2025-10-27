#!/bin/bash

# CI/CD Pipeline Validation Script
# Validates that all CI/CD files are properly configured

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CI/CD Pipeline Validation${NC}"
echo -e "${BLUE}========================================${NC}"

# Track validation status
ERRORS=0
WARNINGS=0

# Function to check file exists
check_file() {
    local file=$1
    local description=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description"
    else
        echo -e "${RED}✗${NC} $description - File not found: $file"
        ((ERRORS++))
    fi
}

# Function to check file is executable
check_executable() {
    local file=$1
    local description=$2

    if [ -x "$file" ]; then
        echo -e "${GREEN}✓${NC} $description"
    else
        echo -e "${YELLOW}⚠${NC} $description - File not executable: $file"
        ((WARNINGS++))
    fi
}

# Function to validate YAML syntax
validate_yaml() {
    local file=$1
    local description=$2

    if command -v yamllint &> /dev/null; then
        if yamllint -d relaxed "$file" &> /dev/null; then
            echo -e "${GREEN}✓${NC} $description - YAML syntax valid"
        else
            echo -e "${RED}✗${NC} $description - YAML syntax errors"
            ((ERRORS++))
        fi
    else
        echo -e "${YELLOW}⚠${NC} $description - yamllint not installed, skipping syntax check"
        ((WARNINGS++))
    fi
}

echo -e "\n${BLUE}Checking GitHub Actions workflows...${NC}"
check_file ".github/workflows/test.yml" "Test Suite workflow exists"
check_file ".github/workflows/coverage-report.yml" "Coverage Report workflow exists"
check_file ".github/workflows/performance.yml" "Performance Tests workflow exists"

echo -e "\n${BLUE}Checking Dependabot configuration...${NC}"
check_file ".github/dependabot.yml" "Dependabot config exists"

echo -e "\n${BLUE}Checking scripts...${NC}"
check_file "scripts/run-all-tests.sh" "Test execution script exists"
check_executable "scripts/run-all-tests.sh" "Test execution script is executable"

echo -e "\n${BLUE}Checking documentation...${NC}"
check_file "CI_CD_IMPLEMENTATION.md" "Implementation documentation exists"
check_file "CI_CD_QUICKSTART.md" "Quick start guide exists"
check_file "README.md" "README exists"

echo -e "\n${BLUE}Validating YAML syntax...${NC}"
if command -v yamllint &> /dev/null; then
    validate_yaml ".github/workflows/test.yml" "Test Suite workflow"
    validate_yaml ".github/workflows/coverage-report.yml" "Coverage Report workflow"
    validate_yaml ".github/workflows/performance.yml" "Performance Tests workflow"
    validate_yaml ".github/dependabot.yml" "Dependabot config"
else
    echo -e "${YELLOW}⚠${NC} yamllint not installed - install with: pip install yamllint"
    ((WARNINGS++))
fi

echo -e "\n${BLUE}Checking service test infrastructure...${NC}"

# Check if services have test directories
SERVICES=("weight-service" "billing-service" "shift-service" "frontend")
for service in "${SERVICES[@]}"; do
    if [ -d "$service" ]; then
        if [ -d "$service/tests" ] || [ "$service" = "frontend" ]; then
            echo -e "${GREEN}✓${NC} $service has test infrastructure"
        else
            echo -e "${YELLOW}⚠${NC} $service missing tests directory"
            ((WARNINGS++))
        fi
    else
        echo -e "${YELLOW}⚠${NC} $service directory not found"
        ((WARNINGS++))
    fi
done

echo -e "\n${BLUE}Checking service configurations...${NC}"

# Check for pyproject.toml in Python services
for service in "weight-service" "billing-service" "shift-service"; do
    if [ -d "$service" ]; then
        if [ -f "$service/pyproject.toml" ]; then
            echo -e "${GREEN}✓${NC} $service has pyproject.toml"
        else
            echo -e "${YELLOW}⚠${NC} $service missing pyproject.toml"
            ((WARNINGS++))
        fi
    fi
done

# Check for package.json in frontend
if [ -d "frontend" ]; then
    if [ -f "frontend/package.json" ]; then
        echo -e "${GREEN}✓${NC} frontend has package.json"
    else
        echo -e "${RED}✗${NC} frontend missing package.json"
        ((ERRORS++))
    fi
fi

echo -e "\n${BLUE}Checking README.md for badges...${NC}"
if grep -q "github.com.*actions/workflows" README.md; then
    echo -e "${GREEN}✓${NC} README contains CI/CD badges"

    if grep -q "YOUR_USERNAME" README.md; then
        echo -e "${YELLOW}⚠${NC} README badges contain placeholder 'YOUR_USERNAME' - needs update"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✓${NC} README badges have been customized"
    fi
else
    echo -e "${YELLOW}⚠${NC} README missing CI/CD badges"
    ((WARNINGS++))
fi

echo -e "\n${BLUE}Checking for GitHub repository setup...${NC}"
if git remote -v &> /dev/null; then
    echo -e "${GREEN}✓${NC} Git repository configured"

    if git remote -v | grep -q "github.com"; then
        echo -e "${GREEN}✓${NC} GitHub remote configured"
    else
        echo -e "${YELLOW}⚠${NC} GitHub remote not found - workflows won't run until pushed to GitHub"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Not a git repository"
    ((WARNINGS++))
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}========================================${NC}"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo -e "\n${GREEN}CI/CD pipeline is ready to use.${NC}"
    echo -e "\n${BLUE}Next steps:${NC}"
    echo -e "1. Update badge URLs in README.md (if needed)"
    echo -e "2. Add CODECOV_TOKEN to GitHub secrets"
    echo -e "3. Push to GitHub to trigger first workflow run"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ Validation completed with $WARNINGS warning(s)${NC}"
    echo -e "\n${YELLOW}CI/CD pipeline is functional but has minor issues.${NC}"
    echo -e "Review warnings above and address as needed."
    exit 0
else
    echo -e "${RED}✗ Validation failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo -e "\n${RED}Please fix the errors above before using the CI/CD pipeline.${NC}"
    exit 1
fi
