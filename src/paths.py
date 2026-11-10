"""Repository paths shared by every script.

All paths are resolved relative to the repository root, so the scripts run
unchanged on Windows, macOS and Linux from any working directory.
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_SRC = os.path.join(REPO, "data", "source")      # public input data
DATA_DER = os.path.join(REPO, "data", "derived")     # analysis tables built by the scripts
TAB = os.path.join(REPO, "results", "tables")        # manuscript tables (CSV)
FIG = os.path.join(REPO, "results", "figures")       # manuscript figures (PNG 300 dpi + vector PDF)
LOG = os.path.join(REPO, "results", "logs")          # run logs

# Unpublished originals (authors only). Override with the DS12B_PRIVATE_DIR and
# DS12B_REPORTS_DIR environment variables if the folders live elsewhere.
PRIVATE = os.environ.get(
    "DS12B_PRIVATE_DIR",
    os.path.join(REPO, "..", "..", "03_Source_Data_PRIVATE"))
REPORTS = os.environ.get(
    "DS12B_REPORTS_DIR",
    os.path.join(REPO, "..", "..", "04_Project_Documents", "Soil_Investigation_Reports"))

for _d in (DATA_SRC, DATA_DER, TAB, FIG, LOG):
    os.makedirs(_d, exist_ok=True)
