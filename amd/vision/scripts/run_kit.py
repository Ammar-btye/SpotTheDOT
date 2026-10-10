"""Run every reader over the kit images and print one line per image (offline; no server needed).

    python scripts/run_kit.py [--kit "<path to SPOT_KnightHacks_Challenge_Kit Part One>"] [--out DIR]

--out writes each annotated JPEG and the JSON response there (handy for eyeballing the V# marks).
"""
import argparse
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vision.config import Settings  # noqa: E402
from vision.pipeline import analyze  # noqa: E402

DEFAULT_KIT = ROOT.parents[1] / "SPOTDATA" / "SPOT_KnightHacks_Challenge_Kit Part One"
SAMPLES = {"thermal_pump_bearing_01.jpg": "THERMAL_INSPECTION", "gauge_pressure_01.jpg": "GAUGE_READING",
           "acoustic_valve_01.jpg": "ACOUSTIC_INSPECTION", "pipe_gallery_01.jpg": "VISUAL_INSPECTION",
           "valve_detail_01.jpg": "VISUAL_INSPECTION", "visual_pump_motor_01.jpg": "VISUAL_INSPECTION"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", default=str(DEFAULT_KIT))
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-orbit", action="store_true")
    a = ap.parse_args(argv)
    kit = Path(a.kit)
    out = Path(a.out) if a.out else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    s = Settings()
    jobs = [(kit / "04_ASSETS" / "sample_inspection_images" / n, at) for n, at in SAMPLES.items()]
    if not a.no_orbit:
        jobs += [(p, None) for p in sorted((kit / "01_REFERENCE" / "Approved_Orbit_Screenshots").glob("*.png"))]
    for path, at in jobs:
        if not path.exists():
            print("missing %s" % path)
            continue
        req = {"image_b64": base64.b64encode(path.read_bytes()).decode(), "media_id": path.stem, "kind": "auto",
               "action_type": at, "annotate": out is not None}
        r = analyze(req, s)
        rd = "; ".join("%s %s=%g%s c%.2f%s" % (x["id"], x["quantity"], x["value"], (" " + x["unit"]) if x["unit"] else "",
                                               x["confidence"], (" [" + ",".join(x["flags"]) + "]") if x["flags"] else "")
                       for x in r["readings"][:6])
        print("%-34s %-16s %5d ms  %s%s%s" % (path.name[-34:], r["kind"], r["latency_ms"], rd or "-",
                                             ("  ALERT s%d %s" % (r["alert"]["severity"], r["alert"]["title"])) if r["alert"] else "",
                                             ("  flags=" + ",".join(r["flags"])) if r["flags"] else ""))
        if out:
            if r["annotated_image_b64"]:
                (out / (path.stem + ".annotated.jpg")).write_bytes(base64.b64decode(r["annotated_image_b64"]))
            r = dict(r, annotated_image_b64="<omitted>")
            (out / (path.stem + ".json")).write_text(json.dumps(r, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
