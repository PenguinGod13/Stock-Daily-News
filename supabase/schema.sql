-- Apply this file via the Supabase dashboard SQL editor (Project ->
-- SQL Editor -> New query -> paste -> Run), on a fresh Supabase project.
-- After applying, set the shared secret used by the RLS policy below:
--   alter database postgres set app.watchlist_shared_secret = '<your-secret>';
-- Then reload the config: select pg_reload_conf();

create table if not exists watchlist (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  owned boolean not null default false,
  shares numeric,
  cost_basis numeric,
  notes text,
  created_at timestamptz not null default now()
);

alter table watchlist enable row level security;

-- The scanner script reads using the Supabase service role key, which
-- bypasses RLS entirely, so no explicit service-role policy is required.

-- The public web form uses the anon key. Access is gated by a shared
-- secret passed as a custom request header, checked here via a Postgres
-- setting configured per-request through PostgREST's `request.headers`.
create policy "shared secret full access"
  on watchlist
  for all
  using (
    current_setting('request.headers', true)::json ->> 'x-watchlist-secret'
      = current_setting('app.watchlist_shared_secret', true)
  )
  with check (
    current_setting('request.headers', true)::json ->> 'x-watchlist-secret'
      = current_setting('app.watchlist_shared_secret', true)
  );
