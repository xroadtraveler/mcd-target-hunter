# MCD Target Hunter

**MCD Target Hunter** is a Windows utility for quickly troubleshooting CATIA / MCD-generated CNC output files.  
It scans NC/MCD text files for specific target strings (e.g. `POST-GENERATED`) and reports each occurrence with useful contextual information to speed up root-cause analysis.

---

## What Problem This Solves

When troubleshooting MCD output, it’s often necessary to answer questions like:

- *Which operation did this post-generated move come from?*
- *Which operation number and tool were active at that time?*
- *How many times does this issue occur across a program?*

Manually searching large NC files is slow and error-prone.  
**MCD Target Hunter automates that search and produces a flat, filterable CSV report.**

---

## Key Features

- Windows GUI (no command line required for normal use)
- Search for a configurable **Target** string (default: `POST-GENERATED`)
- Optional **Parent** string lookup (default: `OPERATION NAME`)
- Captures context for each hit:
  - Line number of the target
  - Full operation name line
  - Operation number line
  - Tool change line (`M06`)
  - Tool number line (`T##`)
- One CSV row per hit (easy filtering/sorting)
- Per-user config persistence (last-used settings are remembered)
- Works with `.nc`, `.V11`, or any text-based CNC output
- “About” dialog showing version and purpose

---

## Versioning

This release is **v1.0.0**.

Versioning follows a simple semantic pattern:

- **MAJOR** – breaking changes
- **MINOR** – new features, no breakage
- **PATCH** – bug fixes only

See `CHANGELOG.txt` for details.

---

## Running the Program (Most Users)

1. Copy the entire `MCDTargetHunter` folder locally  
   (do **not** run directly from a network share if possible)

2. Double-click:
   MCDTargetHunter.exe

3. In the GUI:
- Select the target CNC/MCD output file

- Adjust Target / Parent strings if needed

- Click **Run**
4. A CSV report will be generated at the chosen output location.

---

## Output

- CSV file
- One row per target hit
- Designed for filtering in Excel or similar tools

Example use cases:

- Find all post-generated moves per operation
- Quickly jump to problem operations in CATIA
- Count how many times an issue appears in a program

---

## Configuration Storage

User settings are saved automatically to:
C:\Users<username>\AppData\Local\MCDTargetFinderConfig\

This includes:

- Last-used target file
- Output directory
- Target / Parent search strings

Each user has their own config.

---

## Building From Source (Advanced / Maintainer)

### Requirements

- Windows
- Python 3.x
- PowerShell
- PyQt6
- PyInstaller

DBasic Workflow

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install PyQt6 pyinstaller

Run the GUI:
.\.venv\Scripts\python.exe mcd_target_hunter_gui.py

Build the EXE (example using absolute paths):
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name MCDTargetHunter --collect-all PyQt6 --icon .\assets\target.ico mcd_target_hunter_gui.py

(See the PowerShell command reference document for safe build options for locked-down computers.)



---

## Intended Audience

- NC Programmers
- Manufacturing Engineers
- CNC Troubleshooting / Support Engineers
- CATIA / MCD users

## Status

Stable – Internal Release v1.0.0
Further enhancements are tracked internally and can be added incrementally without breaking existing workflows.
