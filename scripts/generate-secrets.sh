#!/bin/bash
# Secure Secrets Generator for Gan Shmuel System
# Generates cryptographically secure random credentials

set -e

echo "🔐 Generating secure credentials..."
echo ""

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Function to generate JWT secret (longer)
generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "=+/" | cut -c1-64
}

# Create new .env file with secure credentials
cat > .env.new << EOF
# ============================================
# GAN SHMUEL SECURE CREDENTIALS
# Generated: $(date)
# ============================================
# ⚠️ NEVER COMMIT THIS FILE TO GIT
# ⚠️ KEEP THIS FILE SECURE
# ============================================

# Database Root Password
MYSQL_ROOT_PASSWORD=$(generate_password)

# Weight Service Database
WEIGHT_DB_NAME=weight_db
WEIGHT_DB_USER=weight_user
WEIGHT_DB_PASSWORD=$(generate_password)

# Billing Service Database
BILLING_DB_NAME=billdb
BILLING_DB_USER=bill
BILLING_DB_PASSWORD=$(generate_password)

# Shift Service Database
SHIFT_DB_NAME=shift_db
SHIFT_DB_USER=shift_user
SHIFT_DB_PASSWORD=$(generate_password)

# Provider Registration Service Database
PROVIDER_DB_NAME=provider_registration
PROVIDER_DB_USER=provider_user
PROVIDER_DB_PASSWORD=$(generate_password)

# Redis Authentication
REDIS_PASSWORD=$(generate_password)

# JWT Secret Key (64 characters minimum)
JWT_SECRET_KEY=$(generate_jwt_secret)

# Grafana Admin Password
GRAFANA_ADMIN_PASSWORD=$(generate_password)

# Service URLs (internal Docker network)
WEIGHT_SERVICE_URL=http://weight-service:5001
BILLING_SERVICE_URL=http://billing-service:5002
SHIFT_SERVICE_URL=http://shift-service:5003

# Upload directories
UPLOAD_DIRECTORY=/in

# Redis URL (with authentication)
REDIS_URL=redis://:$(generate_password)@shift-redis:6379/0

# Environment
ENVIRONMENT=development
EOF

echo "✅ Secure credentials generated in: .env.new"
echo ""
echo "📋 Next steps:"
echo "   1. Review .env.new"
echo "   2. Backup current .env: cp .env .env.old"
echo "   3. Replace with new: mv .env.new .env"
echo "   4. Restart services: docker-compose down && docker-compose up -d"
echo ""
echo "⚠️  OLD CREDENTIALS ARE IN .env.old - DELETE AFTER VERIFICATION"
