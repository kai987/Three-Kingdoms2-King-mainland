"""Opening active soldiers calibrated to Romance of the Three Kingdoms XIV."""

# Source tables: https://wikiwiki.jp/sangokushi14/メインシナリオ
# Keys match the reference scenario month except for these adaptations:
# - 212-12: interpolate between historical 211-07 and 215-08, to the nearest
#   1,000. Liu Zhang and Zhang Lu retain their July 211 and June 212 counts.
# - 263-05: use August 263, the reference game's fall of Shu scenario.
# When the reference lists only one Western Liang force, its total is split
# between the local Ma and Han factions in proportion to their former openings.
# The Liaodong and Ma faction IDs also cover their successors in either game.
OPENING_TROOPS = {
    'mainland184-02': {
        'ding_yuan': 16_000, 'dong_zhuo': 20_000, 'gongsun_zan': 18_000, 'han': 124_000,
        'liu_yan': 20_000, 'ma_teng': 16_000, 'shi_xie': 8_000, 'wu': 14_000,
        'yellow_turban': 270_000,
    },
    'mainland188-06': {
        'ding_yuan': 18_000, 'dong_zhuo': 25_000, 'han': 176_000, 'han_sui': 12_000,
        'liu_yan': 22_000, 'liu_yu': 23_000, 'ma_teng': 11_000, 'shi_xie': 13_000,
        'sun_jian': 16_000, 'zhang_chun': 34_000,
    },
    'mainland190-01': {
        'dong_zhuo': 164_000, 'gongsun': 14_000, 'gongsun_zan': 23_000, 'han_fu': 30_000,
        'han_sui': 5_391, 'kong_rong': 20_000, 'kong_zhou': 18_000, 'liu_biao': 22_000,
        'liu_dai': 21_000, 'liu_yan': 23_000, 'liu_yu': 28_000, 'ma_teng': 15_609,
        'shi_xie': 14_000, 'shu': 7_000, 'sun_jian': 19_000, 'tao_qian': 22_000,
        'wei': 13_000, 'yuan_shao': 26_000, 'yuan_shu': 25_000, 'zhang_chao': 12_000,
        'zhang_yang': 17_000,
    },
    'mainland191-10': {
        'dong_zhuo': 120_000, 'gongsun': 15_000, 'gongsun_zan': 32_000, 'han_sui': 5_615,
        'kong_rong': 18_000, 'liu_biao': 25_000, 'liu_dai': 25_000, 'liu_yan': 26_000,
        'liu_yu': 28_000, 'ma_teng': 17_385, 'shi_xie': 16_000, 'shu': 9_000,
        'sun_jian': 22_000, 'tao_qian': 26_000, 'wei': 14_000, 'yuan_shao': 46_000,
        'yuan_shu': 39_000, 'zhang_chao': 12_000, 'zhang_yang': 17_000,
    },
    'mainland194-06': {
        'gongsun': 16_000, 'gongsun_zan': 48_000, 'han_sui': 5_713, 'kong_rong': 16_000,
        'li_jue': 43_000, 'liu_biao': 27_000, 'liu_you': 23_000, 'liu_zhang': 28_000,
        'lubu': 28_000, 'ma_teng': 22_287, 'shi_xie': 18_000, 'shu': 14_000,
        'tao_qian': 10_000, 'wang_lang': 20_000, 'wei': 26_000, 'yuan_shao': 60_000,
        'yuan_shu': 46_000, 'zhang_lu': 16_000, 'zhang_yang': 20_000,
    },
    'mainland196-06': {
        'gongsun': 18_000, 'gongsun_zan': 54_000, 'han_sui': 5_713, 'kong_rong': 15_000,
        'li_jue': 29_000, 'liu_biao': 31_000, 'liu_zhang': 30_000, 'lubu': 16_000,
        'ma_teng': 22_287, 'shi_xie': 18_000, 'shu': 20_000, 'wei': 49_000,
        'wu': 24_000, 'yuan_shao': 75_000, 'yuan_shu': 62_000, 'zhang_lu': 17_000,
        'zhang_yang': 21_000,
    },
    'mainland197-07': {
        'gongsun': 19_000, 'gongsun_zan': 58_000, 'han_sui': 5_917, 'li_jue': 23_000,
        'liu_biao': 33_000, 'liu_zhang': 31_000, 'lubu': 90_000, 'ma_teng': 23_083,
        'shi_xie': 18_000, 'shu': 16_000, 'wei': 72_000, 'wu': 25_000,
        'yuan_shao': 81_000, 'zhang_lu': 17_000, 'zhang_xiu': 17_000, 'zhang_yang': 22_000,
    },
    'mainland198-03': {
        'gongsun': 20_000, 'gongsun_zan': 60_000, 'han_sui': 5_450, 'liu_biao': 34_000,
        'liu_zhang': 31_000, 'lubu': 40_000, 'ma_teng': 24_550, 'shi_xie': 18_000,
        'shu': 16_000, 'wei': 76_000, 'wu': 26_000, 'yuan_shao': 89_000,
        'yuan_shu': 51_000, 'zhang_lu': 18_000, 'zhang_xiu': 17_000, 'zhang_yang': 22_000,
    },
    'mainland200-01': {
        'gongsun': 19_000, 'han_sui': 5_609, 'liu_biao': 37_000, 'liu_zhang': 34_000,
        'ma_teng': 26_391, 'shi_xie': 21_000, 'shu': 20_000, 'wei': 87_000,
        'wu': 53_000, 'yuan_shao': 174_000, 'zhang_lu': 21_000,
    },
    'mainland201-05': {
        'gongsun': 18_000, 'han_sui': 5_883, 'liu_biao': 37_000, 'liu_zhang': 34_000,
        'ma_teng': 36_117, 'shi_xie': 21_000, 'shu': 32_000, 'wei': 24_000,
        'wu': 52_000, 'yuan_shao': 228_000, 'zhang_lu': 21_000,
    },
    'mainland202-06': {
        'gao_gan': 22_000, 'gongsun': 20_000, 'han_sui': 5_959, 'liu_biao': 38_000,
        'liu_zhang': 35_000, 'ma_teng': 28_041, 'shi_xie': 21_000, 'shu': 6_000,
        'wei': 147_000, 'wu': 54_000, 'yuan_shang': 73_000, 'yuan_tan': 40_000,
        'zhang_lu': 21_000,
    },
    'mainland207-09': {
        'gongsun': 23_000, 'han_sui': 6_485, 'liu_biao': 40_000, 'liu_zhang': 38_000,
        'ma_teng': 30_515, 'shi_xie': 22_000, 'shu': 10_000, 'wei': 204_000,
        'wu': 66_000, 'zhang_lu': 22_000,
    },
    'mainland208-10': {
        'gongsun': 20_000, 'han_sui': 7_644, 'han_xuan': 10_000, 'jin_xuan': 9_000,
        'liu_du': 8_000, 'liu_zhang': 38_000, 'ma_teng': 31_356, 'shi_xie': 22_000,
        'shu': 14_000, 'wei': 254_000, 'wu': 68_000, 'zhang_lu': 22_000,
        'zhao_fan': 9_000,
    },
    'mainland209-06': {
        'gongsun': 20_000, 'han_sui': 7_011, 'liu_zhang': 41_000, 'ma_teng': 32_989,
        'shi_xie': 23_000, 'shu': 11_000, 'wei': 339_000, 'wu': 44_000,
        'zhang_lu': 24_000,
    },
    'mainland210-11': {
        'gongsun': 20_000, 'han_sui': 7_276, 'ma_teng': 35_724, 'shi_xie': 23_000,
        'shu': 40_000, 'wei': 236_000, 'wu': 154_000,
    },
    'mainland211-07-tongguan': {
        'gongsun': 21_000, 'han_sui': 10_118, 'liu_zhang': 42_000, 'ma_teng': 49_882,
        'shi_xie': 14_000, 'shu': 57_000, 'wei': 238_000, 'wu': 72_000,
        'zhang_lu': 25_000,
    },
    'mainland212-06': {
        'cao_zhang': 46_000, 'gongsun': 17_000, 'han_sui': 10_694, 'liu_zhang': 42_000,
        'ma_teng': 64_306, 'shi_xie': 14_000, 'shu': 64_000, 'wei': 178_000,
        'wu': 73_000, 'zhang_lu': 25_000,
    },
    'mainland212-12': {
        'gongsun': 21_000, 'liu_zhang': 42_000, 'shi_xie': 14_000, 'shu': 68_000,
        'wei': 242_000, 'wu': 81_000, 'zhang_lu': 25_000,
    },
    'mainland215-08': {
        'gongsun': 21_000, 'shi_xie': 15_000, 'shu': 90_000, 'wei': 250_000,
        'wu': 97_000,
    },
    'mainland217-07': {
        'gongsun': 20_000, 'shi_xie': 15_000, 'shu': 106_000, 'wei': 255_000,
        'wu': 94_000,
    },
    'mainland219-07': {
        'gongsun': 20_000, 'shi_xie': 15_000, 'shu': 113_000, 'wei': 254_000,
        'wu': 98_000,
    },
    'mainland221-07': {
        'gongsun': 20_000, 'shi_xie': 15_000, 'shu': 112_000, 'wei': 251_000,
        'wu': 116_000,
    },
    'mainland225-07': {
        'gongsun': 20_000, 'nanman': 29_000, 'shi_xie': 16_000, 'shu': 91_000,
        'wei': 262_000, 'wu': 117_000,
    },
    'mainland227-02': {
        'gongsun': 22_000, 'shu': 96_000, 'wei': 268_000, 'wu': 120_000,
    },
    'mainland234-02': {
        'gongsun': 27_000, 'shu': 105_000, 'wei': 286_000, 'wu': 124_000,
    },
    'mainland235-01': {
        'gongsun': 27_000, 'shu': 130_000, 'wei': 279_000, 'wu': 125_000,
    },
    'mainland238-01': {
        'gongsun': 40_000, 'shu': 98_000, 'wei': 303_000, 'wu': 126_000,
    },
    'mainland249-01': {
        'shu': 108_000, 'wei': 282_000, 'wu': 129_000,
    },
    'mainland263-05': {
        'shu': 112_000, 'wei': 344_000, 'wu': 136_000,
    },
}
