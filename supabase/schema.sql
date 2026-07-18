-- Apply this file via the Supabase dashboard SQL editor (Project ->
-- SQL Editor -> New query -> paste -> Run), on a fresh Supabase project.
--
-- Before running, replace REPLACE_WITH_YOUR_SHARED_SECRET below (two
-- occurrences) with a long random string of your choosing. This is baked
-- directly into the policy rather than set via `alter database ... set`,
-- because Supabase's hosted Postgres does not grant even the `postgres`
-- role permission to set custom database-level parameters.
--
-- To rotate the secret later, re-run just the `create policy` statement
-- below (after `drop policy "shared secret full access" on watchlist;`)
-- with a new value.

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
-- secret passed as a custom request header, checked against a literal
-- value baked into this policy.
create policy "shared secret full access"
  on watchlist
  for all
  using (
    current_setting('request.headers', true)::json ->> 'x-watchlist-secret'
      = 'REPLACE_WITH_YOUR_SHARED_SECRET'
  )
  with check (
    current_setting('request.headers', true)::json ->> 'x-watchlist-secret'
      = 'REPLACE_WITH_YOUR_SHARED_SECRET'
  );
