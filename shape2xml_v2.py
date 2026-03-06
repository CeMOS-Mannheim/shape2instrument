"""
shape2xml

Converts a list of Nx2 numpy arrays (segments) into Leica-style XML format.
Each segment represents one shape consisting of pixel coordinates (x, y).

The XML file contains:
- Calibration points
- ShapeCount
- PointCount per shape
- CapID per shape
"""

from pathlib import Path
from datetime import datetime
import numpy as np
import dicttoxml
import warnings
import xml.etree.ElementTree as ET
from xml.dom import minidom


def shape2xml(
    segments,
    capture_ids,
    calibration_points,
    offset=np.array([0, 0]),
    scaling_factor=1.0,
    invert_factor=np.array([1, 1]),
    folder_name=None,
    unit_scaling=1000,
):
    """
    Export shape segments and calibration points to Leica-compatible XML.

    Parameters
    ----------
    segments : list of numpy.ndarray
        List of (N, 2) arrays, each representing a contour.
    capture_ids: list of str
        The CapID associated with each segment.
    calibration_points : numpy.ndarray
        A (3, 2) array of physical calibration points.
    offset : numpy.ndarray, optional
        A (2,) array for [X, Y] offset (default: [0.0, 0.0]).
    scaling_factor : float, optional
        Global scaling factor (default: 1.0).
    invert_factor : numpy.ndarray, optional
        A (2,) array to flip axes (-1.0 to flip, default: [1.0, 1.0]).
    folder_name : str or Path, optional
        Output directory path.
    unit_scaling : float, optional
        Factor to scale coordinates (default: 1000, e.g. mm to µm).

    Returns
    -------
    pathlib.Path or None
        Path to the created XML file, or None if failed.
    """

    try:
        # -----------------------------
        # Basic Validation
        # -----------------------------
        if len(segments) != len(capture_ids):
            raise ValueError("segments and capture_ids must have same length.")

        calibration_points = np.asarray(calibration_points, dtype=float)
        offset = np.asarray(offset, dtype=float)
        invert_factor = np.asarray(invert_factor, dtype=float)

        # -----------------------------
        # Create main dictionary
        # -----------------------------
        xml_dict = {
            "GlobalCoordinates": 1,
            "X_CalibrationPoint_1": int(round(calibration_points[0, 0] * unit_scaling)),
            "Y_CalibrationPoint_1": int(round(calibration_points[0, 1] * unit_scaling)),
            "X_CalibrationPoint_2": int(round(calibration_points[1, 0] * unit_scaling)),
            "Y_CalibrationPoint_2": int(round(calibration_points[1, 1] * unit_scaling)),
            "X_CalibrationPoint_3": int(round(calibration_points[2, 0] * unit_scaling)),
            "Y_CalibrationPoint_3": int(round(calibration_points[2, 1] * unit_scaling)),
            "ShapeCount": len(segments),
        }

        # -----------------------------
        # Add shapes
        # -----------------------------
        for i, segment in enumerate(segments, start=1):
            segment = np.asarray(segment, dtype=float)

            shape_dict = {
                "PointCount": segment.shape[0],
                "CapID": capture_ids[i - 1],
            }

            # Vectorized coordinate transform
            transformed = (
                invert_factor * segment * scaling_factor + offset
            ) * unit_scaling
            transformed = transformed.round().astype(int)

            for j, (x, y) in enumerate(transformed, start=1):
                shape_dict[f"X_{j}"] = int(x)
                shape_dict[f"Y_{j}"] = int(y)

            xml_dict[f"Shape_{i}"] = shape_dict

        # -----------------------------
        # Convert to XML & Pretty Print
        # -----------------------------
        xml_bytes = dicttoxml.dicttoxml(
            xml_dict,
            custom_root="ImageData",
            attr_type=False,
        )

        reparsed = minidom.parseString(xml_bytes)
        xml_string = reparsed.toprettyxml(indent="  ")

        # -----------------------------
        # Generate filename
        # -----------------------------
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        filename = f"shape_{timestamp}.xml"

        if folder_name:
            folder = Path(folder_name)
            folder.mkdir(parents=True, exist_ok=True)
            filepath = folder / filename
        else:
            filepath = Path(filename)

        filepath.write_text(xml_string)

        print(f"XML exported successfully → {filepath}")

        return filepath

    except (ValueError, TypeError, IndexError) as e:
        warnings.warn(f"shape2xml failed: {e}")
        return None


def addshape2xml(
    segments,
    capture_ids,
    file_name,
    offset=np.array([0.0, 0.0]),
    scaling_factor=1.0,
    invert_factor=np.array([1.0, 1.0]),
    unit_scaling=1000,
):
    """
    Append new shapes to an existing Leica-style XML file.

    Parameters
    ----------
    segments : list of numpy.ndarray
        List of (N, 2) arrays, each representing a contour.
    capture_ids : list of str
        The CapID associated with each new segment.
    file_name : str or Path
        Path to the existing target .xml file.
    offset : numpy.ndarray, optional
        A (2,) array for [X, Y] offset (default: [0.0, 0.0]).
    scaling_factor : float, optional
        Global scaling factor (default: 1.0).
    invert_factor : numpy.ndarray, optional
        A (2,) array to flip axes (-1.0 to flip, default: [1.0, 1.0]).
    unit_scaling : float, optional
        Factor to scale coordinates (default: 1000, e.g. mm to µm).

    Returns
    -------
    pathlib.Path or None
        Path to the modified XML file, or None if failed.
    """

    try:
        path = Path(file_name)

        if not path.exists():
            raise FileNotFoundError(f"{file_name} does not exist.")

        if len(segments) != len(capture_ids):
            raise ValueError("segments and capture_ids must have same length.")

        offset = np.asarray(offset, dtype=float)
        invert_factor = np.asarray(invert_factor, dtype=float)

        # -----------------------------
        # Parse XML
        # -----------------------------
        tree = ET.parse(path)
        root = tree.getroot()

        shape_count_element = root.find("ShapeCount")
        if shape_count_element is None:
            raise ValueError("ShapeCount tag not found in XML.")

        current_shape_count = int(shape_count_element.text)

        # -----------------------------
        # Append new shapes
        # -----------------------------
        for i, segment in enumerate(segments, start=1):

            segment = np.asarray(segment, dtype=float)

            if segment.ndim != 2 or segment.shape[1] != 2:
                raise ValueError("Each segment must have shape (N,2).")

            new_index = current_shape_count + i
            shape_tag = f"Shape_{new_index}"

            shape_element = ET.SubElement(root, shape_tag)

            ET.SubElement(shape_element, "PointCount").text = str(segment.shape[0])
            ET.SubElement(shape_element, "CapID").text = str(capture_ids[i - 1])

            # Vectorized coordinate transformation
            transformed = (
                invert_factor * segment * scaling_factor + offset
            ) * unit_scaling
            transformed = transformed.round().astype(int)

            for j, (x, y) in enumerate(transformed, start=1):
                ET.SubElement(shape_element, f"X_{j}").text = str(int(x))
                ET.SubElement(shape_element, f"Y_{j}").text = str(int(y))

        # -----------------------------
        # Update ShapeCount
        # -----------------------------
        shape_count_element.text = str(int(current_shape_count + len(segments)))

        # -----------------------------
        # Write file (with indent)
        # -----------------------------
        if hasattr(ET, 'indent'):
            ET.indent(tree, space="  ", level=0)
            
        tree.write(path, encoding="utf-8", xml_declaration=True)

        print(f"Added {len(segments)} shape(s) → {path}")

        return path

    except (ValueError, TypeError, IndexError, FileNotFoundError) as e:
        warnings.warn(f"addshape2xml failed: {e}")
        return None


# ---------------------------------------------------------
# Example
# ---------------------------------------------------------
if __name__ == "__main__":

    # Example segments
    segments = [
        np.zeros((2, 2)), #polygon 1
        np.array([[1, 1], [2, 2], [3, 6]]) #polygon 2
    ]

    # Calibration points
    calibration_points = np.array([
        [10, 10],
        [800, 10],
        [800, 700]
    ])

    # Capture IDs
    capture_ids = ["C3", #cap polygon 1
                   "A1"] #cap polygon 2

    # Execute
    output_path = shape2xml(segments, capture_ids, calibration_points)

    # Example segments
    segments_new = [
        np.zeros((2, 2)),
        np.array([[3, 3], [1, 1], [9, 5]])
    ]

    # Capture IDs
    capture_ids_new = ["B2", "X1"]

    # ---------- Append Example ----------
    if Path(output_path).exists():
        addshape2xml(segments_new, capture_ids_new, file_name=output_path)