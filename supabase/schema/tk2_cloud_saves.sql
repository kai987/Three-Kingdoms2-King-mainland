-- Dedicated game table only. Shared project Auth settings and other apps stay owned by those apps.
create table public.tk2_cloud_saves (
    user_id uuid not null default auth.uid(),
    slot smallint not null check (slot between 1 and 5),
    save_id uuid not null default pg_catalog.gen_random_uuid() unique,
    label text not null check (char_length(label) between 1 and 80 and label !~ '[[:cntrl:]]'),
    save_text text not null check (octet_length(save_text) between 1 and 2097024),
    revision bigint not null default 1 check (revision between 1 and 9007199254740991),
    scenario text not null,
    game_year integer not null,
    game_month smallint not null,
    game_turn bigint not null,
    save_sha256 text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (user_id, slot),
    constraint tk2_cloud_saves_user_id_fkey foreign key (user_id) references auth.users(id)
        on delete cascade deferrable initially immediate
);

create function public.tk2_validate_cloud_save() returns trigger
language plpgsql security invoker set search_path = '' as $function$
declare
    document jsonb;
begin
    if tg_op = 'UPDATE' then
        if new.user_id is distinct from old.user_id or new.slot is distinct from old.slot
           or new.save_id is distinct from old.save_id or new.created_at is distinct from old.created_at then
            raise exception using errcode = '22023', message = 'Cloud save identity is immutable';
        end if;
        if new.revision is distinct from old.revision + 1 then
            raise exception using errcode = 'PT409', message = 'Cloud save revision conflict';
        end if;
    else
        if new.revision <> 1 then
            raise exception using errcode = '22023', message = 'Initial revision must be one';
        end if;
        new.created_at := pg_catalog.clock_timestamp();
    end if;
    if pg_catalog.octet_length(new.save_text) not between 1 and 2097024 then
        raise exception using errcode = '22023', message = 'Invalid game save size';
    end if;
    begin
        document := new.save_text::jsonb;
    exception when invalid_text_representation then
        raise exception using errcode = '22023', message = 'Invalid game save JSON';
    end;
    if pg_catalog.jsonb_typeof(document) is distinct from 'object'
       or document->>'format' is distinct from 'three-kingdoms-remake-save'
       or (document->'version' is distinct from '1'::jsonb
           and document->'version' is distinct from '2'::jsonb)
       or pg_catalog.jsonb_typeof(document->'state') is distinct from 'object'
       or pg_catalog.jsonb_typeof(document->'scenario') is distinct from 'string'
       or coalesce(pg_catalog.char_length(document->>'scenario'), 0) not between 1 and 128
       or coalesce(document->>'catalog_sha256', '') !~ '^[0-9a-f]{64}$'
       or coalesce(document->>'checksum', '') !~ '^[0-9a-f]{64}$'
       or pg_catalog.jsonb_typeof(document#>'{state,year}') is distinct from 'number'
       or coalesce(document#>>'{state,year}', '') !~ '^[1-9][0-9]{0,3}$'
       or pg_catalog.jsonb_typeof(document#>'{state,month}') is distinct from 'number'
       or coalesce(document#>>'{state,month}', '') !~ '^([1-9]|1[0-2])$'
       or pg_catalog.jsonb_typeof(document#>'{state,turn}') is distinct from 'number'
       or coalesce(document#>>'{state,turn}', '') !~ '^[0-9]{1,10}$' then
        raise exception using errcode = '22023', message = 'Invalid game save envelope';
    end if;
    -- Extract metadata from a parsed copy, keeping the original text untouched.
    -- The game server separately validates its original gameplay checksum on load.
    new.label := pg_catalog.btrim(new.label);
    new.scenario := document->>'scenario';
    new.game_year := (document#>>'{state,year}')::integer;
    new.game_month := (document#>>'{state,month}')::smallint;
    new.game_turn := (document#>>'{state,turn}')::bigint;
    new.save_sha256 := pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(new.save_text, 'UTF8')), 'hex');
    new.updated_at := pg_catalog.clock_timestamp();
    return new;
end;
$function$;

revoke all on function public.tk2_validate_cloud_save() from public, anon, authenticated;
create trigger tk2_cloud_save_validation before insert or update on public.tk2_cloud_saves
for each row execute function public.tk2_validate_cloud_save();

alter table public.tk2_cloud_saves enable row level security;
alter table public.tk2_cloud_saves force row level security;
revoke all on table public.tk2_cloud_saves from public, anon, authenticated;
grant select, insert, update, delete on table public.tk2_cloud_saves to authenticated;
create policy tk2_cloud_select on public.tk2_cloud_saves for select to authenticated
    using ((select auth.uid()) = user_id);
create policy tk2_cloud_insert on public.tk2_cloud_saves for insert to authenticated
    with check ((select auth.uid()) = user_id);
create policy tk2_cloud_update on public.tk2_cloud_saves for update to authenticated
    using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy tk2_cloud_delete on public.tk2_cloud_saves for delete to authenticated
    using ((select auth.uid()) = user_id);

comment on table public.tk2_cloud_saves is 'Three Kingdoms II remake private account save slots; original JSON text and transport digest, owner RLS, save_id plus revision CAS.';
notify pgrst, 'reload schema';
