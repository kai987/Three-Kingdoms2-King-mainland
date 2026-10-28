-- Accept current command-book saves and existing version 1 saves.
-- Preserve raw bytes, owner isolation, revision CAS, function permissions and all saved rows.
create or replace function public.tk2_validate_cloud_save() returns trigger
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
