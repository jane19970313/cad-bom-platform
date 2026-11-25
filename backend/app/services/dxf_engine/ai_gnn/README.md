# Relation-aware DXF heterogeneous GNN

This optional AI subsystem runs alongside the deterministic DXF engine. It does
not replace DXF parsing, geometry conversion, analytical measurement,
dimension extraction, topology, classification rules, or BOM generation.

## Architecture

The graph contains four node types:

- Geometry
- Dimension
- Anchor
- Text

The relation-aware model uses relation-specific message functions and
destination-normalized attention. Incoming messages compete through a
softmax over all incoming edges for each destination node. Stacked
heterogeneous message-passing layers support multi-hop paths such as
Dimension -> Anchor -> Geometry. Length and radius have direct and relation-aware branches, with the relation-aware
branch receiving the primary auxiliary weight. Area has no independent head:
it is derived from predicted radius for CIRCLE entities, or from corrected length
and the raw Shapely shape area/perimeter for other closed profiles.

The output includes geometry classification, predicted length/radius, an area
estimate derived from corrected length and raw shape scale, and text-link ranking
scores. Direct and relation branch outputs are reported for length/radius.

## Feature schema (version 8)

| Node | Feature dimension |
| --- | ---: |
| geometry | 45 |
| dimension | 17 |
| text | 47 |
| anchor | 12 |

Geometry features preserve position, bounds, vertex count, is_closed,
is_valid, geometry-type one-hot, entity-type hash, and a radius-availability
flag. The raw DXF radius is deliberately excluded from model inputs because
it is a possible radius target; this prevents target leakage. Analytical
length and area values are not concatenated into geometry-node inputs.

The v8 geometry vector retains raw Shapely shape descriptors: bounding-box
diagonal/aspect ratio, component and segment counts, dimensionless segment
fractions and variation, PCA principal-axis spans, hole counts and boundary
fractions, polygonal/circle/arc indicators, and perimeter/hole-data availability.
It deliberately excludes absolute perimeter, arc length, area, and radius values
from the learned geometry-node input.

Area itself and area-derived descriptors are excluded from geometry node
inputs. Text-to-geometry edge features also avoid area-derived circularity;
the former circularity slot is now a bounding-box-only shape proxy. The extractor does not read the source object's analytical length/area or raw
DXF radius. For polygonal
closed geometry, hole topology is extracted from polygon interior rings; for
closed LineStrings, a polygonal view is attempted only when valid.

Dimension features include endpoint-derived direction/span and explicit
validity flags for displayed and actual dimension values. Definition points
are used to associate ordinary linear/aligned dimensions with measured
geometry; endpoints remain an independent source of dimension-line direction.

Special dimension semantics are handled before generic linear attachment:
RADIUS and DIAMETRIC use center/measurement-point semantics, while ANGULAR
and ANGULAR_3P use their available definition points (or endpoint fallback).
This prevents special dimensions from being silently consumed by the generic
measured-point branch.

Dimension-to-geometry edges now carry dimension-kind flags, displayed and
actual value validity/value, and geometry circle/arc/closed applicability.
These features preserve the Dimension -> Anchor -> Geometry evidence path,
including special RADIUS and DIAMETRIC attachment semantics.

The geometry relation builder exposes independent `spatial_tolerance`,
`relation_search_tolerance`, `global_relation_max_neighbors`,
`text_candidate_search_tolerance`, `collinear_tolerance`, `mirror_tolerance`,
`connection_tolerance`, and `text_tolerance` controls. Equal-length and mirror candidates search beyond
the local topology radius, but the wider search is bounded by a nearest-neighbor
cap to limit expensive geometric comparisons. Curvature and tangent continuity are edge/anchor
evidence, not hard constraints. Mirror candidates search unoriented axes in
5-degree coarse increments over 180 degrees, followed by a 1-degree local
refinement; adjust `mirror_tolerance` separately from the collinearity
tolerance.

Geometry-to-geometry edge attributes include a validity indicator for
endpoint distance. Missing/non-finite values are not treated as trustworthy
zero measurements; downstream code can distinguish unavailable evidence.

## Text semantics and evidence (schema version 8)

Text remains a first-class node type. Every category (ANNOTATION,
TOLERANCE_GDT, DIMENSION_VALUE, PART_LABEL, GEOMETRY_DESCRIPTION, UNKNOWN)
has its own multi-hot text-node feature; mixed strings can activate more than
one category (for example, `开孔%%C650` activates both dimension-value and
geometry-description signals). The text vector no longer encodes only
PART_LABEL. The configurable
`text_semantics.json` file defines normalization substitutions, tokenization
settings, category patterns, diameter/radius parsing, and entity-type
compatibility. Edit this file for drawing-specific conventions; for example,
the sample `?10` to `I10` replacement is disabled by default. Enable it only
if that substitution is correct for your drawing convention.

The text categories are:

- `DIMENSION_VALUE`: diameter/radius/linear measurement strings.
- `PART_LABEL`: part names, section identifiers, and part numbers.
- `GEOMETRY_DESCRIPTION`: descriptions of geometric features.
- `ANNOTATION`: general notes and manufacturing/load instructions.
- `TOLERANCE_GDT`: tolerances and GD&T callouts.
- `UNKNOWN`: text that does not match any configured category.

Pure ANNOTATION-only text is preserved as a node without outgoing
text-to-dimension or text-to-geometry edges. Mixed-category strings can still
emit edges for their measurement or geometry-description signals; this avoids
discarding useful information merely because a string also contains a note.
The four category-specific geometry-link relation types are
`dimension_value_candidate`, `part_label_candidate`,
`geometry_description_candidate`, and `gdt_candidate`. A
`reviewed_match_candidate` relation is also available for explicitly reviewed
positive pairs whose category does not map to one of those four relations.

Text-to-geometry edge features combine three independent spatial measures (text
bounding-box to geometry bounding-box, text center to geometry, and text center
to geometry center), semantic compatibility, diameter/radius symbols and values,
geometry-type and entity-type indicators, closed-state, aspect ratio, bounding-box
span, a bbox-only shape proxy, and relative diameter/radius fit. The builder also inspects
existing Dimension -> Geometry measurement links (including the Dimension ->
Anchor -> Geometry path) and records whether a text diameter/radius value agrees
with a linked DIAMETRIC/RADIUS dimension. Candidate ranking uses a configurable
weighted combination of all three distances and semantic compatibility; a
nearby but semantically unsuitable geometry should not automatically win. A
candidate edge is evidence, not a verified text/geometry correspondence.

Chinese text uses jieba when installed. If it is unavailable, deterministic
Chinese character bigrams are used so graph generation does not require an
additional dependency. The JSON file includes editable rules for AutoCAD %%C,
%%D, and %%P symbols, mixed identifiers such as H294X200 and SJ-R-12000,
section-like labels such as 1#??, and optional OCR corrections such as ?10 ->
I10. OCR corrections that could change engineering meaning are disabled by
default and must be enabled only after checking the drawing convention. The
same file controls Chinese tokenization and candidate-ranking weights.

Geometry-to-geometry relations now use a separate `collinear_tolerance`,
plus tangent-continuity and curvature-similarity evidence. Mirror candidates
test multiple unoriented axes over the full 180-degree range, rather than
assuming only a vertical mirror. Curvature features are derived from
tessellated geometry; the raw DXF radius target is not copied into model
features.

Diameter/radius text and the existing Dimension -> Anchor -> Geometry paths
are both retained as evidence routes. A parsed diameter is not treated as a
verified radius/diameter target until a correspondence is reviewed.

## Measurement applicability and provenance

| Task | Validity rule |
| --- | --- |
| Length | Finite reviewed target; CIRCLE/ARC length is evaluated but not directly regressed when its sweep is available |
| Area | Closed CIRCLE (derived from radius), or other closed shape with usable raw Shapely area/perimeter |
| Radius | DXF entity_type is CIRCLE or ARC |

The raw DXF `radius` is kept separately as the supervised target and from
the independently calculated `radius_measured`. A missing value is represented by a numeric placeholder
plus a validity mask; the placeholder is never interpreted as a valid target.

For training labels, use reviewed ground truth in CSV/JSON keyed by DXF
`source_handle`. Radius labels should represent the raw CAD radius when that
is the desired prediction target. Do not copy analytic outputs into labels
without independent review.

Example CSV:

```csv
source_handle,label,length,area,radius
2A1,BEAM,1250.0,,
2A2,PLATE,,245000.0,
2A3,CIRCLE,,,25.0
```

Leave unavailable or inapplicable targets blank. The label builder masks area
for open geometry and radius for entities other than CIRCLE/ARC. CIRCLE and ARC
length targets remain available for validation, but their direct length loss is
masked: the model predicts radius and derives length deterministically. A circle
uses `L = 2*pi*r`; an arc uses `L = r*theta`, where `theta` is the DXF sweep angle
in radians. DXF start/end angles are read in degrees and converted to radians.
If those fields are unavailable, the graph builder estimates the sweep from the
ordered tessellated path around its center, then falls back to path-length/radius.
For non-circle/arc entities, length remains a learned regression target.

## Rebuild graphs and labels

Feature version 8 is incompatible with all earlier graph/checkpoint versions.
The current measurement derivation schema additionally requires
`circle_arc_length_from_predicted_radius_v1` metadata (including the per-entity
arc sweep angle). Rebuild semantic graphs, regenerate labeled graphs, and
retrain from scratch; old v8 graphs do not contain the sweep-angle metadata.
Rebuild every graph, regenerate labeled graphs, and retrain before inference.

```python
from app.services.dxf_engine.ai_gnn import build_semantic_graph
import torch

graph = build_semantic_graph(
    geometry_elements=geometry_elements,
    dimension_elements=dimension_elements,
    text_elements=text_elements,
    raw_entities=raw_entities,
    analytic_graph=analytic_graph,
    spatial_index=spatial_index,
    scale=scale,
    spatial_tolerance=300.0,
    relation_search_tolerance=1500.0,
    global_relation_max_neighbors=24,
    dimension_tolerance=2000.0,
    text_tolerance=300.0,
    text_candidate_search_tolerance=1500.0,
    collinear_tolerance=20.0,
    mirror_tolerance=5.0,
    text_config_path=None,  # defaults to ai_gnn/text_semantics.json
)
torch.save(graph, "graphs/drawing_001_v8.pt")
```

Attach labels:

```bash
python -m app.services.dxf_engine.ai_gnn.labels \
  --graph storage/training_graphs/drawing_001.pt \
  --labels storage/labels/labels_001.csv \
  --text-labels storage/labels/labels_text_001.csv \
  --classes storage/classes.json \
  --output storage/training_graphs/train_001.pt
```

### Reviewed text-to-geometry correspondence labels

The recommended workflow is positive-only: provide rows only for pairs that
you have confirmed are correct. Do not enumerate every other geometry as a
negative. Unlisted pairs remain unlabeled.

```csv
text_handle,geometry_handle,relation_type,is_match
T100,CIRCLE_01,dimension_value_candidate,1
T101,PLATE_03,part_label_candidate,1
```

The training objective uses a per-text listwise ranking loss: it increases the
score mass assigned to reviewed positive candidates relative to the available
candidate pool, with a small positive-attraction term so a reviewed pair still
receives a learning signal when it is the only available candidate. Unlabeled
candidates are ranking alternatives, not asserted ground-truth negatives.
Explicit `is_match=0` rows are accepted if you have high-confidence negative
reviews, but they are never required.

A reviewed positive pair that the spatial candidate generator omitted is
added as a `reviewed_match_candidate` (or its category-specific relation) so
the supervision is not silently dropped. This synthetic edge is marked as a
reviewed override and excluded from message passing; it is scored by the
matching head without leaking the target relationship into the GNN encoder.
The graph metadata reports how many positive edges were added and how many
label handles could not be found. In inference, matcher outputs are normalized
across each text node's candidate pool and exposed as ranking probabilities;
they are not calibrated binary probabilities.

## Train / validation / test

Split by complete drawings or projects, never by geometry rows from the same
drawing. Keep all split graph files disjoint.

```bash
python -m app.services.dxf_engine.ai_gnn.train \
  --train-graphs storage/training_graphs/train_001.pt storage/training_graphs/train_002.pt \
  --val-graphs storage/training_graphs/validation_001.pt \
  --test-graphs storage/training_graphs/test_001.pt \
  --classes storage/classes.json \
  --output storage/models/dxf_relation_aware_gnn_v8.pt \
  --epochs 500 --patience 25 --checkpoint-every 100
```

Training checkpoints are written under `models/checkpoints_relation_aware_gnn_v8/`:

- `checkpoint_epoch_0100.pt`, `checkpoint_epoch_0200.pt`, etc. retain
  numbered snapshots every 100 completed epochs.
- `checkpoint_latest.pt` is atomically replaced with the newest resumable
  snapshot.
- The final `dxf_relation_aware_gnn_v8.pt` remains the best-validation model
  intended for inference; it is not the same thing as the latest training
  snapshot.

To resume after an interruption, keep the same graph splits, class mapping,
and model configuration, then pass the latest checkpoint. The `--epochs`
value is the desired total epoch count, not the number of additional epochs:

```bash
python -m app.services.dxf_engine.ai_gnn.train \
  --train-graphs storage/training_graphs/train_001.pt storage/training_graphs/train_002.pt \
  --val-graphs storage/training_graphs/validation_001.pt \
  --test-graphs storage/training_graphs/test_001.pt \
  --classes storage/classes.json \
  --output storage/models/dxf_relation_aware_gnn_v8.pt \
  --epochs 500 --patience 25 --checkpoint-every 100 \
  --resume-from storage/models/checkpoints/checkpoint_latest.pt
```

A resumable snapshot stores model weights, optimizer state, best-validation
weights/score, early-stopping counter, and random-number-generator state.
Resume validation rejects mismatched graph splits, feature dimensions, class
mapping, or model architecture settings rather than silently continuing an
incompatible run. The periodic checkpoint is a training-resume artifact;
use the final best-validation model file for inference.

Length and radius supervise the fused estimate; their direct geometry-only
branch is a weak auxiliary, while the relation-aware branch receives a stronger
auxiliary loss. Area has no direct regression head and contributes loss only
through its derived estimate. The default regression task weights are equal
(length=1, area=1, radius=1).

Checkpoint selection is regression-first. For each available target, the
validation MAE in original drawing units is divided by that target's median
value in the training split. The three normalized MAEs are then averaged with
equal task weight. This keeps length, area, and radius comparable despite
their different units and numerical scales. `val_total_loss` is still printed
as a diagnostic and still includes classification/text-link losses, so it may
rise while regression quality improves; it no longer chooses the best model
or controls early stopping. The selected score and per-target normalized MAEs
are printed as `val_regression_score` and `val_*_nMAE`. The test split is
evaluated only after selection.

## Inference

```python
from app.services.dxf_engine.ai_gnn.inference import predict_geometry

predictions = predict_geometry(
    graph,
    "models/dxf_relation_aware_gnn_v8.pt",
)
```

Each prediction exposes:

- `predicted_length`, `predicted_area`, `predicted_radius`
- `predicted_length_source` and `central_angle_rad` (for ARC/CIRCLE)
- `direct_measurements` and `relation_measurements`
- `fusion_weights` (weight assigned to the direct branch)
- `measurement_validity`
- `raw_dxf_radius` and `analytic_radius`
- associated dimension, anchor, and text candidates
- text-candidate spatial distances, semantic compatibility, geometry/entity
  type indicators, shape descriptors, and linked DIAMETRIC/RADIUS dimension
  agreement evidence

Area is returned as `None` unless the closed raw shape has a usable area and
perimeter; radius is returned as `None` for non-CIRCLE/ARC entities. For CIRCLE,
`L_pred = 2πr_pred` and `A_pred = πr_pred²`. For ARC,
`L_pred = r_pred * θ` when the sweep angle is available. For other closed profiles,
`A_pred = A_raw * (L_pred / P_raw)^2`. The latter assumes the corrected length
target represents boundary perimeter and the correction is approximately
uniform scaling; it is not a general reconstruction of arbitrary polygon
deformation. Candidate relations remain evidence, not verified engineering
constraints.

## Engineering limitations and next validation

The present relation matcher uses edge-conditioned attention to score and
aggregate candidate relationships. It is not yet a separately supervised
dimension-to-geometry correspondence classifier. Equal-length and mirrored
shape edges are geometric candidates, not hard constraints. Part-to-whole
sums, area composition, and exact Pythagorean equations are not yet solved
as explicit constraint systems; add these only with independently validated
evidence and provenance. Fusion weights are learned weights, not calibrated
probabilities.

Before production BOM use, evaluate by held-out drawings from different
projects, units, CAD conventions, and dimension styles. Report per-task MAE,
coverage, applicability-mask counts, and text-link top-1 / hit@5 ranking metrics. A plausible prediction alone is not proof of correctness.

### Tests

The uploaded archive does not include the host application's backend test
suite. Run the backend's existing DXF/AI-GNN tests after replacing these
modules; add v8 expectations for the 47-value text vector and 39-value
text-to-geometry edge features.

## Geometry feature schema v8

The geometry node has 45 inputs: the preserved 24-value v6 prefix plus 21
versioned descriptors from `geometry_features.py`. The 21-value suffix is
ordered by `GEOMETRY_FEATURE_NAMES`; its final flags identify whether
perimeter and interior-ring information are available. Unavailable values
use numeric placeholders only alongside these validity flags.

Rebuild every graph, reattach reviewed labels, and retrain from scratch.
Earlier checkpoints cannot be used with v8 graphs. Existing graph and
checkpoint files remain historical artifacts and are not migrated in place.
