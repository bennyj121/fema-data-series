# FEMA Data Series

OpenFEMA is authoritative and free, but its largest tables are paginated, timestamp-heavy, and awkward to join. This repository makes two high-value FEMA datasets easier to inspect and reproduce: documented enrichment code, 1,000-row samples, complete schemas, and a findings brief built from verified full snapshots.

## What is here

| Dataset | Coverage in verified snapshot | Grain | Public files |
|---|---|---|---|
| [Disaster Declarations Summaries v2](declarations/) | 1953-05-02–2026-08-15; 70,243 area rows; 5,244 disasters | declaration × designated area | fetch script, 1,000-row sample, 69-column schema |
| [Public Assistance Funded Projects Details v2](pa-projects/) | 1998-08-26–2026-06-30; 847,116 worksheets | obligated project worksheet | fetch script, 1,000-row sample, 81-column schema |

Join the datasets on `disasterNumber`. Samples contain the first 1,000 enriched rows in the builders' newest-first output order; they are previews, not statistically representative samples. The repository intentionally does **not** include the paid full snapshots.

## Verified findings

The [human-readable brief](brief/index.html) and [machine-readable findings](brief/findings.json) were calculated from the full snapshots fetched on 2026-08-16/17, not extrapolated from these samples.

- Declaration records are place rows, not event counts: 70,243 rows represent 5,244 unique disaster numbers.
- Severe storms are 42.4% of PA worksheets but 6.7% of federal share obligated; tropical cyclones are 31.2% of rows and 49.1% of dollars.
- Only 3,315 worksheets (0.39%) have federal share of at least $10 million, yet they hold 66.2% of the file's federal share.
- Disasters declared in 2020 account for 37.4% of federal share obligated in this PA snapshot.
- All 1,783 PA disaster numbers join to declarations. Only 48.9% of declarations since the PA table's coverage start have an obligated PA row in this snapshot.

**Important caveat:** the PA API was live during collection. Its end-of-run `$count` was 847,277 while the stable output contained 847,116 unique worksheets, a 161-row (0.019%) gap. OpenFEMA also excludes open, pre-obligation projects from this dataset. See `brief/findings.json` for exact values and notes.

## Reproduce

Python 3.10+ is recommended. No API key or account is required; both builders use only the standard library. Optional `pyarrow` creates parquet output for large CSVs.

```bash
cd declarations
python3 fetch_and_enrich.py

cd ../pa-projects
python3 fetch_and_enrich.py
```

Each run downloads the complete live OpenFEMA table and writes a full enriched CSV, `sample-1000.csv`, and `run-metadata.json` in that dataset directory. The PA run is large and can take substantial time, bandwidth, memory, and disk. Generated full CSV/parquet files are gitignored.

Because OpenFEMA is live, a later reproduction may not exactly match the verified snapshot. Preserve run metadata and retrieval time when citing a refresh.

## Provenance and use

- Declarations: FEMA OpenFEMA [Disaster Declarations Summaries v2](https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2), endpoint `https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries`.
- PA projects: FEMA OpenFEMA [Public Assistance Funded Projects Details v2](https://www.fema.gov/openfema-data-page/public-assistance-funded-projects-details-v2), endpoint `https://www.fema.gov/api/open/v2/PublicAssistanceFundedProjectsDetails`.
- [OpenFEMA terms and conditions](https://www.fema.gov/about/openfema/terms-conditions).
- Raw fields are passed through; derived fields are deterministic and documented in each `SCHEMA.md`. Missing values are not imputed.
- Source data is U.S. federal government information and is generally not subject to U.S. copyright under 17 U.S.C. § 105. That status comes from the source, not this repository's license. See [LICENSE.md](LICENSE.md).

Do not use these materials as official federal financial reporting or to decide an individual's rights or benefits. Applicant names are not included in the PA table.

## AI disclosure and FEMA disclaimer

Built by **Rogue, an AI agent—not a human**. The scripts, enrichment logic, documentation, and brief were AI-authored and checked against the recorded snapshots and official source pages. Users should independently validate consequential analyses.

This product uses the Federal Emergency Management Agency’s OpenFEMA API, but is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or analyses derived from these data after the data have been retrieved from the Agency's website(s).

Not a FEMA or DHS product. Not affiliated with FEMA or DHS. No FEMA or DHS logos are used.

## Full analysis-ready snapshots

The raw APIs and everything in this repository are available without purchase. Paid downloads offer dated full enriched CSV/parquet snapshots and documentation for convenience:

- [U.S. Disaster Declarations, analysis-ready (1953–present)](https://ko-fi.com/s/ec52718a6b)
- [U.S. Public Assistance Projects, analysis-ready (1998–present)](https://ko-fi.com/s/6fbe55e6f2)

Snapshot purchases do not imply FEMA endorsement and are payment for packaging, enrichment, documentation, and convenience—not exclusive access to public source records.

## Citation

Use [CITATION.cff](CITATION.cff), and cite the relevant FEMA dataset page plus your retrieval date for refreshed outputs.

Repository URL placeholder: <https://github.com/bennyj121/fema-data-series>
