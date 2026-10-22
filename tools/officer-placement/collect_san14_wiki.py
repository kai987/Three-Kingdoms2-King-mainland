#!/usr/bin/env python3
"""Collect factual SAN14 scenario-table cells without copying portraits or prose.

Stable candidate IDs come from the existing official-name roster. The wiki is
third-party game reference material, not an official export or independent
historical attestation. Raw responses stay in a local /tmp cache, outside Git.
Different titles sharing a date are retained, not collapsed or auto-applied.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading
import time
import unicodedata
from urllib.parse import quote, unquote, urljoin

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://wikiwiki.jp/sangokushi14/'
INDEX_URL = BASE + quote('史実武将', safe='')
USER_AGENT = 'Mozilla/5.0 (compatible; TK2-offline-data-audit/1.0)'
# These links are explicitly distinguished by the wiki's officer index. Their
# same-name official entries have stable, independently separate identities.
HOMONYM_SLUGS = {
 'san14-candidate-0173':'韓忠(黄巾)', 'san14-candidate-0174':'韓忠(遼東)',
 'san14-candidate-0634':'張承(呉)', 'san14-candidate-0635':'張承(後漢)',
 'san14-candidate-0651':'張南(袁)', 'san14-candidate-0652':'張南(蜀)',
 'san14-candidate-0767':'馬忠(呉)', 'san14-candidate-0768':'馬忠(蜀)',
 'san14-candidate-0917':'李豊(蜀)', 'san14-candidate-0918':'李豊(魏)',
 'san14-candidate-0919':'李豊(袁)',
}
DATE = re.compile(r'^\s*(\d{3})年\s*(\d{1,2})月[\s　]*(.+?)\s*$')
FICTION_WORDS = ('英雄集結','英雄乱舞','女の戦い','曹家分裂','黄天当立','袁家の覇権',
 '魔王帰還','天下二分','潼関の戦い・袁紹','夷陵の炎','英雄終結','華北の覇者・袁紹',
 '河北の雄・公孫瓚','覇王袁紹','皇帝袁術','曹操の台頭・袁紹','曹操死す','曹操之死')
UNSERVED = {'未登場':'not_appeared','未発見':'undiscovered','在野':'free','死亡':'dead','未発掘':'undiscovered'}
HISTORICAL_REFERENCE_TITLES = {
 (184,2):'黄巾の乱', (190,1):'反董卓連合', (194,6):'群雄割拠',
 (200,1):'官渡の戦い', (207,9):'三顧の礼', (217,7):'漢中争奪戦',
 (221,7):'夷陵の戦い', (227,2):'出師の表', (249,1):'正始政変',
}


class RateGate:
    """Share request spacing and stop the batch on an explicit HTTP429."""
    def __init__(self, interval=3):
        self.lock=threading.Lock();self.interval=interval;self.next_at=0;self.rate_limit=None
    def wait(self):
        while True:
            with self.lock:
                if self.rate_limit is not None:raise RuntimeError('Collection paused after HTTP429: '+json.dumps(self.rate_limit))
                delay=self.next_at-time.monotonic()
                if delay<=0:self.next_at=time.monotonic()+self.interval;return
            time.sleep(min(delay,1))
    def stop(self, headers):
        raw=headers.get('retry-after')
        seconds=None
        if raw:
            try:seconds=max(0,int(raw))
            except ValueError:
                try:seconds=max(0,int((parsedate_to_datetime(raw)-datetime.now(timezone.utc)).total_seconds()))
                except (ValueError,TypeError):pass
        with self.lock:self.rate_limit=dict(retry_after=raw,retry_after_seconds=seconds,received_at=now(),action='batch_network_paused; resume only after indicated time or manual later retry')


GATE=RateGate()


def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def normalize(text): return re.sub(r'[\s　]+','',unicodedata.normalize('NFKC',text or ''))
def read(path): return json.loads((ROOT/path).read_text())


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.row=None;self.cell=None;self.links=[];self.link=None
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.cell=''
        if tag=='br' and self.cell is not None:self.cell+=' '
        if tag=='a':self.link=[attrs.get('href',''),'']
    def handle_data(self,text):
        if self.cell is not None:self.cell+=text
        if self.link is not None:self.link[1]+=text
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            if self.row is not None:self.row.append(re.sub(r'\s+',' ',self.cell).strip())
            self.cell=None
        if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
        if tag=='a' and self.link is not None:self.links.append(self.link);self.link=None


def strip_wiki(text):
    text=re.sub(r'\[\[([^\[\]]+)\]\]',lambda m:m.group(1).split('>')[0],text)
    text=re.sub(r'(?:BGCOLOR|COLOR|SIZE)\([^)]*\):','',text)
    text=re.sub(r'(?:LEFT|CENTER|RIGHT|TOP|MIDDLE|BOTTOM):','',text)
    text=re.sub(r'&br;',' ',text)
    return unescape(text).replace("''",'').strip()


def parsed_rows(body):
    parser=Tables();parser.feed(body)
    if any(r and DATE.match(r[0]) for r in parser.rows):return parser.rows, parser.links, 'html_tables'
    # Some mirrors expose PukiWiki text instead of already-rendered tables.
    rows=[]
    for line in unescape(re.sub(r'<[^>]+>','',body)).splitlines():
        line=line.strip()
        if not line.startswith('|'):continue
        cells=line.split('|')[1:-1]
        rows.append([strip_wiki(x) for x in cells])
    return rows, parser.links, 'pukiwiki_text'


def page_identity(rows):
    for i,row in enumerate(rows[:-1]):
        if '生年' in row and '登場' in row and '没年' in row:
            values=rows[i+1]
            if len(values)<len(row):return None
            return dict(name=re.split(r'[（(]',row[0])[0].strip(),
                birth=number(values[row.index('生年')]),service=number(values[row.index('登場')]),death=number(values[row.index('没年')]))
    return None


def number(value):
    return int(value) if re.fullmatch(r'\d+',value or '') else None


def scenario_rows(rows):
    result=[]
    for row in rows:
        if len(row)<5:continue
        match=DATE.match(row[0])
        if not match:continue
        year,month,title=int(match[1]),int(match[2]),match[3].strip()
        if not 1<=month<=12:continue
        raw_status,city,ruler=row[2:5]
        city=None if city in ('','-','－','死亡') else city
        ruler=None if ruler in ('','-','－','死亡') else ruler
        status=UNSERVED.get(raw_status,'serving' if ruler else 'unknown')
        marker=('historical_game_reference' if HISTORICAL_REFERENCE_TITLES.get((year,month))==title else
                'explicit_fictional_title_marker' if any(w in title for w in FICTION_WORDS) else 'not_classified')
        result.append(dict(year=year,month=month,title=title,fiction_marker=marker,
            status=status,status_source=raw_status,city=city,ruler=ruler,
            position=row[5] if len(row)>5 and row[5] not in ('','-','－') else None))
    return result


def fetch(url, cache, offline=False, retries=2):
    key=sha(url.encode());path=cache/(key+'.body');meta_path=cache/(key+'.json')
    if path.is_file() and meta_path.is_file():
        raw=path.read_bytes();meta=json.loads(meta_path.read_text())
        if meta.get('url')==url and meta.get('response_sha256')==sha(raw):return raw,meta
    if offline:raise RuntimeError('No checked cache for '+url)
    error=''
    for attempt in range(retries+1):
        target=cache/(key+'.download')
        header_path=cache/(key+'.headers')
        try:
            GATE.wait()
            response=subprocess.run(['curl','-L','--max-time','25','--connect-timeout','10','--max-filesize','5000000',
                '-sS','-A',USER_AGENT,'-D',str(header_path),'-w','%{http_code}',url,'-o',str(target)],capture_output=True,text=True,timeout=30)
            status=response.stdout.strip()
            header_text=header_path.read_text() if header_path.exists() else ''
            headers={k.strip().lower():v.strip() for line in header_text.splitlines() if ':' in line for k,v in [line.split(':',1)]}
            if status=='429':
                GATE.stop(headers)
                # Retain status, headers and timestamp, not a false empty table.
                (cache/(key+'.rate-limit.json')).write_text(json.dumps(dict(url=url,http_status=429,headers=headers,**GATE.rate_limit),ensure_ascii=False)+'\n')
                raise RuntimeError('HTTP429; network batch paused: '+json.dumps(GATE.rate_limit))
            if response.returncode==0 and status=='200' and target.is_file():
                raw=target.read_bytes()
                if len(raw)<500 or b'challenge-platform' in raw[:20000] and b'<table' not in raw:
                    raise RuntimeError('Not a usable wiki response')
                meta=dict(url=url,response_sha256=sha(raw),retrieved_at=now(),http_status=200,bytes=len(raw))
                target.replace(path);meta_path.write_text(json.dumps(meta,ensure_ascii=False)+'\n')
                return raw,meta
            error=f'HTTP {status or "unavailable"}, curl {response.returncode}: {response.stderr.strip()[:160]}'
            if status=='404':break
        except (OSError,subprocess.TimeoutExpired,RuntimeError) as exc:error=str(exc)
        finally:
            if target.exists():target.unlink()
        if GATE.rate_limit is not None:raise RuntimeError(error)
        if attempt<retries:time.sleep((attempt+1)*1.5)
    raise RuntimeError(error)


def index_links(body):
    parser=Tables();parser.feed(body)
    by_name={}
    for href,label in parser.links:
        if href.startswith('/sangokushi14/') and not '/::' in href and label.strip():
            by_name.setdefault(normalize(label),set()).add(urljoin(BASE,href))
    return by_name


def candidate_url(person, links):
    pid=person['person_id']
    if pid in HOMONYM_SLUGS:
        url=BASE+quote(HOMONYM_SLUGS[pid],safe='')
        expected=set().union(*(links.get(normalize(n),set()) for n in [person['name_japanese'],person['name_traditional']]))
        if url not in expected:raise RuntimeError('Qualified same-name page not found in officer index')
        return url,'explicit_qualified_homonym_index_link'
    choices=set().union(*(links.get(normalize(n),set()) for n in [person['name_japanese'],person['name_traditional'],person['name_simplified'],*person.get('search_aliases',[])]))
    if len(choices)==1:return next(iter(choices)),'unique_exact_name_officer_index_link'
    if len(choices)>1:raise RuntimeError('Ambiguous wiki name links; no ordinal matching')
    return BASE+quote(person['name_japanese'],safe=''),'exact_official_japanese_name_direct_page'


def collect(person, url, join, dates, cache, offline):
    raw,meta=fetch(url,cache,offline)
    body=raw.decode('utf-8-sig');rows,_links,format_=parsed_rows(body)
    identity=page_identity(rows)
    expected={normalize(n) for n in [person['name_japanese'],person['name_traditional'],person['name_simplified'],*person.get('search_aliases',[])]}
    if not identity or normalize(identity['name']) not in expected:raise RuntimeError('Page identity name not verified')
    chronology=person['chronology'];expected_dates=dict(birth=chronology['game_birth_year'],service=chronology['game_appearance_year'],death=chronology['game_death_year'])
    disagreements={k:dict(existing=expected_dates[k],wiki=identity[k]) for k in expected_dates if identity[k] is not None and expected_dates[k]!=identity[k]}
    if join=='explicit_qualified_homonym_index_link' and disagreements:raise RuntimeError('Same-name page chronology mismatch requires manual review: '+str(disagreements))
    scenarios=scenario_rows(rows)
    if not scenarios:raise RuntimeError('Verified person page has no parsed scenario rows')
    selected=[r for r in scenarios if (r['year'],r['month']) in dates]
    future=[];seen=set()
    for row in scenarios:
        # Exclude clearly cross-era/fictional pages from future location support.
        # A city cell supplies a game location, never a certified birthplace.
        if row['city'] and row['fiction_marker']=='historical_game_reference' and row['city'] not in seen:
            seen.add(row['city']);future.append({k:row[k] for k in ('year','month','title','status','city','ruler','fiction_marker')})
            if len(future)>=4:break
    return dict(person_id=person['person_id'],name=person['name_japanese'],source_url=url,
        response_sha256=meta['response_sha256'],retrieved_at=meta['retrieved_at'],response_bytes=meta['bytes'],
        response_format=format_,identity_validation=join,page_identity=identity,chronology_disagreements=disagreements,
        scenarios=selected,future_city_snapshots=future,parsed_scenario_rows=len(scenarios))


def build_output(people, failures, dates, index_meta, offline=False):
    ordered={k:people[k] for k in sorted(people)}
    return dict(schema='tk2-san14-scenario-postings-v15',source_boundary='third_party_SAN14_game_reference_not_official_export_or_independent_history',
        collection='scenario table facts only; no portraits, biographies or whole HTML committed',
        source_index={k:index_meta[k] for k in ('url','response_sha256','retrieved_at','bytes')},
        current_scenario_dates=[list(d) for d in sorted(dates)],
        identity_policy='Stable official candidate person_id; unique exact names or explicit qualified homonym links with chronology verification; no approximate-name or ordinal joins',
        scenario_policy='Same-date rows retain their own title and fiction marker; a date match alone is not equivalence to a custom/IF remake chapter',
        future_city_policy='At most four distinct cities from the nine explicitly whitelisted historical game snapshots; not certified birthplaces or continuous residence',
        people=ordered,failures=sorted(failures,key=lambda r:r['person_id']),
        snapshot_complete=len(ordered)==1000,collection_mode='offline_cache_only' if offline else 'spaced_network_with_cache',network_rate_limit=GATE.rate_limit,
        counts=dict(expected=1000,collected=len(ordered),failed=len(failures),same_date_rows=sum(len(p['scenarios']) for p in ordered.values()),
            people_with_same_date_rows=sum(bool(p['scenarios']) for p in ordered.values()),future_city_people=sum(bool(p['future_city_snapshots']) for p in ordered.values()),
            chronology_disagreement_people=sum(bool(p['chronology_disagreements']) for p in ordered.values())))


def canonical_candidates():
    """Keep original1000 stable identities; use the current canonical pool."""
    source = read('game/config/campaigns/people.json')
    candidates = []
    for pid in source['order']:
        if not pid.startswith('san14-candidate-'):
            continue
        person = source['people'][pid]
        japanese = person['ability_source']['source_name']
        candidates.append(dict(person_id=pid, name_japanese=japanese,
            name_traditional=person['name'], name_simplified=person['name'],
            search_aliases=list(dict.fromkeys(person.get('aliases', []))),
            chronology=dict(game_birth_year=person['birth_year'],
                game_appearance_year=person['service_year'], game_death_year=person['death_year'])))
    if len(candidates) != 1000 or len({p['person_id'] for p in candidates}) != 1000:
        raise ValueError('Expected1000 canonical SAN14 identities')
    return candidates


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir',type=Path,default=Path('/tmp/tk-placement-audit/wiki-cache'))
    parser.add_argument('--output',type=Path,default=ROOT/'game/config/references/san14-postings.json')
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--min-interval',type=float,default=3,help='Global seconds between requests, shared by all workers')
    parser.add_argument('--limit',type=int)
    parser.add_argument('--offline',action='store_true')
    args=parser.parse_args()
    if not 1<=args.workers<=6:parser.error('workers must be1..6')
    if args.min_interval<1:parser.error('Respectful request spacing must be at least1second')
    GATE.interval=args.min_interval
    args.cache_dir.mkdir(parents=True,exist_ok=True)
    source=canonical_candidates()
    dates={(entry['year'],entry['month']) for entry in read('game/config/campaigns/index.json')['scenarios']}
    raw,index_meta=fetch(INDEX_URL,args.cache_dir,args.offline)
    links=index_links(raw.decode('utf-8-sig'))
    candidates=source[:args.limit] if args.limit else source
    people={};failures=[]
    def task(person):
        url,join=candidate_url(person,links)
        return collect(person,url,join,dates,args.cache_dir,args.offline)
    def save():
        value=build_output(people,failures,dates,index_meta,args.offline)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temporary=args.output.with_suffix(args.output.suffix+'.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n');temporary.replace(args.output)
        print(json.dumps(value['counts']),flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs={pool.submit(task,p):p for p in candidates}
        for i,future in enumerate(as_completed(jobs),1):
            person=jobs[future]
            try:people[person['person_id']]=future.result()
            except Exception as exc:
                try:url,join=candidate_url(person,links)
                except Exception:url,join=None,None
                failures.append(dict(person_id=person['person_id'],name=person['name_japanese'],source_url=url,error=str(exc),
                    meaning='uncollected_or_unverified; not evidence of missing scenario entries'))
            if not args.offline and i%25==0:save()
    save()


if __name__=='__main__':main()
