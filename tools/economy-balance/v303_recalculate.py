"""Verify and recalculate V3.0.3 headline results from an unpacked summary."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
from hashlib import file_digest
import json
from pathlib import Path


def rows(data, name):
    with (data / f"{name}.csv").open(encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def verify_files(summary):
    manifest = summary / "SHA256SUMS.txt"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        file = (summary / name).resolve()
        if not file.is_relative_to(summary):
            raise ValueError(f"Invalid path in checksum manifest: {name}")
        with file.open("rb") as stream:
            if file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(f"SHA-256 mismatch: {name}")


def demand(data):
    groups = defaultdict(Counter)
    allowed = {"ordinary", "strategic", "regional"}
    for row in rows(data, "transport-capability-funnel"):
        values = groups[row["group"]]
        values["targets"] += 1
        if row["l5_actual_reception"] == "null":
            continue
        grain = sum(receipt["cargo"]["grain"] for receipt in json.loads(row["l5_actual_receipts"])
                    if receipt["purpose"] in allowed)
        values["l5_received"] += grain
        values["l5_with_supply"] += grain > 0
        values["l5_full"] += grain >= int(row["first_uncovered_grain"])
    for row in rows(data, "capacity-counterfactual"):
        values = groups[row["group"]]
        values["returning_samples"] += 1
        values["timely_quote_sample"] += bool(json.loads(row["timely_quotes"]))
    return groups


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path, help="Location of the unpacked summary directory")
    summary = parser.parse_args().summary.resolve()
    verify_files(summary)
    data = summary / "data"
    status = json.loads((data / "report-status.json").read_text(encoding="utf-8"))
    routes = list(rows(data, "transport-capacity-by-route"))
    if len(routes) != status["route_census"]["direction_rows"]:
        raise ValueError("Route count disagrees with report")
    if len({row["scenario"] for row in routes}) != status["route_census"]["scenario_count"]:
        raise ValueError("Scenario count disagrees with report")
    groups = demand(data)
    for group, counts in groups.items():
        for key, value in counts.items():
            if status["fixed"][group].get(key, 0) != value:
                raise ValueError(f"Fixed-demand result disagrees with report: {group} {key}")
    receipts = list(rows(data, "transport-dispatch-receipts"))
    issues = sum(sum(json.loads(row["ledger_issues"]).values()) for row in receipts)
    if issues != status["accounting_issues"]:
        raise ValueError("Transport ledger issue count disagrees with report")
    print(json.dumps(dict(routes=len(routes), departures=len(receipts), ledger_issues=issues,
                          fixed_demand=groups), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
