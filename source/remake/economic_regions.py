"""Economic geography for the published map's city IDs."""

VERSION = 1
REGIONS = {
    'liaodong': ('遼東', '遼東'),
    'hebei': ('河北', '河北'),
    'zhongyuan': ('中原', '中原'),
    'guanzhong': ('關中', '関中'),
    'northwest': ('西北', '西北'),
    'hanzhong': ('漢中', '漢中'),
    'bashu': ('巴蜀', '巴蜀'),
    'jingxiang': ('荊襄', '荊襄'),
    'jianghuai': ('江淮', '江淮'),
    'jiangdong': ('江東', '江東'),
    'jingnan': ('荊南', '荊南'),
    'lingnan': ('嶺南', '嶺南'),
    'overseas': ('海外', '海外'),
    'unassigned': ('區域未設定', '地域未設定'),
}
_GROUPS = {
    'liaodong': 'liaodong liaoxi changli liucheng xuantu guonei lelang daifang youbeiping',
    'hebei': ('fanyang taiyuan qi wei xihe bohai beihai yan yuyang shanggu dai changshan zhongshan '
              'anping pingyuan jinan shangdang zhao julu hejian qinghe yanmen xinxing pingyang '
              'donglai taishan leling zhangwu guangping lean leping'),
    'zhongyuan': ('donghai shanyang henan yingchuan dongjun chenliu runan qiao xiapi jiyin dongping henei '
                  'langya liang pengcheng ruyin yiyang_runan lu chengyang dongguan'),
    'guanzhong': 'jingzhao hongnong hedong fengyi fufeng xinping beidi',
    'northwest': 'wuwei anding jincheng tianshui longxi xiping zhangye jiuquan dunhuang shuofang wuyuan yunzhong nanan guangwei xihai xijun',
    'hanzhong': 'hanzhong xincheng wudu yinping xicheng shangyong jiameng',
    'bashu': ('shujun bajun yunnan yongchang badong zitong guanghan wenshan baxi qianwei jiangyang '
              'hanjia zhuti yuexi zangke jianning xinggu fuling fuxian dangqu nanguang'),
    'jingxiang': 'yiyang jiangxia nanjun nanyang yidu qichun xiangyang wuchang yiling jianping nanxiang',
    'jianghuai': 'jiujiang lujiang hefei guangling',
    'jiangdong': 'danyang yuzhang wujun kuaiji xindu poyang luling linhai linchuan jianan wuxing chaisang',
    'jingnan': 'changsha lingling guiyang wuling hengyang xiangdong shian',
    'lingnan': 'jiaozhi yulin cangwu linhe nanhai gaoliang hepu jiuzhen rinan shixing',
    'overseas': 'yizhou zhuya luzon',
}
CITY_REGION = {city: group for group, keys in _GROUPS.items() for city in keys.split()}


def region(city_id):
    return CITY_REGION.get(city_id, 'unassigned')
