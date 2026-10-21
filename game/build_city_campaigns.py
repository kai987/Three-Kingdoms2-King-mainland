#!/usr/bin/env python3
"""v6 city economies and the Yinping-Chengdu road; released catalogs stay fixed."""
from copy import deepcopy
from build_campaigns import read,write


def build():
    source=read('game/data/main-scenarios-v5/index.json')
    spec=read('game/config/city-economy.json')
    paths=[];summary=[]
    for old_path in source['catalogs']:
        data=deepcopy(read('game/data/'+old_path))
        data['id']=data['id'].replace('-v5','-v6');data['content_generation']=6
        data['city_profiles']={}
        data['initial_city_resources']={};data['city_income']={}
        for city in data['cities']:
            ident=city['id'];entry=spec['cities'].get(ident,{});tier=entry.get('tier','normal')
            if ident in ('shujun','guanghan'):city['terrain']='plain'
            rule=spec['tiers'][tier]
            data['city_profiles'][ident]={'tier':tier,'label':rule['label'],'basis':entry.get('basis','unreviewed_expansion_node_ordinary_game_baseline'),
                'reference_income':entry.get('reference_income'),'is_SAN14_starting_resources':False}
            data['initial_city_resources'][ident]=dict(rule['initial'])
            data['city_income'][ident]=dict(rule['monthly'])
        edge=['yinping','shujun']
        if not any(set(e)==set(edge) for e in data['links']):data['links'].append(edge)
        data['road_additions']=[edge]
        data['main_scenario']['city_economy']='city-size-adaptation-v1'
        data['era_metadata']['main_scenario']=data['main_scenario']
        data['design_notes'].append('城市按普通、大城、巨城配置开局钱粮与预备兵，并分别计算每月收入。参考三国志14规模与收入关系；数值缩放为本作设计，并非原游戏剧本资源导出。')
        data['design_notes'].append('新增阴平—成都道路用于调动、出征和AI；地图沿盆地走廊绘制接驳，未模拟逐格行军。')
        data['design_notes'][-3]='已发布39份目录保持原样；旧存档保留原规则，新开v6战役启用城市规模与新增道路。'
        filename=old_path.replace('main-scenarios-v5/','main-scenarios-v6/')
        write('game/data/'+filename,data);paths.append(filename)
        original=next(s for s in source['summary'] if s['id'].replace('-v5','-v6')==data['id'])
        summary.append(dict(original,id=data['id']))
    result={'schema':'main-scenario-index-v1','catalogs':paths,'default':source['default'].replace('-v5','-v6'),'summary':summary}
    write('game/data/main-scenarios-v6/index.json',result)
    return result


if __name__=='__main__':
    import json
    print(json.dumps(build(),ensure_ascii=False))
