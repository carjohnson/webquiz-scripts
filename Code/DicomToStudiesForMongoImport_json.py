"""
Convert dicom_index.xlsx to studies_forImport.jsonl

Input columns:  FilePath, StudyInstanceUID, SeriesInstanceUID, PatientName, PatientID, SeriesDescription
Output fields:  protocol, ptName, studyUID, seriesUIDsToBeAnnotated

- One JSON document per line (JSON Lines / .jsonl), ready for:
    mongoimport --db <db> --collection <coll> --type json --file studies_forImport.jsonl
- One document per unique StudyInstanceUID
- SeriesInstanceUIDs are deduplicated into a true JSON array
- studyUID is always written as a JSON string (quoted), so Mongo imports it
  as a string even when it looks numeric (e.g. "123.456") - no extra
  --columnsHaveTypes flag needed
- protocol field is included as an empty string
"""

import pandas as pd
import json
import sys

INPUT_FILE = "dicom_index.xlsx"
OUTPUT_FILE = "studies_forImportToMongoDB.jsonl"

if len(sys.argv) == 3:
    INPUT_FILE = sys.argv[1]
    OUTPUT_FILE = sys.argv[2]

df = pd.read_excel(INPUT_FILE, dtype={"StudyInstanceUID": str, "SeriesInstanceUID": str})

grouped = (
    df.groupby("StudyInstanceUID", sort=False)
    .agg(
		ptName=("PatientName", "first"),
        seriesUIDsToBeAnnotated=("SeriesInstanceUID", lambda x: list(x.unique())),
    )
    .reset_index()
    .rename(columns={"StudyInstanceUID": "studyUID"})
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for _, row in grouped.iterrows():
        doc = {
            "protocol": "",
            "studyUID": str(row["studyUID"]),
            "seriesUIDsToBeAnnotated": row["seriesUIDsToBeAnnotated"],
        }
        f.write(json.dumps(doc) + "\n")

print(f"Done: {len(grouped)} studies written to {OUTPUT_FILE}")