# Deploying Oura Lab to oura.trollefsen.com

Production deployment guide for a Hostinger VPS running Docker with Caddy as a reverse proxy.

## Architecture

```
Internet
  |
  v
Caddy (:80/:443, automatic HTTPS via Let's Encrypt)
  |
  ├── /api/analytics/*  -->  analytics:8001 (FastAPI, prefix stripped)
  |
  └── /*                -->  web:3000      (Next.js)
                               |
                               └── /api/oura/* --> analytics:8001
                                    (server-side only, via ANALYTICS_BASE_URL)
```

All services run in Docker containers on an internal network. Only Caddy is exposed to the internet on ports 80 and 443.

### Assumptions

- **Domain**: `oura.trollefsen.com` is hardcoded in `docker-compose.prod.yml`, `Caddyfile`, and several environment variables. If you want a different domain, search-and-replace all occurrences.
- **Single user**: The app stores one set of Oura OAuth tokens. There are no user accounts or multi-tenancy.
- **VPS OS**: Ubuntu/Debian-based. Commands below use `apt`. Adjust for other distros.
- **VPS resources**: Minimum 1 GB RAM, 1 vCPU. The app is lightweight but the Docker build step needs ~1 GB free RAM.
- **Ports 80 and 443**: Must be open and not used by another web server (Apache, nginx, etc.). Caddy needs both for HTTPS certificate issuance.

---

## Prerequisites

### 1. DNS

Add an **A record** pointing `oura.trollefsen.com` to your VPS IP address.

```
Type: A
Name: oura
Value: <VPS_IP_ADDRESS>
TTL: 300
```

> Caddy will fail to obtain a TLS certificate if DNS hasn't propagated yet. You can verify with `dig oura.trollefsen.com` or `nslookup oura.trollefsen.com`.

### 2. VPS software

SSH into your VPS and install Docker (if not already installed):

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add your user to the docker group (log out and back in after)
sudo usermod -aG docker $USER

# Verify
docker --version
docker compose version
```

> **Assumption**: Docker Compose V2 is included with modern Docker installs (the `docker compose` subcommand, not the standalone `docker-compose` binary). The deploy script uses `docker compose` (no hyphen).

### 3. Oura OAuth application

Go to [cloud.ouraring.com/oauth/applications](https://cloud.ouraring.com/oauth/applications) and either create a new application or update your existing one:

- **Redirect URI**: `https://oura.trollefsen.com/api/oura/callback`
- Note your **Client ID** and **Client Secret**

> **Important**: The redirect URI must match exactly. The analytics service uses this value when initiating the OAuth flow, and Oura will reject mismatches.

### 4. Firewall

Ensure ports 80 (HTTP) and 443 (HTTPS) are open:

```bash
# If using ufw
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status
```

> **Assumption**: No other process is listening on ports 80 or 443. If you have Apache or nginx running, stop and disable them first (`sudo systemctl disable --now apache2 nginx`), or adapt the setup to use Caddy on different ports.

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/da-troll/oura-dash.git /opt/oura
cd /opt/oura
```

> You can use any directory. `/opt/oura` is used throughout this guide.

### 2. Create the environment file

```bash
cp .env.prod.example .env.prod
```

Edit `.env.prod` with your real values:

```bash
nano .env.prod
```

```ini
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<GENERATE_A_STRONG_PASSWORD>
POSTGRES_DB=oura

# Oura OAuth (from step 3 above)
OURA_CLIENT_ID=<YOUR_CLIENT_ID>
OURA_CLIENT_SECRET=<YOUR_CLIENT_SECRET>
```

Generate a secure password:

```bash
openssl rand -base64 32
```

> **Security note**: `.env.prod` is in `.gitignore` and will not be committed. Keep it only on the server. Do not share it.

### 3. Deploy

```bash
./deploy.sh
```

This script will:

1. Pull the latest code from `origin/main`
2. Build Docker images for the analytics and web services
3. Start all containers (Caddy, Postgres, analytics, web)
4. Run any pending SQL migrations against the database

The first build takes a few minutes. Subsequent deploys are faster due to Docker layer caching.

### 4. Verify

```bash
# Check all containers are running
docker compose -f docker-compose.prod.yml --env-file .env.prod ps

# Check Caddy obtained a TLS certificate
docker compose -f docker-compose.prod.yml --env-file .env.prod logs caddy | tail -20

# Test the health endpoint
curl https://oura.trollefsen.com/api/analytics/health
# Should return: {"ok":true}
```

Open `https://oura.trollefsen.com` in your browser. You should see the dashboard.

---

## Initial data setup

After the first deploy, the database is empty. You need to:

1. **Connect your Oura account**: Go to `https://oura.trollefsen.com/settings` and click the connect button. This initiates OAuth and stores your tokens.

2. **Ingest data**: On the same settings page, set a date range and trigger a sync. This fetches data from the Oura API and populates the database.

3. **Compute features**: After ingestion, trigger the feature engineering pipeline from the settings page. This creates rolling averages, deltas, and other derived metrics.

---

## Redeployment

To deploy new changes after pushing to `main`:

```bash
cd /opt/oura
./deploy.sh
```

The script pulls, rebuilds, restarts, and migrates.

For zero-downtime redeployment (containers restart one at a time):

```bash
cd /opt/oura
git pull origin main
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --remove-orphans
```

---

## Useful commands

```bash
# View logs for a specific service
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f analytics
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f web
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f caddy
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f db

# Restart a single service
docker compose -f docker-compose.prod.yml --env-file .env.prod restart analytics

# Stop everything
docker compose -f docker-compose.prod.yml --env-file .env.prod down

# Stop everything AND delete the database volume (destructive!)
docker compose -f docker-compose.prod.yml --env-file .env.prod down -v

# Open a psql shell
docker compose -f docker-compose.prod.yml --env-file .env.prod exec db \
  psql -U postgres -d oura

# Run a one-off Python command in the analytics container
docker compose -f docker-compose.prod.yml --env-file .env.prod exec analytics \
  uv run python -c "print('hello')"
```

---

## How it works

### Request routing

| Request path | Handled by | Notes |
|---|---|---|
| `https://oura.trollefsen.com/` | Next.js (web) | Dashboard and all page routes |
| `https://oura.trollefsen.com/api/oura/auth` | Next.js (web) | Server-side OAuth initiation |
| `https://oura.trollefsen.com/api/oura/callback` | Next.js (web) | OAuth callback, exchanges code via analytics |
| `https://oura.trollefsen.com/api/analytics/*` | Caddy -> FastAPI | Browser API calls, prefix stripped by Caddy |

### Environment variables

| Variable | Set in | Used by | Purpose |
|---|---|---|---|
| `POSTGRES_PASSWORD` | `.env.prod` | db, analytics | Database authentication |
| `OURA_CLIENT_ID` | `.env.prod` | analytics, web | OAuth client identification |
| `OURA_CLIENT_SECRET` | `.env.prod` | analytics | OAuth token exchange (server-side only) |
| `DATABASE_URL` | compose | analytics | Postgres connection string (constructed from POSTGRES_* vars) |
| `OURA_REDIRECT_URI` | compose | analytics, web | OAuth callback URL (hardcoded to production domain) |
| `CORS_ORIGINS` | compose | analytics | Allowed browser origins for API calls |
| `ANALYTICS_BASE_URL` | compose | web (server-side) | Internal URL for Next.js -> FastAPI calls |
| `NEXT_PUBLIC_ANALYTICS_URL` | compose (build arg) | web (client-side) | Baked into JS at build time; set to `/api/analytics` |
| `NEXT_PUBLIC_BASE_URL` | compose | web | Used for OAuth redirect URLs |

### Database migrations

Migrations live in `services/analytics/migrations/` as numbered `.sql` files. The `deploy.sh` script tracks applied migrations in a `_migrations` table and runs any new ones in alphabetical order.

> **Inference**: The migration runner was created as part of this deployment setup. It is simple and sequential. There is no rollback mechanism. If a migration fails, fix the SQL and re-run `deploy.sh` (it will retry the failed migration).

### TLS certificates

Caddy obtains and renews Let's Encrypt certificates automatically. Certificate data is persisted in the `caddy_data` Docker volume. No manual certificate management is needed.

> **Assumption**: The VPS can reach Let's Encrypt's ACME servers on port 443, and port 80 is open for the HTTP-01 challenge.

---

## Troubleshooting

### Caddy fails to start / no HTTPS

- Check DNS is pointing to the VPS: `dig oura.trollefsen.com`
- Check ports 80/443 are open: `sudo ss -tlnp | grep -E ':80|:443'`
- Check Caddy logs: `docker compose -f docker-compose.prod.yml --env-file .env.prod logs caddy`
- If another service is on port 80/443, stop it first

### "Failed to fetch" errors in the browser

- Check the analytics service is running: `curl http://localhost:8001/health` from the VPS
- Check Caddy is proxying correctly: `curl https://oura.trollefsen.com/api/analytics/health`
- Check analytics logs for Python errors: `docker compose -f docker-compose.prod.yml --env-file .env.prod logs analytics`

### OAuth callback fails

- Verify the redirect URI in your Oura developer app matches exactly: `https://oura.trollefsen.com/api/oura/callback`
- Check the `OURA_CLIENT_ID` and `OURA_CLIENT_SECRET` in `.env.prod` are correct
- Check web logs: `docker compose -f docker-compose.prod.yml --env-file .env.prod logs web`

### Database connection errors

- Check the db container is healthy: `docker compose -f docker-compose.prod.yml --env-file .env.prod ps`
- Verify `POSTGRES_PASSWORD` in `.env.prod` matches what was used when the volume was first created. If you change the password after the volume exists, you need to either drop the volume (`down -v`, destructive) or change the password inside Postgres manually.

### Build fails with out-of-memory

- The Next.js build can use significant memory. If your VPS has <1 GB RAM, add swap:
  ```bash
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```

---

## Changing the domain

If you want to deploy to a different domain, update these files:

1. `Caddyfile` - the site address on line 1
2. `docker-compose.prod.yml` - all occurrences of `oura.trollefsen.com` (OURA_REDIRECT_URI, CORS_ORIGINS, NEXT_PUBLIC_BASE_URL)

Then rebuild and redeploy:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Also update the redirect URI in your Oura OAuth application settings.
