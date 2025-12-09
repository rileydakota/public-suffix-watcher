# Cloud Public Suffix Lists

A Python utility that parses the Public Suffix List (PSL) and stores private domain records in a DuckDB database for fast querying.

## Features

- Downloads and parses the official Public Suffix List
- Stores private domains in DuckDB with metadata
- Query domains by submitter email domain
- Export data to CSV
- Track discovery timestamps

## Database Schema

```sql
CREATE TABLE private_domains (
    submitted_email_domain VARCHAR,  -- Domain from submitter's email (e.g., "akamai.com")
    domain VARCHAR,                  -- The actual domain suffix (e.g., "akamai.net")
    discovered TIMESTAMP,            -- When the record was loaded
    PRIMARY KEY (submitted_email_domain, domain)
)
```

## Installation

```bash
uv sync
```

## Usage

### Load PSL Data into DuckDB

Download and parse the Public Suffix List, loading all private domains into DuckDB:

```bash
uv run main.py load
```

Or use a local PSL file:

```bash
uv run main.py load /path/to/public_suffix_list.dat
```

**Output:**
```
Loading Public Suffix List...
Successfully loaded 8234 private domain records into DuckDB
Unique email domains: 456
Total domains: 8234
```

### Query Domains by Email Domain

Query all domains submitted by organizations using a specific email domain:

```bash
uv run main.py query akamai.com
```

**Output:**
```
Records for email domain: akamai.com
======================================================================
submitted_email_domain           domain              discovered
akamai.com                       akadns.net          2025-12-08 10:30:45
akamai.com                       akamai.net          2025-12-08 10:30:45
akamai.com                       akamai-staging.net  2025-12-08 10:30:45
...

Total: 15 domains
```

### Show Database Statistics

```bash
uv run main.py stats
```

**Output:**
```
Database Statistics
======================================================================
Unique email domains: 456
Total domains: 8234
```

### Generate Summary of New Domains

Generate a markdown summary of domains discovered on a specific date:

```bash
uv run main.py summary
```

Or specify a custom date:

```bash
uv run main.py summary 2025-12-08
```

**Output:**
- Creates a file `summaries/new-domains-YYYY-MM-DD.md` with grouped summary
- Exits with code 0 if new entries found, 1 if none
- Groups domains by submitter email domain

### Export to CSV

Export all records to a CSV file:

```bash
uv run main.py export
```

Or specify a custom filename:

```bash
uv run main.py export my_data.csv
```

## Remote Database Access

The DuckDB database is tracked in git and can be accessed remotely via HTTPS without cloning the repository.

### Attach Database from GitHub

You can attach the database directly from GitHub raw URL using DuckDB's ATTACH feature:

```sql
ATTACH 'https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/psl.db' as psl (READ_ONLY);

-- Query the attached database
SELECT * FROM psl.private_domains LIMIT 10;

-- Get statistics
SELECT
    COUNT(DISTINCT submitted_email_domain) as unique_submitters,
    COUNT(*) as total_domains
FROM psl.private_domains;

-- Top 10 submitters by domain count
SELECT
    submitted_email_domain,
    COUNT(*) as domain_count
FROM psl.private_domains
GROUP BY submitted_email_domain
ORDER BY domain_count DESC
LIMIT 10;
```

### Using DuckDB CLI

```bash
# Install DuckDB
brew install duckdb  # macOS
# or download from https://duckdb.org/

# Launch DuckDB CLI
duckdb

# Attach remote database
ATTACH 'https://raw.githubusercontent.com/rileydakota/public-suffix-watcher/main/psl.db' as psl (READ_ONLY);

# Run queries
SELECT domain FROM psl.private_domains WHERE submitted_email_domain = 'akamai.com';
```

### Using Python with DuckDB

```python
import duckdb

# Connect to DuckDB (in-memory or local)
conn = duckdb.connect()

# Attach remote database
conn.execute("""
    ATTACH 'https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/psl.db'
    as psl (READ_ONLY)
""")

# Query the remote database
result = conn.execute("""
    SELECT submitted_email_domain, COUNT(*) as count
    FROM psl.private_domains
    GROUP BY submitted_email_domain
    ORDER BY count DESC
    LIMIT 10
""").fetchall()

for row in result:
    print(f"{row[0]}: {row[1]} domains")

conn.close()
```

### Local Database Access

If you've cloned the repository, access the local database:

```bash
# Using DuckDB CLI
duckdb psl.db

# Run queries
SELECT * FROM private_domains LIMIT 10;
```

## Programmatic Usage with the Parser

```python
from main import PublicSuffixListParser

# Initialize and load data
parser = PublicSuffixListParser(db_path="psl.db")
count = parser.parse_and_load()
print(f"Loaded {count} records")

# Query by email domain
result = parser.query_by_email_domain("akamai.com")
rows = result.fetchall()
for row in rows:
    print(f"{row[0]} - {row[1]} - {row[2]}")

# Get statistics
stats = parser.get_stats()
print(f"Unique email domains: {stats[0]}")
print(f"Total domains: {stats[1]}")

# Run custom SQL queries directly
custom_result = parser.conn.execute("""
    SELECT submitted_email_domain, COUNT(*) as domain_count
    FROM private_domains
    GROUP BY submitted_email_domain
    ORDER BY domain_count DESC
    LIMIT 10
""").fetchall()

for row in custom_result:
    print(f"{row[0]}: {row[1]} domains")

parser.close()
```

## GitHub Actions Automation

This repository includes a GitHub Actions workflow that:
- Runs daily at 00:00 UTC
- Downloads the latest Public Suffix List
- Updates the DuckDB database
- Generates a summary of newly discovered domains
- Commits the database and summary files to the repository

The workflow is defined in [.github/workflows/update-psl.yml](.github/workflows/update-psl.yml).

**Manual Trigger:**
You can manually trigger the workflow from the Actions tab in GitHub.

## How It Works

1. Downloads or reads the Public Suffix List file (cached for 1 day using cachier)
2. Identifies the `===BEGIN PRIVATE DOMAINS===` section
3. Parses submission metadata from comment lines
4. Extracts the email domain from submitter emails (e.g., `publicsuffixlist@akamai.com` → `akamai.com`)
5. Stores each domain with its submitter email domain and discovery timestamp
6. Uses `INSERT OR IGNORE` to preserve original discovery timestamps

## Requirements

- Python 3.14+
- DuckDB 1.0.0+

## Files Generated

- `psl.db` - DuckDB database file (tracked in git)
- `psl.db.wal` - DuckDB write-ahead log (ignored by git)
- `summaries/new-domains-YYYY-MM-DD.md` - Daily summary files (tracked in git)
- `private_domains.csv` - CSV export (ignored by git)
