import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import nrrd
import cv2

from shape2csv_v2 import shape2csv
from shape2xml_v2 import shape2xml

def parse_mps_calibration(mps_path):
    """Parse calibration points from Medical Point Set (.mps) file."""
    if not Path(mps_path).exists():
        raise FileNotFoundError(f"MPS file not found: {mps_path}")
        
    tree = ET.parse(mps_path)
    root = tree.getroot()
    
    # Extract points from point_set/time_series/point
    points = []
    for point_elem in root.findall(".//point"):
        x = float(point_elem.find("x").text)
        y = float(point_elem.find("y").text)
        points.append([x, y])
        
    if len(points) != 3:
        raise ValueError(f"Expected exactly 3 calibration points in MPS, found {len(points)}")
        
    return np.array(points)

def extract_segments_from_nrrd(nrrd_path):
    """Extract distinct labeled segments from an NRRD file as polygons in physical coordinates."""
    if not Path(nrrd_path).exists():
        raise FileNotFoundError(f"NRRD mask file not found: {nrrd_path}")
        
    data, header = nrrd.read(nrrd_path)
    
    # 1. Extract coordinate transforms from header
    origin = np.zeros(2)
    spacing_i = np.array([1.0, 0.0]) # Direction for dim 0
    spacing_j = np.array([0.0, 1.0]) # Direction for dim 1
    
    if 'space origin' in header:
        o = np.array(header['space origin'])
        # Pad with zeros if shorter than 2, or slice if longer
        if len(o) >= 2:
            origin = o[:2]
        elif len(o) == 1:
            origin[0] = o[0]
            
    if 'space directions' in header:
        sd = np.array(header['space directions'])
        # Clean out potential NaN strings used by some NRRD tools for missing space directions
        # Not strictly needed if standard, but good safety.
        if sd.shape[0] >= 1:
            if not np.any(np.isnan(sd[0][:2])):
                sd_0 = sd[0][:2] if len(sd[0]) >= 2 else np.array([sd[0][0], 0.0])
                spacing_i = sd_0
        if sd.shape[0] >= 2:
            if not np.any(np.isnan(sd[1][:2])):
                sd_1 = sd[1][:2] if len(sd[1]) >= 2 else np.array([sd[1][0], 0.0])
                spacing_j = sd_1

    # Assuming 2D data or 3D data where we take the first slice.
    if data.ndim == 3 and data.shape[2] == 1:
        data = data[:, :, 0]
    elif data.ndim > 2:
        # Default to taking a slice if multiple dimensions exist (e.g. z-stack)
        data = data[:, :, 0]
        
    # Squeeze out single dimensional entries if present
    data = np.squeeze(data)
    
    if data.ndim != 2:
         raise ValueError(f"Expected 2D label mask, got shape: {data.shape}")

    segments = []
    labels = np.unique(data)
    
    # Make sure we process labels in a predictable sorted order
    # Skip label 0 as it conventionally represents background
    for label in sorted(labels):
        if label == 0:
            continue
            
        binary_mask = (data == label).astype(np.uint8)
        
        # Find contours
        # RETR_EXTERNAL gets outer boundary only.
        # CHAIN_APPROX_SIMPLE compresses horizontal/vertical/diagonal segments
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print(f"Warning: No contour found for label {label}")
            continue
            
        # Get the largest contour for this label in case of fragmented pixels
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Reshape from (N, 1, 2) to (N, 2)
        segment_points_cv = largest_contour.reshape(-1, 2)
        
        # TRANSFORM TO PHYSICAL SPACE
        # segment_points_cv[:, 0] is j (column)
        # segment_points_cv[:, 1] is i (row)
        j_vals = segment_points_cv[:, 0:1]
        i_vals = segment_points_cv[:, 1:2]
        
        spi = spacing_i.reshape(1, 2)
        spj = spacing_j.reshape(1, 2)
        orig = origin.reshape(1, 2)
        
        # physical = origin + i * spacing_i + j * spacing_j
        physical_points = orig + i_vals * spi + j_vals * spj
        
        segments.append(physical_points)
        
    return segments

def main():
    parser = argparse.ArgumentParser(description="Shape to Instrument Format Converter")
    
    # Required Arguments
    parser.add_argument("--mask", required=True, help="Path to input multi-label NRRD mask")
    parser.add_argument("--mps", required=True, help="Path to input MPS calibration points")
    parser.add_argument("--output", required=True, help="Output directory folder")
    parser.add_argument("--format", required=True, choices=["csv", "xml"], help="Output format (csv or xml)")
    
    # Conditionally Required / Format specific
    parser.add_argument("--cap_ids", type=str, help="Comma separated Capture IDs (required for xml format)")
    
    # Optional parameters
    parser.add_argument("--offset_x", type=float, default=0.0, help="Optional: X Offset (default: 0.0)")
    parser.add_argument("--offset_y", type=float, default=0.0, help="Optional: Y Offset (default: 0.0)")
    parser.add_argument("--scale", type=float, default=1.0, help="Optional: Scaling factor (default: 1.0)")
    parser.add_argument("--invert_x", type=float, default=1.0, help="Optional: X Invert Factor (-1.0 to invert, default: 1.0)")
    parser.add_argument("--invert_y", type=float, default=1.0, help="Optional: Y Invert Factor (-1.0 to invert, default: 1.0)")

    args = parser.parse_args()

    print("--- Configuration ---")
    print(f"Input Mask: {args.mask}")
    print(f"Input MPS:  {args.mps}")
    print(f"Output Dir: {args.output}")
    print(f"Format:     {args.format}")
    print("---------------------")

    # 1. Parse Calibration Points
    print(f"Parsing MPS: {args.mps}")
    calib_points = parse_mps_calibration(args.mps)
    
    # 2. Extract Segments
    print(f"Extracting Segments from NRRD: {args.mask}")
    segments = extract_segments_from_nrrd(args.mask)
    if not segments:
        print("Error: No segments found in the provided mask.")
        sys.exit(1)
    print(f"Found {len(segments)} segments.")

    # 3. Setup Transform arrays
    offset_arr = np.array([args.offset_x, args.offset_y])
    invert_arr = np.array([args.invert_x, args.invert_y])

    # 4. Ensure output directory exists
    Path(args.output).mkdir(parents=True, exist_ok=True)

    # 5. Dispatch to appropriate script
    if args.format == "csv":
        shape2csv(
            segments=segments,
            calibration_points=calib_points,
            offset=offset_arr,
            scaling_factor=args.scale,
            invert_factor=invert_arr,
            folder_name=args.output
        )
    elif args.format == "xml":
        if not args.cap_ids:
            print("Error: --cap_ids is required when using xml format.")
            sys.exit(1)
            
        capture_ids = [cid.strip() for cid in args.cap_ids.split(",")]
        
        if len(capture_ids) != len(segments):
            print(f"Error: Number of capture IDs ({len(capture_ids)}) does not match number of segments ({len(segments)}).")
            sys.exit(1)
            
        shape2xml(
            segments=segments,
            capture_ids=capture_ids,
            calibration_points=calib_points,
            offset=offset_arr,
            scaling_factor=args.scale,
            invert_factor=invert_arr,
            folder_name=args.output
        )

if __name__ == "__main__":
    main()
