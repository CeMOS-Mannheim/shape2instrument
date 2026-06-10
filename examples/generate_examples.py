import numpy as np
from pathlib import Path
import sys

# Ensure the project root is on sys.path so modules can be imported
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shape2xml_v2 import shape2xml
from shape2csv_v2 import shape2csv
from main import extract_segments_from_nrrd, parse_mps_calibration


def generate_examples():
    output_dir = project_root / "example_results"
    output_dir.mkdir(exist_ok=True)

    nrrd_path = project_root / "examples" / "01_tic_tenzl-labels.nrrd"
    mps_path = project_root / "examples" / "PointSet.mps"

    # 1. Extract segments from NRRD
    print(f"Extracting segments from {nrrd_path}...")
    segments, segment_labels, valid_labels = extract_segments_from_nrrd(str(nrrd_path), physical_space=True)
    print(f"Found {len(segments)} segments across {len(valid_labels)} unique label(s).")

    # 2. Parse calibration points
    print(f"Parsing calibration from {mps_path}...")
    calib_points = parse_mps_calibration(str(mps_path))

    # 3. Generate Leica XML (µm) — auto-generated well-plate IDs
    xml_path = shape2xml(segments, calibration_points=calib_points, folder_name=output_dir, unit_scaling=1000)
    print(f"Generated Leica XML: {xml_path}")

    # 4. Generate MMI CSV (mm) — auto-generated well-plate IDs
    csv_path = shape2csv(segments, calib_points, folder_name=output_dir)
    print(f"Generated MMI CSV: {csv_path}")

if __name__ == "__main__":
    generate_examples()
