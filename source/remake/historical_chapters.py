"""Dated historical events tied to playable scenario fronts."""

from typing import NamedTuple


class Chapter(NamedTuple):
    start: tuple[int, int]
    end: tuple[int, int]
    leaders: tuple[tuple[str, str], ...]
    holdings: tuple[tuple[str, str], ...]
    officers: tuple[tuple[str, str], ...]
    cities: tuple[str, ...]
    people: tuple[str, ...]
    note: str
    approaches: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()


CHAPTERS = {
    'historical_youzhou_pacification': Chapter(
        start=(188, 6), end=(188, 12),
        leaders=(('liu_yu', 'san14-candidate-0932'), ('zhang_chun', 'san14-candidate-0628')),
        holdings=(('yan', 'liu_yu'), ('yuyang', 'zhang_chun')),
        officers=(('san14-candidate-0266', 'liu_yu'), ('san14-candidate-0612', 'zhang_chun')),
        cities=('liaoxi', 'yuyang', 'yan'),
        people=('san14-candidate-0932', 'san14-candidate-0266', 'san14-candidate-0628', 'san14-candidate-0612'),
        note='劉虞出鎮幽州。',
    ),
    'historical_dong_zhuo_coalition': Chapter(
        start=(190, 1), end=(190, 12),
        leaders=(('wang_kuang', 'san14-candidate-0047'), ('dong_zhuo', 'san14-candidate-0736'), ('yuan_shao', 'san14-candidate-0035'), ('wei', 'san14-candidate-0521')),
        holdings=(('henei', 'wang_kuang'), ('henan', 'dong_zhuo'), ('bohai', 'yuan_shao')),
        officers=(),
        cities=('bohai', 'henei', 'henan'),
        people=('san14-candidate-0035', 'san14-candidate-0047', 'san14-candidate-0521', 'san14-candidate-0736'),
        approaches=('henei',),
        targets=('henan',),
        note='關東諸軍討董卓。',
    ),
    'historical_sun_jian_jingzhou': Chapter(
        start=(191, 10), end=(191, 12),
        leaders=(('sun_jian', 'san14-candidate-0551'), ('liu_biao', 'san14-candidate-0953'), ('yuan_shu', 'san14-candidate-0032')),
        holdings=(('changsha', 'sun_jian'), ('xiangyang', 'liu_biao'), ('nanyang', 'yuan_shu')),
        officers=(),
        cities=('changsha', 'nanyang', 'jiangxia', 'xiangyang'),
        people=('san14-candidate-0551', 'san14-candidate-0953', 'san14-candidate-0032'),
        approaches=('changsha', 'wuling'),
        targets=('jiangxia', 'nanjun'),
        note='孫堅進兵荊州。',
    ),
    'historical_yanzhou_counteroffensive': Chapter(
        start=(194, 6), end=(194, 10),
        leaders=(('wei', 'san14-candidate-0521'), ('lubu', 'san14-candidate-0987')),
        holdings=(('jiyin', 'wei'), ('dongjun', 'lubu')),
        officers=(('san14-candidate-0393', 'wei'), ('san14-candidate-0671', 'lubu')),
        cities=('jiyin', 'chenliu', 'dongjun'),
        people=('san14-candidate-0521', 'san14-candidate-0393', 'san14-candidate-0987', 'san14-candidate-0671'),
        approaches=('jiyin',),
        targets=('dongjun',),
        note='兗州之變・濮陽攻防。',
    ),
    'historical_welcome_han_emperor': Chapter(
        start=(196, 6), end=(196, 9),
        leaders=(('wei', 'san14-candidate-0521'),),
        holdings=(('chenliu', 'wei'), ('yingchuan', 'wei')),
        officers=(('san14-candidate-0393', 'wei'), ('san14-candidate-0689', 'wei'), ('san14-candidate-0511', 'wei')),
        cities=('chenliu', 'yingchuan', 'henan'),
        people=('san14-candidate-0521', 'san14-candidate-0393', 'san14-candidate-0689', 'san14-candidate-0511'),
        note='曹操商議奉迎天子。',
    ),
    'historical_xiapi_expedition': Chapter(
        start=(198, 9), end=(198, 12),
        leaders=(('wei', 'san14-candidate-0521'), ('lubu', 'san14-candidate-0987'), ('shu', 'san14-candidate-0952')),
        holdings=(('yingchuan', 'wei'), ('xiapi', 'lubu'), ('qiao', 'shu')),
        officers=(('san14-candidate-0671', 'lubu'),),
        cities=('yingchuan', 'qiao', 'xiapi'),
        people=('san14-candidate-0521', 'san14-candidate-0987', 'san14-candidate-0952', 'san14-candidate-0671'),
        note='曹操東征呂布。',
        targets=('xiapi',),
    ),
    'historical_liyang_campaign': Chapter(
        start=(202, 9), end=(203, 4),
        leaders=(('wei', 'san14-candidate-0521'), ('yuan_shang', 'san14-candidate-0034'), ('yuan_tan', 'san14-candidate-0037')),
        holdings=(('wei', 'yuan_shang'), ('beihai', 'yuan_tan'), ('dongjun', 'wei')),
        officers=(),
        cities=('dongjun', 'beihai', 'wei'),
        people=('san14-candidate-0521', 'san14-candidate-0034', 'san14-candidate-0037'),
        approaches=('dongjun', 'henei'),
        targets=('wei',),
        note='河北爭亂・曹操北攻黎陽。',
    ),
    'historical_three_visits': Chapter(
        start=(207, 9), end=(208, 7),
        leaders=(('shu', 'san14-candidate-0952'), ('liu_biao', 'san14-candidate-0953')),
        holdings=(('yiyang', 'shu'), ('xiangyang', 'liu_biao')),
        officers=(('san14-candidate-0446', 'shu'),),
        cities=('yiyang', 'xiangyang'),
        people=('san14-candidate-0952', 'san14-candidate-0446', 'san14-candidate-0440'),
        note='徐庶薦諸葛亮。',
    ),
    'historical_yizhou_campaign': Chapter(
        start=(212, 12), end=(214, 5),
        leaders=(('shu', 'san14-candidate-0952'), ('liu_zhang', 'san14-candidate-0938')),
        holdings=(('fuxian', 'shu'), ('shujun', 'liu_zhang')),
        officers=(('san14-candidate-0827', 'shu'),),
        cities=('fuxian', 'shujun', 'guanghan'),
        people=('san14-candidate-0952', 'san14-candidate-0938', 'san14-candidate-0827'),
        approaches=('fuxian', 'jiameng'),
        targets=('guanghan', 'zitong', 'baxi', 'bajun'),
        note='涪城決裂・入蜀爭奪戰。',
    ),
    'historical_xiangfan': Chapter(
        start=(219, 7), end=(219, 10),
        leaders=(('shu', 'san14-candidate-0952'), ('wei', 'san14-candidate-0521')),
        holdings=(('nanjun', 'shu'), ('xiangyang', 'wei')),
        officers=(('san14-candidate-0147', 'shu'), ('san14-candidate-0518', 'wei')),
        cities=('nanjun', 'yiyang', 'xincheng', 'xiangyang'),
        people=('san14-candidate-0147', 'san14-candidate-0518', 'san14-candidate-0952', 'san14-candidate-0521'),
        approaches=('nanjun', 'xincheng'),
        targets=('xiangyang', 'yiyang'),
        note='襄樊之戰・關羽北攻。',
    ),
    'historical_memorial': Chapter(
        start=(227, 2), end=(227, 12),
        leaders=(('shu', 'san14-candidate-0945'),),
        holdings=(('shujun', 'shu'), ('hanzhong', 'shu')),
        officers=(('san14-candidate-0440', 'shu'),),
        cities=('shujun', 'hanzhong'),
        people=('san14-candidate-0440', 'san14-candidate-0945'),
        note='諸葛亮上出師表。',
    ),
    'historical_wuzhang': Chapter(
        start=(234, 2), end=(234, 8),
        leaders=(('shu', 'san14-candidate-0945'), ('wei', 'san14-candidate-0501')),
        holdings=(('hanzhong', 'shu'), ('fufeng', 'wei')),
        officers=(('san14-candidate-0440', 'shu'), ('san14-candidate-0344', 'wei')),
        cities=('hanzhong', 'fufeng'),
        people=('san14-candidate-0440', 'san14-candidate-0344'),
        approaches=('hanzhong',),
        targets=('fufeng',),
        note='諸葛亮進軍五丈原。',
    ),
    'historical_gaopingling': Chapter(
        start=(249, 1), end=(249, 1),
        leaders=(('wei', 'san14-candidate-0529'),),
        holdings=(('henan', 'wei'),),
        officers=(('san14-candidate-0344', 'wei'), ('san14-candidate-0522', 'wei')),
        cities=('henan',),
        people=('san14-candidate-0344', 'san14-candidate-0522', 'san14-candidate-0529'),
        note='高平陵之變。',
    ),
    'historical_wei_invades_shu': Chapter(
        start=(263, 5), end=(263, 11),
        leaders=(('wei', 'san14-candidate-0503'), ('shu', 'san14-candidate-0945')),
        holdings=(('hanzhong', 'shu'), ('shujun', 'shu')),
        officers=(('san14-candidate-0406', 'wei'), ('san14-candidate-0720', 'wei')),
        cities=('fufeng', 'wudu', 'hanzhong'),
        people=('san14-candidate-0406', 'san14-candidate-0720', 'san14-candidate-0503', 'san14-candidate-0945'),
        approaches=('fufeng', 'jingzhao', 'longxi'),
        targets=('hanzhong', 'wudu'),
        note='魏軍奉詔伐蜀。',
    ),
}
