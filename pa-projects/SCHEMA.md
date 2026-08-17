# Public Assistance Funded Projects schema

One row is one obligated Public Assistance project worksheet. `gmProjectId` is the business key; join declarations on `disasterNumber`.

## Column dictionary

### Raw (passed through from OpenFEMA)

Meanings follow the [official v2 data dictionary](https://www.fema.gov/openfema-data-page/public-assistance-funded-projects-details-v2). Business key: `gmProjectId` (OpenFEMA `primaryKey`).

| Name | Type | Meaning | Origin |
|---|---|---|---|
| disasterNumber | integer | Sequential event number. Join key to the declarations dataset. | raw |
| declarationDate | datetime | Date the disaster was declared. | raw |
| incidentType | text | Official incident type (Hurricane, Flood, Severe Storm(s), …). | raw |
| pwNumber | integer | Project worksheet number within the applicant/disaster. | raw |
| applicationTitle | text | Free-form project / facility title. Not a person name. | raw |
| applicantId | text | Public Assistance applicant id (not a name). | raw |
| damageCategoryCode | text | PA work category letter: A–G, Z, I. | raw |
| damageCategoryDescrip | text | Official category label (Debris Removal, Utilities, …). | raw |
| projectStatus | text | Eligibility status (Eligible, Ineligible, Withdrawn, …). | raw |
| projectProcessStep | text | Process location from formulation through closeout. | raw |
| projectSize | text | `Small` or `Large`, from the eligible amount in the damage survey. | raw |
| county | text | County / parish / borough of the applicant location. | raw |
| countyCode | text | Three-digit county FIPS, zero-padded in this file. | raw |
| stateAbbreviation | text | Two-letter jurisdiction code. | raw |
| stateNumberCode | text | Two-digit state FIPS, zero-padded in this file. | raw |
| projectAmount | decimal | Estimated project cost in dollars, without administrative costs. | raw |
| federalShareObligated | decimal | Federal PA dollars obligated to the grantee for this worksheet. | raw |
| totalObligated | decimal | Federal share plus grantee/subgrantee administrative costs. | raw |
| lastObligationDate | datetime | Date the grant was last obligated. | raw |
| firstObligationDate | datetime | Date the grant was first obligated. | raw |
| mitigationAmount | decimal | Proposed PA 406 mitigation dollars. Can be negative (adjustments). | raw |
| gmProjectId | integer | Grants Manager project id. **Primary key.** | raw |
| gmApplicantId | integer | Grants Manager applicant id for this declaration. | raw |
| lastRefresh | datetime | When OpenFEMA last updated this record. | raw |
| hash | text | OpenFEMA record hash (changes if any field changes). | raw |

### Derived (deterministic from raw fields)

No facts invented. Empty when the source field is missing or a ratio’s denominator is zero.

| Name | Type | Meaning | Origin |
|---|---|---|---|
| declaration_date_iso | date | `declarationDate` as `YYYY-MM-DD`. | derived |
| first_obligation_date_iso | date | `firstObligationDate` as `YYYY-MM-DD`. | derived |
| last_obligation_date_iso | date | `lastObligationDate` as `YYYY-MM-DD`. | derived |
| last_refresh_iso | datetime | `lastRefresh` as UTC `YYYY-MM-DDTHH:MM:SSZ`. | derived |
| declaration_year | integer | Calendar year of `declarationDate`. | derived |
| declaration_month | text | Month of `declarationDate`, `01`–`12`. | derived |
| declaration_quarter | integer | Quarter of `declarationDate`, 1–4. | derived |
| first_obligation_year | integer | Calendar year of first obligation. | derived |
| last_obligation_year | integer | Calendar year of last obligation. | derived |
| days_declaration_to_first_obligation | integer | `firstObligationDate − declarationDate` in calendar days. | derived |
| days_first_to_last_obligation | integer | `lastObligationDate − firstObligationDate` in calendar days. | derived |
| is_single_obligation | boolean | First and last obligation dates are the same calendar day. | derived |
| state_name | text | Full jurisdiction name from the USPS code. | derived |
| region | integer | FEMA region number 1–10, from the state. | derived |
| region_name | text | Official FEMA region label, e.g. `Region 5 — Chicago`. | derived |
| region_hq_city | text | FEMA region headquarters city. | derived |
| region_states | text | Member jurisdictions of that FEMA region. | derived |
| fips_state_code | text | Two-digit state FIPS. | derived |
| fips_county_code | text | Three-digit county FIPS. | derived |
| fips_geoid | text | Five-digit `state + county` FIPS. | derived |
| work_class | text | `Emergency Work` / `Permanent Work` / `Management Costs` / `Building Code / Administration`. | derived |
| is_emergency_work | boolean | Category A or B. | derived |
| is_permanent_work | boolean | Category C, D, E, F, or G. | derived |
| is_management_costs | boolean | Category Z. | derived |
| is_debris | boolean | Category A. | derived |
| is_protective_measures | boolean | Category B. | derived |
| is_roads_bridges | boolean | Category C. | derived |
| is_water_control | boolean | Category D. | derived |
| is_buildings | boolean | Category E. | derived |
| is_utilities | boolean | Category F. | derived |
| is_parks_rec | boolean | Category G. | derived |
| incident_type_group | text | Taxonomy over `incidentType` (same groups as 005). | derived |
| is_hurricane | boolean | “hurricane” or “typhoon” in official `incidentType`. | derived |
| is_flood | boolean | “flood” in official `incidentType`. | derived |
| is_fire | boolean | “fire” in official `incidentType` (includes Wildfire). | derived |
| is_covid | boolean | “covid” / “coronavirus” in `incidentType` or `applicationTitle`. | derived |
| is_tornado | boolean | “tornado” in official `incidentType`. | derived |
| is_earthquake | boolean | “earthquake” in official `incidentType`. | derived |
| is_drought | boolean | “drought” in official `incidentType`. | derived |
| is_winter | boolean | Snow / ice / freezing / winter-storm language in `incidentType`. | derived |
| is_severe_storm | boolean | “severe storm” or “straight-line wind” in `incidentType`. | derived |
| is_biological | boolean | “biological” in official `incidentType`. | derived |
| is_tropical | boolean | Hurricane, typhoon, tropical storm, or tropical depression in `incidentType`. | derived |
| federal_share_pct | decimal | `federalShareObligated / projectAmount × 100`. Blank if amount is 0 or missing. | derived |
| mitigation_share_pct | decimal | `mitigationAmount / projectAmount × 100`. Blank if amount is 0 or missing. | derived |
| has_mitigation | boolean | `mitigationAmount` present and not zero. | derived |
| is_deobligation | boolean | Project, federal, or total amount is negative. | derived |
| is_zero_federal_share | boolean | `federalShareObligated` is exactly 0. | derived |
| is_large_project | boolean | `projectSize` is Large. | derived |
| is_small_project | boolean | `projectSize` is Small. | derived |
| is_closed | boolean | `projectProcessStep` is `Project Closed Out`. | derived |
| is_eligible | boolean | `projectStatus` is Eligible. | derived |
| federal_obligation_bucket | text | `negative` / `zero` / `under_10k` / `10k_to_100k` / `100k_to_1m` / `1m_to_10m` / `10m_plus`. | derived |
| source_api_endpoint | text | API URL used for this fetch. | derived |
| source_dataset_page | text | Official dataset page URL. | derived |
| fetched_at | datetime | UTC timestamp of this download. | derived |

Hazard flags (`is_hurricane`, `is_fire`, …) search official `incidentType` only. Project titles name facilities (“Evart Fire Dept”) and are not used, except `is_covid`, which also searches `applicationTitle` because the official type for those events is `Biological`. A row can have more than one flag true. That is matching, not a new fact.

### Public Assistance category codebook (official)

From the [PA program overview](https://www.fema.gov/assistance/public/program-overview):

**Emergency work:** `A` Debris Removal · `B` Emergency Protective Measures (includes Emergency Work Donated Resources)

**Permanent work:** `C` Roads and Bridges · `D` Water Control Facilities · `E` Buildings and Equipment · `F` Utilities · `G` Parks, Recreational Facilities, and Other Items

**Other:** `Z` Management Costs / Direct Administrative Costs / Section 324 Management Costs · `I` Building Code Management and Enforcement

