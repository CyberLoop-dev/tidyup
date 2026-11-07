<p align="center">
  <img src="assets/banner.svg" alt="tidyup" width="100%">
</p>

# tidyup 🧹

**Messy folder in. Clean folder out.** One command sorts your Downloads (or any folder) into tidy sub-folders. 😎

It shows you a **preview first**, never overwrites anything, and has an **undo button**. No dependencies, nothing to configure.

## ✨ Why you'll like it

- 👀 **Preview by default.** Nothing moves until you add `--apply`.
- ↩️ **Undo anytime.** Run `--undo` and every file goes back where it was.
- 🛡️ **Safe.** It never overwrites (a name clash becomes `photo (1).jpg`), skips hidden files, and leaves alone anything still downloading or changed in the last 10 minutes.
- 📁 **Smart folders:** Images, Videos, Audio, Documents, Archives, Code, Programs, Design & CAD (STL, DXF, STEP...) and Other.
- 📅 **Optional date folders** like `Images/2026-11`.
- 🪶 **Pure Python.** Standard library only.

## 👀 Example

```text
$ tidyup Downloads
Preview: 19 file(s) in C:\Users\you\Downloads

  Documents         5
  Images            4
  Archives          2
  Code              2
  Design & CAD      2
  Audio             1
  Other             1
  Programs          1
  Videos            1

  Skipped 3 file(s) (hidden, still downloading or changed recently).

This was only a preview. Run again with --apply to do it.
  backup.7z  ->  Archives/backup.7z
  bracket.dxf  ->  Design & CAD/bracket.dxf
  budget.xlsx  ->  Documents/budget.xlsx
  holiday-01.jpg  ->  Images/holiday-01.jpg
  ... and 15 more
```

Looks good? Add `--apply`:

```text
$ tidyup Downloads --apply
Done. Moved 19 file(s). Changed your mind? Run: tidyup "C:\Users\you\Downloads" --undo
```

## 🚀 Install

**Option 1: as a command**
```bash
pip install git+https://github.com/CyberLoop-dev/tidyup.git
tidyup --help
```

**Option 2: just run the file**
```bash
git clone https://github.com/CyberLoop-dev/tidyup.git
cd tidyup
python tidyup.py --help
```

Needs Python 3.8 or newer. Works on Windows, Linux and macOS.

## 🎮 Usage

```bash
tidyup                      # preview the current folder
tidyup Downloads            # preview a folder
tidyup Downloads --apply    # really do it
tidyup Downloads --undo     # put everything back
tidyup Downloads --apply --by-date   # Images/2026-11/...
```

| Option | What it does |
|---|---|
| `--apply` | Actually move the files (default is a safe preview) |
| `--undo` | Undo the last run in that folder |
| `--by-date` | Also group files by month |
| `--min-age MINUTES` | Leave files changed in the last N minutes alone (default 10) |
| `--include-hidden` | Also move hidden files |

## 🔍 Good to know

- Only the files **directly inside** the folder are moved. Existing sub-folders are never touched.
- The undo history lives in a small hidden file, `.tidyup-log.json`, inside the folder. It keeps the last 20 runs.
- If you put a new file with the same name back before undoing, tidyup skips that one instead of overwriting it.
- Want different categories? Edit the `CATEGORIES` table at the top of `tidyup.py`, it's just a Python dictionary.

## 🧪 Tests

```bash
python -m unittest discover tests
```

## 📄 License

MIT
