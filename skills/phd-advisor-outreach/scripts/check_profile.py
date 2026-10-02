#!/usr/bin/env python3
"""Report which readiness gates an applicant profile passes. Read-only.

Gate A (ready to scout advisors) and gate B (ready to write emails) are marked
in the profile template with 〔A〕 / 〔B〕 at the start of a list item. A field
counts as unfilled while its value is empty or still contains 【待补】. The
script only checks presence; whether the content is credible is a judgment
for the reader.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FIELD = re.compile(r"^\s*[-*]\s*〔([AB])〕\s*([^:：]+)[:：]\s*(.*)$")
EMPTY = "【待补】"
TAGS = {"假设": "[假设]", "推断待确认": "[推断-待确认]"}


def filled(value):
    value = value.strip()
    # A value that is only the template's bracketed hint was never filled in.
    return bool(value) and EMPTY not in value and not value.startswith(("（", "("))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", help="申请者档案.md 的路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    path = Path(args.profile).expanduser()
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        print(f"无法读取档案: {exc}")
        return 2

    fields = []
    for number, line in enumerate(text.splitlines(), 1):
        match = FIELD.match(line)
        if match:
            gate, name, value = match.group(1), match.group(2).strip(), match.group(3)
            fields.append({"gate": gate, "name": name, "line": number, "filled": filled(value)})
    if not fields:
        print("档案里没有找到 〔A〕／〔B〕 标记的字段。请用 assets/profile-template.md 建档。")
        return 2

    missing = {g: [f for f in fields if f["gate"] == g and not f["filled"]] for g in "AB"}
    gate_a = not missing["A"]
    gate_b = gate_a and not missing["B"]
    # Mentions wrapped in backticks are the template's own instructions, not content.
    def occurrences(token):
        return len(re.findall(r"(?<!`)" + re.escape(token), text))

    counts = {key: occurrences(tag) for key, tag in TAGS.items()}
    remaining = occurrences(EMPTY)

    warnings = []
    ledger = re.search(r"^\s*[-*]\s*〔A〕\s*联系账本[:：]\s*(.+)$", text, re.M)
    if ledger and filled(ledger.group(1)):
        raw = re.split(r"[（(]", ledger.group(1).strip().strip("`"))[0].strip().strip("`")
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = path.parent / candidate
        if not candidate.exists():
            warnings.append(f"档案里写的联系账本路径不存在: {candidate}")

    result = {"profile": str(path), "gate_A": gate_a, "gate_B": gate_b,
              "missing_A": [f["name"] for f in missing["A"]],
              "missing_B": [f["name"] for f in missing["B"]],
              "assumptions": counts["假设"], "unconfirmed_inferences": counts["推断待确认"],
              "placeholders_remaining": remaining, "warnings": warnings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return 0

    def show(label, ok, items):
        print(f"{label}：{'通过' if ok else '未通过'}")
        for item in items:
            print(f"  缺：{item['name']}（第 {item['line']} 行）")

    show("闸门 A（可以筛导师）", gate_a, missing["A"])
    show("闸门 B（可以写邮件）", gate_b, missing["B"])
    if not gate_a and not missing["B"]:
        print("  闸门 B 自身的字段已填，但需要先过闸门 A")
    print(f"标为 [假设] 的内容：{counts['假设']} 处（交付时要向用户说明）")
    print(f"标为 [推断-待确认] 的内容：{counts['推断待确认']} 处（确认前不能写进邮件）")
    print(f"仍为 {EMPTY} 的位置：{remaining} 处（含非必需字段）")
    for warning in warnings:
        print(f"注意：{warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
