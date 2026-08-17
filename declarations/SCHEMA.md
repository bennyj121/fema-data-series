# Disaster Declarations schema

One row is one declaration × designated area (usually a county or parish). A disaster number can appear in many rows.

## Column dictionary

### Raw (passed through from OpenFEMA)

Meanings follow the [official v2 data dictionary](https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2).

| Name | Type | Meaning | Origin |
|---|---|---|---|
| femaDeclarationString | text | Agency id: type + number + state. Example: `DR-4393-NC`. | raw |
| disasterNumber | integer | Sequential event number. | raw |
| state | text | Two-letter jurisdiction code (state, DC, or territory). | raw |
| declarationType | text | `DR` major disaster, `EM` emergency, `FM` fire management. | raw |
| declarationDate | datetime | Date the disaster was declared (API timestamp). | raw |
| fyDeclared | integer | Federal fiscal year of the declaration. | raw |
| incidentType | text | Primary official incident type (Fire, Flood, Hurricane, …). | raw |
| declarationTitle | text | Title of the declaration. | raw |
| ihProgramDeclared | boolean | Individuals and Households program declared. | raw |
| iaProgramDeclared | boolean | Individual Assistance program declared. | raw |
| paProgramDeclared | boolean | Public Assistance program declared. | raw |
| hmProgramDeclared | boolean | Hazard Mitigation program declared. | raw |
| incidentBeginDate | datetime | Date the incident itself began. | raw |
| incidentEndDate | datetime | Date the incident itself ended (blank if still open). | raw |
| disasterCloseoutDate | datetime | Date all financial transactions closed. | raw |
| tribalRequest | boolean | Request submitted by a Tribal Nation, independent of a state. | raw |
| fipsStateCode | text | Two-digit FIPS state code, zero-padded. | raw |
| fipsCountyCode | text | Three-digit FIPS county code, zero-padded. `000` = statewide. | raw |
| placeCode | text | FEMA place id (`99` + county FIPS, or a FEMA-assigned id). | raw |
| designatedArea | text | Named geographic area in the declaration. | raw |
| declarationRequestNumber | text | Number assigned to the request. | raw |
| lastIAFilingDate | datetime | Last date IA requests can be filed (after 1998; IA only). | raw |
| incidentId | text | Identifier for the underlying incident. | raw |
| region | integer | FEMA region number 1–10. | raw |
| designatedIncidentTypes | text | Comma-separated incident-type codes (see codebook below). | raw |
| lastRefresh | datetime | When OpenFEMA last updated this record. | raw |
| hash | text | OpenFEMA record hash (changes if any field changes). | raw |
| id | uuid | OpenFEMA row id. **Does not persist across API refreshes.** | raw |

### Derived (deterministic from raw fields)

No facts invented. Empty when the source field is missing.

| Name | Type | Meaning | Origin |
|---|---|---|---|
| declaration_date_iso | date | `declarationDate` as `YYYY-MM-DD`. | derived |
| incident_begin_date_iso | date | `incidentBeginDate` as `YYYY-MM-DD`. | derived |
| incident_end_date_iso | date | `incidentEndDate` as `YYYY-MM-DD`. | derived |
| disaster_closeout_date_iso | date | `disasterCloseoutDate` as `YYYY-MM-DD`. | derived |
| last_ia_filing_date_iso | date | `lastIAFilingDate` as `YYYY-MM-DD`. | derived |
| last_refresh_iso | datetime | `lastRefresh` as UTC `YYYY-MM-DDTHH:MM:SSZ`. | derived |
| declaration_year | integer | Calendar year of `declarationDate`. | derived |
| declaration_month | text | Month of `declarationDate`, `01`–`12`. | derived |
| declaration_quarter | integer | Quarter of `declarationDate`, 1–4. | derived |
| incident_begin_year | integer | Calendar year of `incidentBeginDate`. | derived |
| incident_duration_days | integer | `incidentEndDate − incidentBeginDate` in calendar days. Blank if either date is missing. | derived |
| days_incident_start_to_declaration | integer | `declarationDate − incidentBeginDate` in calendar days. | derived |
| days_declaration_to_closeout | integer | `disasterCloseoutDate − declarationDate` in calendar days. | derived |
| is_incident_open | boolean | Begin date present and end date missing. | derived |
| is_disaster_closed | boolean | Closeout date present. | derived |
| declaration_type_label | text | `Major Disaster` / `Emergency` / `Fire Management Assistance`. | derived |
| state_name | text | Full jurisdiction name from the USPS code. | derived |
| region_name | text | Official FEMA region label, e.g. `Region 5 — Chicago`. | derived |
| region_hq_city | text | FEMA region headquarters city. | derived |
| region_states | text | Member jurisdictions of that FEMA region. | derived |
| incident_type_group | text | Taxonomy over `incidentType` (Tropical cyclone, Flood, Fire, …). | derived |
| designated_incident_type_labels | text | Codebook decode of `designatedIncidentTypes`. | derived |
| is_hurricane | boolean | “hurricane” or “typhoon” in type, title, or designated labels. | derived |
| is_flood | boolean | “flood” in type, title, or designated labels. | derived |
| is_fire | boolean | “fire” in type, title, or designated labels. | derived |
| is_covid | boolean | “covid” / “coronavirus” in type, title, or designated labels. | derived |
| is_tornado | boolean | “tornado” in type, title, or designated labels. | derived |
| is_earthquake | boolean | “earthquake” in type, title, or designated labels. | derived |
| is_drought | boolean | “drought” in type, title, or designated labels. | derived |
| is_winter | boolean | Snow / ice / freezing / winter-storm language. | derived |
| is_severe_storm | boolean | “severe storm” or “straight-line wind” language. | derived |
| is_biological | boolean | “biological” in type, title, or designated labels. | derived |
| is_tropical | boolean | Hurricane, typhoon, tropical storm, or tropical depression language. | derived |
| programs_declared_count | integer | Count of IH, IA, PA, HM flags that are true (0–4). | derived |
| has_individual_assistance | boolean | `ihProgramDeclared` or `iaProgramDeclared`. | derived |
| has_public_assistance | boolean | `paProgramDeclared`. | derived |
| has_hazard_mitigation | boolean | `hmProgramDeclared`. | derived |
| fips_geoid | text | Five-digit `state + county` FIPS. | derived |
| source_api_endpoint | text | API URL used for this fetch. | derived |
| source_dataset_page | text | Official dataset page URL. | derived |
| fetched_at | datetime | UTC timestamp of this download. | derived |

Keyword flags search `incidentType`, `declarationTitle`, and the decoded designated-type labels. A row can have more than one flag true (a “severe storms and flooding” title is both `is_severe_storm` and `is_flood`). That is matching, not a new fact.

### designatedIncidentTypes codebook (official)

`0` Not applicable · `1` Explosion · `2` Straight-Line Winds · `3` Tidal Wave · `4` Tropical Storm · `5` Winter Storm · `8` Tropical Depression · `A` Tsunami · `B` Biological · `C` Coastal Storm · `D` Drought · `E` Earthquake · `F` Flood · `G` Freezing · `H` Hurricane · `I` Terrorist · `J` Typhoon · `K` Dam/Levee Break · `L` Chemical · `M` Mud/Landslide · `N` Nuclear · `O` Severe Ice Storm · `P` Fishing Losses · `Q` Crop Losses · `R` Fire · `S` Snowstorm · `T` Tornado · `U` Civil Unrest · `V` Volcanic Eruption · `W` Severe Storm · `X` Toxic Substances · `Y` Human Cause · `Z` Other

