#!/usr/bin/env python3
"""Write calendar reminders (.ics) for interviews, application deadlines and follow-ups.

The assistant cannot contact the user between sessions; a calendar file the
user imports into their phone or computer calendar is what actually reminds
them. Standard library only.

Each --event is "WHEN|TITLE|NOTE" (NOTE optional). WHEN is "YYYY-MM-DD" for an
all-day item or "YYYY-MM-DD HH:MM" for a timed one (local time, 1 hour long).

Example:
  python make_reminders.py --out 申博提醒.ics \
    --event "2026-10-12 20:00|王老师线上交流|腾讯会议，PPT 讲 15 分钟" \
    --event "2026-11-10|某大学博士报名开始|材料清单见 06_院校报名" \
    --event "2026-10-09|跟进：李老师、陈老师|发出已满一周，各跟进一次"
"""
import argparse
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def escape(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line):
    """Fold a content line at 75 octets, as RFC 5545 requires."""
    raw, out, chunk = line.encode("utf-8"), [], b""
    for char in line:
        piece = char.encode("utf-8")
        limit = 75 if not out else 74
        if len(chunk) + len(piece) > limit:
            out.append(chunk)
            chunk = b""
        chunk += piece
    out.append(chunk)
    return "\r\n ".join(part.decode("utf-8") for part in out) if len(raw) > 75 else line


def parse(spec):
    parts = [p.strip() for p in spec.split("|")]
    if len(parts) < 2 or not parts[1]:
        raise ValueError(f"格式应为 “日期|标题|备注”：{spec}")
    when, title, note = parts[0], parts[1], parts[2] if len(parts) > 2 else ""
    for fmt, timed in (("%Y-%m-%d %H:%M", True), ("%Y-%m-%d", False)):
        try:
            return datetime.strptime(when, fmt), timed, title, note
        except ValueError:
            continue
    raise ValueError(f"日期看不懂（用 2026-10-12 或 2026-10-12 20:00）：{when}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, help="输出的 .ics 文件路径")
    parser.add_argument("--event", action="append", default=[], help="“日期|标题|备注”，可重复")
    parser.add_argument("--alarm-days", default="3,1", help="全天事项提前几天提醒，逗号分隔，默认 3,1")
    parser.add_argument("--alarm-hours", default="24,2", help="定时事项提前几小时提醒，逗号分隔，默认 24,2")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not args.event:
        parser.error("至少给一个 --event")

    try:
        events = [parse(spec) for spec in args.event]
        day_alarms = [int(x) for x in args.alarm_days.split(",") if x.strip()]
        hour_alarms = [int(x) for x in args.alarm_hours.split(",") if x.strip()]
    except ValueError as exc:
        print(exc)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//phd-advisor-outreach//reminders//CN", "CALSCALE:GREGORIAN"]
    for when, timed, title, note in sorted(events, key=lambda e: e[0]):
        uid = hashlib.sha1(f"{when.isoformat()}|{title}".encode("utf-8")).hexdigest()[:20]
        lines += ["BEGIN:VEVENT", f"UID:{uid}@phd-advisor-outreach", f"DTSTAMP:{stamp}"]
        if timed:
            # Floating local time: calendar apps read it in the user's own time zone.
            lines += [f"DTSTART:{when.strftime('%Y%m%dT%H%M%S')}",
                      f"DTEND:{(when + timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')}"]
            alarms = [f"-PT{h}H" for h in hour_alarms]
        else:
            lines += [f"DTSTART;VALUE=DATE:{when.strftime('%Y%m%d')}",
                      f"DTEND;VALUE=DATE:{(when + timedelta(days=1)).strftime('%Y%m%d')}"]
            # All-day items start at midnight, so fire at 09:00 on the days before.
            alarms = [f"-PT{d * 24 - 9}H" for d in day_alarms]
        lines.append(fold(f"SUMMARY:{escape('申博｜' + title)}"))
        if note:
            lines.append(fold(f"DESCRIPTION:{escape(note)}"))
        for trigger in alarms:
            lines += ["BEGIN:VALARM", "ACTION:DISPLAY", fold(f"DESCRIPTION:{escape(title)}"),
                      f"TRIGGER:{trigger}", "END:VALARM"]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")

    out = Path(args.out).expanduser()
    out.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    print(f"已写入 {out}，共 {len(events)} 条提醒：")
    for when, timed, title, _ in sorted(events, key=lambda e: e[0]):
        print("  " + when.strftime("%Y-%m-%d %H:%M" if timed else "%Y-%m-%d") + "  " + title)
    print("把这个文件发到手机上点开，或在电脑上双击，就能导入日历。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
