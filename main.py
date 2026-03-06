import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import nrrd
import cv2
import datetime

from shape2csv_v2 import shape2csv
from shape2xml_v2 import shape2xml
from mis_maker_class import mismaker

def parse_mps_calibration(mps_path):
    """
    Parse calibration points from Medical Point Set (.mps) file.

    Parameters
    ----------
    mps_path : str or Path
        Path to the target .mps XML file.

    Returns
    -------
    numpy.ndarray
        A (3, 2) array containing the [x, y] coordinates of the 3 calibration points.

    Raises
    ------
    FileNotFoundError
        If the mps_path does not exist.
    ValueError
        If the file does not contain exactly 3 points.
    """
    if not Path(mps_path).exists():
        raise FileNotFoundError(f"MPS file not found: {mps_path}")
        
    tree = ET.parse(mps_path)
    root = tree.getroot()
    
    points = []
    for point_elem in root.findall(".//point"):
        x = float(point_elem.find("x").text)
        y = float(point_elem.find("y").text)
        points.append([x, y])
        
    if len(points) != 3:
        raise ValueError(f"Expected exactly 3 calibration points in MPS, found {len(points)}")
        
    return np.array(points)

def extract_segments_from_nrrd(nrrd_path, physical_space=True):
    """
    Extract distinct labeled segments from an NRRD multi-label mask as polygons.

    Uses OpenCV's findContours to generate vector outlines of each labeled region.
    Filters out noise (contours with < 3 points).

    Parameters
    ----------
    nrrd_path : str or Path
        Path to the multi-label NRRD image.
    physical_space : bool, optional
        If True (default), transforms pixel coordinates into physical space (mm)
        using the NRRD 'space origin' and 'space directions' header fields.
        If False, returns raw image pixel coordinates (X=column, Y=row).

    Returns
    -------
    segments : list of numpy.ndarray
        List of (N, 2) arrays, each representing a contour.
    segment_labels : list of int
        The label value associated with each segment in the list.
    valid_labels : list of int
        Unique non-zero labels found in the mask.

    Raises
    ------
    FileNotFoundError
        If nrrd_path does not exist.
    ValueError
        If the data is not 2D (after squeezing/slicing).
    """
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
    segment_labels = []
    valid_labels = sorted([l for l in np.unique(data) if l != 0])
    
    for label in valid_labels:
        binary_mask = (data == label).astype(np.uint8)
        
        # Find contours
        # RETR_EXTERNAL gets outer boundary only.
        # CHAIN_APPROX_SIMPLE compresses horizontal/vertical/diagonal segments
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print(f"Warning: No contour found for label {label}")
            continue
            
        for c in contours:
            # Reshape from (N, 1, 2) to (N, 2)
            segment_points_cv = c.reshape(-1, 2)
            
            # Skip invalid contours (lines or points)
            if len(segment_points_cv) < 3:
                continue
            
            # TRANSFORM TO PHYSICAL SPACE
            # segment_points_cv[:, 0] is j (column)
            # segment_points_cv[:, 1] is i (row)
            j_vals = segment_points_cv[:, 0:1]
            i_vals = segment_points_cv[:, 1:2]
            
            spi = spacing_i.reshape(1, 2)
            spj = spacing_j.reshape(1, 2)
            orig = origin.reshape(1, 2)
            
            if physical_space:
                # physical = origin + i * spacing_i + j * spacing_j
                points = orig + i_vals * spi + j_vals * spj
            else:
                # Raw image coordinates: X=j, Y=i
                points = np.hstack((j_vals, i_vals))
                
            segments.append(points)
            segment_labels.append(label)
        
    return segments, segment_labels, valid_labels

def main():
    parser = argparse.ArgumentParser(description="Shape to Instrument Format Converter")
    
    # Required Arguments
    parser.add_argument("--mask", required=True, help="Path to input multi-label NRRD mask")
    parser.add_argument("--output", required=True, help="Output directory folder")
    parser.add_argument("--format", required=True, choices=["csv", "xml", "mis"], help="Output format (csv for LMD from MMI, xml for LMD from Leica, or mis for Bruker FlexImaging)")
    
    # Conditionally Required / Format specific
    parser.add_argument("--mps", help="Path to input MPS calibration points (required for csv and xml)")
    parser.add_argument("--mis_template", help="Path to template MIS file (required for mis format)")
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

    # Format specific validation
    if args.format in ["csv", "xml"] and not args.mps:
        print(f"Error: --mps is required when using format {args.format}.")
        sys.exit(1)
    if args.format == "mis" and not args.mis_template:
        print("Error: --mis_template is required when using mis format.")
        sys.exit(1)

    # 1. Parse Calibration Points (only needed for CSV/XML)
    calib_points = None
    if args.format in ["csv", "xml"]:
        print(f"Parsing MPS: {args.mps}")
        calib_points = parse_mps_calibration(args.mps)
    
    # 2. Extract Segments
    print(f"Extracting Segments from NRRD: {args.mask}")
    segments, segment_labels, valid_labels = extract_segments_from_nrrd(args.mask, physical_space=(args.format != "mis"))
    if not segments:
        print("Error: No segments found in the provided mask.")
        sys.exit(1)
    print(f"Found {len(segments)} segments across {len(valid_labels)} unique labels.")

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
        
        if len(capture_ids) != len(valid_labels):
            print(f"Error: Number of capture IDs ({len(capture_ids)}) does not match number of unique labels ({len(valid_labels)}).")
            sys.exit(1)
            
        label_to_capid = dict(zip(valid_labels, capture_ids))
        mapped_cap_ids = [label_to_capid[lbl] for lbl in segment_labels]
            
        shape2xml(
            segments=segments,
            capture_ids=mapped_cap_ids,
            calibration_points=calib_points,
            offset=offset_arr,
            scaling_factor=args.scale,
            invert_factor=invert_arr,
            folder_name=args.output,
            unit_scaling=1000
        )
    elif args.format == "mis":
        timestamp = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
        out_file = Path(args.output) / f"shape_{timestamp}.mis"
        
        # Mismaker instantiation
        mm = mismaker(imagefilename="mask.tif", outputfilename=str(out_file))
        mm.load_mis(args.mis_template, mode="add")
        
        contourDict = {}
        for i, (seg, lbl) in enumerate(zip(segments, segment_labels)):
            # Apply user transforms
            transformed = seg * args.scale * invert_arr + offset_arr
            
            contourDict[i] = {
                "contour": transformed.astype(int),
                "parameters": {
                    "areaname": f"Label_{lbl}_{i}",
                    "polygontype": "Area"
                }
            }
            
        mm.add_contours(contourDict)
        mm.save_mis(str(out_file))
        print(f"Export done: {out_file}")

if __name__ == "__main__":
    main()
