"""
shape2csv

Converts a list of Nx2 numpy arrays (segments) into MMI-style csv format.
Each segment represents one shape consisting of pixel coordinates (x, y).

The csv file contains:
- Calibration points
- Shapes
"""

import numpy as np
from datetime import datetime
import warnings
from pathlib import Path

def _transform_points(points, offset, scaling_factor, invert_factor):
    """Apply invert, scaling and offset transformation to Nx2 array."""
    return points * invert_factor * scaling_factor + offset


def _format_points(points):
    """Convert Nx2 array into list of 'x,y' strings."""
    return [f"{x},{y}" for x, y in points]


def shape2csv(
        segments,
        calibration_points,
        offset=np.array([0.0, 0.0]),
        scaling_factor=1.0,
        invert_factor=np.array([1.0, 1.0]),
        folder_name=None,
):
    """
    Export shape segments and calibration points to MMI-compatible CSV.

    segments: list of ndarray (N,2)
    calibration_points: ndarray (3,2)
    """

    # ---------- Input validation ----------
    if not isinstance(segments, (list, tuple)):
        raise TypeError("segments must be list of Nx2 numpy arrays")

    if calibration_points.shape != (3, 2):
        raise ValueError("calibration_points must have shape (3,2)")

    # ---------- Transform calibration ----------
    cal_trans = _transform_points(
        calibration_points, offset, scaling_factor, invert_factor
    )

    lines = []

    # ---------- Add calibration references ----------
    for i, point in enumerate(cal_trans):
        lines.append(f"# reference {i}")
        lines.append(f"{point[0]},{point[1]}")
        lines.append("")

    # ---------- Add segments ----------
    for segment in segments:
        if segment.shape[1] != 2:
            raise ValueError("Each segment must have shape (N,2)")

        transformed = _transform_points(
            segment, offset, scaling_factor, invert_factor
        )

        lines.append("#")
        lines.extend(_format_points(transformed))
        lines.append("")

    # ---------- Create filename ----------
    timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
    filename = f"shape_{timestamp}.csv"

    if folder_name:
        path = Path(folder_name) / filename
    else:
        path = Path(filename)

    # ---------- Write file ----------
    path.write_text("\n".join(lines))

    print(f"Export done: {path}")
    return path


def addshape2csv(
        segments,
        file_name,
        offset=np.array([0.0, 0.0]),
        scaling_factor=1.0,
        invert_factor=np.array([1.0, 1.0]),
):
    """
    Append segments to existing CSV file.
    """

    path = Path(file_name)

    if not path.exists():
        raise FileNotFoundError(f"{file_name} does not exist")

    lines = path.read_text().splitlines()
    lines.append("")

    for segment in segments:
        if segment.shape[1] != 2:
            raise ValueError("Each segment must have shape (N,2)")

        transformed = _transform_points(
            segment, offset, scaling_factor, invert_factor
        )

        lines.append("#")
        lines.extend(_format_points(transformed))
        lines.append("")

    path.write_text("\n".join(lines))

    print(f"Segments appended to {path}")


if __name__ == "__main__":

    # ---------- Example Segments ----------
    segments = [
        np.array([
            [14.956224, 6.195648],
            [2.0, 3.0],
        ]),
        np.ones((3, 2))
    ]

    # ---------- Calibration Points ----------
    calibration_points = np.array([
        [9264.192, 3.088064],
        [17353.28, 2.553216],
        [14942.56, 9.60872],
    ])

    # ---------- Export ----------
    output_path = shape2csv(segments, calibration_points)

    # Example segments
    segments_new = [
        np.zeros((2, 2)),
        np.array([[3, 3], [1, 1], [9, 5]])
    ]

    # ---------- Append Example ----------
    if Path(output_path).exists():
        addshape2csv(segments_new, file_name=output_path)

