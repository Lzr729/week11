from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


expected_directories = {"data", "metadata", "reports", "scripts"}
actual_directories = {path.name for path in ROOT.iterdir() if path.is_dir()}
assert actual_directories == expected_directories, f"Unexpected top-level directories: {sorted(actual_directories)}"
assert not any(path.is_dir() for folder in expected_directories for path in (ROOT / folder).iterdir()), "Nested directory found"

required = [
    ROOT / "README.md",
    ROOT / "CHECKSUMS.sha256",
    DATA / "company09_ugreen_standard_dataset_v1.0.json",
    DATA / "company10_laplace_standard_dataset_v1.1.json",
    DATA / "ten_company_integrated_dataset_v1.1.json",
    DATA / "ten_company_variable_long_v1.1.csv",
    DATA / "two_company_acceptance_checks.csv",
    DATA / "two_company_reuse_assessment.csv",
    REPORTS / "week11_company09_ugreen_extension_test_v1.1.xlsx",
    REPORTS / "week11_company10_laplace_boundary_test_v1.1.xlsx",
    REPORTS / "week11_two_company_extension_validation_summary_v1.1.pdf",
]
missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
assert not missing, f"Missing files: {missing}"

standard_tables = {
    "companies", "financing_events", "transactions", "entities", "transaction_parties",
    "evidence", "numeric_validation", "investment_paths", "validation_issues",
}
assert {path.stem.removeprefix("ten_companies_") for path in DATA.glob("ten_companies_*.csv")} == standard_tables

integrated = json.loads((DATA / "ten_company_integrated_dataset_v1.1.json").read_text(encoding="utf-8"))
assert integrated["table_counts"]["companies"] == 10
assert len(read_csv(DATA / "ten_company_variable_long_v1.1.csv")) == 320

checks = read_csv(DATA / "two_company_acceptance_checks.csv")
assert len(checks) == 34
assert all(row["status"] == "PASS" for row in checks)
assert {row["company_code"] for row in checks} == {"301606", "688726"}

stale = re.compile(r"week\s*12", re.IGNORECASE)
for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix.lower() in {".md", ".json", ".csv"}:
        assert not stale.search(path.read_text(encoding="utf-8-sig", errors="replace")), f"Stale prior-week label: {path.name}"

for workbook in REPORTS.glob("*.xlsx"):
    with zipfile.ZipFile(workbook) as archive:
        xml = "\n".join(archive.read(name).decode("utf-8", errors="ignore") for name in archive.namelist() if name.endswith(".xml"))
    assert not stale.search(xml), f"Stale prior-week label in {workbook.name}"
    assert not re.search(r"#REF!|#DIV/0!|#VALUE!|#NAME\?|#N/A", xml), f"Formula error token in {workbook.name}"

pdf = REPORTS / "week11_two_company_extension_validation_summary_v1.1.pdf"
pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(pdf).pages)
assert "第九、十家公司扩展性验证" in pdf_text
assert not stale.search(pdf_text)

for line in (ROOT / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
    digest, relative = line.split("  ", 1)
    target = ROOT / relative
    assert target.exists() and sha256(target) == digest, f"Checksum mismatch: {relative}"

print("PASS: Week 11 compact release verified")
