"""Download IRI CSV from blob and save for WASM bundling."""

import ocha_stratus as stratus

blob_name = "ds-aa-ner-drought/raw/iri/ner_maproom_export_2026-04-25_thresh35 - Sheet1.csv"
df = stratus.load_csv_from_blob(blob_name)
df.to_csv("exploration/public/iri_data.csv", index=False)
print(f"Saved {len(df)} rows to exploration/public/iri_data.csv")
