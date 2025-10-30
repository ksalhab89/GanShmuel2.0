# Setup Scripts

Utility scripts for local development setup.

---

## Available Scripts

### 1. `generate-secrets.sh`
Generates cryptographically secure credentials for all services.

```bash
bash scripts/generate-secrets.sh
```

**Output**: `.env.new` file with strong passwords

**Usage:**
```bash
# Generate new credentials
bash scripts/generate-secrets.sh

# Review the generated file
cat .env.new

# If you want to use them, backup current .env and replace
cp .env .env.backup
mv .env.new .env

# Restart services to use new credentials
docker-compose down
docker-compose up -d
```

---

### 2. `generate-traefik-auth.sh`
Generates Traefik dashboard authentication credentials.

```bash
bash scripts/generate-traefik-auth.sh
```

**Output**: `infrastructure/gateway/.htpasswd`

**Usage:**
```bash
# Generate dashboard password
bash scripts/generate-traefik-auth.sh

# Restart Traefik to apply
docker-compose restart traefik
```

**Demo Credentials (Already Configured):**
- **URL**: http://localhost:9999/dashboard/
- **Username**: `admin`
- **Password**: `Ma3fiVksYL8yq+bsYA+oX2UWm7ea4cLp`

---

## Script Permissions

All bash scripts need execute permission:

```bash
chmod +x scripts/*.sh
```

---

## Troubleshooting

If scripts fail, check:

1. **Docker is running**: `docker ps`
2. **You're in project root**: `pwd` should show `gan-shmuel-2`
3. **Scripts are executable**: `ls -la scripts/`
4. **.env file exists**: `ls -la .env`

---

## Demo Setup

For a fresh demo environment:

```bash
# 1. Generate fresh credentials (optional)
bash scripts/generate-secrets.sh

# 2. Start all services
docker-compose up -d

# 3. Wait for services to be healthy (30 seconds)
sleep 30

# 4. Check status
docker-compose ps

# 5. Access the system
# Frontend: http://localhost/
# Traefik: http://localhost:9999/dashboard/
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
```
