"""Opening population estimates for the map's large cities.

Dates follow the historical anchors in docs/city-development-rules.md.
Populations represent the game city's settled area, using a common game scale.
"""

OPENINGS = {
    # Jiangzhou: the Shu eastern route and Li Yan's building program in 226.
    'bajun': (
        ((184, 2), 49_000), ((194, 6), 53_000), ((212, 12), 61_000),
        ((214, 6), 58_000), ((221, 7), 62_000), ((226, 7), 68_000),
        ((238, 1), 79_000), ((263, 5), 88_000),
    ),
    # Nanzheng: Zhang Lu's rule, migration after the 215 conquest, then Shu's northern base.
    'hanzhong': (
        ((184, 2), 54_000), ((191, 10), 58_000), ((207, 9), 75_000),
        ((215, 6), 97_000), ((217, 7), 51_000), ((219, 7), 33_000),
        ((225, 7), 42_000), ((234, 2), 57_000), ((249, 1), 68_000), ((263, 5), 72_000),
    ),
    # Shouchun: Yuan Shu's seat, recovery on the Huai, and the 255–258 upheavals.
    'jiujiang': (
        ((184, 2), 62_000), ((193, 6), 67_000), ((197, 7), 83_000),
        ((200, 1), 56_000), ((215, 8), 72_000), ((233, 1), 97_000),
        ((249, 1), 111_000), ((254, 12), 117_000), ((255, 3), 82_000),
        ((258, 3), 64_000), ((263, 5), 73_000),
    ),
    # Shanyin: seat of Kuaiji, with a small interruption during the Sun Ce conquest.
    'kuaiji': (
        ((184, 2), 54_000), ((196, 6), 61_000), ((197, 7), 58_000),
        ((207, 9), 68_000), ((221, 7), 77_000), ((249, 1), 93_000), ((263, 5), 101_000),
    ),
    # Jiangling: contested after Red Cliffs, then a fortified Wu center.
    'nanjun': (
        ((184, 2), 72_000), ((194, 6), 76_000), ((207, 9), 89_000),
        ((208, 10), 83_000), ((209, 12), 74_000), ((215, 8), 83_000),
        ((219, 7), 90_000), ((221, 7), 83_000), ((223, 4), 68_000),
        ((234, 2), 85_000), ((249, 1), 96_000), ((263, 5), 104_000),
    ),
    # Wan: the Yellow Turban siege, Yuan Shu and Zhang Xiu, then the Wei frontier.
    'nanyang': (
        ((184, 2), 68_000), ((184, 12), 48_000), ((188, 6), 59_000),
        ((193, 1), 66_000), ((194, 6), 53_000), ((196, 6), 57_000),
        ((198, 3), 49_000), ((207, 9), 66_000), ((221, 7), 78_000),
        ((238, 1), 89_000), ((263, 5), 93_000),
    ),
    # Before 221 the same board node can represent Xiaopei instead of Qiao.
    'qiao': (
        ((221, 1), 71_000), ((227, 2), 76_000), ((249, 1), 84_000), ((263, 5), 87_000),
    ),
    # E/Wuchang: one site, with an increase after 221 and a smaller court after 229.
    'wuchang': (
        ((184, 2), 29_000), ((196, 6), 33_000), ((208, 10), 42_000),
        ((219, 7), 49_000), ((221, 4), 64_000), ((227, 2), 91_000),
        ((229, 8), 98_000), ((234, 2), 79_000), ((249, 1), 87_000), ((263, 5), 97_000),
    ),
    # Wu County: the early Sun regime's Jiangdong base, then a regional center.
    'wujun': (
        ((184, 2), 64_000), ((194, 6), 69_000), ((196, 6), 67_000),
        ((200, 1), 76_000), ((211, 7), 87_000), ((229, 9), 94_000),
        ((249, 1), 103_000), ((263, 5), 109_000),
    ),
    # Xiangyang: Liu Biao's center and the Wei–Wu frontier in the Han valley.
    'xiangyang': (
        ((184, 2), 71_000), ((190, 1), 76_000), ((194, 6), 87_000),
        ((207, 9), 112_000), ((208, 10), 97_000), ((219, 7), 104_000),
        ((220, 1), 94_000), ((234, 2), 102_000), ((241, 7), 96_000),
        ((249, 1), 103_000), ((263, 5), 111_000),
    ),
}
