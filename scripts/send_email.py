#!/usr/bin/env python3
"""Send the daily report via email from GitHub Actions."""
import os
import sys
from pathlib import Path

# Ensure we can import from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ashare_us_catalyst.notifier import send_email


def main() -> int:
    report_file = os.environ.get("REPORT_FILE", "")
    if not report_file or not os.path.isfile(report_file):
        print(f"Report file not found: {report_file}", file=sys.stderr)
        return 1

    # Credentials from GitHub Secrets (env)
    if not os.environ.get("SMTP_USER") or not os.environ.get("SMTP_PASSWORD"):
        print("SMTP_USER or SMTP_PASSWORD not set, skipping email.", file=sys.stderr)
        return 0

    report = Path(report_file).read_text(encoding="utf-8")
    report_date = os.environ.get("REPORT_DATE", "")

    title = f"美股映射A股早报 - {report_date}" if report_date else "美股映射A股早报"
    result = send_email(report, subject=title)
    print(f"Email sent to: {', '.join(result['to'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
