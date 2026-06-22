import os
import pydicom
import pandas as pd

# -------- CONFIG --------
# Uncomment the ROOT_DIR folder as needed
# FOR LIVE_TESTING...
ROOT_DIR = r"D:/Users/cjohnson/Work/ForHarryMarshall/TCGA-LiverStudies/manifest-1779818875630/TCGA-LIHC"
# FOR LOCALPACS
# ROOT_DIR = r"D:/Users/cjohnson/Work/Projects/WebQuiz/Testing dicom LiverStudy/LocalPACS-DevTesting"
OUTPUT_XLSX = "dicom_index.xlsx"
# ------------------------

records = []
seen_series = set()

def is_dicom_file(path):
    """Quick check: DICOM files start with 'DICM' at byte offset 128."""
    try:
        with open(path, "rb") as f:
            f.seek(128)
            return f.read(4) == b"DICM"
    except:
        return False

for root, dirs, files in os.walk(ROOT_DIR):
    # A folder of slices for one series is typically uniform, so once we've
    # recorded a series from this folder we can skip straight to the next folder.
    folder_series_captured = None

    for filename in files:
        # If this folder's series has already been recorded, stop scanning it.
        if folder_series_captured is not None and folder_series_captured in seen_series:
            break

        filepath = os.path.join(root, filename)

        # Skip non-DICOM files early
        if not is_dicom_file(filepath):
            continue

        try:
            ds = pydicom.dcmread(filepath, stop_before_pixels=True)
            series_uid = getattr(ds, "SeriesInstanceUID", None)

            # Already captured this series (e.g. from an earlier file/folder) - skip.
            if series_uid in seen_series:
                folder_series_captured = series_uid
                continue

            study_uid = getattr(ds, "StudyInstanceUID", None)
            patient_name = getattr(ds, "PatientName", None)
            patient_id = getattr(ds, "PatientID", None)
            series_desc = getattr(ds, "SeriesDescription", None)

            records.append({
                "FilePath": filepath,
                "StudyInstanceUID": study_uid,
                "SeriesInstanceUID": series_uid,
                "PatientName": str(patient_name) if patient_name else None,
                "PatientID": patient_id,
                "SeriesDescription": series_desc,
            })

            seen_series.add(series_uid)
            folder_series_captured = series_uid

        except Exception as e:
            print(f"Skipping unreadable file: {filepath} ({e})")

# Convert to DataFrame
df = pd.DataFrame(records)

# Write Excel
df.to_excel(OUTPUT_XLSX, index=False)

print(f"Done. Extracted {len(df)} DICOM files into {OUTPUT_XLSX}")