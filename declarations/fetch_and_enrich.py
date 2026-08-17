#!/usr/bin/env python3
"""
Rogue FEMA Data Series — OpenFEMA Disaster Declarations, enriched.

Downloads every record from the official OpenFEMA Disaster Declarations
Summaries v2 API (paginated), adds deterministic derived columns, and
writes analysis-ready CSV products.

No API key. No accounts. No scraping. No personal data.

Re-run:
    python3 fetch_and_enrich.py

Source:
    https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries
    https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2

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
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_ENDPOINT = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
DATASET_PAGE = (
    "https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2"
)
TERMS_PAGE = "https://www.fema.gov/about/openfema/terms-conditions"
USER_AGENT = (
    "Rogue/fema-data-series/declarations "
    "(Rogue AI dataset builder; no personal data collected)"
)
PAGE_SIZE = 10000  # OpenFEMA maximum $top
MAX_RETRIES = 6
BACKOFF_BASE_SECONDS = 2.0
TIMEOUT_SECONDS = 90

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE
FULL_CSV = DATA_DIR / "fema-disaster-declarations-enriched.csv"
SAMPLE_CSV = DATA_DIR / "sample-1000.csv"
RUN_META = DATA_DIR / "run-metadata.json"

# Official Stafford Act declaration-type codes (dataset dictionary).
DECLARATION_TYPE_LABEL = {
    "DR": "Major Disaster",
    "EM": "Emergency",
    "FM": "Fire Management Assistance",
}

# Official designatedIncidentTypes codebook from the v2 data dictionary
# (https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2).
DESIGNATED_TYPE_CODE = {
    "0": "Not applicable",
    "1": "Explosion",
    "2": "Straight-Line Winds",
    "3": "Tidal Wave",
    "4": "Tropical Storm",
    "5": "Winter Storm",
    "8": "Tropical Depression",
    "A": "Tsunami",
    "B": "Biological",
    "C": "Coastal Storm",
    "D": "Drought",
    "E": "Earthquake",
    "F": "Flood",
    "G": "Freezing",
    "H": "Hurricane",
    "I": "Terrorist",
    "J": "Typhoon",
    "K": "Dam/Levee Break",
    "L": "Chemical",
    "M": "Mud/Landslide",
    "N": "Nuclear",
    "O": "Severe Ice Storm",
    "P": "Fishing Losses",
    "Q": "Crop Losses",
    "R": "Fire",
    "S": "Snowstorm",
    "T": "Tornado",
    "U": "Civil Unrest",
    "V": "Volcanic Eruption",
    "W": "Severe Storm",
    "X": "Toxic Substances",
    "Y": "Human Cause",
    "Z": "Other",
}

# Official FEMA region names and member jurisdictions (FEMA Regions v2 /
# FEMA public region list). Derived from the numeric `region` field.
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

# USPS / FIPS-style jurisdiction names. Deterministic from `state`.
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

# Taxonomy over official incidentType values. Unknown values become "Other".
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
    "mud/landslide": "Geologic",
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
    "femaDeclarationString",
    "disasterNumber",
    "state",
    "declarationType",
    "declarationDate",
    "fyDeclared",
    "incidentType",
    "declarationTitle",
    "ihProgramDeclared",
    "iaProgramDeclared",
    "paProgramDeclared",
    "hmProgramDeclared",
    "incidentBeginDate",
    "incidentEndDate",
    "disasterCloseoutDate",
    "tribalRequest",
    "fipsStateCode",
    "fipsCountyCode",
    "placeCode",
    "designatedArea",
    "declarationRequestNumber",
    "lastIAFilingDate",
    "incidentId",
    "region",
    "designatedIncidentTypes",
    "lastRefresh",
    "hash",
    "id",
]

DERIVED_FIELDS = [
    "declaration_date_iso",
    "incident_begin_date_iso",
    "incident_end_date_iso",
    "disaster_closeout_date_iso",
    "last_ia_filing_date_iso",
    "last_refresh_iso",
    "declaration_year",
    "declaration_month",
    "declaration_quarter",
    "incident_begin_year",
    "incident_duration_days",
    "days_incident_start_to_declaration",
    "days_declaration_to_closeout",
    "is_incident_open",
    "is_disaster_closed",
    "declaration_type_label",
    "state_name",
    "region_name",
    "region_hq_city",
    "region_states",
    "incident_type_group",
    "designated_incident_type_labels",
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
    "programs_declared_count",
    "has_individual_assistance",
    "has_public_assistance",
    "has_hazard_mitigation",
    "fips_geoid",
    "source_api_endpoint",
    "source_dataset_page",
    "fetched_at",
]

OUTPUT_FIELDS = RAW_FIELDS + DERIVED_FIELDS


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    return ctx


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
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
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
        # Last-ditch: date-only
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


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "t"}


def as_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def csv_bool(flag: bool) -> str:
    return "true" if flag else "false"


def days_between(a: datetime | None, b: datetime | None) -> str:
    if a is None or b is None:
        return ""
    return str((b.date() - a.date()).days)


def decode_designated_types(raw) -> str:
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    labels = []
    for code in parts:
        labels.append(DESIGNATED_TYPE_CODE.get(code, f"Unknown code {code}"))
    return "; ".join(labels)


def incident_group(incident_type: str) -> str:
    key = (incident_type or "").strip().lower()
    if not key:
        return ""
    return INCIDENT_TYPE_GROUP.get(key, "Other")


def keyword_blob(*parts: object) -> str:
    return " ".join("" if p is None else str(p) for p in parts).lower()


def contains_any(blob: str, needles: tuple[str, ...]) -> bool:
    return any(n in blob for n in needles)


def pad_fips(value, width: int) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.isdigit():
        return text.zfill(width)
    return text


def enrich(row: dict, fetched_at: str) -> dict:
    decl = parse_dt(row.get("declarationDate"))
    begin = parse_dt(row.get("incidentBeginDate"))
    end = parse_dt(row.get("incidentEndDate"))
    close = parse_dt(row.get("disasterCloseoutDate"))
    last_ia = parse_dt(row.get("lastIAFilingDate"))
    last_ref = parse_dt(row.get("lastRefresh"))

    incident_type = row.get("incidentType") or ""
    title = row.get("declarationTitle") or ""
    designated = row.get("designatedIncidentTypes") or ""
    designated_labels = decode_designated_types(designated)
    blob = keyword_blob(incident_type, title, designated_labels)

    ih = as_bool(row.get("ihProgramDeclared"))
    ia = as_bool(row.get("iaProgramDeclared"))
    pa = as_bool(row.get("paProgramDeclared"))
    hm = as_bool(row.get("hmProgramDeclared"))

    region_n = as_int(row.get("region"))
    region_info = FEMA_REGION.get(region_n, {})
    state = (row.get("state") or "").strip().upper()
    decl_type = (row.get("declarationType") or "").strip().upper()

    fips_state = pad_fips(row.get("fipsStateCode"), 2)
    fips_county = pad_fips(row.get("fipsCountyCode"), 3)
    geoid = f"{fips_state}{fips_county}" if fips_state and fips_county else ""

    out = {k: row.get(k, "") for k in RAW_FIELDS}
    # Normalize raw booleans / numbers for a clean CSV
    out["disasterNumber"] = row.get("disasterNumber", "")
    out["fyDeclared"] = row.get("fyDeclared", "")
    out["region"] = row.get("region", "")
    out["ihProgramDeclared"] = csv_bool(ih)
    out["iaProgramDeclared"] = csv_bool(ia)
    out["paProgramDeclared"] = csv_bool(pa)
    out["hmProgramDeclared"] = csv_bool(hm)
    out["tribalRequest"] = csv_bool(as_bool(row.get("tribalRequest")))
    out["fipsStateCode"] = fips_state
    out["fipsCountyCode"] = fips_county

    out["declaration_date_iso"] = iso_date(decl)
    out["incident_begin_date_iso"] = iso_date(begin)
    out["incident_end_date_iso"] = iso_date(end)
    out["disaster_closeout_date_iso"] = iso_date(close)
    out["last_ia_filing_date_iso"] = iso_date(last_ia)
    out["last_refresh_iso"] = iso_datetime(last_ref)
    out["declaration_year"] = str(decl.year) if decl else ""
    out["declaration_month"] = f"{decl.month:02d}" if decl else ""
    out["declaration_quarter"] = str((decl.month - 1) // 3 + 1) if decl else ""
    out["incident_begin_year"] = str(begin.year) if begin else ""
    out["incident_duration_days"] = days_between(begin, end)
    out["days_incident_start_to_declaration"] = days_between(begin, decl)
    out["days_declaration_to_closeout"] = days_between(decl, close)
    out["is_incident_open"] = csv_bool(begin is not None and end is None)
    out["is_disaster_closed"] = csv_bool(close is not None)
    out["declaration_type_label"] = DECLARATION_TYPE_LABEL.get(decl_type, "")
    out["state_name"] = STATE_NAME.get(state, "")
    out["region_name"] = region_info.get("name", "")
    out["region_hq_city"] = region_info.get("hq_city", "")
    out["region_states"] = region_info.get("states", "")
    out["incident_type_group"] = incident_group(incident_type)
    out["designated_incident_type_labels"] = designated_labels
    out["is_hurricane"] = csv_bool(
        contains_any(blob, ("hurricane", "typhoon"))
    )
    out["is_flood"] = csv_bool(contains_any(blob, ("flood",)))
    out["is_fire"] = csv_bool(contains_any(blob, ("fire",)))
    out["is_covid"] = csv_bool(
        contains_any(blob, ("covid", "coronavirus", "covid-19", "covid19"))
    )
    out["is_tornado"] = csv_bool(contains_any(blob, ("tornado",)))
    out["is_earthquake"] = csv_bool(contains_any(blob, ("earthquake",)))
    out["is_drought"] = csv_bool(contains_any(blob, ("drought",)))
    out["is_winter"] = csv_bool(
        contains_any(
            blob,
            ("snow", "ice storm", "freezing", "winter storm", "winter weather"),
        )
    )
    out["is_severe_storm"] = csv_bool(
        contains_any(blob, ("severe storm", "straight-line wind"))
    )
    out["is_biological"] = csv_bool(contains_any(blob, ("biological",)))
    out["is_tropical"] = csv_bool(
        contains_any(
            blob,
            (
                "hurricane",
                "typhoon",
                "tropical storm",
                "tropical depression",
            ),
        )
    )
    out["programs_declared_count"] = str(sum([ih, ia, pa, hm]))
    out["has_individual_assistance"] = csv_bool(ih or ia)
    out["has_public_assistance"] = csv_bool(pa)
    out["has_hazard_mitigation"] = csv_bool(hm)
    out["fips_geoid"] = geoid
    out["source_api_endpoint"] = API_ENDPOINT
    out["source_dataset_page"] = DATASET_PAGE
    out["fetched_at"] = fetched_at

    # Blank remaining Nones so csv.DictWriter is happy
    for key in OUTPUT_FIELDS:
        if out.get(key) is None:
            out[key] = ""
    return out


def fetch_all() -> tuple[list[dict], int]:
    """Page through the official API. Returns (records, reported_count)."""
    count_url = (
        f"{API_ENDPOINT}?$count=true&$top=1&$metadata=true"
        "&$select=id"
    )
    print(f"Counting records: {count_url}")
    meta = http_get_json(count_url)
    reported = int(meta.get("metadata", {}).get("count") or 0)
    print(f"OpenFEMA reported count: {reported}")

    records: list[dict] = []
    skip = 0
    while True:
        url = (
            f"{API_ENDPOINT}?$top={PAGE_SIZE}&$skip={skip}"
            "&$metadata=off"
            "&$orderby=disasterNumber,placeCode,id"
        )
        print(f"Fetching skip={skip} top={PAGE_SIZE}")
        payload = http_get_json(url)
        page = payload.get("DisasterDeclarationsSummaries")
        if page is None:
            # Some responses nest differently if metadata is off
            if isinstance(payload, list):
                page = payload
            else:
                page = payload.get("DisasterDeclarationsSummaries", [])
        if not page:
            break
        records.extend(page)
        print(f"  got {len(page)} (running total {len(records)})")
        if len(page) < PAGE_SIZE:
            break
        skip += PAGE_SIZE

    return records, reported


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"fetched_at={fetched_at}")
    print(f"User-Agent={USER_AGENT}")
    print(f"endpoint={API_ENDPOINT}")

    try:
        raw_rows, reported = fetch_all()
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        print(
            "Stopped. No output files written. Re-run when the API is reachable.",
            file=sys.stderr,
        )
        return 1

    if not raw_rows:
        print("FATAL: API returned 0 records. Stopping.", file=sys.stderr)
        return 1

    print(f"Enriching {len(raw_rows)} records …")
    enriched = [enrich(r, fetched_at) for r in raw_rows]

    # Stable, useful order: newest declaration first.
    def sort_key(r: dict):
        return (
            r.get("declaration_date_iso") or "",
            str(r.get("disasterNumber") or ""),
            r.get("placeCode") or "",
            r.get("id") or "",
        )

    enriched.sort(key=sort_key, reverse=True)

    write_csv(FULL_CSV, enriched)
    sample_n = min(1000, len(enriched))
    write_csv(SAMPLE_CSV, enriched[:sample_n])

    full_bytes = FULL_CSV.stat().st_size
    sample_bytes = SAMPLE_CSV.stat().st_size

    # Optional parquet if the CSV is large and pyarrow is present.
    parquet_path = DATA_DIR / "fema-disaster-declarations-enriched.parquet"
    parquet_written = False
    if full_bytes > 25 * 1024 * 1024:
        try:
            import pyarrow.csv as pacsv  # type: ignore
            import pyarrow.parquet as papq  # type: ignore

            table = pacsv.read_csv(str(FULL_CSV))
            papq.write_table(table, str(parquet_path))
            parquet_written = True
        except ImportError:
            print("CSV > 25MB and pyarrow not installed; CSV only.")

    unique_types = sorted(
        { (r.get("incidentType") or "") for r in raw_rows }
    )
    unique_groups = sorted(
        { r.get("incident_type_group") or "" for r in enriched }
    )

    meta = {
        "fetched_at_utc": fetched_at,
        "api_endpoint": API_ENDPOINT,
        "dataset_page": DATASET_PAGE,
        "terms_page": TERMS_PAGE,
        "reported_count": reported,
        "downloaded_count": len(raw_rows),
        "enriched_count": len(enriched),
        "sample_count": sample_n,
        "full_csv": str(FULL_CSV.name),
        "full_csv_bytes": full_bytes,
        "sample_csv_bytes": sample_bytes,
        "parquet_written": parquet_written,
        "unique_incident_types": unique_types,
        "unique_incident_type_groups": unique_groups,
        "user_agent": USER_AGENT,
        "ai_authorship": (
            "Built by Rogue, an AI agent. Not a human. "
            "Source data is U.S. government public information."
        ),
    }
    RUN_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print()
    print("=== done ===")
    print(f"rows downloaded : {len(raw_rows)}")
    print(f"rows reported   : {reported}")
    print(f"full csv        : {FULL_CSV} ({full_bytes} bytes)")
    print(f"sample csv      : {SAMPLE_CSV} ({sample_bytes} bytes, {sample_n} rows)")
    if parquet_written:
        print(f"parquet         : {parquet_path} ({parquet_path.stat().st_size} bytes)")
    print(f"incident types  : {unique_types}")
    print(f"groups          : {unique_groups}")
    if reported and len(raw_rows) != reported:
        print(
            f"WARNING: downloaded {len(raw_rows)} != reported {reported}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
