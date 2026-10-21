"""Japanese runtime notices retain real names, numbers and message meanings."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def translate(text, data):
    """Exercise the resource contract, without a browser or game-state edits."""
    if text in data['exact']:
        return data['exact'][text]
    for row in data['patterns']:
        match = re.fullmatch(row['pattern'], text)
        if match:
            return re.sub(r'\$(\d+)', lambda token: translate(match.group(int(token.group(1))) or '', data),
                          row['replacement'])
    words = {**dict(data['terms']), **data['names'], **data['exact']}
    expression = '|'.join(re.escape(key) for key in sorted(words, key=lambda value: (-len(value), value)))
    return re.sub(expression, lambda match: words[match[0]], text) if expression else text


class MessageLocaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'game/locales/messages-ja.json').read_text())
        cls.catalog = json.loads((ROOT / 'game/data/main-scenarios-v11/217-07.json').read_text())

    def test_all_runtime_game_errors_have_a_japanese_translation(self):
        checked = set()
        for path in (ROOT / 'source/remake').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == 'GameError' and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    continue
                text = node.args[0].value
                checked.add(text)
                self.assertIn(text, self.data['exact'], (str(path), node.lineno, text))
                self.assertNotEqual(text, translate(text, self.data))
        self.assertGreater(len(checked), 60)

    def test_all_thousand_officer_identities_keep_the_existing_name_crosswalk(self):
        self.assertEqual(len(self.catalog['people']), 1000)
        ids = set()
        for person in self.catalog['people']:
            ids.add(person['person_id'])
            japanese = person['ability_source']['source_name']
            self.assertEqual(translate(person['name'], self.data), japanese)
            self.assertEqual(translate(japanese, self.data), japanese)
        self.assertEqual(len(ids), 1000)
        self.assertEqual(translate('乐𬘭', self.data), '楽綝')
        self.assertEqual(translate('马云𫘧', self.data), '馬雲騄')
        self.assertEqual(translate('吴郡', self.data), '呉郡')
        self.assertEqual(translate('长安', self.data), '長安')

    def test_every_city_and_period_label_is_a_complete_japanese_name(self):
        for city in self.catalog['cities']:
            self.assertIn(city['name'], self.data['names'])
            for period in self.catalog.get('city_history', {}).get(city['id'], {}).get('names', []):
                self.assertIn(period['name'], self.data['names'])
        for source, japanese in {'犍为': '犍為', '临贺': '臨賀', '弘农': '弘農',
                                 '扶风': '扶風', '张掖': '張掖', '雁门': '雁門',
                                 '蕲春': '蘄春', '赵国': '趙国', '汉寿': '漢寿',
                                 '甘陵': '甘陵', '官渡': '官渡の戦い', '赤壁': '赤壁の戦い'}.items():
            self.assertEqual(translate(source, self.data), japanese)

    def test_latest_catalog_rule_notes_and_chronology_are_japanese_prose(self):
        for text in self.catalog['design_notes'] + [self.catalog['main_scenario']['city_chronology_note']]:
            with self.subTest(text=text):
                translated = translate(text, self.data)
                self.assertNotEqual(translated, text)
                self.assertRegex(translated, '[ぁ-ゖァ-ヶ]')

    def test_dlc_scope_notes_have_japanese_prose_without_changing_sources(self):
        data = json.loads((ROOT / 'game/data/main-scenarios-v12/225-07.json').read_text())
        for text in data['design_notes']:
            self.assertIn(text, self.data['exact'])
            self.assertRegex(translate(text, self.data), '[ぁ-ゖァ-ヶ]')
        custom = json.loads((ROOT / 'game/config/dlc-scenarios.json').read_text())
        note = next(row['scope_note'] for row in custom['entries'] if row['year'] == 211)
        self.assertIn(note, self.data['exact'])

    def test_battle_personnel_and_travel_messages_translate_captured_values(self):
        cases = {
            '217年7月　张辽寻访赵云，招募未获应允，花费60金。':
                '217年7月　張遼が趙雲を訪問。登用結果：拒否。金60を消費しました。',
            '周瑜劝说张飞，转属成功，花费100金。':
                '周瑜が張飛を勧誘。結果：仕官先の変更に成功。金100を消費しました。',
            '关羽攻击张辽，损兵17。': '関羽が張遼を攻撃。17の兵力損耗。',
            '十面埋伏触发，张辽损兵75。': '十面埋伏が発動。張遼に75の兵力損耗。',
            '诸葛亮与司马懿开始单挑。': '諸葛亮と司馬懿が一騎討ちを開始しました。',
            '本方突击，对方佯攻；体力损伤3/14。': '自軍：突撃、相手：陽動。体力損耗は自軍3／相手14。',
            '战果已结算，合计损兵217，劝降兵员32入城。': '戦果を精算しました。合計兵力損耗217、降伏兵32を都市に収容しました。',
            '221年8月　探索航行成功抵达夷洲，发现朱崖—夷洲海路，现已显示在地图上。':
                '221年8月　探索部隊が夷洲に到着。朱崖―夷洲航路を発見し、地図に表示しました。',
            '行军3因出发城失陷或人员退场取消。': '行軍3は出発都市の陥落、または参加武将の退場により中止されました。',
            '行军2到达成都，3将入城。': '行軍2が成都に到着。武将3人が入城しました。',
            '本城已满30人，招募未执行。': 'この都市は定員30人に達しているため、登用は行いませんでした。',
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(translate(source, self.data), expected)

    def test_storm_and_special_route_numbers_survive_japanese_display(self):
        source = ('221年8月　行军1遭遇西南季风顺风及暴风雨：全程减员80–90%，'
                  '全程兵员由999减至109，伤亡890；减员只结算一次。')
        result = translate(source, self.data)
        self.assertEqual(result, '221年8月　行軍1：南西季節風・追い風と暴風雨：全行程の兵力損耗80–90%。全行程の兵力999→109、損耗890。損耗の精算は一度のみ。')
        self.assertEqual(translate('子午谷暴雨：减员50%', self.data), '子午谷の豪雨：兵力損耗50%')
        self.assertEqual(translate('阴平险道：全军最终余三分之一', self.data), '陰平の険路：到着時の兵力は出発時の3分の1')
        result = translate('3将从汉中出发，至长安约323.8公里、44日，2个月回合后到达，耗粮15。', self.data)
        self.assertEqual(result, '武将3人が漢中から出発。長安まで約323.8km・44日、2か月ターン後に到着予定です。兵糧15を消費しました。')

    def test_message_resource_rebuild_is_deterministic_and_does_not_edit_catalog(self):
        path = ROOT / 'game/locales/messages-ja.json'
        before = path.read_bytes()
        catalog_path = ROOT / 'game/data/main-scenarios-v11/217-07.json'
        original = catalog_path.read_bytes()
        subprocess.run([sys.executable, '-B', 'game/build_message_locales.py'], cwd=ROOT,
                       check=True, capture_output=True)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(catalog_path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
