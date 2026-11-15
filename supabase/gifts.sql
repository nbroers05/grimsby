-- Grimsby's world, WERELD.md step 3: leaving something (an item and/or a note) by the water.
-- Run once in the Supabase SQL editor of project "grimsby", after grimsby.sql. Safe to run again.
--
-- Anyone may read gifts and add one; only the brain (service key, bypasses RLS) sets seen, reply and taken.
-- No content filter (VOLGENDE.md block D). Only: lengths, and a rate limit against flooding, checked here in the
-- database so a browser cannot skip it. Who sent what (browser id, IP) is kept apart, as a hash, unreadable for
-- the site.

-- ---------- gifts ----------
create table if not exists public.gifts (
  id            bigint generated always as identity primary key,
  visitor_name  text not null check (char_length(btrim(visitor_name)) between 1 and 24),
  item          text check (item is null or char_length(item) between 1 and 40),
  note          text check (note is null or char_length(note) between 1 and 280),
  x             real not null check (x between -500 and 500),   -- island metres, x = east
  z             real not null check (z between -300 and 300),   -- z = south
  created_at    timestamptz not null default now(),
  seen          boolean not null default false,                 -- the brain picked it up
  reply         text,                                           -- his answer, if he gave one
  replied_at    timestamptz,
  taken         boolean not null default false,                 -- he took the item to his roof
  check (item is not null or note is not null)
);
create index if not exists gifts_created_idx on public.gifts (created_at desc);
create index if not exists gifts_unseen_idx on public.gifts (created_at) where not seen;

-- ---------- the rate limit: a private log, out of reach of the site ----------
create schema if not exists private;
revoke all on schema private from anon, authenticated;
create table if not exists private.gift_log (
  at      timestamptz not null default now(),
  client  text not null,          -- md5 of the browser's random id (header x-grimsby-client)
  ip      text not null           -- md5 of the address, salted
);
create index if not exists gift_log_at_idx on private.gift_log (at desc);

create or replace function public.gift_guard() returns trigger
language plpgsql security definer set search_path = public, private as $$
declare
  hdr     json := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  v_client text := md5('grimsby-client:' || coalesce(hdr->>'x-grimsby-client', ''));
  v_ip     text := md5('grimsby-ip:' || btrim(split_part(coalesce(hdr->>'x-forwarded-for', ''), ',', 1)));
  per_client int; per_ip int; per_all int;
begin
  if coalesce(auth.role(), '') = 'service_role' then
    return new;                                   -- the brain (it never inserts, but it may)
  end if;
  -- a visitor only ever adds a fresh, unanswered gift
  new.created_at := now(); new.seen := false; new.reply := null; new.replied_at := null; new.taken := false;
  new.visitor_name := btrim(new.visitor_name);
  new.item := nullif(btrim(coalesce(new.item, '')), '');
  new.note := nullif(btrim(coalesce(new.note, '')), '');
  if new.item is null and new.note is null then
    raise exception 'empty gift' using errcode = 'check_violation';
  end if;
  delete from private.gift_log where at < now() - interval '1 day';
  select count(*) filter (where client = v_client), count(*) filter (where ip = v_ip), count(*)
    into per_client, per_ip, per_all
    from private.gift_log where at > now() - interval '1 hour';
  if per_client >= 5 or per_ip >= 15 or per_all >= 150 then
    raise exception 'too many gifts, try again later' using errcode = 'P0001', hint = 'rate_limit';
  end if;
  insert into private.gift_log (client, ip) values (v_client, v_ip);
  return new;
end $$;

drop trigger if exists gift_guard on public.gifts;
create trigger gift_guard before insert on public.gifts for each row execute function public.gift_guard();

-- ---------- RLS ----------
alter table public.gifts enable row level security;
drop policy if exists "anyone reads" on public.gifts;
create policy "anyone reads" on public.gifts for select to anon, authenticated using (true);
drop policy if exists "anyone leaves something" on public.gifts;
create policy "anyone leaves something" on public.gifts for insert to anon, authenticated with check (true);
revoke update, delete, truncate on public.gifts from anon, authenticated;
grant select, insert on public.gifts to anon, authenticated;

-- ---------- Realtime: new gifts and his replies show up at once ----------
do $$ begin
  alter publication supabase_realtime add table public.gifts;
exception when duplicate_object then null; end $$;
