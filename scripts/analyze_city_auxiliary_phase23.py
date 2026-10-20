#!/usr/bin/env python3
"""Phase23: must scalar-cell relations and complete trusted caller/producer groups.

All older modules are imported read-only; temporary class hooks modify only
this Python process. No old producer/main or recovered game source is run.
"""
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase23/fields-static'
SPEC=importlib.util.spec_from_file_location('frozen_phase22_fields',ROOT/'scripts/analyze_city_auxiliary_phase22.py')
old=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=old;SPEC.loader.exec_module(old)
context=old.old.old;base=old.base
OLD_AUDIT='ca94229cff060e16b25f8f3e92eb752a94121af730ae70d114ce4ddf3a6d8eb8'
OLD_ZIP='9fd37c2ae0d7d857c787801e8bdc92ca43fb038099491f7dbe09f17b204cef80'
DISJOINT=old.DISJOINT
INPUTS=list(dict.fromkeys(old.INPUTS+['scripts/analyze_city_auxiliary_phase22.py','analysis/phase22/verification.json',
 'analysis/phase22/fields-static/all-indirect-accesses.json','analysis/phase22/fields-static/analysis-summary.json',
 'analysis/phase22/fields-static/verification.json','analysis/phase22/fields-static/raw345-executability-ledger.json',
 'analysis/phase22/fields-static/logical-vs-dummy-bus-contracts.json']))
OriginalState=context.ContextState;original_join=base.join;original_kill=base.kill


@dataclass
class ScalarState(OriginalState):
    scalar_cells:dict=field(default_factory=dict)
    cell_refs:tuple=(None,None,None)

    def copy(self):
        return ScalarState(dict(self.pairs),self.registers,dict(self.pending),self.stack,self.builders,
          self.numbers,self.number_stack,dict(self.scalar_cells),self.cell_refs)


def finite(values):
    return frozenset(values)if values is not None and len(values)<=32 else None


def scalar_join(left,right):
    result=original_join(left,right)
    result.scalar_cells={key:finite(left.scalar_cells[key]|right.scalar_cells[key])for key in left.scalar_cells.keys()&right.scalar_cells.keys()}
    result.scalar_cells={key:value for key,value in result.scalar_cells.items()if value is not None}
    result.cell_refs=tuple(a if a==b and a in result.scalar_cells else None for a,b in zip(left.cell_refs,right.cell_refs))
    return result


def scalar_kill(state,written):
    written=set(written);original_kill(state,written)
    if isinstance(state,ScalarState):
        for address in written:state.scalar_cells.pop(address,None)
        state.cell_refs=tuple(None if ref in written else ref for ref in state.cell_refs)


# All existing State()/copy()/join() users retain the new domain. These are
# process-local hooks; no frozen files or outputs are changed.
context.ContextState=ScalarState;base.State=ScalarState;base.join=scalar_join;base.kill=scalar_kill


def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


class Analysis(old.Analysis):
    def __init__(self,rom):
        super().__init__(rom);self.scalar_cell_loads=set();self.scalar_branch_filters=set();self.NZ_branch_filters=set()

    def load_cells(self,row,state):
        mode,operand=row['mode'],row['operand']
        if mode in('zp','ab'):addresses=[operand]
        elif mode in('zpx','zpy','abx','aby'):
            index=state.numbers[1 if mode.endswith('x')else 2]
            if index is None:return None,None
            addresses=[(operand+i)&(255 if mode.startswith('zp')else 65535)for i in index]
        else:return None,None
        addresses={base.normalized_ram(address)for address in addresses}
        if None in addresses or not all(address<256 and address in state.scalar_cells for address in addresses):return None,None
        values=finite(frozenset(v for address in addresses for v in state.scalar_cells[address]))
        return values,next(iter(addresses))if len(addresses)==1 and values is not None else None

    def must_scalar_store_target(self,key,state):
        """A singleton MAY-ZP projection is not a MUST physical write.

        E.g. STA00FF,X may write00FF or0101: its ZP projection has one
        address but cannot create a must fact. Check the complete EA domain.
        """
        row=self.known[key];mode,operand=row['mode'],row['operand']
        if mode in('zp','ab'):addresses=(operand,)
        elif mode in('zpx','zpy','abx','aby'):
            values=state.numbers[1 if mode.endswith('x')else 2]
            values=self.indices(key)if values is None else values
            addresses=((operand+v)&(255 if mode.startswith('zp')else 65535)for v in values)
        elif mode in('iy','ix'):
            addresses=self.indirect_addresses(key,state)
            if addresses is None:return None
        else:return None
        normalized={base.normalized_ram(address)for address in addresses}
        if len(normalized)!=1:return None
        address=next(iter(normalized))
        return address if address is not None and address<256 else None

    def transfer(self,key,state):
        result=super().transfer(key,state);row=self.known[key];op,mode=row['op'],row['mode']
        refs=list(result.cell_refs)
        if op in('LDA','LDX','LDY'):
            index=('LDA','LDX','LDY').index(op);refs[index]=None
            values,address=self.load_cells(row,state)
            if values is not None:
                numbers=list(result.numbers);numbers[index]=finite(values if numbers[index]is None else values&numbers[index]);result.numbers=tuple(numbers)
                refs[index]=address;self.scalar_cell_loads.add(key)
        elif op in('TAX','TAY','TXA','TYA'):
            source,destination={'TAX':(0,1),'TAY':(0,2),'TXA':(1,0),'TYA':(2,0)}[op]
            refs[destination]=state.cell_refs[source]if state.cell_refs[source]in result.scalar_cells else None
        elif op in('INX','DEX','TSX'):refs[1]=None
        elif op in('INY','DEY'):refs[2]=None
        elif op in('ADC','SBC','AND','ORA','EOR','PLA')or op in('ASL','LSR','ROL','ROR')and mode=='a':refs[0]=None
        result.cell_refs=tuple(refs)
        if op in base.WRITES and mode!='a':
            written,_=self.store_effect(key,state)
            # RMW needs the old memory value, before the real store kills it.
            values=None
            address=self.must_scalar_store_target(key,state)
            if address is not None:
                if op in('STA','STX','STY'):values=state.numbers[('STA','STX','STY').index(op)]
                elif address in state.scalar_cells:
                    before=state.scalar_cells[address]
                    if op=='INC':values=finite({(v+1)&255 for v in before})
                    elif op=='DEC':values=finite({(v-1)&255 for v in before})
                    elif op=='ASL':values=finite({v*2&255 for v in before})
                    elif op=='LSR':values=finite({v>>1 for v in before})
                    elif op=='ROL':values=finite({(v*2+c)&255 for v in before for c in(0,1)})
                    elif op=='ROR':values=finite({(v>>1)|(c<<7)for v in before for c in(0,1)})
            scalar_kill(result,written)
            if address is not None and values is not None:
                result.scalar_cells[address]=finite(values)
                if op in('STA','STX','STY'):
                    refs=list(result.cell_refs);refs[('STA','STX','STY').index(op)]=address;result.cell_refs=tuple(refs)
        return result

    def apply_call(self,state,target,key,far=False):
        result=super().apply_call(state,target,key,far)
        descriptor=self.factories.get(target);effect=self.effects.get(target)
        changed=set(descriptor['regs']if descriptor else effect['register_may_write']if effect else('A','X','Y'))
        preserved=set(self.passthrough.get(target,()))
        refs=list(result.cell_refs)
        for i,name in enumerate(('A','X','Y')):
            if name in changed and name not in preserved or far and name in('A','Y'):refs[i]=None
        result.cell_refs=tuple(refs)
        return result

    def branch_successors(self,key,state):
        successors=super().branch_successors(key,state)
        row=self.known[key]
        following=base.mapped(key,row['cpu']+row['size'])
        taken=base.mapped(key,row['cpu']+row['size']+(row['operand']if row['operand']<128 else row['operand']-256))
        predecessors=self.predecessors.get(key,())
        # This is an exact last-instruction flag contract, not a guessed
        # relationship between arbitrary old register values and current P.
        if row['op']in('BMI','BPL','BEQ','BNE')and taken!=following and len(set(predecessors))==1:
            previous_key=next(iter(predecessors));previous=self.known[previous_key]
            produces={'LDA':0,'LDX':1,'LDY':2,'TAX':1,'TAY':2,'TXA':0,'TYA':0,'INX':1,'DEX':1,'INY':2,'DEY':2,'AND':0,'ORA':0,'EOR':0,'ADC':0,'SBC':0,'PLA':0}
            if previous['op']in('ASL','LSR','ROL','ROR')and previous['mode']=='a':register=0
            else:register=produces.get(previous['op'])
            if register is not None and base.mapped(previous_key,previous['cpu']+previous['size'])==key:
                values=state.numbers[register]
                if values is not None:
                    filtered=[]
                    for target,value in successors:
                        def predicate(number):
                            return bool(number&128)if row['op']=='BMI'else not bool(number&128)if row['op']=='BPL'else number==0 if row['op']=='BEQ'else number!=0
                        allowed=frozenset(number for number in values if predicate(number)==(target==taken))
                        if not allowed:continue
                        value=value.copy();numbers=list(value.numbers);numbers[register]=finite(allowed);value.numbers=tuple(numbers)
                        filtered.append((target,value));self.NZ_branch_filters.add((key,previous_key,register))
                    successors=filtered
        for target,value in successors:
            refs=list(value.cell_refs)
            for i,address in enumerate(refs):
                if address is None or value.numbers[i]is None or address not in value.scalar_cells:continue
                narrowed=value.scalar_cells[address]&value.numbers[i]
                if narrowed!=value.scalar_cells[address]:
                    value.scalar_cells[address]=finite(narrowed);self.scalar_branch_filters.add((key,target,address))
        return successors

    def dispatch_successors(self,key,state):
        results=super().dispatch_successors(key,state)
        for target,value in results:value.cell_refs=(None,)+value.cell_refs[1:]
        return results

    def run_queue(self):
        while self.queue:
            key=self.queue.popleft();self.scheduled.discard(key)
            state=self.transfer(key,self.states[key]);row=self.known[key]
            if row['op']!='JSR':
                successors=self.branch_successors(key,state)if row['mode']=='rel'else[(target,state)for target in self.edges.get(key,())]
                for target,value in successors:self.emit(target,value)
            elif key in self.dispatch:
                for target,value in self.dispatch_successors(key,state):self.emit(target,value)
            else:
                following,result=self.call_result(key,state)
                targets=[target for target in self.edges.get(key,())if target!=following]
                for target in targets:
                    callee=state.copy()
                    if row['operand']==0xEE07:
                        scalar_kill(callee,set(range(0x58,0x5E))|{0xE2,0xE3})
                        callee.pairs[0x5B]=base.Pair(frozenset((target[1],)),self.add_origin(key,'farcall_CPU_target'))
                        callee.registers=(frozenset(),callee.registers[1],callee.registers[2]);callee.numbers=(frozenset((0x4C,)),callee.numbers[1],callee.numbers[2]);callee.cell_refs=(None,)+callee.cell_refs[1:]
                    callee.stack,callee.number_stack,callee.builders=(),(),frozenset();self.emit(target,callee)
                self.emit(following,result)
            self.steps+=1
            if self.steps%50000==0:print('scalar-cell transfers',self.steps,'positions',len(self.states),'queued',len(self.queue),flush=True)

    def contract(self,key):
        proof=super().contract(key)
        if proof is not None:
            state=self.states[key]
            proof['scalar_cell_relation_scope']='Must scalar ZP cells and equality to the current cell generation; all possible mirrored/direct/indexed/indirect/callee writes kill cells and references. Ordinary bounded CFG execution without intervening interrupts/external mutation.'
            proof['scalar_cells_at_access']={str(k):sorted(v)for k,v in sorted(state.scalar_cells.items())}
            proof['register_cell_equalities']={name:ref for name,ref in zip(('A','X','Y'),state.cell_refs)}
        return proof


def make_groups(engine,rows):
    """A complete trusted-graph caller inventory, not whole-ROM reachability."""
    byroot=defaultdict(list);callers=defaultdict(list)
    for key,row in engine.known.items():
        if row['op']!='JSR':continue
        following=base.mapped(key,row['cpu']+row['size']+(2 if row['operand']==0xEE07 else 0))
        if key in engine.dispatch:targets=engine.dispatch[key]['mapped_targets']
        else:targets=[target for target in engine.edges.get(key,())if target!=following]
        for target in targets:callers[target].append(dict(call=engine.raw(key),target_physical_bank=target[0],target_cpu=target[1],kind='bounded_inline_dispatch'if key in engine.dispatch else'inline_far_call'if row['operand']==0xEE07 else'local_JSR'))
    # The most local enclosing procedure is used for compact presentation. Every
    # known enclosing entry is retained as a separate list; no arbitrary jump
    # from outside the trusted graph is ruled out by this choice.
    owners=defaultdict(list)
    wanted={(r['physical_bank'],r['cpu'])for r in rows}
    for entry in engine.effects:
        structure=engine.function_structure(entry)
        for key in wanted&structure['nodes']:owners[key].append((len(structure['nodes']),entry))
    for row in rows:
        key=row['physical_bank'],row['cpu'];proof=row['address_contract'];origins=(proof or{}).get('origins',[])
        signatures=tuple(sorted({(v['physical_bank'],v['cpu'],v.get('origin_kind'))for v in origins}))
        identity=(row['physical_bank'],row['pointer_zero_page'],signatures)
        byroot[identity].append(row)
    result=[]
    for n,(identity,members)in enumerate(sorted(byroot.items(),key=lambda v:str(v[0]))):
        bank,pointer,signatures=identity;entries={entry for row in members for _,entry in owners[row['physical_bank'],row['cpu']]}
        result.append(dict(group_id=f'G{n:03d}',physical_bank=bank,pointer_zero_page=pointer,access_count=len(members),
            accesses=[dict(physical_bank=r['physical_bank'],cpu=r['cpu'],raw_hex=r['raw_hex'],phase22_classification=r['phase22_classification'],classification=r['classification'])for r in members],
            shared_pointer_producers=[dict(physical_bank=b,cpu=p,origin_kind=kind,original_instruction=engine.raw((b,p)))for b,p,kind in signatures],
            known_enclosing_procedures=[dict(entry=engine.raw(entry),all_trusted_incoming_callers=callers.get(entry,[]),local_control_barriers=engine.function_structure(entry)['barriers'])for entry in sorted(entries)],
            unknown_producer=not bool(signatures),scope='Complete enumeration of known producer facts and trusted enclosing procedure/caller edges only. Unknown roots, bounded selector/mapping preconditions, dynamic callbacks and external entries are not excluded. Grouping is not a semantic field name or new dynamic coverage.'))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('rom');args=parser.parse_args()
    rom=Path(args.rom).read_bytes();assert hashlib.sha256(rom).hexdigest()==base.ROM_SHA256
    assert base.digest(ROOT/'analysis/phase22/verification.json')==OLD_AUDIT
    assert base.digest(ROOT/'build/三国志2超级版-逆向分析-v22.zip')==OLD_ZIP
    engine=Analysis(rom)
    for round_number in range(3):
        engine.prove_returns();engine.steps=0;engine.states={};engine.queue=deque();engine.scheduled=set()
        roots,fallback=engine.run();added=engine.refine_write_effects()if round_number<2 else None
        engine.refinement_rounds.append(dict(round=round_number+1,original_instruction_transfers=engine.steps,new_non_ZP_store_proofs=added,return_contract_count=len(engine.return_contracts)))
        if not added:break
    before=base.read('analysis/phase22/fields-static/all-indirect-accesses.json')['accesses'];rows=[]
    for prior in before:
        key=prior['physical_bank'],prior['cpu'];candidate=engine.contract(key);previous=prior['address_contract']
        newdisjoint=candidate is not None and not old.auxiliary_intersection(candidate)
        inherited=prior['classification']==DISJOINT and not newdisjoint or candidate is None
        authority=previous if inherited else candidate
        classification=DISJOINT if authority is not None and not old.auxiliary_intersection(authority)else'possible_city_auxiliary_alias'if authority else'unresolved_pointer_or_index_contract'
        row=dict(prior);row.update(classification=classification,address_contract=authority,
            phase22_classification=prior['classification'],newly_proved_disjoint=classification==DISJOINT and prior['classification']!=DISJOINT,
            phase23_authoritative_contract_origin=dict(path='analysis/phase22/fields-static/all-indirect-accesses.json',sha256=base.digest(ROOT/'analysis/phase22/fields-static/all-indirect-accesses.json'),physical_bank=key[0],cpu=key[1],contract_field='address_contract')if inherited and authority else None,
            proof_basis='frozen_phase22_authoritative_contract'if inherited else'phase23_must_scalar_cell_context',
            whole_pointer_values=sorted(old.projection_words(authority))if authority else None,Y_values=old.projection_Y(authority)if authority else prior['Y_values'],
            candidate_address_contract=candidate if inherited else previous,candidate_whole_pointer_values=sorted(old.projection_words(candidate if inherited else previous))if(candidate if inherited else previous)else None,
            candidate_Y_values=old.projection_Y(candidate if inherited else previous)if(candidate if inherited else previous)else None,candidate_contract_is_authoritative=False)
        row['phase22_authoritative_contract_origin']=prior.get('authoritative_contract_origin')
        row['authoritative_contract_origin']=row['phase23_authoritative_contract_origin']
        row['authoritative_pointer_representation']='explicit_guarded_pointer_index_cases'if authority and'address_cases'in authority else'complete_joint_address_set'if authority and'whole_pointer_values'in authority else'inherited_independent_low_high_Cartesian_domain'if authority else None
        if authority:
            hits=old.auxiliary_intersection(authority);assert hits==authority['possible_auxiliary_effective_addresses']and len(hits)==authority['auxiliary_address_intersection_count']
        rows.append(row)
    previous368=[r for r in rows if r['phase22_classification']!=DISJOINT];remaining=[r for r in rows if r['classification']!=DISJOINT]
    groups=make_groups(engine,previous368)
    for name,selected in [('all-indirect-accesses.json',rows),('access-contracts.json',[r for r in rows if r['phase17_remaining_candidate']]),('new-indirect-accesses.json',[r for r in rows if not r['phase17_instruction_access']]),('phase22-remaining368-handling.json',previous368),('remaining-accesses.json',remaining)]:
        save(name,dict(schema='phase23-must-scalar-cell-and-pointer-access-contracts-v1',ROM_sha256=base.ROM_SHA256,source_CPU_cases=0,access_count=len(selected),classification_counts=dict(Counter(r['classification']for r in selected)),newly_proved_disjoint_count=sum(r['newly_proved_disjoint']for r in selected),accesses=selected))
    save('shared-producer-caller-groups.json',dict(schema='phase23-shared-pointer-producer-complete-trusted-caller-groups-v1',previous_candidate_count=368,group_count=len(groups),groups=groups))
    scalar_rows=[]
    for row in previous368:
        key=row['physical_bank'],row['cpu'];state=engine.states[key]
        if state.scalar_cells or any(r is not None for r in state.cell_refs):
            scalar_rows.append(dict(physical_bank=key[0],cpu=key[1],raw_hex=row['raw_hex'],newly_proved_disjoint=row['newly_proved_disjoint'],scalar_cells={str(k):sorted(v)for k,v in sorted(state.scalar_cells.items())},register_cell_equalities=dict(zip(('A','X','Y'),state.cell_refs)),register_numeric_domains={name:sorted(values)if values is not None else None for name,values in zip(('A','X','Y'),state.numbers)}))
    save('scalar-cell-site-proofs.json',dict(schema='phase23-must-scalar-cell-site-proof-v1',site_count=len(scalar_rows),sites=scalar_rows,cell_load_sites=[engine.raw(k)for k in sorted(engine.scalar_cell_loads)],branch_filter_sites=[dict(branch=engine.raw(k),target=engine.raw(t),scalar_cell=address)for k,t,address in sorted(engine.scalar_branch_filters)],last_instruction_NZ_branch_contracts=[dict(branch=engine.raw(k),unique_predecessor=engine.raw(p),register=('A','X','Y')[register])for k,p,register in sorted(engine.NZ_branch_filters)]))
    # The raw345 inventory is carried verbatim, never promoted to new code.
    raw=base.read('analysis/phase22/fields-static/raw345-executability-ledger.json');save('raw345-executability-ledger.json',raw)
    dummy=[]
    for row in rows:
        proof=row['address_contract'];hit=old.dummy_auxiliary_intersection(proof,row['op'])if proof else None
        dummy.append(dict(physical_bank=row['physical_bank'],cpu=row['cpu'],logical_classification=row['classification'],operation=row['op'],dummy_auxiliary_bus_addresses=hit,dummy_auxiliary_intersection_count=len(hit)if hit is not None else None,logical_contract_changed=False))
    save('logical-vs-dummy-bus-contracts.json',dict(schema='phase23-logical-and-dummy-bus-domain-v1',access_count=1526,accesses=dummy,scope='Logical effective data addresses and IndY_R/IndY_W uncorrected-page reads remain separate; dummy values are not consumed. Original addressing implementation is frozen in phase22.'))
    summary=dict(schema='phase23-must-scalar-cell-and-producer-context-summary-v1',status='analyzed',ROM_sha256=base.ROM_SHA256,
      analyzer_path='scripts/analyze_city_auxiliary_phase23.py',analyzer_sha256=base.digest(__file__),artifact_sha256={p:base.digest(ROOT/p)for p in INPUTS},
      old_phase22_audit_sha256=OLD_AUDIT,old_v22_preserved_sha256=OLD_ZIP,source_CPU_cases=0,
      all_indirect_access_count=1526,previous_candidate_count=368,remaining_access_count=len(remaining),newly_proved_disjoint_all_count=sum(r['newly_proved_disjoint']for r in rows),
      all_indirect_classification_counts=dict(Counter(r['classification']for r in rows)),previous_candidate_classification_counts=dict(Counter(r['classification']for r in previous368)),
      grouping_count=len(groups),scalar_cell_site_count=len(scalar_rows),scalar_cell_load_site_count=len(engine.scalar_cell_loads),scalar_branch_filter_edge_count=len(engine.scalar_branch_filters),last_instruction_NZ_branch_contract_count=len(engine.NZ_branch_filters),
      finite_refinement_rounds=engine.refinement_rounds,complete_analysis_fixed_point_proven=False,
      raw_window_count=345,raw_window_categories=raw['categories'],official_target_field_names=dict(city_plus1=None,city_plus28=None,city_plus29=None,city_plus30=None,city_plus31=None),
      limits=['Finite must-memory scalar relations; every possible write including RAM mirrors and unknown callees invalidates cells and current-register equalities.',
        'Caller grouping is complete only for the frozen trusted graph; no whole-ROM dynamic reachability or unknown external-entry exclusion.',
        'All raw selectors retained; naked firstFF suffix counterexamples remain outside guarded entry contracts.',
        'No official field meaning, unused/reserved/padding conclusion from zeros or bounded observations. Logical data EA is separate from dummy micro-cycle bus reads.',
        'At most three finite proof-strengthening rounds; the actual round list is authoritative and is not a complete-program fixed-point theorem.'])
    save('analysis-summary.json',summary)
    print(json.dumps({k:summary[k]for k in('grouping_count','all_indirect_classification_counts','remaining_access_count','newly_proved_disjoint_all_count')},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
