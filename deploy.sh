#!/usr/bin/env bash
set -euo pipefail

# Deploy oura.trollefsen.com
# Run on the VPS: ./deploy.sh

cd "$(dirname "$0")"

echo "Pulling latest code..."
git pull origin main

echo "Building and starting services..."
docker compose -f docker-compose.prod.yml --env-file .env.prod build
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

echo "Running database migrations..."
docker compose -f docker-compose.prod.yml --env-file .env.prod exec analytics uv run python -c "
import asyncio
from app.db import get_db

async def migrate():
    async with get_db() as conn:
        async with conn.cursor() as cur:
            # Check if migrations table exists
            await cur.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS _migrations (
                    name TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            \"\"\")

            import os
            migration_dir = 'migrations'
            if not os.path.isdir(migration_dir):
                print('No migrations directory found')
                return

            files = sorted(f for f in os.listdir(migration_dir) if f.endswith('.sql'))
            for f in files:
                await cur.execute('SELECT 1 FROM _migrations WHERE name = %s', (f,))
                if await cur.fetchone():
                    print(f'  skip {f} (already applied)')
                    continue
                print(f'  applying {f}...')
                with open(os.path.join(migration_dir, f)) as fh:
                    await cur.execute(fh.read())
                await cur.execute('INSERT INTO _migrations (name) VALUES (%s)', (f,))
                print(f'  done {f}')

asyncio.run(migrate())
"

echo ""
echo "Deployed! Check https://oura.trollefsen.com"
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
