#!/usr/bin/env python3
"""Build an offline, auditable SAN14 candidate roster from saved source pages.

This prepares research data. It does not modify a ROM, import SAN14 assets, or
claim that third-party game-setting years are historically established dates.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from collections import Counter, defaultdict

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "source"
DATA = BASE / "data"
OFFICIAL_TW = "https://www.gamecity.com.tw/sangokushi14/officers-list.html"
OFFICIAL_JP = "https://www.gamecity.ne.jp/sangokushi14/officers-list.html"
CHRONOLOGY_URL = "https://xgodgame.blogspot.com/2020/02/14_9.html"
PROPER_NAME_SIMPLIFICATION = {"孫乾": "孙乾"}

# These are differences observed at the same position in both 1000-row source
# tables, not a claim that every spelling is a historically certified alias.
NAME_DISCREPANCIES = {
    797: ("閔純", "關純", "name_variant_requires_historical_review"),
    875: ("羊衜", "羊", "third_party_name_truncated"),
    876: ("楊白", "楊柏", "name_variant_requires_historical_review"),
    990: ("綸直", "倫直", "name_variant_requires_historical_review"),
}

# Labels distinguish separate people in the source chronology. They are not
# new aliases and they do not convert the public list number into a game ID.
HOMONYM_LABELS = {
    173: "黄巾军，第三方设定151—184",
    174: "辽东公孙氏，第三方设定170—213",
    634: "孙吴系，第三方设定178—244",
    635: "东汉、曹操系，第三方设定156—215",
    651: "袁绍、曹操系，第三方设定168—208",
    652: "蜀汉刘备系，第三方设定187—222",
    767: "孙吴系，第三方设定186—222",
    768: "蜀汉系，第三方设定187—249",
    917: "蜀汉系，第三方设定202—260",
    918: "曹魏系，第三方设定204—254",
    919: "袁术系，第三方设定158—199",
}


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
            self.tables.append(self.table)
        elif tag == "tr" and self.table is not None:
            self.row = []
            self.table.append(self.row)
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr":
            self.row = None
        elif tag == "table":
            self.table = None


def read_official(filename):
    text = (SOURCE / filename).read_text(encoding="utf-8")
    rows = re.findall(r"<div>\s*(\d+)\s*<b>(.*?)</b>(.*?)</div>", text)
    result = []
    for number, name, reading in rows:
        result.append({
            "official_list_number": int(number),
            "name": html.unescape(name).strip(),
            "reading": html.unescape(reading).strip().strip("（）"),
        })
    assert [r["official_list_number"] for r in result] == list(range(1, 1001))
    assert all(not re.search(r"[<>]", r["name"]) for r in result)
    return result


def load_converter():
    # Source dictionaries are pinned and licensed in the source manifest.
    # For short names a longest-prefix scan is transparent and sufficient.
    mapping = {}
    for filename in ("opencc-TSPhrases.txt", "opencc-TSCharacters.txt"):
        for line in (SOURCE / filename).read_text(encoding="utf-8").splitlines():
            if "\t" in line and not line.startswith("#"):
                key, values = line.split("\t", 1)
                mapping.setdefault(key, values.split()[0])

    def convert(value):
        output, index = [], 0
        while index < len(value):
            key = next((value[index:index + size]
                        for size in range(len(value) - index, 0, -1)
                        if value[index:index + size] in mapping), value[index])
            output.append(mapping.get(key, key))
            index += len(key)
        return "".join(output)
    return convert


def parse_scenario(raw):
    if raw.lower() == "x":
        return {"status": "dead", "city_source_name": None,
                "ruler_source_name": None, "raw": raw}
    match = re.fullmatch(r"(.+?)\(([未野-])\)", raw)
    if match:
        statuses = {"-": "not_appeared", "未": "undiscovered", "野": "free"}
        return {"status": statuses[match[2]], "city_source_name": match[1],
                "ruler_source_name": None, "raw": raw}
    if raw and "(" not in raw:
        return {"status": "serving", "city_source_name": None,
                "ruler_source_name": raw, "raw": raw}
    raise ValueError(f"Unparsed scenario state: {raw!r}")


def write_json(filename, value):
    (DATA / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")


def write_csv(filename, rows, columns):
    with (DATA / filename).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def original_overlap_audit(people):
    """Only join names actually transcribed in prior local evidence."""
    root = BASE.parents[1]
    portal_source = root / "scripts/make_portal.py"
    tree = ast.parse(portal_source.read_text(encoding="utf-8"))
    known = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "known"
                                               for t in node.targets):
            known = ast.literal_eval(node.value)
    assert known is not None and len(known) == 8
    tables = json.loads((root / "analysis/game_data/recovered_tables.json").read_text())
    original_ids = {record["id"] for record in tables["second_table"]["records"]}
    assert len(original_ids) == 237
    rows = []
    for original_id, source_name in known.items():
        matches = [p for p in people if source_name in p["search_aliases"]]
        assert original_id in original_ids and len(matches) == 1
        rows.append({"original_officer_id": original_id, "original_transcribed_name": source_name,
                     "candidate_person_id": matches[0]["person_id"],
                     "official_list_number": matches[0]["official_list_number"],
                     "candidate_name_traditional": matches[0]["name_traditional"],
                     "match_method": "exact_retained_chinese_or_japanese_search_form",
                     "identity_source": "scripts/make_portal.py:12"})
    return {
        "original_officer_count": len(original_ids), "candidate_officer_count": len(people),
        "original_name_transcriptions_available": len(known),
        "matched_original_name_transcriptions": len(rows),
        "original_ids_without_transcribed_identity": sorted(original_ids - known.keys()),
        "original_unresolved_count": len(original_ids - known.keys()),
        "confirmed_union_size": None, "confirmed_net_new_people": None,
        "reason": "229 original records have no retained name transcription. Do not claim that original237 plus official1000 has exactly1000 unique people, or that net growth is763.",
        "source_file": "scripts/make_portal.py",
        "source_sha256": hashlib.sha256(portal_source.read_bytes()).hexdigest(),
        "matches": rows,
    }


def build():
    manifest = json.loads((SOURCE / "san14-source-manifest.json").read_text())
    for entry in manifest["files"]:
        path = SOURCE / entry["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], path
    traditional = read_official("san14-official-tw-officers-list.html")
    japanese = read_official("san14-official-jp-officers-list.html")
    parser = Tables()
    parser.feed((SOURCE / "san14-xgodgame-chronology.html").read_text(encoding="utf-8"))
    assert len(parser.tables) == 2
    assert all(len(t) == 1001 and len(t[0]) == 9 for t in parser.tables)
    assert all(a[:4] == b[:4] for a, b in zip(parser.tables[0][1:], parser.tables[1][1:]))
    to_simplified = load_converter()
    name_counts = Counter(row["name"] for row in traditional)
    scenario_headers = [h for t in parser.tables for h in t[0][4:]]
    scenarios = []
    for header in scenario_headers:
        match = re.fullmatch(r"(\d+)/(\d+) (.+)", header)
        assert match, header
        scenarios.append({"scenario_id": f"san14-{int(match[1])}-{int(match[2]):02d}",
                          "year": int(match[1]), "month": int(match[2]),
                          "source_label": match[3],
                          "historical_timeline": int(match[1]) != 251,
                          "note": "英雄集结为跨年代虚构剧本，不参与生卒年筛选" if int(match[1]) == 251 else None})
    people, chronology_rows, scenario_rows = [], [], []
    chronological_anomalies = []
    discrepancy_audit = []
    for index, (tw, jp) in enumerate(zip(traditional, japanese)):
        number = tw["official_list_number"]
        first, second = (table[index + 1] for table in parser.tables)
        assert all(len(r) == 9 for r in (first, second))
        assert jp["official_list_number"] == number
        flags = []
        if number in NAME_DISCREPANCIES:
            expected, observed, reason = NAME_DISCREPANCIES[number]
            assert (tw["name"], first[0]) == (expected, observed)
            flags.append(reason)
            discrepancy_audit.append({"official_list_number": number,
                                      "official_name": expected, "chronology_name": observed,
                                      "reason": reason,
                                      "join_basis": "same ordinal; all 996 other rows match names; both tables agree",
                                      "historically_verified_alias": False})
        else:
            assert first[0] == tw["name"], (number, first[0], tw["name"])
        birth, appearance, death = (int(x) for x in first[1:4])
        assert birth <= appearance <= death
        person_id = f"san14-candidate-{number:04d}"
        is_homonym = name_counts[tw["name"]] > 1
        if is_homonym:
            flags.append("same_name_different_source_people_retained")
        simplified_name = PROPER_NAME_SIMPLIFICATION.get(tw["name"], to_simplified(tw["name"]))
        aliases = list(dict.fromkeys([tw["name"], simplified_name,
                                      to_simplified(tw["name"]), jp["name"]]))
        # A truncated single-character source value is not a useful alias.
        if number in NAME_DISCREPANCIES and number != 875:
            aliases.extend(x for x in (first[0], to_simplified(first[0])) if x not in aliases)
        chronology = {
            "game_birth_year": birth, "game_appearance_year": appearance,
            "game_death_year": death, "historical_birth_year": None,
            "historical_death_year": None,
            "basis": "third_party_SAN14_game_setting_transcription",
            "source": CHRONOLOGY_URL, "source_row": number,
            "source_name": first[0],
            "join_method": "official_order_and_matching_name" if number not in NAME_DISCREPANCIES
                           else "official_order_with_explicit_source_name_discrepancy",
            "independent_official_year_verification": False,
            "historical_year_verification": "pending",
        }
        if appearance - birth < 14:
            chronological_anomalies.append({"person_id": person_id, "name": tw["name"],
                                           "flag": "early_appearance_in_source_setting",
                                           "age_at_game_appearance": appearance - birth})
        source_states = first[4:] + second[4:]
        states = {}
        for scenario, raw in zip(scenarios, source_states):
            parsed = parse_scenario(raw)
            states[scenario["scenario_id"]] = parsed
            scenario_rows.append({"person_id": person_id, "official_list_number": number,
                                  "name_traditional": tw["name"],
                                  "scenario_id": scenario["scenario_id"],
                                  "scenario_year": scenario["year"],
                                  "scenario_month": scenario["month"],
                                  "historical_timeline": scenario["historical_timeline"], **parsed})
        person = {
            "person_id": person_id,
            "official_list_number": number,
            "official_number_is_internal_game_id": False,
            "name_traditional": tw["name"], "name_simplified": simplified_name,
            "name_japanese": jp["name"], "reading_japanese": jp["reading"],
            "search_aliases": aliases,
            "disambiguator": HOMONYM_LABELS.get(number),
            "homonym_group": tw["name"] if is_homonym else None,
            "identity_status": "distinct_official_roster_entry",
            "classification": {
                "historical_or_novel": "pending_individual_review",
                "gender": None, "ancient_or_guest": "not_in_this_base_official_list",
                "note": "Official list does not individually certify historical/novel or gender classifications.",
            },
            "chronology": chronology, "scenario_states": states,
            "source_refs": ["san14-official-tw", "san14-official-jp", "san14-xgodgame"],
            "review_flags": flags,
        }
        people.append(person)
        chronology_rows.append({"person_id": person_id, "official_list_number": number,
                                "name_traditional": tw["name"],
                                "name_simplified": person["name_simplified"],
                                "disambiguator": person["disambiguator"], **chronology})

    assert len({p["person_id"] for p in people}) == 1000
    assert len(chronology_rows) == 1000 and len(scenario_rows) == 10000
    homonyms = []
    for name, count in name_counts.items():
        if count > 1:
            members = [p for p in people if p["name_traditional"] == name]
            homonyms.append({"name": name, "count": count,
                             "action": "retain_distinct_people",
                             "members": [{"person_id": p["person_id"],
                                          "official_list_number": p["official_list_number"],
                                          "disambiguator": p["disambiguator"],
                                          "birth": p["chronology"]["game_birth_year"],
                                          "death": p["chronology"]["game_death_year"]} for p in members]})
    audit = {
        "schema_version": 1, "official_rows": 1000,
        "official_unique_ordinals": 1000,
        "unique_traditional_name_strings": len(name_counts),
        "unique_simplified_name_strings": len({p["name_simplified"] for p in people}),
        "same_name_groups": len(homonyms),
        "same_name_people": sum(g["count"] for g in homonyms),
        "text_only_dedup_would_wrongly_remove": sum(g["count"] - 1 for g in homonyms),
        "confirmed_duplicate_person_entries_removed": 0,
        "candidate_people_after_entity_aware_dedup": len(people),
        "chronology_rows_first_table": len(parser.tables[0]) - 1,
        "chronology_rows_second_table": len(parser.tables[1]) - 1,
        "second_table_not_counted_as_new_people": True,
        "chronology_triples_agree_between_tables": 1000,
        "official_to_chronology_exact_name_and_order": 996,
        "explicit_name_discrepancy_crosswalks": discrepancy_audit,
        "proper_name_simplification_overrides": PROPER_NAME_SIMPLIFICATION,
        "historical_birth_death_individually_verified": 0,
        "game_year_triplets_available_from_secondary_source": 1000,
        "homonyms": homonyms,
        "early_appearance_flags": chronological_anomalies,
        "interpretation": "1000 candidate people in the official base roster; 994 distinct name strings. Same-name people must not be collapsed. Game chronology is provisional secondary-source data, not certified historical dates.",
    }
    summary = {
        "schema_version": 1,
        "scope": "SAN14 official original base 1000 roster; excludes PK additions, DLC, custom officers, crossovers and ancient guests",
        "count": len(people), "source_manifest": "../source/san14-source-manifest.json",
        "id_policy": "person_id is a new project ID; official_list_number is a public list ordinal, not a verified internal SAN14 ID",
        "year_policy": "All 1000 game-setting year triplets come from a third-party transcription. Historical year fields remain null pending individual verification.",
        "dedup_policy": "Normalize search forms but retain official independent entries; never use name-only or simplified-name-only deduplication.",
        "scenarios": scenarios,
        "officers": people,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    write_json("roster-candidates.json", summary)
    write_json("dedup-audit.json", audit)
    write_json("chronology-candidates.json", {
        "source": CHRONOLOGY_URL, "basis": "third_party_game_setting",
        "historical_years_verified": False, "count": len(chronology_rows), "rows": chronology_rows})
    write_json("scenario-states.json", {"source": CHRONOLOGY_URL, "scenarios": scenarios,
                                       "count": len(scenario_rows), "rows": scenario_rows})
    roster_csv = [{"person_id": p["person_id"], "official_list_number": p["official_list_number"],
                   "name_traditional": p["name_traditional"], "name_simplified": p["name_simplified"],
                   "name_japanese": p["name_japanese"], "reading_japanese": p["reading_japanese"],
                   "disambiguator": p["disambiguator"],
                   "search_aliases": " | ".join(p["search_aliases"]),
                   "game_birth_year": p["chronology"]["game_birth_year"],
                   "game_appearance_year": p["chronology"]["game_appearance_year"],
                   "game_death_year": p["chronology"]["game_death_year"],
                   "chronology_source": CHRONOLOGY_URL,
                   "chronology_basis": "third_party_game_setting_not_historical_verification",
                   "review_flags": " | ".join(p["review_flags"])} for p in people]
    write_csv("roster-candidates.csv", roster_csv, list(roster_csv[0]))
    write_csv("chronology-candidates.csv", chronology_rows, list(chronology_rows[0]))
    write_csv("scenario-states.csv", scenario_rows, list(scenario_rows[0]))
    stats = []
    for scenario in scenarios:
        counts = Counter(p["scenario_states"][scenario["scenario_id"]]["status"] for p in people)
        stats.append({**scenario, "counts": dict(counts),
                      "active_visible": counts["serving"] + counts["free"],
                      "active_including_undiscovered": counts["serving"] + counts["free"] + counts["undiscovered"],
                      "total": sum(counts.values())})
    write_json("scenario-availability-summary.json", {"basis": "source_scenario_states_not_age_formula", "scenarios": stats})
    write_json("original-overlap-audit.json", original_overlap_audit(people))
    print(json.dumps({k: audit[k] for k in ("official_rows", "unique_traditional_name_strings",
                      "same_name_groups", "candidate_people_after_entity_aware_dedup",
                      "game_year_triplets_available_from_secondary_source")}, ensure_ascii=False))


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
