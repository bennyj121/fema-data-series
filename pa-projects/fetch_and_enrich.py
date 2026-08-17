#!/usr/bin/env python3
"""
Rogue FEMA Data Series — OpenFEMA Public Assistance Funded Projects, enriched.

Downloads every obligated Public Assistance project worksheet from the
official OpenFEMA Public Assistance Funded Projects Details v2 API
(paginated), adds deterministic derived columns, and writes analysis-ready
CSV / parquet products.

Companion to the declarations dataset. Grain is one
funded project worksheet, not a declaration. Join on disasterNumber.

No API key. No accounts. No scraping. No personal data. Applicant names
are not in this table (IDs only). Project titles are facility/work
descriptions, not people.

Re-run:
    python3 fetch_and_enrich.py

Source:
    https://www.fema.gov/api/open/v2/PublicAssistanceFundedProjectsDetails
    https://www.fema.gov/openfema-data-page/public-assistance-funded-projects-details-v2

This product uses the Federal Emergency Management Agency's OpenFEMA API,
but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch
for the data or analyses derived from these data after the data have been
retrieved from the Agency's website(s).
"""

from __future__ import annotations

import csv
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_ENDPOINT = (
    "https://www.fema.gov/api/open/v2/PublicAssistanceFundedProjectsDetails"
)
DATASET_PAGE = (
    "https://www.fema.gov/openfema-data-page/"
    "public-assistance-funded-projects-details-v2"
)
TERMS_PAGE = "https://www.fema.gov/about/openfema/terms-conditions"
USER_AGENT = (
    "Rogue/fema-data-series/pa-projects "
    "(Rogue AI dataset builder; no personal data collected)"
)
PAGE_SIZE = 10000  # OpenFEMA maximum $top
MAX_RETRIES = 6
BACKOFF_BASE_SECONDS = 2.0
TIMEOUT_SECONDS = 120

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE
FULL_CSV = DATA_DIR / "fema-pa-funded-projects-enriched.csv"
SAMPLE_CSV = DATA_DIR / "sample-1000.csv"
RUN_META = DATA_DIR / "run-metadata.json"
PARQUET_PATH = DATA_DIR / "fema-pa-funded-projects-enriched.parquet"

# Official PA work categories (FEMA Public Assistance Program Overview).
# https://www.fema.gov/assistance/public/program-overview
WORK_CLASS = {
    "A": "Emergency Work",
    "B": "Emergency Work",
    "C": "Permanent Work",
    "D": "Permanent Work",
    "E": "Permanent Work",
    "F": "Permanent Work",
    "G": "Permanent Work",
    "Z": "Management Costs",
    "I": "Building Code / Administration",
}

# Official FEMA region names and member jurisdictions (same map as 005).
FEMA_REGION = {
    1: {
        "name": "Region 1 — Boston",
        "hq_city": "Boston",
        "states": "CT,ME,MA,NH,RI,VT",
    },
    2: {
        "name": "Region 2 — New York",
        "hq_city": "New York",
        "states": "NJ,NY,PR,VI",
    },
    3: {
        "name": "Region 3 — Philadelphia",
        "hq_city": "Philadelphia",
        "states": "DE,DC,MD,PA,VA,WV",
    },
    4: {
        "name": "Region 4 — Atlanta",
        "hq_city": "Atlanta",
        "states": "AL,FL,GA,KY,MS,NC,SC,TN",
    },
    5: {
        "name": "Region 5 — Chicago",
        "hq_city": "Chicago",
        "states": "IL,IN,MI,MN,OH,WI",
    },
    6: {
        "name": "Region 6 — Denton",
        "hq_city": "Denton",
        "states": "AR,LA,NM,OK,TX",
    },
    7: {
        "name": "Region 7 — Kansas City",
        "hq_city": "Kansas City",
        "states": "IA,KS,MO,NE",
    },
    8: {
        "name": "Region 8 — Denver",
        "hq_city": "Denver",
        "states": "CO,MT,ND,SD,UT,WY",
    },
    9: {
        "name": "Region 9 — Oakland",
        "hq_city": "Oakland",
        "states": "AZ,CA,HI,NV,AS,GU,MP",
    },
    10: {
        "name": "Region 10 — Bothell",
        "hq_city": "Bothell",
        "states": "AK,ID,OR,WA",
    },
}

STATE_TO_REGION = {
    "CT": 1, "ME": 1, "MA": 1, "NH": 1, "RI": 1, "VT": 1,
    "NJ": 2, "NY": 2, "PR": 2, "VI": 2,
    "DE": 3, "DC": 3, "MD": 3, "PA": 3, "VA": 3, "WV": 3,
    "AL": 4, "FL": 4, "GA": 4, "KY": 4, "MS": 4, "NC": 4, "SC": 4, "TN": 4,
    "IL": 5, "IN": 5, "MI": 5, "MN": 5, "OH": 5, "WI": 5,
    "AR": 6, "LA": 6, "NM": 6, "OK": 6, "TX": 6,
    "IA": 7, "KS": 7, "MO": 7, "NE": 7,
    "CO": 8, "MT": 8, "ND": 8, "SD": 8, "UT": 8, "WY": 8,
    "AZ": 9, "CA": 9, "HI": 9, "NV": 9, "AS": 9, "GU": 9, "MP": 9,
    "AK": 10, "ID": 10, "OR": 10, "WA": 10,
}

STATE_NAME = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "AS": "American Samoa",
    "GU": "Guam",
    "MP": "Northern Mariana Islands",
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
    "FM": "Federated States of Micronesia",
    "MH": "Marshall Islands",
    "PW": "Palau",
    "UM": "U.S. Minor Outlying Islands",
}

# Taxonomy over official incidentType values. Same groups as 005 so the
# two files can be filtered together. Unknown values become "Other".
INCIDENT_TYPE_GROUP = {
    "hurricane": "Tropical cyclone",
    "typhoon": "Tropical cyclone",
    "tropical storm": "Tropical cyclone",
    "tropical depression": "Tropical cyclone",
    "flood": "Flood",
    "coastal storm": "Coastal / marine",
    "tidal wave": "Coastal / marine",
    "tsunami": "Coastal / marine",
    "dam/levee break": "Flood",
    "dam break": "Flood",
    "fire": "Fire",
    "wildfire": "Fire",
    "severe storm(s)": "Severe storm",
    "severe storm": "Severe storm",
    "straight-line winds": "Severe storm",
    "tornado": "Tornado",
    "snow": "Winter weather",
    "snowstorm": "Winter weather",
    "severe ice storm": "Winter weather",
    "freezing": "Winter weather",
    "winter storm": "Winter weather",
    "drought": "Drought / agriculture",
    "crop losses": "Drought / agriculture",
    "fishing losses": "Drought / agriculture",
    "earthquake": "Geologic",
    "volcanic eruption": "Geologic",
    "volcano": "Geologic",
    "mud/landslide": "Geologic",
    "terrorist attack": "Human / technological",
    "national special security event": "Human / technological",
    "severe storms, straight-line winds, tornadoes, and flooding": "Severe storm",
    "biological": "Biological",
    "chemical": "Human / technological",
    "toxic substances": "Human / technological",
    "terrorist": "Human / technological",
    "human cause": "Human / technological",
    "civil unrest": "Human / technological",
    "nuclear": "Human / technological",
    "explosion": "Human / technological",
    "other": "Other",
}

RAW_FIELDS = [
    "disasterNumber",
    "declarationDate",
    "incidentType",
    "pwNumber",
    "applicationTitle",
    "applicantId",
    "damageCategoryCode",
    "damageCategoryDescrip",
    "projectStatus",
    "projectProcessStep",
    "projectSize",
    "county",
    "countyCode",
    "stateAbbreviation",
    "stateNumberCode",
    "projectAmount",
    "federalShareObligated",
    "totalObligated",
    "lastObligationDate",
    "firstObligationDate",
    "mitigationAmount",
    "gmProjectId",
    "gmApplicantId",
    "lastRefresh",
    "hash",
]

SELECT_FIELDS = ",".join(RAW_FIELDS)

DERIVED_FIELDS = [
    "declaration_date_iso",
    "first_obligation_date_iso",
    "last_obligation_date_iso",
    "last_refresh_iso",
    "declaration_year",
    "declaration_month",
    "declaration_quarter",
    "first_obligation_year",
    "last_obligation_year",
    "days_declaration_to_first_obligation",
    "days_first_to_last_obligation",
    "is_single_obligation",
    "state_name",
    "region",
    "region_name",
    "region_hq_city",
    "region_states",
    "fips_state_code",
    "fips_county_code",
    "fips_geoid",
    "work_class",
    "is_emergency_work",
    "is_permanent_work",
    "is_management_costs",
    "is_debris",
    "is_protective_measures",
    "is_roads_bridges",
    "is_water_control",
    "is_buildings",
    "is_utilities",
    "is_parks_rec",
    "incident_type_group",
    "is_hurricane",
    "is_flood",
    "is_fire",
    "is_covid",
    "is_tornado",
    "is_earthquake",
    "is_drought",
    "is_winter",
    "is_severe_storm",
    "is_biological",
    "is_tropical",
    "federal_share_pct",
    "mitigation_share_pct",
    "has_mitigation",
    "is_deobligation",
    "is_zero_federal_share",
    "is_large_project",
    "is_small_project",
    "is_closed",
    "is_eligible",
    "federal_obligation_bucket",
    "source_api_endpoint",
    "source_dataset_page",
    "fetched_at",
]

OUTPUT_FIELDS = RAW_FIELDS + DERIVED_FIELDS


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def http_get_json(url: str) -> dict:
    """GET JSON with retries and exponential backoff. Raises on final failure."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(
                req, timeout=TIMEOUT_SECONDS, context=_ssl_context()
            ) as resp:
                raw = resp.read()
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status} for {url}")
                return json.loads(raw.decode("utf-8"))
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            RuntimeError,
        ) as exc:
            last_error = exc
            wait = BACKOFF_BASE_SECONDS ** attempt
            print(
                f"  request failed (attempt {attempt}/{MAX_RETRIES}): {exc}",
                file=sys.stderr,
            )
            if attempt < MAX_RETRIES:
                print(f"  retrying in {wait:.1f}s …", file=sys.stderr)
                time.sleep(wait)
    raise RuntimeError(
        f"OpenFEMA API failed after {MAX_RETRIES} attempts: {last_error}"
    )


# ---------------------------------------------------------------------------
# Parsing helpers (deterministic; never invent facts)
# ---------------------------------------------------------------------------

def parse_dt(value) -> datetime | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10]).replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_date(dt: datetime | None) -> str:
    return dt.date().isoformat() if dt else ""


def iso_datetime(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def as_bool_size(value: str, target: str) -> bool:
    return (value or "").strip().lower() == target


def csv_bool(flag: bool) -> str:
    return "true" if flag else "false"


def days_between(a: datetime | None, b: datetime | None) -> str:
    if a is None or b is None:
        return ""
    return str((b.date() - a.date()).days)


def pad_fips(value, width: int) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(width)
    return text


def as_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def csv_num(value) -> str:
    """Pass through a number without inventing precision."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return csv_bool(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        # Keep source precision; avoid scientific notation.
        return format(value, "f").rstrip("0").rstrip(".")
    text = str(value).strip()
    return text


def pct(numer: float | None, denom: float | None) -> str:
    if numer is None or denom is None or denom == 0:
        return ""
    return f"{(numer / denom) * 100:.2f}"


def incident_group(incident_type: str) -> str:
    key = (incident_type or "").strip().lower()
    if not key:
        return ""
    return INCIDENT_TYPE_GROUP.get(key, "Other")


def keyword_blob(*parts: object) -> str:
    return " ".join("" if p is None else str(p) for p in parts).lower()


def contains_any(blob: str, needles: tuple[str, ...]) -> bool:
    return any(n in blob for n in needles)


def obligation_bucket(amount: float | None) -> str:
    if amount is None:
        return ""
    if amount < 0:
        return "negative"
    if amount == 0:
        return "zero"
    if amount < 10_000:
        return "under_10k"
    if amount < 100_000:
        return "10k_to_100k"
    if amount < 1_000_000:
        return "100k_to_1m"
    if amount < 10_000_000:
        return "1m_to_10m"
    return "10m_plus"


def enrich(row: dict, fetched_at: str) -> dict:
    decl = parse_dt(row.get("declarationDate"))
    first_ob = parse_dt(row.get("firstObligationDate"))
    last_ob = parse_dt(row.get("lastObligationDate"))
    last_ref = parse_dt(row.get("lastRefresh"))

    incident_type = row.get("incidentType") or ""
    title = row.get("applicationTitle") or ""
    # Hazard flags use official incidentType only. applicationTitle is a
    # project/facility name ("Evart Fire Dept") and must not set is_fire.
    type_blob = keyword_blob(incident_type)
    title_blob = keyword_blob(title)

    state = (row.get("stateAbbreviation") or "").strip().upper()
    region_n = STATE_TO_REGION.get(state)
    region_info = FEMA_REGION.get(region_n, {}) if region_n else {}

    fips_state = pad_fips(row.get("stateNumberCode"), 2)
    fips_county = pad_fips(row.get("countyCode"), 3)
    geoid = f"{fips_state}{fips_county}" if fips_state and fips_county else ""

    cat = (row.get("damageCategoryCode") or "").strip().upper()
    work = WORK_CLASS.get(cat, "Other" if cat else "")

    project_amt = as_float(row.get("projectAmount"))
    fed = as_float(row.get("federalShareObligated"))
    total = as_float(row.get("totalObligated"))
    mitig = as_float(row.get("mitigationAmount"))

    size = (row.get("projectSize") or "").strip()
    status = (row.get("projectStatus") or "").strip()
    step = (row.get("projectProcessStep") or "").strip()

    out = {k: row.get(k, "") for k in RAW_FIELDS}
    out["disasterNumber"] = row.get("disasterNumber", "")
    out["pwNumber"] = row.get("pwNumber", "")
    out["projectAmount"] = csv_num(row.get("projectAmount"))
    out["federalShareObligated"] = csv_num(row.get("federalShareObligated"))
    out["totalObligated"] = csv_num(row.get("totalObligated"))
    out["mitigationAmount"] = csv_num(row.get("mitigationAmount"))
    out["gmProjectId"] = row.get("gmProjectId", "")
    out["gmApplicantId"] = row.get("gmApplicantId", "")
    out["stateNumberCode"] = fips_state
    out["countyCode"] = fips_county
    out["stateAbbreviation"] = state

    out["declaration_date_iso"] = iso_date(decl)
    out["first_obligation_date_iso"] = iso_date(first_ob)
    out["last_obligation_date_iso"] = iso_date(last_ob)
    out["last_refresh_iso"] = iso_datetime(last_ref)
    out["declaration_year"] = str(decl.year) if decl else ""
    out["declaration_month"] = f"{decl.month:02d}" if decl else ""
    out["declaration_quarter"] = str((decl.month - 1) // 3 + 1) if decl else ""
    out["first_obligation_year"] = str(first_ob.year) if first_ob else ""
    out["last_obligation_year"] = str(last_ob.year) if last_ob else ""
    out["days_declaration_to_first_obligation"] = days_between(decl, first_ob)
    out["days_first_to_last_obligation"] = days_between(first_ob, last_ob)
    out["is_single_obligation"] = csv_bool(
        first_ob is not None
        and last_ob is not None
        and first_ob.date() == last_ob.date()
    )
    out["state_name"] = STATE_NAME.get(state, "")
    out["region"] = str(region_n) if region_n else ""
    out["region_name"] = region_info.get("name", "")
    out["region_hq_city"] = region_info.get("hq_city", "")
    out["region_states"] = region_info.get("states", "")
    out["fips_state_code"] = fips_state
    out["fips_county_code"] = fips_county
    out["fips_geoid"] = geoid
    out["work_class"] = work
    out["is_emergency_work"] = csv_bool(work == "Emergency Work")
    out["is_permanent_work"] = csv_bool(work == "Permanent Work")
    out["is_management_costs"] = csv_bool(work == "Management Costs")
    out["is_debris"] = csv_bool(cat == "A")
    out["is_protective_measures"] = csv_bool(cat == "B")
    out["is_roads_bridges"] = csv_bool(cat == "C")
    out["is_water_control"] = csv_bool(cat == "D")
    out["is_buildings"] = csv_bool(cat == "E")
    out["is_utilities"] = csv_bool(cat == "F")
    out["is_parks_rec"] = csv_bool(cat == "G")
    out["incident_type_group"] = incident_group(incident_type)
    out["is_hurricane"] = csv_bool(contains_any(type_blob, ("hurricane", "typhoon")))
    out["is_flood"] = csv_bool(contains_any(type_blob, ("flood",)))
    out["is_fire"] = csv_bool(contains_any(type_blob, ("fire",)))
    out["is_covid"] = csv_bool(
        contains_any(type_blob, ("covid", "coronavirus", "covid-19", "covid19"))
        or contains_any(title_blob, ("covid", "coronavirus", "covid-19", "covid19"))
    )
    out["is_tornado"] = csv_bool(contains_any(type_blob, ("tornado",)))
    out["is_earthquake"] = csv_bool(contains_any(type_blob, ("earthquake",)))
    out["is_drought"] = csv_bool(contains_any(type_blob, ("drought",)))
    out["is_winter"] = csv_bool(
        contains_any(
            type_blob,
            ("snow", "ice storm", "freezing", "winter storm", "winter weather"),
        )
    )
    out["is_severe_storm"] = csv_bool(
        contains_any(type_blob, ("severe storm", "straight-line wind"))
    )
    out["is_biological"] = csv_bool(contains_any(type_blob, ("biological",)))
    out["is_tropical"] = csv_bool(
        contains_any(
            type_blob,
            (
                "hurricane",
                "typhoon",
                "tropical storm",
                "tropical depression",
            ),
        )
    )
    out["federal_share_pct"] = pct(fed, project_amt)
    out["mitigation_share_pct"] = pct(mitig, project_amt)
    out["has_mitigation"] = csv_bool(mitig is not None and mitig != 0)
    out["is_deobligation"] = csv_bool(
        (fed is not None and fed < 0)
        or (total is not None and total < 0)
        or (project_amt is not None and project_amt < 0)
    )
    out["is_zero_federal_share"] = csv_bool(fed is not None and fed == 0)
    out["is_large_project"] = csv_bool(as_bool_size(size, "large"))
    out["is_small_project"] = csv_bool(as_bool_size(size, "small"))
    out["is_closed"] = csv_bool(step == "Project Closed Out")
    out["is_eligible"] = csv_bool(status.lower() == "eligible")
    out["federal_obligation_bucket"] = obligation_bucket(fed)
    out["source_api_endpoint"] = API_ENDPOINT
    out["source_dataset_page"] = DATASET_PAGE
    out["fetched_at"] = fetched_at

    for key in OUTPUT_FIELDS:
        if out.get(key) is None:
            out[key] = ""
    return out


def fetch_count() -> int:
    count_url = (
        f"{API_ENDPOINT}?$count=true&$top=1&$metadata=true"
        "&$select=hash"
    )
    print(f"Counting records: {count_url}")
    meta = http_get_json(count_url)
    reported = int(meta.get("metadata", {}).get("count") or 0)
    print(f"OpenFEMA reported count: {reported}")
    return reported


def iter_pages():
    """Yield pages of raw records, newest declaration first."""
    skip = 0
    while True:
        query = urllib.parse.urlencode(
            {
                "$top": PAGE_SIZE,
                "$skip": skip,
                "$metadata": "off",
                "$orderby": "declarationDate desc,disasterNumber desc,gmProjectId",
                "$select": SELECT_FIELDS,
            }
        )
        url = f"{API_ENDPOINT}?{query}"
        print(f"Fetching skip={skip} top={PAGE_SIZE}")
        payload = http_get_json(url)
        page = payload.get("PublicAssistanceFundedProjectsDetails")
        if page is None:
            if isinstance(payload, list):
                page = payload
            else:
                page = []
        if not page:
            break
        print(f"  got {len(page)}")
        yield page
        if len(page) < PAGE_SIZE:
            break
        skip += PAGE_SIZE


def write_parquet(csv_path: Path, parquet_path: Path) -> bool:
    try:
        import pyarrow.csv as pacsv  # type: ignore
        import pyarrow.parquet as papq  # type: ignore
    except ImportError:
        print("pyarrow not installed; CSV only.")
        return False
    table = pacsv.read_csv(str(csv_path))
    papq.write_table(table, str(parquet_path), compression="zstd")
    return True


def main() -> int:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"fetched_at={fetched_at}")
    print(f"User-Agent={USER_AGENT}")
    print(f"endpoint={API_ENDPOINT}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        reported = fetch_count()
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        print(
            "Stopped. No output files written. Re-run when the API is reachable.",
            file=sys.stderr,
        )
        return 1

    downloaded = 0
    sample_rows: list[dict] = []
    incident_types: Counter[str] = Counter()
    work_classes: Counter[str] = Counter()
    buckets: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    empty_state_name = 0
    empty_region = 0
    closed_n = 0
    eligible_n = 0
    large_n = 0
    deob_n = 0
    mitig_n = 0
    min_date = ""
    max_date = ""
    sum_federal = 0.0
    sum_project = 0.0
    sum_total = 0.0

    FLAG_KEYS = (
        "is_hurricane",
        "is_flood",
        "is_fire",
        "is_covid",
        "is_tornado",
        "is_earthquake",
        "is_drought",
        "is_winter",
        "is_severe_storm",
        "is_biological",
        "is_tropical",
        "is_emergency_work",
        "is_permanent_work",
        "is_management_costs",
    )

    try:
        with FULL_CSV.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=OUTPUT_FIELDS, extrasaction="ignore"
            )
            writer.writeheader()
            for page in iter_pages():
                for raw in page:
                    row = enrich(raw, fetched_at)
                    writer.writerow(row)
                    downloaded += 1
                    if len(sample_rows) < 1000:
                        sample_rows.append(row)

                    itype = (raw.get("incidentType") or "").strip()
                    incident_types[itype] += 1
                    work_classes[row["work_class"]] += 1
                    buckets[row["federal_obligation_bucket"]] += 1
                    categories[
                        f"{row.get('damageCategoryCode') or ''}|"
                        f"{row.get('damageCategoryDescrip') or ''}"
                    ] += 1
                    if not row["state_name"]:
                        empty_state_name += 1
                    if not row["region_name"]:
                        empty_region += 1
                    if row["is_closed"] == "true":
                        closed_n += 1
                    if row["is_eligible"] == "true":
                        eligible_n += 1
                    if row["is_large_project"] == "true":
                        large_n += 1
                    if row["is_deobligation"] == "true":
                        deob_n += 1
                    if row["has_mitigation"] == "true":
                        mitig_n += 1
                    for fk in FLAG_KEYS:
                        if row[fk] == "true":
                            flag_counts[fk] += 1
                    d = row["declaration_date_iso"]
                    if d:
                        if not min_date or d < min_date:
                            min_date = d
                        if not max_date or d > max_date:
                            max_date = d
                    fed = as_float(row["federalShareObligated"])
                    proj = as_float(row["projectAmount"])
                    tot = as_float(row["totalObligated"])
                    if fed is not None:
                        sum_federal += fed
                    if proj is not None:
                        sum_project += proj
                    if tot is not None:
                        sum_total += tot
                print(f"  running total {downloaded}")
                fh.flush()
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        print(
            "Stopped mid-fetch. Partial CSV may exist. Re-run to replace it.",
            file=sys.stderr,
        )
        return 1

    if downloaded == 0:
        print("FATAL: API returned 0 records. Stopping.", file=sys.stderr)
        if FULL_CSV.exists():
            FULL_CSV.unlink()
        return 1

    with SAMPLE_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=OUTPUT_FIELDS, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(sample_rows)

    full_bytes = FULL_CSV.stat().st_size
    sample_bytes = SAMPLE_CSV.stat().st_size
    sample_n = len(sample_rows)

    parquet_written = False
    parquet_bytes = 0
    if full_bytes > 25 * 1024 * 1024:
        print("Writing parquet …")
        parquet_written = write_parquet(FULL_CSV, PARQUET_PATH)
        if parquet_written:
            parquet_bytes = PARQUET_PATH.stat().st_size

    meta = {
        "fetched_at_utc": fetched_at,
        "api_endpoint": API_ENDPOINT,
        "dataset_page": DATASET_PAGE,
        "terms_page": TERMS_PAGE,
        "reported_count": reported,
        "downloaded_count": downloaded,
        "enriched_count": downloaded,
        "sample_count": sample_n,
        "full_csv": FULL_CSV.name,
        "full_csv_bytes": full_bytes,
        "sample_csv_bytes": sample_bytes,
        "parquet_written": parquet_written,
        "parquet_bytes": parquet_bytes,
        "coverage_declaration_date_min": min_date,
        "coverage_declaration_date_max": max_date,
        "sum_project_amount": round(sum_project, 2),
        "sum_federal_share_obligated": round(sum_federal, 2),
        "sum_total_obligated": round(sum_total, 2),
        "closed_count": closed_n,
        "eligible_count": eligible_n,
        "large_project_count": large_n,
        "deobligation_count": deob_n,
        "has_mitigation_count": mitig_n,
        "empty_state_name": empty_state_name,
        "empty_region_name": empty_region,
        "unique_incident_types": sorted(incident_types.keys()),
        "incident_type_counts": dict(incident_types.most_common()),
        "work_class_counts": dict(work_classes.most_common()),
        "federal_obligation_bucket_counts": dict(buckets.most_common()),
        "damage_category_counts": dict(categories.most_common()),
        "flag_counts": dict(flag_counts),
        "user_agent": USER_AGENT,
        "ai_authorship": (
            "Built by Rogue, an AI agent. Not a human. "
            "Source data is U.S. government public information."
        ),
        "listed_on_kofi": False,
        "pushed_to_github": False,
    }
    RUN_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print()
    print("=== done ===")
    print(f"rows downloaded : {downloaded}")
    print(f"rows reported   : {reported}")
    print(f"full csv        : {FULL_CSV} ({full_bytes} bytes)")
    print(f"sample csv      : {SAMPLE_CSV} ({sample_bytes} bytes, {sample_n} rows)")
    if parquet_written:
        print(f"parquet         : {PARQUET_PATH} ({parquet_bytes} bytes)")
    print(f"coverage        : {min_date} through {max_date}")
    print(f"incident types  : {sorted(incident_types.keys())}")
    print(f"work classes    : {dict(work_classes)}")
    if reported and downloaded != reported:
        print(
            f"WARNING: downloaded {downloaded} != reported {reported}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
