"""Dated population estimates for the 18 new commandery seats.

Each estimate covers the seat and nearby settlements. The historical household
and population references are in docs/han-wei-commanderies.md.
"""

OPENINGS = {
    # Central Plain and Xu–Qing. Cao Cao's campaigns in Xu and the unrest and
    # famine of the 190s broke up the earlier Han settlement pattern.
    'liang': (
        ((184, 2), 47_900), ((194, 6), 33_600), ((196, 6), 26_200),
        ((207, 9), 27_300), ((221, 7), 29_700), ((263, 5), 35_500),
    ),
    'pengcheng': (
        ((184, 2), 61_600), ((190, 1), 57_900), ((193, 7), 54_200), ((194, 6), 26_800),
        ((198, 12), 15_900), ((207, 9), 16_900), ((238, 1), 18_200), ((263, 5), 19_300),
    ),
    'lu': (
        ((184, 2), 68_600), ((190, 1), 54_800), ((194, 6), 35_400),
        ((202, 6), 18_600), ((221, 7), 12_600), ((263, 5), 16_300),
    ),
    'lean': (
        ((184, 2), 47_100), ((192, 12), 24_300), ((200, 1), 21_300),
        ((207, 9), 23_100), ((221, 7), 25_200), ((263, 5), 32_400),
    ),
    'chengyang': (
        ((198, 12), 19_600), ((207, 9), 20_800), ((221, 7), 22_600),
        ((238, 1), 26_700), ((263, 5), 30_400),
    ),
    'dongguan': (
        ((198, 12), 14_900), ((207, 9), 16_400), ((221, 7), 18_300),
        ((238, 1), 23_700), ((263, 5), 27_300),
    ),
    # Seats on the Huai and upper Han rivers. Ruyin also has a Tai Shi
    # restoration date. Yiyang here is 弋陽 in former Runan territory.
    'ruyin': (
        ((222, 1), 19_500), ((238, 1), 22_300), ((249, 1), 24_100),
        ((259, 12), 25_100), ((266, 1), 25_600),
    ),
    'nanxiang': (
        ((208, 9), 23_700), ((221, 7), 22_500), ((238, 1), 27_400),
        ((249, 1), 31_200), ((263, 5), 33_600),
    ),
    'yiyang_runan': (
        ((218, 1), 21_500), ((227, 2), 22_100), ((249, 1), 26_500), ((263, 5), 29_700),
    ),
    # North China. Youbeiping's profile spans the late Han frontier upheavals
    # and Cao Wei recovery. Zhangwu has a separate Jin reopening anchor.
    'leling': (
        ((213, 1), 22_500), ((221, 7), 25_900), ((244, 1), 35_800), ((263, 5), 43_700),
    ),
    'zhangwu': (
        ((215, 1), 16_200), ((221, 7), 18_400), ((249, 1), 24_100), ((265, 1), 25_500),
    ),
    'youbeiping': (
        ((184, 2), 13_400), ((188, 6), 11_700), ((198, 3), 9_400),
        ((207, 9), 9_100), ((221, 7), 12_300), ((263, 5), 16_500),
    ),
    'guangping': (
        ((221, 1), 28_300), ((238, 1), 33_600), ((249, 1), 35_200), ((263, 5), 38_400),
    ),
    'leping': (
        ((215, 1), 8_400), ((221, 7), 9_100), ((249, 1), 12_500), ((263, 5), 13_700),
    ),
    # Hexi. Xihai is the small Juyan jurisdiction. Rile uses a separate
    # southeastern Zhangye profile with a dip around the Hexi unrest in 220.
    'xihai': (
        ((195, 1), 4_700), ((221, 1), 5_500), ((249, 1), 6_800), ((263, 5), 7_400),
    ),
    'xijun': (
        ((194, 6), 7_800), ((215, 8), 7_600), ((221, 7), 5_600),
        ((238, 1), 6_200), ((263, 5), 7_300),
    ),
    # Both southern seats first become playable during the campaign.
    'shixing': (((265, 1), 13_700),),
    'shian': (((265, 1), 16_400),),
}
