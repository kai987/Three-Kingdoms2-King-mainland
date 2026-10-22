"""Direction, month-boundary and exact integer losses for pure route quotes."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.route_hazards import allocate_survivors,evaluate_leg,route_allowed


def fixture():
    return dict(travel_hazards={},travel_rules=dict(speeds=dict(plain=30,sea=70),embark_days=2),
        city_coordinates=dict(southwest=[110,20],northeast=[120,30]))


def land(a,b,distance=300):
    return dict(id=f'{a}:{b}:land',**{'from':a,'to':b},mode='land',terrain='mountain',
                distance_km=distance,land_km=distance,sea_km=0,days=20)


class RouteHazardTests(unittest.TestCase):
    def data(self):
        value=fixture();value['travel_hazards']={'schema':'hazard-test'}
        return value

    def test_yinping_is_directed_and_uses_plain_baseline_not_mountain_days(self):
        data=self.data();raw=land('yinping','shujun');before=deepcopy(raw)
        self.assertTrue(route_allowed(data,raw,'yinping','shujun'))
        self.assertFalse(route_allowed(data,raw,'shujun','yinping'))
        self.assertFalse(route_allowed(data,raw,'yinping','elsewhere'))
        q=evaluate_leg(data,raw,'yinping','shujun',7)
        self.assertEqual(q['base_days'],10);self.assertEqual(q['days'],20)
        self.assertEqual(q['hazard']['survival_numerator'],1)
        self.assertEqual(q['hazard']['survival_denominator'],3)
        self.assertEqual(q['id'],raw['id']);self.assertEqual(raw,before)
        with self.assertRaises(ValueError):evaluate_leg(data,raw,'shujun','yinping',7)
        self.assertEqual(sum(allocate_survivors([1000]*30,1,3)),10000)

    def test_ziwu_july_through_september_is_four_times_plain_time(self):
        data=self.data();raw=land('hanzhong','jingzhao');raw['special']='ziwu'
        for month in range(1,13):
            for source,target in [('hanzhong','jingzhao'),('jingzhao','hanzhong')]:
                q=evaluate_leg(data,raw,source,target,month);rain=7<=month<=9
                self.assertEqual(q['days'],40 if rain else 20)
                self.assertEqual(q['base_days'],10)
                self.assertEqual((q['from'],q['to']),(source,target))
                self.assertEqual(q['hazard']['loss_percent'],50 if rain else 20)
                self.assertEqual(sum(allocate_survivors([1000]*30,
                    q['hazard']['survival_numerator'],q['hazard']['survival_denominator'])),15000 if rain else 24000)
        ordinary=deepcopy(raw);ordinary['special']='other_mountain_road'
        self.assertIsNone(evaluate_leg(data,ordinary,'hanzhong','jingzhao',7)['hazard'])

    def test_monsoon_direction_reversal_speeds_and_winter_reversal(self):
        data=self.data()
        raw=dict(id='sea-test',**{'from':'southwest','to':'northeast'},mode='sea',
                 distance_km=1200,land_km=0,sea_km=1200,days=20)
        for month in (5,7,9):
            following=evaluate_leg(data,raw,'southwest','northeast',month)
            opposing=evaluate_leg(data,raw,'northeast','southwest',month)
            self.assertEqual(following['days'],12)
            self.assertEqual(opposing['days'],162)
            self.assertEqual(following['hazard']['speed_km_per_day'],120)
            self.assertEqual(opposing['hazard']['speed_km_per_day'],7.5)
            self.assertEqual(following['hazard']['wind'],'tailwind')
            self.assertEqual(opposing['hazard']['wind'],'headwind')
            self.assertEqual(following['hazard']['season'],'southwest_monsoon')
        for month in (10,12,1,3):
            reverse=evaluate_leg(data,raw,'northeast','southwest',month)
            self.assertEqual(reverse['days'],12)
            self.assertEqual(reverse['hazard']['season'],'northeast_monsoon')
        calm=evaluate_leg(data,raw,'southwest','northeast',4)
        self.assertEqual(calm['days'],raw['days']);self.assertIsNone(calm['hazard'])

    def test_sea_access_uses_plain_speed_and_storm_quote_does_not_roll_severity(self):
        data=self.data();raw=dict(id='access-sea',**{'from':'southwest','to':'northeast'},
            mode='sea',distance_km=1231,land_km=31,sea_km=1200,days=22)
        before=deepcopy((data,raw))
        q=evaluate_leg(data,raw,'southwest','northeast',9)
        self.assertEqual(q['days'],14)  #2 access +10 sailing +2 embark
        self.assertEqual(q['hazard']['loss_percent_min'],80)
        self.assertEqual(q['hazard']['loss_percent_max'],90)
        self.assertIsNone(q['hazard']['loss_percent'])
        self.assertEqual(q,evaluate_leg(data,raw,'southwest','northeast',9))
        self.assertEqual((data,raw),before)

    def test_proportional_integer_survivors_conserve_total_and_never_create_men(self):
        for counts in ([],[0],[1],[1,1,1],[0,1,2,999,1000],[999]*30,[1000]*30,[1000]*99):
            for numerator,denominator in ((1,3),(1,2),(4,5),(1,5),(1,10),(0,1),(1,1)):
                survivors=allocate_survivors(counts,numerator,denominator)
                self.assertEqual(sum(survivors),sum(counts)*numerator//denominator)
                self.assertTrue(all(0<=new<=old for new,old in zip(survivors,counts)))
                self.assertEqual(survivors,allocate_survivors(counts,numerator,denominator))
        self.assertEqual(allocate_survivors([1,1,1],1,3),[1,0,0])
        self.assertEqual(allocate_survivors([1,2],1,3),[0,1])
        self.assertEqual(allocate_survivors([0,1],1,1),[0,1])

    def test_invalid_months_ratios_and_troop_counts_are_rejected(self):
        for numerator,denominator in ((-1,3),(4,3),(1,0),(True,3),(1,1.0)):
            with self.assertRaises(ValueError):allocate_survivors([300],numerator,denominator)
        for troops in ([-1],[1.5],[True]):
            with self.assertRaises(ValueError):allocate_survivors(troops,1,3)
        for month in (0,13,True,1.5):
            with self.assertRaises(ValueError):evaluate_leg(self.data(),land('a','b'),'a','b',month)


if __name__=='__main__':unittest.main()
