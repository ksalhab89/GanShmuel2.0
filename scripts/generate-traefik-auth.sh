#!/bin/bash
# Generate Traefik Dashboard Authentication

set -e

echo "🔐 Generating Traefik Dashboard Credentials..."
echo ""

# Prompt for username
read -p "Enter admin username [admin]: " USERNAME
USERNAME=${USERNAME:-admin}

# Prompt for password
read -sp "Enter admin password: " PASSWORD
echo ""

if [ -z "$PASSWORD" ]; then
    echo "❌ Password cannot be empty!"
    exit 1
fi

# Generate htpasswd hash using openssl
# Format: username:hash
HASHED=$(openssl passwd -apr1 "$PASSWORD")
AUTH_STRING="$USERNAME:$HASHED"

# Save to file
mkdir -p infrastructure/gateway
echo "$AUTH_STRING" > infrastructure/gateway/.htpasswd

echo ""
echo "✅ Authentication file created: infrastructure/gateway/.htpasswd"
echo "   Username: $USERNAME"
echo "   Password hash saved securely"
echo ""
echo "⚠️  Add to traefik.yml under middlewares:"
echo "    http:"
echo "      middlewares:"
echo "        dashboard-auth:"
echo "          basicAuth:"
echo "            usersFile: /etc/traefik/.htpasswd"
