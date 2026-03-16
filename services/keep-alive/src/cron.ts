import cron from 'node-cron';

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('Missing required env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY');
  process.exit(1);
}

async function pingSupabase() {
  console.log(`[${new Date().toISOString()}] Pinging Supabase keep-alive...`);
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/`, {
      method: 'GET',
      headers: {
        apikey: SUPABASE_SERVICE_ROLE_KEY!,
        Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY!}`,
      },
    });

    if (!res.ok) {
      console.error('Supabase ping failed:', res.status, await res.text());
    } else {
      console.log('Supabase ping OK');
    }
  } catch (err) {
    console.error('Error pinging Supabase:', err);
  }
}

// Run every 6 hours
cron.schedule('0 */6 * * *', pingSupabase);

// Ping once on startup to verify connectivity
pingSupabase();

console.log('Supabase keep-alive cron service started (every 6 hours).');

// Keep process alive
setInterval(() => {}, 1 << 30);
