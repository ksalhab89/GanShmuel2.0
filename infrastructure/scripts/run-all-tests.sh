#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track failures
FAILED_TESTS=()

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Running All Tests${NC}"
echo -e "${BLUE}================================${NC}"

# Function to run tests for a service
run_service_tests() {
    local service_name=$1
    local service_dir=$2
    local coverage_threshold=$3

    echo -e "\n${YELLOW}[${service_name}] Starting tests...${NC}"

    cd "$service_dir" || { echo -e "${RED}Failed to enter $service_dir${NC}"; return 1; }

    # Run type checking
    echo -e "${BLUE}[${service_name}] Running type checking...${NC}"
    if uv run mypy src; then
        echo -e "${GREEN}✓ Type checking passed${NC}"
    else
        echo -e "${RED}✗ Type checking failed${NC}"
        FAILED_TESTS+=("$service_name: Type checking")
    fi

    # Run linting (different tools for different services)
    echo -e "${BLUE}[${service_name}] Running linting...${NC}"
    if [ -f "pyproject.toml" ] && grep -q "ruff" "pyproject.toml"; then
        if uv run ruff check src; then
            echo -e "${GREEN}✓ Linting passed${NC}"
        else
            echo -e "${RED}✗ Linting failed${NC}"
            FAILED_TESTS+=("$service_name: Linting")
        fi
    elif [ -f "pyproject.toml" ] && grep -q "flake8" "pyproject.toml"; then
        if uv run flake8 src tests; then
            echo -e "${GREEN}✓ Linting passed${NC}"
        else
            echo -e "${RED}✗ Linting failed${NC}"
            FAILED_TESTS+=("$service_name: Linting")
        fi
    fi

    # Run tests with coverage
    echo -e "${BLUE}[${service_name}] Running tests with coverage...${NC}"
    if uv run pytest tests/ -v --cov=src --cov-report=term --cov-report=html --cov-fail-under="$coverage_threshold"; then
        echo -e "${GREEN}✓ Tests passed (coverage >= ${coverage_threshold}%)${NC}"
    else
        echo -e "${RED}✗ Tests failed or coverage below ${coverage_threshold}%${NC}"
        FAILED_TESTS+=("$service_name: Tests")
        cd - > /dev/null
        return 1
    fi

    cd - > /dev/null
    echo -e "${GREEN}[${service_name}] All checks passed!${NC}"
}

# Function to run frontend tests
run_frontend_tests() {
    echo -e "\n${YELLOW}[Frontend] Starting tests...${NC}"

    cd frontend || { echo -e "${RED}Failed to enter frontend directory${NC}"; return 1; }

    # Run type checking
    echo -e "${BLUE}[Frontend] Running type checking...${NC}"
    if npm run type-check; then
        echo -e "${GREEN}✓ Type checking passed${NC}"
    else
        echo -e "${RED}✗ Type checking failed${NC}"
        FAILED_TESTS+=("Frontend: Type checking")
    fi

    # Run linting
    echo -e "${BLUE}[Frontend] Running linting...${NC}"
    if npm run lint; then
        echo -e "${GREEN}✓ Linting passed${NC}"
    else
        echo -e "${RED}✗ Linting failed${NC}"
        FAILED_TESTS+=("Frontend: Linting")
    fi

    # Run tests with coverage
    echo -e "${BLUE}[Frontend] Running tests with coverage...${NC}"
    if npm run test:coverage; then
        echo -e "${GREEN}✓ Tests passed${NC}"
    else
        echo -e "${RED}✗ Tests failed${NC}"
        FAILED_TESTS+=("Frontend: Tests")
        cd - > /dev/null
        return 1
    fi

    cd - > /dev/null
    echo -e "${GREEN}[Frontend] All checks passed!${NC}"
}

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Run tests for each service
echo -e "\n${BLUE}Testing Python Services...${NC}"

# Weight Service (95% coverage)
run_service_tests "Weight Service" "weight-service" 95

# Billing Service (90% coverage)
run_service_tests "Billing Service" "billing-service" 90

# Shift Service (90% coverage)
if [ -d "shift-service" ]; then
    run_service_tests "Shift Service" "shift-service" 90
fi

# Frontend
echo -e "\n${BLUE}Testing Frontend...${NC}"
if [ -d "frontend" ]; then
    run_frontend_tests
fi

# Integration tests (if directory exists)
if [ -d "integration-tests" ]; then
    echo -e "\n${YELLOW}[Integration Tests] Starting...${NC}"

    # Check if services are running
    if ! curl -f http://localhost:5001/health > /dev/null 2>&1; then
        echo -e "${YELLOW}Services not running. Starting with docker-compose...${NC}"
        docker-compose up -d
        sleep 10
    fi

    if pytest integration-tests/ -v; then
        echo -e "${GREEN}✓ Integration tests passed${NC}"
    else
        echo -e "${RED}✗ Integration tests failed${NC}"
        FAILED_TESTS+=("Integration Tests")
    fi
fi

# Summary
echo -e "\n${BLUE}================================${NC}"
if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All Tests Passed!${NC}"
    echo -e "${BLUE}================================${NC}"
    exit 0
else
    echo -e "${RED}✗ Some Tests Failed:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}  - $test${NC}"
    done
    echo -e "${BLUE}================================${NC}"
    exit 1
fi
