# Data Population Service

This service populates the Gan Shmuel Weight Management System with test data.

## Usage

### Option 1: Using Docker Profile (Recommended)

```bash
# Fast mode (default) - Quick data population
docker-compose --profile populate up populate-data

# Realistic mode - Simulates actual factory operations with timing
docker-compose --profile populate run populate-data --realistic

# Alternative with -r flag
docker-compose --profile populate run populate-data -r
```

### Option 2: One-time Run

```bash
# Fast mode
docker-compose run --rm populate-data

# Realistic mode
docker-compose run --rm populate-data --realistic
```

## Modes

- **Fast Mode** (`--fast` or default): Quick data population without delays
- **Realistic Mode** (`--realistic` or `-r`): Simulates actual factory operations with realistic timing delays

## What it populates

1. **Billing Data**: 
   - Providers and trucks
   - Rates via Excel file upload (rates.xlsx)
   - Fallback to hardcoded rates if Excel upload fails
2. **Shift Data**: Operators and active shifts  
3. **Container Weights**: Batch upload from weight-service/in/ directory files
4. **Weighing Sessions**: Complete IN/OUT truck weighing transactions

## Prerequisites

Make sure all services are running:
```bash
docker-compose up -d
```