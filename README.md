# Shape2Instrument Docker Container

This containerized add-on for M2AIA converts segmented shape definitions (multi-label NRRD mask) and calibration points (MPS PointSet) into physical vector polygons formatted for specific instrument interfaces (Leica `.xml` or MMI `.csv`).

## Prerequisites
- Docker must be installed and running on your system.

---

## 🏗️ 1. Building the Image

Navigate to this directory (where the `Dockerfile` is located) and build the Docker image locally:

```bash
docker build -t shape2instrument:latest .
```

---

## 🚀 2. Running the Container

The tool expects specific inputs mounted as a volume so that the container can read the source files and write the generated configuration. 

### Core Required Arguments:
- `--mask`: Path to the input multi-label `.nrrd` image mask.
- `--mps`: Path to the `.mps` calibration points file.
- `--output`: Output directory inside the mounted volume where the result file will be saved.
- `--format`: The target machine format to generate (`xml` or `csv`).

### Optional Transformation Arguments:
- `--offset_x`: Float (default `0.0`)
- `--offset_y`: Float (default `0.0`)
- `--scale`: Float (default `1.0`)
- `--invert_x`: Float (default `1.0`, use `-1.0` to invert)
- `--invert_y`: Float (default `1.0`, use `-1.0` to invert)

---

### Example A: Generating Leica XML

Generating XML files requires one additional required parameter: `--cap_ids`. This should be a comma-separated list of strings representing the Capture IDs for each generated polygon map.

*Note: Ensure you map `-v "${PWD}:/data"` to mount your local folder into the container's `/data` directory.*

```bash
docker run --rm \
  -v "${PWD}:/data" \
  shape2instrument:latest \
  --mask /data/01-labels.nrrd \
  --mps /data/pointset.mps \
  --output /data/results \
  --format xml \
  --cap_ids A1,B2,C3
```
*This outputs a file named `shape_<timestamp>.xml` in the `./results/` folder.*

---

### Example B: Generating MMI CSV

CSV generation extracts the identical contour sets but formats them natively to the .csv coordinates without requiring capture IDs.

```bash
docker run --rm \
  -v "${PWD}:/data" \
  shape2instrument:latest \
  --mask /data/01-labels.nrrd \
  --mps /data/pointset.mps \
  --output /data/results \
  --format csv 
```
*This outputs a file named `shape_<timestamp>.csv` in the `./results/` folder.*
