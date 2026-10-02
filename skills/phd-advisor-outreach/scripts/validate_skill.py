#!/usr/bin/env python3
"""Check that this skill is internally consistent. Read-only, standard library only.

Verifies: required files exist; Markdown links resolve; a quoted section name
after a link exists as a heading in the target file; the workspace folders in
init_workspace.py are documented; gate fields, status words and table columns
defined in templates are the same ones the reference files describe; the sample
opening message stays within its length limit.
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SKILL.md",
    "references/expert-stance.md", "references/workflow.md", "references/operation.md",
    "references/interview-guide.md", "references/profile-schema.md",
    "references/capital-assessment.md", "references/tradeoffs.md",
    "references/scouting.md", "references/fit-analysis.md", "references/verification.md",
    "references/email-model.md", "references/email-writing.md",
    "references/reply-playbook.md", "references/intent-stage.md",
    "assets/workspace-readme.md", "assets/todo-template.md",
    "assets/profile-template.md", "assets/ledger-template.md",
    "assets/advisor-table-template.csv", "assets/advisor-check-template.md",
    "assets/intent-table-template.xlsx", "assets/intent-table-template.csv",
    "assets/email-skeleton.md", "assets/core-papers-template.md",
    "assets/examples/email-master-example.md",
    "scripts/init_workspace.py", "scripts/check_profile.py", "scripts/check_duplicates.py",
    "scripts/make_reminders.py",
]
LINK = re.compile(r"\[([^\]]+)\]\(([^)#]+)\)")
SECTION_REF = re.compile(r"\]\(([^)#]+\.md)\)\s*(?:里的|的)?\s*“([^”]+)”")
GATE = re.compile(r"^\s*[-*]\s*〔([AB])〕\s*([^:：]+)[:：]", re.M)
OPENING_LIMIT = 700


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def headings(text):
    # Section headings only: the file's own H1 title would match too loosely.
    return [line.lstrip("#").strip() for line in text.splitlines() if line.startswith("##")]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    errors = []

    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    errors += [f"缺文件: {p}" for p in missing]
    if missing:
        print("\n".join(errors))
        return 1

    md_files = sorted(ROOT.rglob("*.md"))
    for md in md_files:
        text = md.read_text(encoding="utf-8")
        rel = md.relative_to(ROOT).as_posix()
        for _, target in LINK.findall(text):
            if target.startswith(("http://", "https://")):
                continue
            if not (md.parent / target).resolve().exists():
                errors.append(f"失效链接: {rel} -> {target}")
        for target, name in SECTION_REF.findall(text):
            path = (md.parent / target).resolve()
            if path.is_file() and not any(name in h for h in headings(path.read_text(encoding="utf-8"))):
                errors.append(f"章节引用对不上: {rel} 提到 {target} 的“{name}”，目标文件里没有这个标题")

    skill = read("SKILL.md")
    if not re.search(r"^name:\s*phd-advisor-outreach\s*$", skill, re.M):
        errors.append("SKILL.md 的 name 不对")
    for ref in sorted((ROOT / "references").glob("*.md")):
        if ref.name not in skill:
            errors.append(f"SKILL.md 没有提到 references/{ref.name}")

    # Workspace folders created by the script must be documented in both places.
    init = read("scripts/init_workspace.py")
    tops = sorted({m.split("/")[0] for m in re.findall(r'"(\d\d_[^"]+)"', init)})
    for doc in ("references/operation.md", "assets/workspace-readme.md"):
        text = read(doc)
        errors += [f"{doc} 没有写到文件夹 {t}" for t in tops if t not in text]

    # Gate fields in the profile template must match the schema's gate table.
    template = read("assets/profile-template.md")
    schema = read("references/profile-schema.md")
    gate_section = schema[schema.index("## 四、闸门"):] if "## 四、闸门" in schema else schema
    for gate, name in GATE.findall(template):
        if name.strip() not in gate_section:
            errors.append(f"档案模板的闸门 {gate} 字段“{name.strip()}”不在 profile-schema.md 的闸门表里")

    # Ledger status words must be the ones the workflow defines.
    workflow = read("references/workflow.md")
    ledger = read("assets/ledger-template.md")
    status_line = next((l for l in ledger.splitlines() if "状态用这几个词" in l), "")
    words = re.findall(r"`([^`]+)`", status_line)
    if not words:
        errors.append("联系账本模板里没有找到状态词的说明行")
    for word in words:
        if word not in workflow:
            errors.append(f"联系账本的状态词“{word}”不在 workflow.md 的状态表里")

    # The sample opening message must stay within the length the workflow promises:
    # it is the first thing a new user reads, and it grows a little with every edit.
    quote, started = [], False
    for line in workflow[workflow.find("### 要做到的五件事"):].splitlines():
        if line.startswith(">"):
            started = True
            quote.append(line)
        elif started:
            break
    opening = len(re.sub(r"\s|[>*`|-]", "", "".join(quote)))
    if not quote:
        errors.append("workflow.md 的“开场”里没有找到示范话术")
    elif opening > OPENING_LIMIT:
        errors.append(f"开场示范话术有 {opening} 字，超过了 {OPENING_LIMIT} 字的上限")

    # Table headers must be described where the docs say they are.
    scouting = read("references/scouting.md")
    with open(ROOT / "assets/advisor-table-template.csv", encoding="utf-8-sig", newline="") as fh:
        columns = next(csv.reader(fh))
    for col in columns:
        if "（深查后）" in col:
            continue
        if col not in scouting:
            errors.append(f"名单表的列“{col}”在 scouting.md 里没有说明")
    operation = read("references/operation.md")
    with open(ROOT / "assets/intent-table-template.csv", encoding="utf-8-sig", newline="") as fh:
        intent_cols = next(csv.reader(fh))
    for col in intent_cols:
        if col not in operation:
            errors.append(f"意向导师表的列“{col}”在 operation.md 里没有说明")

    if errors:
        print("发现问题：")
        print("\n".join("  " + e for e in errors))
        return 1
    print(f"通过：{len(REQUIRED)} 个必需文件齐全，{len(md_files)} 个 Markdown 文件的链接和章节引用有效，"
          f"{len(tops)} 个工作文件夹、{len(GATE.findall(template))} 个闸门字段、"
          f"{len(columns)} 列名单表、{len(intent_cols)} 列意向表与说明一致；开场示范 {opening} 字")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
