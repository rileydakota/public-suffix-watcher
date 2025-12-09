# GitHub Actions Setup

This document explains the automated workflow for tracking Public Suffix List changes.

## What the Workflow Does

The GitHub Actions workflow (`.github/workflows/update-psl.yml`) automatically:

1. **Runs daily at 00:00 UTC** (or manually via workflow_dispatch)
2. **Downloads** the latest Public Suffix List from Mozilla
3. **Updates** the DuckDB database with any new private domains
4. **Generates** a markdown summary of newly discovered domains
5. **Commits** the database and summary files to the main branch

## Files Tracked in Git

- `psl.db` - The DuckDB database containing all private domain records
- `summaries/new-domains-YYYY-MM-DD.md` - Daily summary files showing new discoveries

## Summary File Format

Each summary file contains:
- Total count of new domains discovered that day
- Number of submitter organizations
- Domains grouped by submitter email domain

Example:
```markdown
# Public Suffix List Update - 2025-12-08

**Total new domains:** 15

**Submitter organizations:** 1

---

## akamai.com

**New domains:** 15

- `akadns.net`
- `akamai.net`
- `akamai-staging.net`
...
```

## How Discovery Works

- The `discovered` timestamp is set when a domain is **first seen** in the database
- Running the load command multiple times preserves the original timestamp
- The summary command queries for domains discovered on a specific date
- Exit codes: 0 if new domains found, 1 if none (used by workflow)

## Manual Usage

You can manually trigger the workflow from GitHub:
1. Go to the **Actions** tab
2. Select **Update Public Suffix List**
3. Click **Run workflow**

Or run locally:
```bash
uv run main.py load      # Download and update database
uv run main.py summary   # Generate today's summary
```

## Initial Setup

To initialize this repository:

1. **Update Database URL**: Edit `docs/index.html` and replace `YOUR_USERNAME/YOUR_REPO` with your GitHub username and repository name
2. **Commit all files** to your repository
3. **Push to GitHub**
4. **Enable GitHub Pages**:
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main`
   - Folder: `/docs`
   - Click Save
5. The workflow will run automatically daily
6. Check the Actions tab to monitor runs
7. Access your web interface at `https://YOUR_USERNAME.github.io/YOUR_REPO/`

## Troubleshooting

- If the workflow fails, check the Actions tab for error logs
- The workflow requires `contents: write` permission to commit changes
- Ensure the main branch is not protected or configure the workflow accordingly
