import re
import urllib.request
from datetime import datetime, timedelta
from typing import Optional
import duckdb
from cachier import cachier


@cachier(stale_after=timedelta(days=1))
def _download_psl() -> str:
    """Download and cache the Public Suffix List for 1 day."""
    PSL_URL = "https://publicsuffix.org/list/public_suffix_list.dat"
    with urllib.request.urlopen(PSL_URL) as response:
        return response.read().decode('utf-8')


class PublicSuffixListParser:
    """Parser for the Public Suffix List that stores private domains in DuckDB."""

    def __init__(self, db_path: str = "psl.db", file_path: Optional[str] = None):
        """
        Initialize the parser and database.

        Args:
            db_path: Path to DuckDB database file
            file_path: Optional local PSL file path. If not provided, downloads from official URL.
        """
        self.db_path = db_path
        self.file_path = file_path
        self.conn = duckdb.connect(db_path)
        self._create_table()

    def _create_table(self):
        """Create the private_domains table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS private_domains (
                submitted_email_domain VARCHAR,
                domain VARCHAR,
                discovered TIMESTAMP,
                PRIMARY KEY (submitted_email_domain, domain)
            )
        """)

    def _fetch_content(self) -> str:
        """Fetch the Public Suffix List content (cached for 1 day if downloaded)."""
        if self.file_path:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return _download_psl()

    def parse_and_load(self):
        """Parse the Public Suffix List and load private domains into DuckDB."""
        content = self._fetch_content()
        lines = content.split('\n')

        in_private_section = False
        current_email = ""
        discovered = datetime.now()
        records = []

        for line in lines:
            line = line.strip()

            # Check if we've entered the private domains section
            if "===BEGIN PRIVATE DOMAINS===" in line:
                in_private_section = True
                continue

            if not in_private_section:
                continue

            # Skip empty lines
            if not line:
                continue

            # Parse submitted by line to extract email
            submitted_match = re.match(r'^//\s*Submitted by\s+.+?\s*<([^>]+)>', line)
            if submitted_match:
                email = submitted_match.group(1).strip()
                current_email = email.split('@')[-1] if '@' in email else ""
                continue

            # Skip other comment lines
            if line.startswith('//'):
                continue

            # This is a domain line
            if current_email:
                domain = line.strip()
                if domain:
                    records.append({
                        'submitted_email_domain': current_email,
                        'domain': domain,
                        'discovered': discovered
                    })

        # Bulk insert all records using executemany
        # Use INSERT OR IGNORE to preserve original discovered timestamp
        if records:
            self.conn.executemany("""
                INSERT OR IGNORE INTO private_domains
                (submitted_email_domain, domain, discovered)
                VALUES (?, ?, ?)
            """, [(r['submitted_email_domain'], r['domain'], r['discovered']) for r in records])

        return len(records)

    def query_by_email_domain(self, email_domain: str):
        """
        Query all domains submitted by a specific email domain.

        Args:
            email_domain: The email domain to search for

        Returns:
            DuckDB relation object
        """
        return self.conn.execute("""
            SELECT submitted_email_domain, domain, discovered
            FROM private_domains
            WHERE submitted_email_domain = ?
            ORDER BY domain
        """, [email_domain])

    def get_all_records(self):
        """Get all records from the database."""
        return self.conn.execute("""
            SELECT submitted_email_domain, domain, discovered
            FROM private_domains
            ORDER BY submitted_email_domain, domain
        """)

    def get_stats(self):
        """Get statistics about the database."""
        return self.conn.execute("""
            SELECT
                COUNT(DISTINCT submitted_email_domain) as unique_email_domains,
                COUNT(*) as total_domains
            FROM private_domains
        """).fetchone()

    def get_new_entries_today(self):
        """Get entries discovered today."""
        return self.conn.execute("""
            SELECT submitted_email_domain, domain, discovered
            FROM private_domains
            WHERE DATE(discovered) = CURRENT_DATE
            ORDER BY submitted_email_domain, domain
        """).fetchall()

    def get_new_entries_by_date(self, date_str: str):
        """Get entries discovered on a specific date (YYYY-MM-DD)."""
        return self.conn.execute("""
            SELECT submitted_email_domain, domain, discovered
            FROM private_domains
            WHERE DATE(discovered) = ?
            ORDER BY submitted_email_domain, domain
        """, [date_str]).fetchall()

    def generate_summary(self, entries, date_str: str) -> str:
        """Generate a markdown summary of new entries grouped by submitter domain."""
        if not entries:
            return f"# Public Suffix List Update - {date_str}\n\nNo new domains discovered on this date.\n"

        # Group by submitted_email_domain
        grouped = {}
        for email_domain, domain, discovered in entries:
            if email_domain not in grouped:
                grouped[email_domain] = []
            grouped[email_domain].append(domain)

        # Generate markdown
        md = [f"# Public Suffix List Update - {date_str}\n"]
        md.append(f"**Total new domains:** {len(entries)}\n")
        md.append(f"**Submitter organizations:** {len(grouped)}\n")
        md.append("---\n")

        for email_domain in sorted(grouped.keys()):
            domains = grouped[email_domain]
            md.append(f"## {email_domain}\n")
            md.append(f"**New domains:** {len(domains)}\n")
            md.append("")
            for domain in domains:
                md.append(f"- `{domain}`")
            md.append("")

        return "\n".join(md)

    def close(self):
        """Close the database connection."""
        self.conn.close()


def main():
    """Main entry point for the utility."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python main.py <command> [arguments]")
        print("\nCommands:")
        print("  load [psl_file]           - Load PSL data into DuckDB")
        print("  query <email_domain>      - Query domains by email domain")
        print("  stats                     - Show database statistics")
        print("  summary [date]            - Generate summary of new entries (default: today)")
        print("  export [filename]         - Export all data to CSV")
        print("\nExamples:")
        print("  python main.py load")
        print("  python main.py load /path/to/public_suffix_list.dat")
        print("  python main.py query akamai.com")
        print("  python main.py stats")
        print("  python main.py summary")
        print("  python main.py summary 2025-12-08")
        print("  python main.py export")
        sys.exit(1)

    command = sys.argv[1]
    parser = PublicSuffixListParser()

    try:
        if command == "load":
            file_path = sys.argv[2] if len(sys.argv) > 2 else None
            parser.file_path = file_path
            print("Loading Public Suffix List...")
            count = parser.parse_and_load()
            print(f"Successfully loaded {count} private domain records into DuckDB")

            stats = parser.get_stats()
            print(f"Unique email domains: {stats[0]}")
            print(f"Total domains: {stats[1]}")

        elif command == "query":
            if len(sys.argv) < 3:
                print("Error: email_domain required")
                print("Usage: python main.py query <email_domain>")
                sys.exit(1)

            email_domain = sys.argv[2]
            result = parser.query_by_email_domain(email_domain)
            rows = result.fetchall()

            if len(rows) == 0:
                print(f"No records found for email domain: {email_domain}")
            else:
                print(f"\nRecords for email domain: {email_domain}")
                print("=" * 70)
                print(f"{'Submitted Email Domain':<30} {'Domain':<40} {'Discovered':<20}")
                print("-" * 70)
                for row in rows:
                    print(f"{row[0]:<30} {row[1]:<40} {row[2]}")
                print(f"\nTotal: {len(rows)} domains")

        elif command == "stats":
            stats = parser.get_stats()
            print("\nDatabase Statistics")
            print("=" * 70)
            print(f"Unique email domains: {stats[0]}")
            print(f"Total domains: {stats[1]}")

        elif command == "summary":
            from datetime import date
            import os

            # Get date from argument or use today
            if len(sys.argv) > 2:
                date_str = sys.argv[2]
                entries = parser.get_new_entries_by_date(date_str)
            else:
                date_str = date.today().isoformat()
                entries = parser.get_new_entries_today()

            # Only create file if there are new entries
            if entries:
                # Generate markdown summary
                summary_md = parser.generate_summary(entries, date_str)

                # Ensure summaries directory exists
                os.makedirs("summaries", exist_ok=True)

                # Write to file in summaries subdirectory
                filename = f"summaries/new-domains-{date_str}.md"
                with open(filename, 'w') as f:
                    f.write(summary_md)

                print(f"Generated summary: {filename}")
                print(f"New domains found: {len(entries)}")
                sys.exit(0)
            else:
                print(f"No new domains found for {date_str}")
                print("No summary file created")
                sys.exit(1)

        elif command == "export":
            output_file = sys.argv[2] if len(sys.argv) > 2 else "private_domains.csv"
            parser.conn.execute(f"""
                COPY (
                    SELECT submitted_email_domain, domain, discovered
                    FROM private_domains
                    ORDER BY submitted_email_domain, domain
                ) TO '{output_file}' (HEADER, DELIMITER ',')
            """)
            print(f"Exported all records to {output_file}")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    finally:
        parser.close()


if __name__ == "__main__":
    main()
