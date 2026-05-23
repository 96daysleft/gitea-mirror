# gitea-mirror

Sync GitHub org repos to Gitea as mirrors.

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv gitea-mirror-venv
```

### 2. Activate the virtual environment

**Linux / macOS:**
```bash
source gitea-mirror-venv/bin/activate
```

**Windows:**
```bash
gitea-mirror-venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure secrets

Create a `secret.json` file in the project root:

```json
{
  "github_token": "your_github_pat",
  "gitea_token": "your_gitea_token"
}
```

## Usage

**Sync missing repos from GitHub to Gitea:**
```bash
python main.py sync
```

**Update the GitHub PAT on all mirror repos:**
```bash
python main.py update-pat
```

**Dry run (preview only):**
```bash
python main.py update-pat --dry-run
```

**If installed as a package, use the console script:**
```bash
mirror-sync sync
mirror-sync update-pat --dry-run
```

## Deactivate the virtual environment

```bash
deactivate
```
