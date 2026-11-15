-- Grimsby's live world (WERELD.md step 2). Run once in the Supabase SQL editor of project "grimsby".
-- Everyone may read; only the brain (service key, bypasses RLS) may write. Safe to run again.

-- ---------- bird_state: always exactly one row ----------
create table if not exists public.bird_state (
  id         smallint primary key default 1 check (id = 1),
  now        jsonb not null default '{}'::jsonb,   -- data/now.json as is
  x          real,                                 -- where he is now (world metres, x = east)
  z          real,                                 -- (z = south)
  target_x   real,                                 -- where he is heading (= x, z when he is not travelling)
  target_z   real,
  target_id  text,                                 -- place id from world/places.json
  at         timestamptz not null default now()    -- time of the tick; old = laptop off = he sleeps
);

-- ---------- feed: one row per entry, like data/feed.json ----------
create table if not exists public.feed (
  id      bigint generated always as identity primary key,
  at      timestamptz not null,
  kind    text not null,                           -- did | noticed | felt | mind
  text    text not null,
  why     text,
  ok      boolean,
  action  text,
  extra   jsonb not null default '{}'::jsonb,      -- any other fields of the entry
  unique (at, kind, text)                          -- the brain upserts; no doubles
);
create index if not exists feed_at_idx on public.feed (at desc);

-- ---------- RLS: read for everyone, write only for service_role ----------
alter table public.bird_state enable row level security;
alter table public.feed       enable row level security;

drop policy if exists "anyone reads" on public.bird_state;
create policy "anyone reads" on public.bird_state for select to anon, authenticated using (true);
drop policy if exists "anyone reads" on public.feed;
create policy "anyone reads" on public.feed for select to anon, authenticated using (true);
-- no insert/update/delete policies: anon and authenticated cannot write. Belt and braces:
revoke insert, update, delete, truncate on public.bird_state, public.feed from anon, authenticated;
grant select on public.bird_state, public.feed to anon, authenticated;

-- ---------- Realtime ----------
do $$ begin
  alter publication supabase_realtime add table public.bird_state;
exception when duplicate_object then null; end $$;
do $$ begin
  alter publication supabase_realtime add table public.feed;
exception when duplicate_object then null; end $$;
