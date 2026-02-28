# v408 Example — External Nuclear Dataset Intake

This folder contains minimal example inputs for the **v408 Nuclear Dataset Intake & Provenance Builder**.

## 1) Full dataset JSON import

- `example_dataset_full.json`

Use in UI (v408 panel) by uploading the JSON and clicking **Build + validate**, then **Save dataset to registry**.

## 2) Metadata JSON + sigma-removal CSV import

- `example_metadata.json`
- `example_sigma_removal.csv`

In UI:
1. Upload the metadata JSON and sigma-removal CSV
2. Provide spectrum fractions and TBR response weights
3. Click **Build + validate**, then **Save dataset to registry**

Notes
-----
These are **screening proxies**. They are not ENDF/TENDL-derived nuclear data.

Author: © 2026 Afshin Arjhangmehr
