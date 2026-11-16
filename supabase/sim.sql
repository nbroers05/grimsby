-- Grimsby, site v2: the log of the simulation (tab "simulation" on index.html).
-- Run once in the Supabase SQL editor of project "grimsby". Safe to run again.
--
-- Every browser with the simulation open sends a batch of events at most every 5 minutes.
-- Visitors may only add, not read. You read it through the dashboard or the service key.
-- Limit against flooding: 20 batches per browser per hour, 600 in total per hour.

create table if not exists public.sim_log (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  client      text not null check (char_length(client) between 4 and 64),  -- random id per browser
  preset      text check (preset is null or char_length(preset) <= 16),
  sim_from    integer,                 -- simulated minute
  sim_to      integer,
  n           integer not null check (n between 1 and 400),
  events      jsonb not null check (octet_length(events::text) < 400000)
);
create index if not exists sim_log_created_idx on public.sim_log (created_at desc);
create index if not exists sim_log_client_idx on public.sim_log (client, created_at desc);

alter table public.sim_log enable row level security;
drop policy if exists "sim_log insert" on public.sim_log;
create policy "sim_log insert" on public.sim_log for insert to anon, authenticated with check (true);
-- no select policy: the site cannot read anything back

create or replace function public.sim_log_guard() returns trigger
language plpgsql security definer set search_path = public as $$
declare per_client int; per_all int;
begin
  if coalesce(auth.role(), '') = 'service_role' then return new; end if;
  new.created_at := now();
  select count(*) filter (where client = new.client), count(*)
    into per_client, per_all
    from public.sim_log where created_at > now() - interval '1 hour';
  if per_client >= 20 or per_all >= 600 then
    raise exception 'too many, wait a bit' using errcode = 'P0001';
  end if;
  return new;
end $$;

drop trigger if exists sim_log_guard on public.sim_log;
create trigger sim_log_guard before insert on public.sim_log
  for each row execute function public.sim_log_guard();
