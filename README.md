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
pip install -e .
```

## Usage

### Load PSL Data into DuckDB

Download and parse the Public Suffix List, loading all private domains into DuckDB:

```bash
python main.py load
```

Or use a local PSL file:

```bash
python main.py load /path/to/public_suffix_list.dat
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
python main.py query akamai.com
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
python main.py stats
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
python main.py summary
```

Or specify a custom date:

```bash
python main.py summary 2025-12-08
```

**Output:**
- Creates a file `summaries/new-domains-YYYY-MM-DD.md` with grouped summary
- Exits with code 0 if new entries found, 1 if none
- Groups domains by submitter email domain

### Export to CSV

Export all records to a CSV file:

```bash
python main.py export
```

Or specify a custom filename:

```bash
python main.py export my_data.csv
```

## Programmatic Usage

```python
from main import PublicSuffixListParser

# Initialize and load data
parser = PublicSuffixListParser(db_path="psl.db")
count = parser.parse_and_load()
print(f"Loaded {count} records")

# Query by email domain
result = parser.query_by_email_domain("akamai.com")
df = result.df()
print(df)

# Get statistics
stats = parser.get_stats()
print(f"Unique email domains: {stats[0]}")
print(f"Total domains: {stats[1]}")

# Run custom SQL queries
custom_result = parser.conn.execute("""
    SELECT submitted_email_domain, COUNT(*) as domain_count
    FROM private_domains
    GROUP BY submitted_email_domain
    ORDER BY domain_count DESC
    LIMIT 10
""").df()
print(custom_result)

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
