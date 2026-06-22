"""
Extract one representative metadata record per DICOM series from an Orthanc
server (e.g. hosted on Render), via Orthanc's REST API - no file downloads,
no pydicom required.

Usage:
    python ExtractDicomMetadata_Orthanc.py --url https://your-orthanc.onrender.com \
        --user myuser --password mypass --output dicom_index.xlsx

Or set credentials via environment variables instead of the command line:
    ORTHANC_URL, ORTHANC_USER, ORTHANC_PASSWORD
"""

import argparse
import os
import sys
import requests
import pandas as pd


def get_args():
    parser = argparse.ArgumentParser(description="Extract one metadata record per series from Orthanc.")
    parser.add_argument("--url", default=os.environ.get("ORTHANC_URL"),
                         help="Base URL of the Orthanc server, e.g. https://your-orthanc.onrender.com")
    parser.add_argument("--user", default=os.environ.get("ORTHANC_USER"),
                         help="Orthanc username")
    parser.add_argument("--password", default=os.environ.get("ORTHANC_PASSWORD"),
                         help="Orthanc password")
    parser.add_argument("--output", default="dicom_index.xlsx",
                         help="Output .xlsx file path (default: dicom_index.xlsx)")
    args = parser.parse_args()

    missing = [name for name, val in
               [("--url/ORTHANC_URL", args.url), ("--user/ORTHANC_USER", args.user),
                ("--password/ORTHANC_PASSWORD", args.password)] if not val]
    if missing:
        parser.error(f"Missing required value(s): {', '.join(missing)}")

    args.url = args.url.rstrip("/")
    return args


def main():
    args = get_args()
    auth = (args.user, args.password)
    session = requests.Session()
    session.auth = auth

    # Confirm connectivity / credentials up front with a clear error message.
    try:
        resp = session.get(f"{args.url}/system", timeout=15)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 401:
            sys.exit("Authentication failed: check --user / --password.")
        sys.exit(f"Could not reach Orthanc server: {e}")
    except requests.exceptions.RequestException as e:
        sys.exit(f"Could not reach Orthanc server at {args.url}: {e}")

    # Get all series IDs (Orthanc internal IDs).
    resp = session.get(f"{args.url}/series", timeout=30)
    resp.raise_for_status()
    series_ids = resp.json()
    print(f"Found {len(series_ids)} series on the server.")

    records = []

    for i, series_id in enumerate(series_ids, start=1):
        try:
            # Get the list of instances belonging to this series.
            resp = session.get(f"{args.url}/series/{series_id}/instances", timeout=30)
            resp.raise_for_status()
            instances = resp.json()
            if not instances:
                print(f"  Skipping series {series_id}: no instances found.")
                continue

            # Only need ONE representative instance per series.
            instance_id = instances[0]["ID"]

            # Fetch simplified DICOM tags for that single instance.
            resp = session.get(f"{args.url}/instances/{instance_id}/tags?simplify", timeout=30)
            resp.raise_for_status()
            tags = resp.json()

            study_uid = tags.get("StudyInstanceUID")
            series_uid = tags.get("SeriesInstanceUID")
            patient_name = tags.get("PatientName")
            patient_id = tags.get("PatientID")
            series_desc = tags.get("SeriesDescription")

            records.append({
                "OrthancSeriesID": series_id,
                "StudyInstanceUID": study_uid,
                "SeriesInstanceUID": series_uid,
                "PatientName": str(patient_name) if patient_name else None,
                "PatientID": patient_id,
                "SeriesDescription": series_desc,
            })

        except requests.exceptions.RequestException as e:
            print(f"  Skipping series {series_id}: {e}")
            continue

        if i % 25 == 0 or i == len(series_ids):
            print(f"  Processed {i}/{len(series_ids)} series...")

    df = pd.DataFrame(records)
    df.to_excel(args.output, index=False)
    print(f"Done. Extracted {len(df)} series into {args.output}")


if __name__ == "__main__":
    main()