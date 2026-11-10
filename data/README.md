# Data dictionary

All files are UTF-8 CSV with a header row. Levels are in metres on the project datum; depths are in metres below existing ground level. Blank cells are missing values.

## source/foundation_input_records.csv — site log of the foundation package (417 rows)

One row per recorded activity, in the order of the original sheet (*DPR Backup sheet.xlsx*, sheet *Foundation Input*). Column names are those of the original sheet, except the anonymised columns.

| Column | Meaning |
|---|---|
| source_row | Row number in the original sheet |
| Date | Date the work was recorded |
| Ch. From, Ch. To, Side | Chainage and side, where recorded |
| BOQ items | Bill-of-quantities pay item |
| Structure ID | Pier or abutment (structural reference, e.g. P-21, A2) |
| Activity | Free-text activity description |
| Code | Activity code: Pile (186 rows), Rebar (186), Pile Breaking, PIT, C-35, HSDT, SLT, LLT |
| Unit | Unit of *Quantity Reported* (m for piles, Ton for reinforcement) |
| Steel caging top, EGL, Casting level, Cut off level, Toe level | Surveyed levels, m (EGL = existing ground level) |
| Dia | Nominal shaft diameter, m |
| D | Empty in the source |
| Quantity Reported | Reported quantity (cast pile length in m on Pile rows; reinforcement in t on Rebar rows) |
| Theoritical Volume (Cum) | Recorded theoretical concrete volume, m³ (spelling as in the source) |
| Actual Volume Qty. | Recorded placed concrete volume, m³ |
| Difference | Spreadsheet column found to be internally inconsistent; not used (paper, section 4.4) |
| rig_code | Piling rig, coded RIG-A/B/C in order of first appearance on pile rows |
| contractor_code | Subcontractor, coded SC-1 to SC-5 in order of first appearance (all pile rows are SC-1) |
| Mason, Labour | Crew counts, where recorded |
| Remarks | Free-text remarks, where recorded |

## source/client_dpr_daily_pile_length.csv — formal daily progress report (138 rows)

| Column | Meaning |
|---|---|
| date | Calendar day |
| pile_length_m | Pile length reported for that day in the formal daily progress report (pay-item grid, row *Pile / Actual*); days with zero are omitted |

## source/borehole_spt_profiles.csv — SPT profiles (620 rows)

| Column | Meaning |
|---|---|
| pier | Pier whose borehole the interval belongs to |
| src | Submission number of the site-investigation report the profile was extracted from (048, 054, 265) |
| d_from, d_to | Interval depth, m below existing ground level |
| N | SPT blow count (50 is the refusal value recorded in the logs) |
| strata | Stratum as logged |
| cohesionless | True for Sand, Silt, Silt/Sand, Silty Sand, Sandy Silt |

## source/borehole_locations.csv — borehole-to-structure map (26 rows)

| Column | Meaning |
|---|---|
| borehole | Borehole number (BH-01 to BH-26) |
| structure | Abutment or pier served (BH-01 = A-1, BH-(k+1) = P-k, BH-26 = A-2) |
| E, N | Easting and northing, m, from the borehole location drawings |
| has_SPT_profile | True where an SPT profile was available for this study |

## source/foundation_summary_check.json

Cumulative pile length on the summary tab of the original workbook, used by step 01 as a cross-sheet check.

## source/SHA256SUMS_original_workbooks.txt

SHA-256 checksums of the two unpublished original workbooks.

## derived/pile_analysis_table.csv — analysis table (186 rows, one per pile)

| Column | Meaning |
|---|---|
| pile_id | Sequential identifier, PL-001 to PL-186, ordered by date, pier and rig |
| date | Date the pile was recorded as completed |
| pier | Pier or abutment |
| rig_code | Rig, RIG-A/B/C |
| contractor_code | Piling subcontractor (SC-1) |
| is_test_pile | True for the contractual test pile (2025-03-20) |
| seq_index | Production sequence number (test pile excluded) |
| length_reported_m | Reported cast pile length, m |
| length_calc_m | Cut-off level minus toe level, m (equation 1) |
| resid_F1_m | length_reported_m − length_calc_m |
| cut_off_level_m, toe_level_m, casting_level_m | Surveyed levels, m |
| egl_m | Existing ground level as recorded, m |
| steel_caging_top_m | Recorded top of the reinforcement cage, m |
| dia_m | Nominal shaft diameter, m |
| V_th_reported_m3 | Recorded theoretical concrete volume, m³ |
| V_th_calc_m3 | (π/4)D²(L + c), m³ (equation 2) |
| resid_F2_m3 | V_th_reported_m3 − V_th_calc_m3 |
| V_act_m3 | Recorded placed concrete volume, m³ (106 of 186 recorded) |
| eta_overbreak | V_act / V_th (equation 6) |
| crew_recorded | Crew count where recorded |

## derived/pile_analysis_table_with_soil.csv — analysis table with soil covariates (supplementary S1)

All columns of the analysis table, plus:

| Column | Meaning |
|---|---|
| egl_used_m | Existing ground level used for depth conversion, m |
| egl_imputed | True where existing ground level was imputed (P-10, P-19; median cut-off-to-ground offset 2.31 m) |
| depth_top_m, depth_toe_m | Shaft top and toe, m below existing ground level |
| N_shaft_wavg | Length-weighted mean SPT N over the shaft |
| frac_cohesionless | Fraction of shaft length in cohesionless strata |
| N_at_toe, strata_at_toe | SPT N and stratum at the pile toe (blank where the toe falls in a gap in the log) |
| profile_depth_m | Explored depth of the pier's borehole, m |
| shaft_covered_frac | Fraction of the shaft lying within the explored depth |

Soil columns are blank for piers without a borehole profile.
