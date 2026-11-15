-- Grimsby's world, WERELD.md step 4: whistling. Other visitors hear a whistle live (Realtime Broadcast, no table);
-- this table is only so the brain (plain Python, no websocket) can hear it too: it reads new rows every tick.
-- Run once in the Supabase SQL editor of project "grimsby", after gifts.sql (it reuses the private schema).
-- Safe to run again.

create table if not exists public.whistles (
  id   bigint generated always as identity primary key,
  x    real not null check (x between -500 and 500),
  z    real not null check (z between -300 and 300),
  at   timestamptz not null default now()
);
create index if not exists whistles_at_idx on public.whistles (at desc);

create table if not exists private.whistle_log (
  at      timestamptz not null default now(),
  client  text not null,
  ip      text not null
);
create index if not exists whistle_log_at_idx on private.whistle_log (at desc);

create or replace function public.whistle_guard() returns trigger
language plpgsql security definer set search_path = public, private as $$
declare
  hdr      json := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  v_client text := md5('grimsby-client:' || coalesce(hdr->>'x-grimsby-client', ''));
  v_ip     text := md5('grimsby-ip:' || btrim(split_part(coalesce(hdr->>'x-forwarded-for', ''), ',', 1)));
  per_client int; per_ip int; per_all int;
begin
  if coalesce(auth.role(), '') = 'service_role' then
    return new;
  end if;
  new.at := now();
  delete from private.whistle_log where at < now() - interval '1 hour';
  delete from public.whistles where at < now() - interval '1 day';
  select count(*) filter (where client = v_client), count(*) filter (where ip = v_ip), count(*)
    into per_client, per_ip, per_all
    from private.whistle_log;
  if per_client >= 10 or per_ip >= 30 or per_all >= 300 then
    raise exception 'too much whistling, try again later' using errcode = 'P0001', hint = 'rate_limit';
  end if;
  insert into private.whistle_log (client, ip) values (v_client, v_ip);
  return new;
end $$;

drop trigger if exists whistle_guard on public.whistles;
create trigger whistle_guard before insert on public.whistles for each row execute function public.whistle_guard();

alter table public.whistles enable row level security;
drop policy if exists "anyone reads" on public.whistles;
create policy "anyone reads" on public.whistles for select to anon, authenticated using (true);
drop policy if exists "anyone whistles" on public.whistles;
create policy "anyone whistles" on public.whistles for insert to anon, authenticated with check (true);
revoke update, delete, truncate on public.whistles from anon, authenticated;
grant select, insert on public.whistles to anon, authenticated;
