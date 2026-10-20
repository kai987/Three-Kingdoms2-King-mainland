"""Join every retained marine direction to its actual map-city endpoints.

Only route geometry changes. Ports and land approaches are game-map choices,
not newly asserted archaeological identifications of ancient harbours.
"""
from pathlib import Path
from collections import defaultdict, deque
import copy, heapq, json, math
import cv2
import numpy as np
from PIL import Image

B=Path(__file__).parent
load=lambda f:json.loads((B/f).read_text())
P=load('city-map-natural-plan-v41.json')
S=load('city-map-existing-cities-sea-routes.json')
R=load('city-map-natural-roads-v41.json')
C={c['key']:c for c in P['cities']}
centres={k:(c['displayArtX']-136,c['displayArtY']) for k,c in C.items()}
rgb=np.asarray(Image.open(B/'city-map-natural-terrain-v41.png').convert('RGB'))[:,136:1488]
H,W=rgb.shape[:2]
wet=(rgb[:,:,0]<80)&(rgb[:,:,1]<150)&(rgb[:,:,2]>160)
sea_dist=cv2.distanceTransform(wet.astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
core=np.fromfile(B/'natural-road-core-mask-v41.bin',dtype=np.uint8).reshape(H,W)>0
ocean_count,ocean_labels=cv2.connectedComponents((sea_dist>=3).astype(np.uint8),8)
ocean_label=ocean_labels[1000,1300]
ocean=(ocean_labels==ocean_label)
dirs=[(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]

def sample(ps,step=.75):
    for a,b in zip(ps,ps[1:]):
        n=max(1,math.ceil(math.dist(a,b)/step))
        for j in range(n):
            t=j/n;yield (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
    yield tuple(ps[-1])

def pix(p):return max(0,min(H-1,round(p[1]))),max(0,min(W-1,round(p[0])))
def hits(ps,mask):return sum(bool(mask[pix(p)]) for p in sample(ps))
def length(ps):return sum(math.dist(a,b)for a,b in zip(ps,ps[1:]))

def simplify(ps,valid):
    out=[ps[0]];i=0
    while i<len(ps)-1:
        j=min(len(ps)-1,i+25)
        while j>i+1 and not valid([ps[i],ps[j]],ps[i:j+1]):j-=1
        out.append(ps[j]);i=j
    return out

def land_approach(k):
    cx,cy=centres[k];old=S['ports'].get(k,S['checks']['rinanShoreEntry'])
    # This local search may enter only the immediate shoreline fringe. A
    # short brown landing pier joins the road to an offshore water-only lane.
    start=(round(cx/2),round(cy/2));dist={start:0.};prev={};q=[(0.,start)]
    best=None
    while q:
        d,u=heapq.heappop(q)
        if d>dist[u]+1e-8:continue
        x,y=u[0]*2,u[1]*2
        if best and d>best[0]:break
        if ocean[y,x] and 4.5<=sea_dist[y,x]<=7.5:
            score=d+.3*math.dist((x,y),old)
            if not best or score<best[0]:best=(score,u)
        for dx,dy in dirs:
            v=(u[0]+dx,u[1]+dy);xx,yy=v[0]*2,v[1]*2
            if not(2<=xx<W-2 and 2<=yy<H-2):continue
            if math.hypot(xx-cx,yy-cy)>115:continue
            if sea_dist[yy,xx]>7.5:continue
            if any(abs(xx-z[0])<17 and abs(yy-z[1])<15 for key,z in centres.items() if key!=k):continue
            # Leaving a mountain beneath an existing city marker is allowed;
            # any mountain after the 18px city clearance is strongly avoided.
            at_city=math.hypot(xx-cx,yy-cy)<18
            penalty=1+(22 if core[yy,xx] and not at_city else 0)+(12 if wet[yy,xx] else 0)
            nd=d+math.hypot(dx,dy)*2*penalty
            if nd<dist.get(v,math.inf):
                dist[v]=nd;prev[v]=u;heapq.heappush(q,(nd,v))
    assert best,k
    path=[best[1]]
    while path[-1]!=start:path.append(prev[path[-1]])
    ps=[(x*2,y*2)for x,y in path[::-1]];ps[0]=centres[k]
    # Simplification cannot introduce deep-water shortcuts or mountain hits.
    valid=lambda a,raw: hits(a,core)<=hits(raw,core) and all(sea_dist[pix(p)]<=7.5 for p in sample(a))
    ps=simplify(ps,valid)
    return {'city':k,'cityName':C[k]['displayName'],'cityPoint':centres[k],
            'port':ps[-1],'points':ps,'length':round(length(ps),3),
            'coreSamplesOutsideCity':int(sum(core[pix(p)] and math.dist(p,centres[k])>18 for p in sample(ps))),
            'harbourStatus':'Schematic shoreline landing, not an identified historical harbour.'}

keys=['wujun','liaodong','beihai','lelang','daifang','kuaiji','yizhou','hepu','zhuya','jiaozhi','rinan']
approaches=[land_approach(k)for k in keys]
ports={a['city']:a['port']for a in approaches}
access_by_city={a['city']:a for a in approaches}
for access in approaches:
    # The final few water pixels are the solid-colour landing pier. No brown
    # road is allowed to substitute for a long offshore shipping segment.
    run=maximum=0.
    for p in sample(access['points'],.5):
        if wet[pix(p)]:run+=.5;maximum=max(maximum,run)
        else:run=0.
    access['maximumContinuousWaterContactPixels']=maximum
    assert maximum<=10,(access['city'],maximum)
# 2px navigation lattice. Every segment is checked against the actual current
# terrain pixels, rather than merely checking its vertices.
safe=ocean[::2,::2]
ys,xs=np.where(safe);safe_points=np.column_stack((xs*2,ys*2))
def snap(p):
    z=safe_points[np.argmin(((safe_points-np.asarray(p))**2).sum(axis=1))]
    return (int(z[0]//2),int(z[1]//2))
def sea_astar(a,b):
    start,end=snap(a),snap(b);ds={start:0};prev={};h=lambda v:math.dist(v,end);q=[(h(start),0,start)]
    while q:
        _,d,u=heapq.heappop(q)
        if d>ds[u]+1e-8:continue
        if u==end:break
        for dx,dy in dirs:
            v=(u[0]+dx,u[1]+dy);x,y=v
            if not(0<=y<safe.shape[0] and 0<=x<safe.shape[1])or not safe[y,x]:continue
            if dx and dy and not(safe[u[1],x]and safe[y,u[0]]):continue
            nd=d+math.hypot(dx,dy)
            if nd<ds.get(v,math.inf):ds[v]=nd;prev[v]=u;heapq.heappush(q,(nd+h(v),nd,v))
    assert end in ds,(a,b)
    out=[end]
    while out[-1]!=start:out.append(prev[out[-1]])
    return [(x*2,y*2)for x,y in out[::-1]]
def travel(waypoints):
    out=[]
    for a,b in zip(waypoints,waypoints[1:]):
        ps=sea_astar(a,b);out.extend(ps if not out else ps[1:])
    assert all(wet[pix(p)]for p in sample(out))
    return out

spec=[
 ('wujun','liaodong',1,[(1210,420),(1202,340),(1166,250),(1170,228),(1202,212)]),
 ('beihai','lelang',2,[(1170,228),(1202,212)]),
 ('beihai','daifang',2,[(1170,228),(1202,212),(1226,234)]),
 ('kuaiji','yizhou',4,[(1198,574),(1150,634)]),
 ('hepu','zhuya',5,[(548,865)]),
 ('hepu','jiaozhi',6,[(486,878),(450,884)]),
 ('jiaozhi','rinan',6,[(450,910),(470,972)])]
source_by_id={r['sourceRecordId']:r for r in S['routes']}
routes=[]
for a,b,sid,via in spec:
    original=source_by_id[sid];sea=travel([ports[a],*via,ports[b]])
    assert tuple(sea[0])==tuple(ports[a])and tuple(sea[-1])==tuple(ports[b])
    from_land=access_by_city[a]['points'];to_land=access_by_city[b]['points'][::-1]
    full=[*from_land,*sea[1:],*to_land[1:]]
    assert tuple(full[0])==tuple(centres[a])and tuple(full[-1])==tuple(centres[b])
    routes.append({'from':a,'to':b,'name':C[a]['displayName']+'—'+C[b]['displayName'],
      'sourceRecordId':sid,'source':original['source'],'period':original['period'],
      'evidence':original['evidence'],'uncertainty':original['uncertainty'],
      'seaPoints':sea,'fromCityPoint':centres[a],'toCityPoint':centres[b],
      'fromPort':ports[a],'toPort':ports[b],
      'fullCityToCityPoints':full,
      'transportParts':[{'mode':'land-road-and-shore-landing','points':from_land},
                        {'mode':'sea','points':sea},
                        {'mode':'land-road-and-shore-landing','points':to_land}],
      'allSeaSamplesOnWater':all(wet[pix(p)]for p in sample(sea)),
      'completeCityToCity':True})

EK=lambda a,b:tuple(sorted((tuple(a),tuple(b))))
edges={EK(a,b)for r in routes for a,b in zip(r['seaPoints'],r['seaPoints'][1:])if a!=b}
g=defaultdict(set)
for a,b in edges:g[a].add(b);g[b].add(a)
ends={p for p in g if len(g[p])!=2 or p in ports.values()};seen=set();segments=[]
for a in sorted(ends):
    for b in sorted(g[a]):
        if EK(a,b)in seen:continue
        ps=[a,b];seen.add(EK(a,b))
        while ps[-1]not in ends:
            nxt=next(p for p in g[ps[-1]]if p!=ps[-2]);seen.add(EK(ps[-1],nxt));ps.append(nxt)
        simple=simplify(ps,lambda p,raw:all(ocean[pix(x)]for x in sample(p)))
        segments.append({'points':simple,'sourcePoints':ps})
assert seen==edges
city_graph=defaultdict(set)
for route in [*R['directConnections'],*routes]:
    a,b=route['from'],route['to'];city_graph[a].add(b);city_graph[b].add(a)
visited=set();todo=['jingzhao']
while todo:
    p=todo.pop()
    if p in visited:continue
    visited.add(p);todo.extend(city_graph[p]-visited)
assert visited==set(C),set(C)-visited
checks={'cityCount':len(C),'cityToCityRelations':len(routes),'historicalSourceGroups':len(source_by_id),
 'accessCityCount':len(approaches),'allSeaSamplesOnWater':all(r['allSeaSamplesOnWater']for r in routes),
 'allEndpointCitiesExist':all(r['from']in C and r['to']in C for r in routes),
 'allAccessStartsExactlyAtCity':all(tuple(a['points'][0])==centres[a['city']]for a in approaches),
 'allAccessEndsExactlyAtSeaPort':all(tuple(a['points'][-1])==tuple(ports[a['city']])for a in approaches),
 'allCitiesConnectedAcrossLandAndSea':len(visited),
 'maximumSolidLandingWaterContactPixels':max(a['maximumContinuousWaterContactPixels']for a in approaches),
 'maxApproachMountainCoreSamplesOutsideCity':max(a['coreSamplesOutsideCity']for a in approaches),
 'uniquePhysicalSeaEdges':len(edges),'sharedSeaSegmentCount':len(segments),
 'terrainChanged':False,'riverChanged':False,'cityPositionChanged':False,
 'portPolicy':'Game-map landing points and land approaches are schematic; original source and uncertainty retained per relation.',
 'southernExtensionStatus':'Jiaozhi–Rinan is a map-contained southern continuation; not an independently attested exact city-pair voyage.'}
out={'version':42,'coordinateFrame':'cropped artwork 1352x1024; world x = screen x + 136',
 'ports':ports,'accessRoads':approaches,'routes':routes,'segments':segments,'checks':checks,
 'historicalSources':S['routes'],'displayPolicy':'Complete city–land road–shore landing–sea lane–landing–land road–city. Solid brown on land; yellow dashed over water only. No route numbers, foreign destinations or incomplete plans.'}
(B/'city-map-city-sea-links-v42.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
roads=copy.deepcopy(R);roads.update(version=42,marineAccessRoads=approaches,
 marineConnections=[{k:r[k]for k in ['from','to','sourceRecordId','completeCityToCity']}for r in routes],
 marineNetworkFile=str(B/'city-map-city-sea-links-v42.json'))
roads['checks'].update(allCitiesConnectedAcrossLandAndSea=len(visited),completeCityToCityMarineRelations=len(routes))
(B/'city-map-city-sea-roads-v42.json').write_text(json.dumps(roads,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'checks':checks,'ports':ports,'approaches':[{k:a[k]for k in ['city','length','coreSamplesOutsideCity']}for a in approaches]},ensure_ascii=False))
