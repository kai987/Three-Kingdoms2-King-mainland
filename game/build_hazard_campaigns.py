#!/usr/bin/env python3
"""Publish optional dangerous routes and chart discovery without save migration."""
from copy import deepcopy
from heapq import heappop,heappush
from math import ceil

from build_campaigns import read,write
from remake.travel import kilometers


def marine_geography():
    # Offshore corridor estimates, separate from the compressed artwork.
    chain=[[123,40],[122.3,39],[121,38.6],[123.3,38.2],[123,35],
        [122.5,33.5],[121.8,31.7],[121.5,30.5],[121.4,29.6],
        [121.65,28.7],[121.5,27.6],[121,25.8],[119.9,26.3],
        [118.4,24.2],[116.9,23.1],[115,22.5],[113.6,22.7],
        [112.9,21.8],[111.6,21.5],[110.5,20.4],[109.6,20.3],
        [109.4,21.4],[108.8,21],[107.8,20.8],[106.9,20.7],
        [106.4,19.8],[107.4,19],[107.9,17.4],[108.2,16.2]]
    attach={'liaodong':(0,chain[0]),'liaoxi':(1,[120.8,40.5]),
        'bohai':(2,[118.3,38.5]),'beihai':(2,[119.7,37.6]),
        'lelang':(3,[125,38.3]),'daifang':(3,[125.2,38.1]),
        'donghai':(4,[120.4,34.8]),'wujun':(6,chain[6]),
        'kuaiji':(8,chain[8]),'linhai':(9,chain[9]),
        'yizhou':(11,[120.5,24.6]),'nanhai':(16,chain[16]),
        'gaoliang':(18,chain[18]),'zhuya':(19,[110.5,20.1]),
        'hepu':(21,chain[21]),'jiaozhi':(24,chain[24]),
        'jiuzhen':(25,chain[25]),'rinan':(28,chain[28])}
    coords={str(i):p for i,p in enumerate(chain)}
    graph={str(i):[] for i in range(len(chain))}
    def link(a,b):
        distance=kilometers(coords[a],coords[b])
        graph.setdefault(a,[]).append((b,distance));graph.setdefault(b,[]).append((a,distance))
    for i in range(len(chain)-1):link(str(i),str(i+1))
    for key,(index,point) in attach.items():coords[key]=point;link(key,str(index))
    def path(source,target):
        queue=[(0,source,[source])];seen=set()
        while queue:
            cost,here,steps=heappop(queue)
            if here in seen:continue
            seen.add(here)
            if here==target:
                points=[]
                for step in steps:
                    if not points or coords[step]!=points[-1]:points.append(coords[step])
                return points
            for nxt,distance in graph[here]:
                if nxt not in seen:heappush(queue,(cost+distance,nxt,steps+[nxt]))
        raise ValueError('Disconnected marine corridor')
    return path


def sea_route(data,art,geo_path,*,known):
    a,b=art['from'],art['to'];geo=geo_path(a,b)
    plain=data['travel_rules']['speeds']['plain']
    land=round((kilometers(data['city_coordinates'][a],geo[0])+
                kilometers(geo[-1],data['city_coordinates'][b]))*data['travel_rules']['detours']['plain'],1)
    water=round(sum(kilometers(x,y) for x,y in zip(geo,geo[1:])),1)
    return dict(id=f'{a}:{b}:sea' if known else f'explore:{a}:{b}:sea',
        **{'from':a,'to':b},mode='sea',terrain='sea',distance_km=round(land+water,1),
        land_km=land,sea_km=water,days=max(1,ceil(land/plain)+ceil(water/data['travel_rules']['speeds']['sea'])+2),
        draw=deepcopy(art['draw']),geo=geo,discovery_candidate=not known)


def build():
    previous=read('game/data/main-scenarios-v10/index.json')
    policy=read('game/config/travel-hazards.json')
    marine=read('game/config/navigation-geometry.json')
    geo_path=marine_geography();paths=[];summary=[]
    for filename in previous['catalogs']:
        data=deepcopy(read('game/data/'+filename))
        data.update(id=data['id'].replace('-v10','-v11'),content_generation=11,
                    travel_hazards=deepcopy(policy))
        data['world']['background']='/assets/map-navigation.png'
        known={frozenset((r['from'],r['to'])) for r in data['travel_routes'] if r['mode']=='sea'}
        known.add(frozenset(('kuaiji','jiaozhi')))
        sea=[];exploration=[]
        for art in marine['routes']:
            is_known=frozenset((art['from'],art['to'])) in known
            row=sea_route(data,art,geo_path,known=is_known)
            (sea if is_known else exploration).append(row)
        data['travel_routes']=[r for r in data['travel_routes'] if r['mode']!='sea']+sea
        data['sea_routes']=sea;data['exploration_routes']=exploration
        for a,b in (('hanzhong','jingzhao'),('kuaiji','jiaozhi')):
            if not any(set(edge)=={a,b} for edge in data['links']):data['links'].append([a,b])
        for row in data['travel_routes']:
            if row['mode']=='land' and {row['from'],row['to']}=={'yinping','shujun'}:
                row['special']='yinping'
        # An explicit shortcut, in addition to the existing indirect routes.
        distance=round(kilometers(data['city_coordinates']['hanzhong'],data['city_coordinates']['jingzhao'])*1.45,1)
        data['travel_routes'].append(dict(id='hanzhong:jingzhao:ziwu',**{'from':'hanzhong','to':'jingzhao'},
            mode='land',terrain='mountain',special='ziwu',distance_km=distance,land_km=distance,
            sea_km=0,days=ceil(distance/data['travel_rules']['speeds']['plain'])))
        data['regional_roads'].append(dict(**{'from':'hanzhong','to':'jingzhao'},mode='land',terrain='mountain',
            draw=[dict(mode='land',points=[[421,411],[441,405],[453,387],[476,378],[497,354]])]))
        data['main_scenario']['travel']='hazardous-marches-v1'
        data['era_metadata']['main_scenario']=data['main_scenario']
        data['design_notes'] += [
            '阴平赴成都为单程险道，按平地基准2倍耗时，完成时全军余三分之一；反向不能走这条边，可另寻其他道路。',
            '新增汉中—长安子午谷；7–9月暴雨为平地4倍耗时、减员50%，其他月份为平地2倍、减员20%。可主动选择险道，也可选择其他最快路线。',
            '海路以出发月和方向判断季风：5–9月西南风，10–3月东北风，4月过渡。顺风120公里/日、逆风7.5公里/日；季风航行全程只结算一次80–90%暴风雨兵损。此为用户指定玩法，不是史实天气或伤亡测量。',
            '仅沿海港区节点可探索未知海路；实际到岸且仍有带兵者才显路，探索全损或途中取消不显路。发现与攻下敌城分开判定；发现路线会保存。',
            '未修改人物属性、城池年代或旧目录；新规则需新开v11战役。右栏势力资源为实际控制城池的钱、粮、预备兵之和。']
        path=filename.replace('main-scenarios-v10/','main-scenarios-v11/')
        write('game/data/'+path,data);paths.append(path)
        prior=next(r for r in previous['summary'] if r['id'].replace('-v10','-v11')==data['id'])
        summary.append(dict(prior,id=data['id'],known_sea_routes=len(sea),exploration_routes=len(exploration)))
    result=dict(schema='main-scenario-index-v1',catalogs=paths,
        default=previous['default'].replace('-v10','-v11'),summary=summary)
    write('game/data/main-scenarios-v11/index.json',result)
    return result


if __name__=='__main__':
    import json
    result=build();print(json.dumps(dict(catalogs=len(result['catalogs']),default=result['default'])))
