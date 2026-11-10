# What daily progress reports can and cannot measure — data and code

Data and analysis code for the paper

> Mondol, P. and Mondol, M. (2026). *What daily progress reports can and cannot measure: auditing productivity metrics from 186 bored piles.* Manuscript under review.

The study audits the productivity metrics that can be derived from the complete as-recorded daily log of a large-diameter bored-piling package (186 piles of 1.20 m diameter, 7,710.4 m, 138 working days) on contract DS-12B of the SASEC Dhaka–Sylhet Corridor Road Investment Project, Bangladesh. This repository contains the anonymised records, the extracted borehole SPT profiles, and the Python code that reproduces every table and figure in the paper.

## Quick start

Python 3.10 or later.

```bash
pip install -r requirements.txt
python run_all.py
```

`run_all.py` runs the analysis steps in order, writes the tables to `results/tables/` and the figures to `results/figures/`, saves each step's console output to `results/logs/`, and finally compares the tables with the reference checksums in `results/SHA256SUMS_tables.txt`. A full run takes one to two minutes. With the library versions in `requirements.txt` every table reproduces byte-for-byte.

## Repository layout

```
data/
  source/                     public input data (start here)
    foundation_input_records.csv      site log of the foundation package, 417 rows (anonymised)
    client_dpr_daily_pile_length.csv  daily pile length in the formal daily progress report
    borehole_spt_profiles.csv         620 SPT intervals from 14 boreholes
    borehole_locations.csv            borehole-to-structure map with coordinates
    foundation_summary_check.json     cumulative pile length on the workbook summary tab
    SHA256SUMS_original_workbooks.txt checksums of the unpublished original workbooks
  derived/                    analysis tables built by the code
    pile_analysis_table.csv           186 piles, the analysis table (step 01)
    pile_analysis_table_with_soil.csv the same with soil covariates (step 07; supplementary S1)
  README.md                   data dictionary
src/                          analysis steps (run in numerical order by run_all.py)
results/
  tables/                     every manuscript table as CSV
  figures/                    every manuscript figure, PNG (300 dpi) and vector PDF
  logs/                       console output of the last run
run_all.py                    one-command reproduction
```

## Analysis steps and where their results appear in the paper

| Step | Script | Audit check | Paper | Outputs |
|---|---|---|---|---|
| 00 | `00_make_public_extracts.py` | — | Section 3.4 | `data/source/*` (authors only, see below) |
| 01 | `01_extract_validate.py` | A1 identity validation | Sections 4.3, 5.1 | Table 3, analysis table |
| 02 | `02_baselines_figures.py` | A3 rate decomposition | Sections 3.2, 5.2, 5.3, 5.4 | Tables 1, 4, 5; Figures 1, 2, 3 |
| 03 | `03_continuity_learning.py` | A4 continuity, A5 learning-curve companion test | Sections 5.4, 5.5 | Tables 6, 7, 8; Figures 4, 5, 6 |
| 04 | `04_overbreak.py` | — | Section 5.6 | Table 10; Figure 7 |
| 05 | `05_reconciliation_sensitivity_M1.py` | A2 corroboration, A7 reconciliation, A8 missingness | Sections 5.1, 5.3, 5.5, 5.8 | Table 9 |
| 06 | `06_soil_extraction.py` | — | Section 3.3 | `data/source/borehole_spt_profiles.csv` (authors only) |
| 07 | `07_soil_covariates_models.py` | A6 linked-covariate design check | Sections 3.3, 5.6, 5.7 | Tables A1, A2; Figure 8; models M2/M3 |

Table 2 of the paper (the audit procedure) is a text table and is not computed.

| Paper | File |
|---|---|
| Table 1 | `results/tables/Table_01_dataset_description.csv` |
| Table 3 | `results/tables/Table_03_identity_validation.csv` |
| Table 4 | `results/tables/Table_04_baseline_rates.csv` |
| Table 5 | `results/tables/Table_05_single_vs_two_rig_days.csv` |
| Table 6 | `results/tables/Table_06_pier_cycles.csv` |
| Table 7 | `results/tables/Table_07_learning_models.csv` |
| Table 8 | `results/tables/Table_08_unit_level_trend.csv` |
| Table 9 | `results/tables/Table_09_M1_logistic.csv` |
| Table 10 | `results/tables/Table_10_overbreak_by_pier.csv` |
| Tables A1, A2 | `results/tables/Table_A1_borehole_locations.csv`, `Table_A2_borehole_profiles.csv` |
| Models M2, M3 (section 5.7) | `results/tables/Supplementary_soil_models.csv` |
| Figures 1–8 | `results/figures/Figure_<n>_*.png` and `.pdf` |

Numbers quoted in the text but not tabulated (for example the stoppage windows, the working-calendar ratios, the reinforcement intensity and the cross-file reconciliation) are printed in the step logs in `results/logs/`.

## Data provenance and anonymisation

The records are the contractor's site log of the foundation package — the spreadsheet kept as the backup to the formal daily progress report — and the formal daily progress report issued to the client. They are published with permission.

The original workbooks are not published because they contain the names of site personnel and commercial information unrelated to this study. Step 00 produced the public extracts from them and applied the anonymisation before any analysis:

- the *Responsible person* column (names of site staff) is removed;
- rigs are coded RIG-A, RIG-B and RIG-C in order of first appearance on pile rows;
- subcontractors are coded SC-1 to SC-5 in order of first appearance;
- the formal daily progress report contributes only its daily pile-length row.

The coding key is held by the authors and is not published. `data/source/SHA256SUMS_original_workbooks.txt` records the checksums of the two originals, so that the extracts can be verified against them on request. The analysis table built from the public extract is byte-identical to the one built from the original workbook.

Step 06 extracted the SPT profiles from the text layer of three site-investigation reports (submissions 048, 054 and 265), which are unpublished submissions to the client; its output is `data/source/borehole_spt_profiles.csv`. Steps 00 and 06 are included so that the extraction is documented, and `python run_all.py --originals` reruns them where the originals are available (set `DS12B_PRIVATE_DIR` and `DS12B_REPORTS_DIR` if they are not in the default locations given in `src/paths.py`).

A few descriptive statements in the paper about the original workbooks as a whole (their sheet structure, and the count of weather remarks across all activities) refer to material that is not published and are therefore not reproduced here.

## Statistical conventions

Seed 20260909 throughout. Intervals for means are bias-corrected and accelerated (BCa) bootstrap intervals with 10,000 resamples; intervals for correlations, regression slopes and learning-curve parameters are percentile bootstrap intervals with 4,000 resamples; model coefficients use a cluster bootstrap over piers with 2,000 resamples. The code uses only numpy, pandas and the Python standard library for statistics (no scipy), so that every procedure is visible in the source.

## Licence

Code: MIT licence (`LICENSE`). Data, tables and figures: Creative Commons Attribution 4.0 International (`LICENSE-DATA.md`). Please cite the paper and this repository (`CITATION.cff`) when using them.

## Contact

Mithun Mondol (corresponding author) — mithun.mondol@gmail.com  
Pollab Mondol — pollab.080102@gmail.com
