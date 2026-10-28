-- Run with an authorized database connection. No Auth users or emails created.
-- The FK is deferred only inside this rollback transaction; real commits still
-- require a valid Auth user. Assertions execute as authenticated/anon, NOT postgres.
begin;
set constraints public.tk2_cloud_saves_user_id_fkey deferred;
select set_config('tk2.qa_a', gen_random_uuid()::text, true);
select set_config('tk2.qa_b', gen_random_uuid()::text, true);
select set_config('tk2.qa_raw', '{"format":"three-kingdoms-remake-save","version":1,"catalog_sha256":"0000000000000000000000000000000000000000000000000000000000000000","scenario":"qa-rollback-only","state":{"year":217,"month":7,"turn":1,"distance":315.0,"zero":-0.0},"checksum":"1111111111111111111111111111111111111111111111111111111111111111"}', true);
set local role authenticated;
select set_config('request.jwt.claims', json_build_object('sub', current_setting('tk2.qa_a'), 'role', 'authenticated')::text, true);
do $qa$
declare r public.tk2_cloud_saves; n integer;
begin
    if current_user <> 'authenticated' then raise exception 'RLS test role missing'; end if;
    insert into public.tk2_cloud_saves (slot, label, save_text) values (1, 'QA original', current_setting('tk2.qa_raw')) returning * into r;
    perform set_config('tk2.qa_old_id', r.save_id::text, true);
    if r.user_id::text <> current_setting('tk2.qa_a') or r.revision <> 1
       or r.save_text <> current_setting('tk2.qa_raw')
       or r.save_sha256 <> encode(sha256(convert_to(r.save_text, 'UTF8')), 'hex')
       or r.scenario <> 'qa-rollback-only' or r.game_month <> 7 then
        raise exception 'Raw text or derived metadata mismatch';
    end if;
    -- New format must keep fractional values and raw original bytes as well.
    perform set_config('tk2.qa_raw_v2', replace(current_setting('tk2.qa_raw'), '"version":1', '"version":2'), true);
    insert into public.tk2_cloud_saves (slot,label,save_text)
        values (3,'QA save format 2',current_setting('tk2.qa_raw_v2')) returning * into r;
    if r.save_text <> current_setting('tk2.qa_raw_v2')
       or r.save_sha256 <> encode(sha256(convert_to(r.save_text, 'UTF8')), 'hex')
       or r.game_year <> 217 or r.game_month <> 7 or r.game_turn <> 1 then
        raise exception 'Format 2 raw text or metadata mismatch';
    end if;
    begin
        insert into public.tk2_cloud_saves (slot,label,save_text)
            values (4,'unknown format',replace(current_setting('tk2.qa_raw'), '"version":1', '"version":999'));
        raise exception 'Unknown save format accepted';
    exception when invalid_parameter_value then null; end;
    begin
        insert into public.tk2_cloud_saves (slot,label,save_text)
            values (4,'string format',replace(current_setting('tk2.qa_raw'), '"version":1', '"version":"2"'));
        raise exception 'String save version accepted';
    exception when invalid_parameter_value then null; end;
    update public.tk2_cloud_saves set label='QA revision 2', revision=2
        where slot=1 and revision=1 and save_id=current_setting('tk2.qa_old_id')::uuid;
    get diagnostics n = row_count;
    if n <> 1 then raise exception 'Valid CAS update failed'; end if;
    update public.tk2_cloud_saves set label='stale', revision=2 where slot=1 and revision=1 and save_id=current_setting('tk2.qa_old_id')::uuid;
    get diagnostics n = row_count;
    if n <> 0 then raise exception 'Stale CAS matched'; end if;
    begin
        update public.tk2_cloud_saves set revision=4 where slot=1;
        raise exception 'Revision jump accepted';
    exception when sqlstate 'PT409' then null; end;
    begin
        update public.tk2_cloud_saves set save_id=gen_random_uuid(), revision=3 where slot=1;
        raise exception 'Identity mutation accepted';
    exception when invalid_parameter_value then null; end;
    begin
        update public.tk2_cloud_saves set created_at=created_at - interval '1 day', revision=3 where slot=1;
        raise exception 'Created timestamp mutation accepted';
    exception when invalid_parameter_value then null; end;
    begin
        update public.tk2_cloud_saves set user_id=current_setting('tk2.qa_b')::uuid, revision=3 where slot=1;
        raise exception 'Owner mutation accepted';
    exception when invalid_parameter_value then null; end;
    begin
        insert into public.tk2_cloud_saves (slot,label,save_text) values (2,'bad','{}');
        raise exception 'Malformed envelope accepted';
    exception when invalid_parameter_value then null; end;
end;
$qa$;
select set_config('request.jwt.claims', json_build_object('sub', current_setting('tk2.qa_b'), 'role', 'authenticated')::text, true);
do $qa$
declare n integer;
begin
    select count(*) into n from public.tk2_cloud_saves where user_id=current_setting('tk2.qa_a')::uuid;
    if n <> 0 then raise exception 'Other owner visible'; end if;
    update public.tk2_cloud_saves set label='intruder', revision=3 where user_id=current_setting('tk2.qa_a')::uuid;
    get diagnostics n = row_count;
    if n <> 0 then raise exception 'Other owner mutable'; end if;
    delete from public.tk2_cloud_saves where user_id=current_setting('tk2.qa_a')::uuid;
    get diagnostics n = row_count;
    if n <> 0 then raise exception 'Other owner deletable'; end if;
    begin
        insert into public.tk2_cloud_saves (user_id,slot,label,save_text) values (current_setting('tk2.qa_a')::uuid,2,'foreign',current_setting('tk2.qa_raw'));
        raise exception 'Foreign owner insert accepted';
    exception when insufficient_privilege then null; end;
    insert into public.tk2_cloud_saves (slot,label,save_text) values (1,'QA B',current_setting('tk2.qa_raw'));
end;
$qa$;
select set_config('request.jwt.claims', json_build_object('sub', current_setting('tk2.qa_a'), 'role', 'authenticated')::text, true);
do $qa$
declare new_id uuid; n integer;
begin
    delete from public.tk2_cloud_saves where slot=1 and save_id=current_setting('tk2.qa_old_id')::uuid and revision=2;
    insert into public.tk2_cloud_saves (slot,label,save_text) values (1,'QA recreated',current_setting('tk2.qa_raw')) returning save_id into new_id;
    if new_id=current_setting('tk2.qa_old_id')::uuid then raise exception 'Recreated save has old identity'; end if;
    update public.tk2_cloud_saves set label='stale incarnation',revision=2 where slot=1 and revision=1 and save_id=current_setting('tk2.qa_old_id')::uuid;
    get diagnostics n = row_count;
    if n <> 0 then raise exception 'ABA stale update matched'; end if;
    delete from public.tk2_cloud_saves where slot=1 and revision=1 and save_id=current_setting('tk2.qa_old_id')::uuid;
    get diagnostics n = row_count;
    if n <> 0 then raise exception 'ABA stale delete matched'; end if;
end;
$qa$;
reset role;
set local role anon;
do $qa$
begin
    begin
        perform count(*) from public.tk2_cloud_saves;
        raise exception 'Anonymous read accepted';
    exception when insufficient_privilege then null; end;
end;
$qa$;
reset role;
rollback;
select 'RLS, save formats 1/2, raw text, metadata, CAS and ABA assertions passed; rolled back' as result;
