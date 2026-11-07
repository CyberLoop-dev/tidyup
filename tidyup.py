"""tidyup: clean a messy folder (like Downloads) in one command.

Files are sorted into folders by type (Images, Documents, ...).
It shows a preview first, never overwrites anything, and can undo the last run.
Standard library only.
"""

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime

__version__ = "1.0.0"

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic", ".tiff", ".ico"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".ppt", ".pptx",
                  ".xls", ".xlsx", ".csv", ".md", ".epub"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".c", ".cpp", ".h", ".java",
             ".php", ".sh", ".ino", ".yml", ".yaml", ".xml"},
    "Programs": {".exe", ".msi", ".apk", ".dmg", ".deb", ".iso"},
    "Design & CAD": {".psd", ".ai", ".fig", ".sketch", ".dxf", ".dwg", ".stl", ".step", ".stp", ".obj"},
}
OTHER = "Other"

# Browsers use these while a download is still running: never touch them.
SKIP_EXTENSIONS = {".crdownload", ".part", ".tmp", ".download", ".partial"}

LOG_NAME = ".tidyup-log.json"
MAX_RUNS_KEPT = 20


@dataclass
class Move:
    src: str  # path relative to the folder
    dst: str  # path relative to the folder


def category_for(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return OTHER


def unique_name(folder: str, rel_path: str, taken: set) -> str:
    """Return a relative path that does not exist yet (adds ' (1)', ' (2)'...)."""
    base, ext = os.path.splitext(rel_path)
    candidate = rel_path
    counter = 1
    while os.path.exists(os.path.join(folder, candidate)) or candidate in taken:
        candidate = f"{base} ({counter}){ext}"
        counter += 1
    return candidate


def plan(folder: str, by_date: bool = False, min_age_minutes: float = 10,
         include_hidden: bool = False, now: float = None):
    """Decide what would move where. Touches nothing."""
    now = time.time() if now is None else now
    moves, skipped = [], []
    taken = set()

    for name in sorted(os.listdir(folder)):
        full = os.path.join(folder, name)
        if name == LOG_NAME or os.path.isdir(full) or os.path.islink(full):
            continue
        if name.startswith(".") and not include_hidden:
            skipped.append((name, "hidden file"))
            continue
        if os.path.splitext(name)[1].lower() in SKIP_EXTENSIONS:
            skipped.append((name, "download in progress"))
            continue
        modified = os.path.getmtime(full)
        if now - modified < min_age_minutes * 60:
            skipped.append((name, "changed recently"))
            continue

        parts = [category_for(name)]
        if by_date:
            parts.append(datetime.fromtimestamp(modified).strftime("%Y-%m"))
        parts.append(name)
        dst = unique_name(folder, os.path.join(*parts), taken)
        taken.add(dst)
        moves.append(Move(src=name, dst=dst))
    return moves, skipped


def _read_log(folder: str):
    path = os.path.join(folder, LOG_NAME)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_log(folder: str, runs):
    path = os.path.join(folder, LOG_NAME)
    if not runs:
        if os.path.exists(path):
            os.remove(path)
        return
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(runs[-MAX_RUNS_KEPT:], handle, indent=2, ensure_ascii=False)


def apply_moves(folder: str, moves):
    """Really move the files and remember how to undo it."""
    done = []
    for move in moves:
        target = os.path.join(folder, move.dst)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.move(os.path.join(folder, move.src), target)
        done.append({"from": move.src, "to": move.dst})
    if done:
        runs = _read_log(folder)
        runs.append({"time": datetime.now().isoformat(timespec="seconds"), "moves": done})
        _write_log(folder, runs)
    return len(done)


def undo_last(folder: str):
    """Put the files of the last run back. Returns (restored, problems)."""
    runs = _read_log(folder)
    if not runs:
        return 0, ["Nothing to undo."]
    last = runs.pop()
    restored, problems = 0, []
    for item in reversed(last["moves"]):
        source = os.path.join(folder, item["to"])
        original = os.path.join(folder, item["from"])
        if not os.path.exists(source):
            problems.append(f"missing, skipped: {item['to']}")
            continue
        if os.path.exists(original):
            problems.append(f"name already taken, skipped: {item['from']}")
            continue
        shutil.move(source, original)
        restored += 1
        # remove folders we created if they are empty now
        parent = os.path.dirname(source)
        while parent and os.path.abspath(parent) != os.path.abspath(folder):
            try:
                os.rmdir(parent)
            except OSError:
                break
            parent = os.path.dirname(parent)
    _write_log(folder, runs)
    return restored, problems


def summarize(moves):
    counts = {}
    for move in moves:
        top = move.dst.split(os.sep)[0]
        counts[top] = counts.get(top, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tidyup", description="Clean a messy folder in one command")
    parser.add_argument("folder", nargs="?", default=".", help="folder to clean (default: current folder)")
    parser.add_argument("--apply", action="store_true", help="really move the files (default is a safe preview)")
    parser.add_argument("--undo", action="store_true", help="undo the last run in this folder")
    parser.add_argument("--by-date", action="store_true", help="also group by month, like Images/2026-11")
    parser.add_argument("--min-age", type=float, default=10, metavar="MINUTES",
                        help="leave files changed in the last N minutes alone (default 10)")
    parser.add_argument("--include-hidden", action="store_true", help="also move hidden files")
    parser.add_argument("--version", action="version", version=f"tidyup {__version__}")
    args = parser.parse_args(argv)

    folder = os.path.abspath(args.folder)
    if not os.path.isdir(folder):
        print(f"Not a folder: {folder}")
        return 1

    if args.undo:
        restored, problems = undo_last(folder)
        print(f"Restored {restored} file(s).")
        for problem in problems:
            print(f"  ! {problem}")
        return 0

    moves, skipped = plan(folder, args.by_date, args.min_age, args.include_hidden)
    if not moves:
        print("Nothing to tidy. The folder is already clean. ✨")
        return 0

    print(f"{'Moving' if args.apply else 'Preview:'} {len(moves)} file(s) in {folder}\n")
    for category, count in summarize(moves).items():
        print(f"  {category:<14} {count:>4}")
    if skipped:
        print(f"\n  Skipped {len(skipped)} file(s) (hidden, still downloading or changed recently).")

    if not args.apply:
        print("\nThis was only a preview. Run again with --apply to do it.")
        for move in moves[:10]:
            print(f"  {move.src}  ->  {move.dst}")
        if len(moves) > 10:
            print(f"  ... and {len(moves) - 10} more")
        return 0

    count = apply_moves(folder, moves)
    print(f"\nDone. Moved {count} file(s). Changed your mind? Run: tidyup \"{folder}\" --undo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
