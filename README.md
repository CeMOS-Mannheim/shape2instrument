# Shape2Instrument

Converts segmented shape definitions (multi-label NRRD mask) and point sets (MPS) into physical vector polygons formatted for specific mass spectrometry imaging (MSI) instrument interfaces.

**Supported formats:**
| Format | Instrument | Use case |
|--------|-----------|----------|
| `xml` | Leica LMD | Laser microdissection |
| `csv` | MMI (Molecular Machines & Industries) | Laser microdissection |
| `mis` | Bruker flexImaging | MALDI imaging |

---

## Prerequisites

- **Docker** (recommended) — must be installed and running.
- **Python 3.11+** (optional, for local use) — install dependencies via `pip install -r requirements.txt`.

---

## 🏗️ 1. Building the Image

```bash
docker build -t shape2instrument:latest .
```

> The image is ~370 MB (slim Debian base, no OpenGL dependencies).

---

## 🚀 2. Running the Container

Mount your data directory so the container can read inputs and write results:

```bash
docker run --rm -v "${PWD}:/data" shape2instrument:latest [arguments]
```

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--mask` | Path to the input multi-label `.nrrd` image mask |
| `--output` | Output directory inside the mounted volume |
| `--format` | Target format: `xml`, `csv`, or `mis` |

### Conditionally Required Arguments

| Argument | Required for | Description |
|----------|-------------|-------------|
| `--mps` | `csv`, `xml` | Path to the `.mps` calibration points file (3-point set) |
| `--mis_template` | `mis` | Path to a template `.mis` file (Bruker slide optical mappings) |

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--cap_ids` | auto-generated | Comma-separated capture IDs, one per **unique label** in the mask |
| `--offset_x` | `0.0` | X offset |
| `--offset_y` | `0.0` | Y offset |
| `--scale` | `1.0` | Global scaling factor |
| `--invert_x` | `1.0` | X invert factor (`-1.0` to mirror) |
| `--invert_y` | `1.0` | Y invert factor (`-1.0` to mirror) |

---

## 🏷️ Capture IDs

Capture IDs label each segment group in the output. They work identically for both **xml** and **csv** formats.

### How it works

- **One ID per unique label** — the NRRD mask contains labeled regions (e.g., label 2 = tumor, label 3 = stroma). You supply one capture ID per unique label.
- **Auto-expansion** — if a single label produces multiple disconnected contours, all of them get the same capture ID.
- **Auto-generation** — if `--cap_ids` is omitted, IDs are generated automatically using the **96-well-plate naming convention**: `A1, B1, C1, ..., H1, A2, B2, ...`

### Examples

| Unique labels | `--cap_ids` | Result |
|:-------------:|-------------|--------|
| 1 | *(omitted)* | `A1` → all segments |
| 2 | *(omitted)* | `A1, B1` → one per label |
| 2 | `TUMOR,STROMA` | Custom names, one per label |
| 46 | *(omitted)* | `A1` through `H6` (wraps columns) |

### Output appearance

**XML** — each `<Shape_N>` contains a `<CapID>` element.

**CSV** — each segment group is labelled with `# Group: <cap_id>`:

```csv
# reference 0
1.1203,1.2922

# reference 1
43.7406,1.3146

# reference 2
43.6189,15.1379

# Group: A1
18.24,5.92
18.28,5.92
18.28,5.98
18.24,5.98

# Group: A1
18.20,5.00
18.24,5.00
```

---

## 📋 Examples

### A: Leica XML (with custom capture IDs)

```bash
docker run --rm \
  -v "${PWD}:/data" \
  shape2instrument:latest \
  --mask /data/01-labels.nrrd \
  --mps /data/pointset.mps \
  --output /data/results \
  --format xml \
  --cap_ids TUMOR,STROMA
```

### B: Leica XML (auto-generated IDs)

```bash
docker run --rm \
  -v "${PWD}:/data" \
  shape2instrument:latest \
  --mask /data/01-labels.nrrd \
  --mps /data/pointset.mps \
  --output /data/results \
  --format xml
```

### C: MMI CSV (with custom capture IDs)

```bash
docker run --rm \
  -v "${PWD}:/data" \
  shape2instrument:latest \
  --mask /data/01-labels.nrrd \
  --mps /data/pointset.mps \
  --output /data/results \
  --format csv \
  --cap_ids TUMOR,STROMA
```

### D: MMI CSV (auto-generated IDs)

```bash
docker run --rm \
  -v "${PWD}:/data" \
  shape2instrument:latest \
  --mask /data/01-labels.nrrd \
  --mps /data/pointset.mps \
  --output /data/results \
  --format csv
```

### E: Bruker flexImaging MIS

```bash
docker run --rm \
  -v "${PWD}:/data" \
  shape2instrument:latest \
  --mask /data/01-labels.nrrd \
  --mis_template "/data/Bruker_Slide_Template.mis" \
  --output /data/results \
  --format mis
```

---

## 🐍 Local Python Usage

```python
from main import extract_segments_from_nrrd, parse_mps_calibration
from shape2xml_v2 import shape2xml
from shape2csv_v2 import shape2csv

# 1. Extract segments from NRRD
segments, segment_labels, valid_labels = extract_segments_from_nrrd(
    "examples/01_tic_tenzl-labels.nrrd", physical_space=True
)

# 2. Parse calibration points
calib = parse_mps_calibration("examples/PointSet.mps")

# 3. Generate XML (auto-generated well-plate IDs)
shape2xml(segments, calibration_points=calib, folder_name="example_results")

# 4. Generate CSV (custom capture IDs)
shape2csv(segments, calib, capture_ids=["TUMOR", "STROMA"], folder_name="example_results")
```

---

## 📂 Project Structure

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point, argument parsing, segment extraction |
| `shape2xml_v2.py` | Leica XML export |
| `shape2csv_v2.py` | MMI CSV export |
| `mis_maker_class.py` | Bruker MIS export |
| `utils.py` | Shared utilities (e.g., well-plate ID generation) |
| `Dockerfile` | Container definition |
| `examples/` | Sample NRRD mask and MPS calibration |
| `example_results/` | Generated output files |
