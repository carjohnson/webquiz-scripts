"""
Convert dicom_index.xlsx to studies_forImport.csv

Input columns:  FilePath, StudyInstanceUID, SeriesInstanceUID, PatientName, PatientID, SeriesDescription
Output columns: protocol, ptName, studyUID, seriesUIDsToBeAnnotated

- One row per unique StudyInstanceUID
- SeriesInstanceUIDs are deduplicated and written as a JSON array string
  (e.g. ["uid1","uid2"]) so Mongo imports the column as an array
- protocol column is left empty
"""

import pandas as pd
import json
import csv
import sys

INPUT_FILE = "dicom_index.xlsx"
OUTPUT_FILE = "studies_forImportToMongoDB.csv"

if len(sys.argv) == 3:
    INPUT_FILE = sys.argv[1]
    OUTPUT_FILE = sys.argv[2]

df = pd.read_excel(INPUT_FILE)

grouped = (
    df.groupby("StudyInstanceUID", sort=False)
    .agg(
        ptName=("PatientName", "first"),
        seriesUIDsToBeAnnotated=("SeriesInstanceUID", lambda x: list(x.unique())),
    )
    .reset_index()
    .rename(columns={"StudyInstanceUID": "studyUID"})
)

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["protocol", "studyUID", "seriesUIDsToBeAnnotated"])

    for _, row in grouped.iterrows():
        protocol = ""
        study_uid = row["studyUID"]
        series_json = json.dumps(row["seriesUIDsToBeAnnotated"])
        writer.writerow([protocol, study_uid, series_json])

print(f"Done: {len(grouped)} studies written to {OUTPUT_FILE}")