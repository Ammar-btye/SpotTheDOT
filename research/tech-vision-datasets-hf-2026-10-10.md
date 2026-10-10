# Vision data on Hugging Face for SPOT inspections (2026-10-10)

## 1. Scope
- **Question:** the kit has no image linked to any reading, only 6 synthetic samples (`04_ASSETS/sample_inspection_images/`, about 250×166, one per inspection type). Can Hugging Face supply training or evaluation data for each inspection type?
- **Searched:** the HF Hub dataset API for gauge, thermal, infrared, corrosion, rust, leak, valve, pump, MIMII, DCASE, MVTec, VisA, substation, power equipment and meter terms. Sizes, splits and labels were checked with the datasets-server `info`/`statistics`/`rows` endpoints and the dataset cards.
- **Skipped:** Kaggle and Roboflow Universe (not HF); no dataset was downloaded.
- **Kit context:** readings are PRESSURE_PSI 68.6–150.6, TEMPERATURE_C 39.8–83.5, SOUND_DB and VISUAL_SCORE.
  - The kit gauge image is AI-generated: "290" is printed where 250 belongs, and the long needle points at about 0 psi.
  - The kit thermal image peaks at about 99 °C (an OpenCV colour-bar probe agreed).
  - So neither sample image matches any CSV row.

## 2. Datasets by SPOT inspection type
| Inspection (kit action type) | Dataset | Size | Labels | Licence | Fit |
|---|---|---|---|---|---|
| Gauge (GAUGE_READING) | [FlagEval/MeasureBench](https://huggingface.co/datasets/FlagEval/MeasureBench) | 1,272 real + 1,170 synthetic; **118 real + 120 synthetic pressure gauges** | question + accepted value interval + units | CC-BY-SA-4.0 | **Best eval set.** It's the benchmark where the best VLM scored 30.3% on real images (`tech-amd-rocm-hf-serving`). Lets us report OpenCV vs Qwen3.5 accuracy on real gauges. |
| Gauge | [monica-sekoyan/MeasureBenchPressureGauge-DiverseSynthetic](https://huggingface.co/datasets/monica-sekoyan/MeasureBenchPressureGauge-DiverseSynthetic) | 1,000 / 50 / 100 | exact psi value, needle angle, scale-zero angle | not stated on card | Pressure gauges with exact ground truth; good for tuning an OpenCV needle reader. |
| Gauge | [moondream/synthetic-gauges-v6](https://huggingface.co/datasets/moondream/synthetic-gauges-v6) | 262,144 (~20 GB) | JSON with value, tick and label pixel positions | not stated on card | Huge; stream a slice. Keypoints suit a learned needle/tick detector. |
| Gauge | [KhoaUIT/Synthetic-Data-for-Precision-Gauge-Reading](https://huggingface.co/datasets/KhoaUIT/Synthetic-Data-for-Precision-Gauge-Reading) | 500 | question/answer text | not stated | Small VQA set; a quick VLM sanity check. |
| Visual (VISUAL_INSPECTION, VISUAL_DEFECT) | [LibreYOLO/corrosion-bi3q3](https://huggingface.co/datasets/LibreYOLO/corrosion-bi3q3) | 840 / 304 / 105 | boxes: corrosion, crack, slippage | CC-BY-4.0 | Roboflow-100 subset, real photos; fine-tune a small YOLO detector or evaluate VLM yes/no. |
| Visual | [lg227210/gas-valve-anomaly-dataset](https://huggingface.co/datasets/lg227210/gas-valve-anomaly-dataset) | 1,301 images, 3,071 boxes | water, corrosion_rust, seepage, crack, coating damage, fog | MIT | Real gas-valve-well inspections, closest to plant equipment; boxes are VLM-made + human-verified. |
| Visual | [khoaliamle/Corrosion_Rust](https://huggingface.co/datasets/khoaliamle/Corrosion_Rust) | 750 | rust / no rust | MIT | Simplest binary classifier set. |
| Visual | [Voxel51/mvtec-ad](https://huggingface.co/datasets/Voxel51/mvtec-ad) | 5,200 | defect masks (FiftyOne format) | CC-BY-NC-SA-4.0 | Classic anomaly benchmark, but factory parts, not plant equipment. Low fit. |
| Acoustic (ACOUSTIC_INSPECTION, ABNORMAL_VIBRATION) | [HTill/dcase2025_task2_dev](https://huggingface.co/datasets/HTill/dcase2025_task2_dev) | 5,000 / 1,000 / 700 | machine type (**valve**, bearing, fan, gearbox, slider…) + normal/anomaly | MIT | Real machine audio; spectrogram → anomaly score matches the kit's spectrogram sample. |
| Acoustic | [stdt1/mimii_pump_datasets](https://huggingface.co/datasets/stdt1/mimii_pump_datasets) | 8,830 / 1,893 / 1,892 | normal/abnormal pump, SNR, precomputed mel spectrograms | not stated | Pumps (kit has PUMP assets); already in mel-spectrogram form. |
| Thermal (THERMAL_INSPECTION) | [Manishsahu53/Solar-Panel-Thermal-Drone-UAV-Images](https://huggingface.co/datasets/Manishsahu53/Solar-Panel-Thermal-Drone-UAV-Images) | 22,810 | none | Apache-2.0 | Unlabelled solar panels. Weak fit. |
| Thermal | [nealgoogs/thermal-fault-detection-dataset](https://huggingface.co/datasets/nealgoogs/thermal-fault-detection-dataset) | 9,016 | only "rgb" vs "thermal" folders; no card | none | No fault or temperature labels. Not usable. |

## 3. Takeaways
- **Gauges are well covered.** MeasureBench gives a real, cited eval set; the synthetic sets give exact ground truth for building a reader. This is the strongest AMD/HF "measured" story: OpenCV vs VLM accuracy on real gauges, on Radeon.
- **Visual defects are covered** by real corrosion/crack/valve-well sets with boxes (MIT/CC-BY), enough for a small detector or a VLM yes/no eval like Orbit's "AI" inspections.
- **Acoustic is covered** by DCASE 2025 (includes valves) and MIMII pumps, both labelled normal/anomaly.
- **Thermal is the gap.** No labelled equipment-thermal set with temperatures was found on HF. Colour-mapped thermal images carry no radiometric data, so read temperature from the colour bar (OpenCV) and test on images we render at known temperatures.
- **MeasureBench numbers to quote correctly** ([paper](https://arxiv.org/abs/2510.26865), HTML version, Table 2/7): "30%" is Gemini-2.5-Pro's real-world score over **all 26 instrument types** (30.2% overall, 31.5% on dials); pressure gauges are not broken out. Closest to our model: Qwen3-VL-8B 15.3% overall, 14.5% dials. Prior special-purpose CV gauge readers did worse (Reitsma et al. 2024: 8.5%; Shu et al. 2023: failed on all). GRPO fine-tuning on synthetic gauges lifted Qwen2.5-VL-7B from 14.6% to 19.7% on real. Scoring is interval matching, so answers within a per-image tolerance count. Qwen3.5-9B is not in the paper.
- **Implication:** beating 30% on wild, unknown gauges is unlikely this weekend. SPOT's setting is easier: it revisits the same gauge from the same waypoint, so each gauge's range and min/max needle angles can be calibrated once (as Orbit/Levatas do). Measure the lift from that calibration rather than chasing the open benchmark.
- None of these link to kit missions. In the demo, label images as illustrative and show the cross-check, not a claim that SPOT took them.

## 4. Open questions / next searches
- Licences are unstated for the sekoyan, moondream, KhoaUIT and MIMII mirrors; check before publishing derived data.
- `Synanthropic/reading-analog-gauge` (42,442 images, folder labels "corners"/"keypoint") is unclear; inspect its files before use.
- `Mileeena/synthetic-analog-gauges` (CC-BY-4.0, COCO boxes + segmentation) is gated; requires accepting terms.
- Equipment-thermal data may exist on Kaggle/Roboflow (e.g., motor or electrical-panel IR sets); not searched.
