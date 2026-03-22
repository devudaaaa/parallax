# How to Upload v2 to Your devudaaaa/parallax Fork — BROWSER ONLY

No terminal. No git commands. Just your browser and this zip file.

---

## What You're Doing

Your fork at `github.com/devudaaaa/parallax` currently has v1 code.
This zip contains v1 + v2 code together. You'll upload the new/changed
files through GitHub's web interface.

---

## Step 1: Update Existing Files (LICENSE, README, .gitignore)

These files already exist in your repo and need to be REPLACED.

### Replace LICENSE:
1. Go to https://github.com/devudaaaa/parallax
2. Click on `LICENSE` file
3. Click the **pencil icon** (✏️ Edit) in the top-right of the file view
4. Select all text (Ctrl+A / Cmd+A) and delete it
5. Copy the ENTIRE contents of `LICENSE` from the unzipped folder and paste
6. Click **"Commit changes"** button
7. In the popup, type: `Update LICENSE to Collective Intelligence License v1.0`
8. Click **"Commit changes"**

### Replace README.md:
1. Click on `README.md` in the repo
2. Click the **pencil icon** (✏️ Edit)
3. Select all and delete
4. Copy the ENTIRE contents of `README.md` from the unzipped folder and paste
5. Commit with message: `Update README for v2.0`

---

## Step 2: Upload New Folders

### Upload sequential/ folder:
1. Go to https://github.com/devudaaaa/parallax
2. Click **"Add file"** → **"Upload files"**
3. From your unzipped folder, drag ALL 4 files from `sequential/`:
   - `__init__.py`
   - `state.py`
   - `transition.py`
   - `model.py`

   **IMPORTANT:** GitHub's upload creates files in the ROOT. We need them
   in a `sequential/` folder. Instead, do this:

   1. Click **"Add file"** → **"Create new file"**
   2. In the filename box, type: `sequential/__init__.py`
      (typing the `/` automatically creates the folder)
   3. Copy the contents of `sequential/__init__.py` from the unzipped folder
   4. Commit with message: `Add sequential/__init__.py`

   5. Repeat for `sequential/state.py`:
      - Click **"Add file"** → **"Create new file"**
      - Type filename: `sequential/state.py`
      - Paste contents
      - Commit

   6. Repeat for `sequential/transition.py`
   7. Repeat for `sequential/model.py`

### Upload argumentation/ folder:
Same process:
1. **"Add file"** → **"Create new file"**
2. Filename: `argumentation/__init__.py` → paste contents → commit
3. Filename: `argumentation/framework.py` → paste contents → commit

### Upload new test files:
1. Navigate to the `tests/` folder in your repo
2. Click **"Add file"** → **"Create new file"**
3. Filename: just type `test_sequential.py` (you're already in tests/)
   OR if you're at root, type: `tests/test_sequential.py`
4. Paste contents → commit
5. Repeat for `tests/test_argumentation.py`

### Upload CHANGELOG.md:
1. Go to repo root
2. **"Add file"** → **"Create new file"**
3. Filename: `CHANGELOG.md`
4. Paste contents → commit

### Upload docs/register.html:
1. **"Add file"** → **"Create new file"**
2. Filename: `docs/register.html`
3. Paste contents → commit

### Upload .gitignore:
1. **"Add file"** → **"Create new file"**
2. Filename: `.gitignore`
3. Paste contents → commit

---

## Step 3: Verify

After all uploads, your repo should show these folders:
- `sequential/` (NEW — 4 files)
- `argumentation/` (NEW — 2 files)
- `temporal_engine/` (existing)
- `phase1_data_pipeline/` (existing)
- `phase2_logic_twin/` (existing)
- `phase4_platform/` (existing)
- `tests/` (existing + 2 new test files)
- `docs/` (NEW — register.html)

And these updated files:
- `LICENSE` → Should show "Collective Intelligence License"
- `README.md` → Should show the new v2 readme with architecture diagram
- `CHANGELOG.md` → NEW
- `.gitignore` → NEW

---

## Step 4: Update Repository Settings

1. Go to **Settings** (gear icon, top of repo page)
2. In the "About" section (right sidebar on main page), click the gear
3. Change Description to: `A generative agent of one — Parallax Engine v2`
4. Add Website: `https://devudaaaa.xyz`
5. Add Topics: `argumentation`, `game-theory`, `decision-making`, `ai-safety`, `behavioral-science`

---

## File Upload Order (Checklist)

Use this checklist to track your progress:

- [ ] LICENSE (edit existing)
- [ ] README.md (edit existing)
- [ ] sequential/__init__.py (create new)
- [ ] sequential/state.py (create new)
- [ ] sequential/transition.py (create new)
- [ ] sequential/model.py (create new)
- [ ] argumentation/__init__.py (create new)
- [ ] argumentation/framework.py (create new)
- [ ] tests/test_sequential.py (create new)
- [ ] tests/test_argumentation.py (create new)
- [ ] CHANGELOG.md (create new)
- [ ] docs/register.html (create new)
- [ ] .gitignore (create new)

Total: 13 file operations (2 edits + 11 creates)

---

## Alternative: Faster Upload If You Have Git Installed

If you have git on your machine (even if you're not comfortable with it),
this is faster than 13 individual browser uploads:

```bash
git clone https://github.com/devudaaaa/parallax.git
cd parallax
```

Then unzip `parallax-v2-update.zip`, copy all files on top of the cloned
folder (overwriting LICENSE, README, etc.), and:

```bash
git add -A
git commit -m "v2.0.0: Sequential Decision Model + Formal Argumentation Engine"
git push origin main
```

Three commands. Done.
