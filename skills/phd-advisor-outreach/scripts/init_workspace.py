#!/usr/bin/env python3
"""Create the applicant's workspace folder with subfolders and starter files.

Defaults to <Desktop>/申博资料. Never overwrites, moves or deletes anything that
already exists. Standard library only; works on Windows, macOS and Linux.
"""
import argparse
import os
import re
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
FOLDERS = [
    "01_我的材料/简历",
    "01_我的材料/论文与稿件",
    "01_我的材料/成绩与证书",
    "01_我的材料/其他经历",
    "02_档案",
    "03_申请材料/简历",
    "03_申请材料/工作介绍",
    "03_申请材料/研究计划",
    "03_申请材料/汇报PPT",
    "04_导师联系/筛选表",
    "05_意向导师",
    "06_院校报名",
    "07_临时文件",
]
PROFILE = "02_档案/申请者档案.md"
LEDGER = "02_档案/联系账本.md"
LEDGER_FIELD = "〔A〕联系账本："
STARTERS = [
    ("assets/workspace-readme.md", "使用说明.md"),
    ("assets/todo-template.md", "待办与日程.md"),
    ("assets/profile-template.md", PROFILE),
    ("assets/ledger-template.md", LEDGER),
    ("assets/intent-table-template.xlsx", "05_意向导师/意向导师表.xlsx"),
]


def desktop():
    """Locate the real Desktop, which may be redirected (OneDrive) or localized."""
    home = Path.home()
    candidates = []
    if os.name == "nt":
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                candidates.append(Path(os.path.expandvars(winreg.QueryValueEx(key, "Desktop")[0])))
        except OSError:
            pass
    else:
        dirs = home / ".config" / "user-dirs.dirs"
        if dirs.is_file():
            match = re.search(r'^XDG_DESKTOP_DIR="?([^"\n]+)"?', dirs.read_text(errors="ignore"), re.M)
            if match:
                candidates.append(Path(match.group(1).replace("$HOME", str(home))))
    candidates += [home / "Desktop", home / "桌面"]
    return next((c for c in candidates if c.is_dir()), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="工作文件夹的完整路径；默认是 桌面/申博资料")
    parser.add_argument("--name", default="申博资料", help="放在桌面时使用的文件夹名")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.root:
        root = Path(args.root).expanduser()
    else:
        base = desktop()
        if base is None:
            print("没有找到桌面文件夹。请用 --root 指定工作文件夹的位置。")
            return 2
        root = base / args.name

    existed = root.exists()
    created, kept = [], []
    for folder in FOLDERS:
        target = root / folder
        (kept if target.is_dir() else created).append(folder + "/")
        target.mkdir(parents=True, exist_ok=True)
    for source, name in STARTERS:
        target = root / name
        if target.exists():
            kept.append(name)
        else:
            shutil.copyfile(SKILL / source, target)
            created.append(name)

    # A freshly copied profile still says the ledger is missing, although the
    # ledger was created alongside it. Point the profile at it so gate A does
    # not report a gap the user never had. Existing profiles are left alone.
    if PROFILE in created and (root / LEDGER).is_file():
        profile = root / PROFILE
        text = profile.read_text(encoding="utf-8")
        filled = text.replace(LEDGER_FIELD + "【待补】", LEDGER_FIELD + LEDGER, 1)
        if filled != text:
            profile.write_text(filled, encoding="utf-8")

    print(f"工作文件夹：{root}")
    print("状态：" + ("原来就有，只补了缺少的部分" if existed else "新建"))
    for item in created:
        print(f"  新建  {item}")
    for item in kept:
        print(f"  保留  {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
