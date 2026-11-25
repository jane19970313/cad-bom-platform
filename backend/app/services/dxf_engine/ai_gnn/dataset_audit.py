from __future__ import annotations

"""
Audit saved v6 DXF semantic-graph training files before training.

What this script checks
-----------------------
1. Graph/node/edge counts and feature schema compatibility.
2. Geometry class-label distribution and majority-class baseline.
3. Reviewed length/area/radius target counts and distributions.
4. Decoded target values in drawing units (labels.py stores log1p(value)).
5. Text-to-geometry candidate edges and reviewed positive/negative labels.
6. Graph metadata, scale-related fields, feature ranges, non-finite values.
7. Simple per-feature Pearson correlations with decoded regression targets.

Run from the backend directory:
    python -m app.services.dxf_engine.ai_gnn.dataset_audit

Or specify files:
    python -m app.services.dxf_engine.ai_gnn.dataset_audit \
        --graphs storage/training_graphs/train_001.pt \
                 storage/training_graphs/train_002.pt \
                 storage/training_graphs/validation_001.pt \
                 storage/training_graphs/test_001.pt \
        --classes storage/classes.json \
        --json-out storage/reports/dataset_audit.json

This is a read-only audit. It does not modify graph files or model checkpoints.
"""

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import torch


DEFAULT_GRAPHS = [
    "storage/training_graphs/train_001.pt",
    "storage/training_graphs/train_002.pt",
    "storage/training_graphs/validation_001.pt",
    "storage/training_graphs/test_001.pt",
]
REGRESSION_TARGETS = ("length", "area", "radius")
TEXT_GEOMETRY_RELATIONS = {
    "dimension_value_candidate",
    "part_label_candidate",
    "geometry_description_candidate",
    "gdt_candidate",
    "reviewed_match_candidate",
}


def _plain(value: Any) -> Any:
    """Convert common PyTorch/Python values to JSON-safe values."""
    if isinstance(value, torch.Tensor):
        if value.numel() == 1:
            return value.detach().cpu().item()
        return value.detach().cpu().tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, float) and not math.isfinite(value):
            return str(value)
        return value
    return str(value)


def _tensor_1d(value: Any) -> torch.Tensor | None:
    if not isinstance(value, torch.Tensor):
        try:
            value = torch.as_tensor(value)
        except Exception:
            return None
    if value.numel() == 0:
        return value.detach().cpu().reshape(-1)
    return value.detach().cpu().reshape(-1)


def _finite_values(value: Any) -> torch.Tensor:
    tensor = _tensor_1d(value)
    if tensor is None or tensor.numel() == 0:
        return torch.empty(0, dtype=torch.float64)
    try:
        tensor = tensor.to(torch.float64)
    except (TypeError, RuntimeError):
        return torch.empty(0, dtype=torch.float64)
    return tensor[torch.isfinite(tensor)]


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    ordered = sorted(float(v) for v in values)
    n = len(ordered)

    def percentile(p: float) -> float:
        if n == 1:
            return ordered[0]
        position = (n - 1) * p
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered[lower]
        fraction = position - lower
        return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction

    return {
        "count": n,
        "min": ordered[0],
        "p05": percentile(0.05),
        "p25": percentile(0.25),
        "median": percentile(0.50),
        "mean": statistics.fmean(ordered),
        "p75": percentile(0.75),
        "p95": percentile(0.95),
        "max": ordered[-1],
        "std": statistics.pstdev(ordered) if n > 1 else 0.0,
    }


def _get_store(data: Any, node_type: str):
    try:
        return data[node_type]
    except Exception:
        return None


def _store_num_nodes(store: Any) -> int:
    if store is None:
        return 0
    try:
        return int(store.num_nodes)
    except Exception:
        pass
    for key in ("x", "source_handle", "element_id"):
        value = getattr(store, key, None)
        if value is not None:
            try:
                return len(value)
            except TypeError:
                pass
    return 0


def _graph_metadata(data: Any) -> dict[str, Any]:
    metadata = getattr(data, "graph_metadata", {})
    if isinstance(metadata, dict):
        return metadata
    return {}


def _find_scale_values(value: Any, prefix: str = "") -> dict[str, Any]:
    found: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if "scale" in str(key).lower():
                found[path] = _plain(child)
            found.update(_find_scale_values(child, path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found.update(_find_scale_values(child, f"{prefix}[{index}]"))
    return found


def _class_mapping(path: str | None) -> dict[int, str]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Class mapping must be a JSON object: {path}")
    return {int(class_id): str(name) for name, class_id in payload.items()}


def _feature_summary(x: Any) -> dict[str, Any] | None:
    if not isinstance(x, torch.Tensor) or x.ndim != 2:
        return None
    values = x.detach().cpu().to(torch.float64)
    finite_mask = torch.isfinite(values)
    result = {
        "shape": list(values.shape),
        "non_finite_count": int((~finite_mask).sum().item()),
        "columns": [],
    }
    for column in range(values.size(1)):
        col = values[:, column]
        finite = col[torch.isfinite(col)]
        if finite.numel():
            result["columns"].append({
                "index": column,
                "min": float(finite.min()),
                "max": float(finite.max()),
                "mean": float(finite.mean()),
                "std": float(finite.std(unbiased=False)) if finite.numel() > 1 else 0.0,
            })
        else:
            result["columns"].append({
                "index": column, "min": None, "max": None,
                "mean": None, "std": None,
            })
    return result


def _target_summary(store: Any, name: str) -> dict[str, Any]:
    mask = getattr(store, f"{name}_mask", None)
    target = getattr(store, f"{name}_y", None)
    if mask is None or target is None:
        return {
            "label_count": 0,
            "mask_present": mask is not None,
            "target_present": target is not None,
            "encoded_log1p": {"count": 0},
            "decoded_value": {"count": 0},
            "invalid_masked_values": 0,
        }

    mask_tensor = _tensor_1d(mask)
    target_tensor = _tensor_1d(target)
    if mask_tensor is None or target_tensor is None:
        return {"label_count": 0, "error": "Mask/target could not be converted to tensors"}

    mask_tensor = mask_tensor.bool()
    target_tensor = target_tensor.to(torch.float64)
    length = min(mask_tensor.numel(), target_tensor.numel())
    mask_tensor = mask_tensor[:length]
    target_tensor = target_tensor[:length]
    selected = target_tensor[mask_tensor]
    finite_mask = torch.isfinite(selected)
    finite_selected = selected[finite_mask]
    decoded = torch.expm1(finite_selected.clamp(min=0.0, max=30.0))
    invalid = int((~finite_mask).sum().item())

    return {
        "label_count": int(mask_tensor.sum().item()),
        "mask_present": True,
        "target_present": True,
        "encoded_log1p": _distribution(finite_selected.tolist()),
        "decoded_value": _distribution(decoded.tolist()),
        "invalid_masked_values": invalid,
        "masked_target_count": int(mask_tensor.sum().item()),
        "target_tensor_length": int(target_tensor.numel()),
    }


def _class_summary(store: Any, class_names: dict[int, str]) -> dict[str, Any]:
    y = getattr(store, "y", None)
    mask = getattr(store, "class_mask", getattr(store, "train_mask", None))
    if y is None or mask is None:
        return {"label_count": 0, "class_counts": {}}
    y_tensor = _tensor_1d(y)
    mask_tensor = _tensor_1d(mask)
    if y_tensor is None or mask_tensor is None:
        return {"label_count": 0, "class_counts": {}}
    length = min(y_tensor.numel(), mask_tensor.numel())
    selected = y_tensor[:length][mask_tensor[:length].bool()].to(torch.long)
    counts = Counter(int(v) for v in selected.tolist())
    total = sum(counts.values())
    majority = max(counts.values()) if counts else 0
    return {
        "label_count": total,
        "class_counts": {
            str(class_id): {
                "name": class_names.get(class_id, "UNKNOWN"),
                "count": count,
                "fraction": count / total if total else None,
            }
            for class_id, count in sorted(counts.items())
        },
        "majority_class_baseline_accuracy": majority / total if total else None,
    }


def _text_link_summary(data: Any) -> dict[str, Any]:
    relation_rows = {}
    total_candidates = total_labeled = positives = negatives = 0
    for edge_type in getattr(data, "edge_types", []):
        source, relation, target = edge_type
        if source != "text" or target != "geometry" or relation not in TEXT_GEOMETRY_RELATIONS:
            continue
        store = data[edge_type]
        edge_index = getattr(store, "edge_index", None)
        candidate_count = int(edge_index.size(1)) if isinstance(edge_index, torch.Tensor) else 0
        mask = getattr(store, "match_mask", None)
        labels = getattr(store, "match_y", None)
        labeled_count = positive_count = negative_count = 0
        if mask is not None and labels is not None:
            mask_tensor = _tensor_1d(mask)
            label_tensor = _tensor_1d(labels)
            if mask_tensor is not None and label_tensor is not None:
                length = min(mask_tensor.numel(), label_tensor.numel())
                selected_mask = mask_tensor[:length].bool()
                selected_labels = label_tensor[:length][selected_mask]
                labeled_count = int(selected_mask.sum().item())
                positive_count = int((selected_labels >= 0.5).sum().item())
                negative_count = int((selected_labels < 0.5).sum().item())
        relation_rows[relation] = {
            "candidate_edges": candidate_count,
            "labeled_edges": labeled_count,
            "positive_labels": positive_count,
            "negative_labels": negative_count,
            "unlabeled_candidate_edges": max(0, candidate_count - labeled_count),
        }
        total_candidates += candidate_count
        total_labeled += labeled_count
        positives += positive_count
        negatives += negative_count

    return {
        "relations": relation_rows,
        "candidate_edges": total_candidates,
        "labeled_edges": total_labeled,
        "positive_labels": positives,
        "negative_labels": negatives,
        "unlabeled_candidate_edges": max(0, total_candidates - total_labeled),
        "supervision_available": total_labeled > 0,
    }


def _geometry_metadata_summary(store: Any) -> dict[str, Any]:
    if store is None:
        return {}
    result = {}
    for field in ("entity_type", "is_closed", "is_valid"):
        values = getattr(store, field, None)
        if values is None:
            continue
        if isinstance(values, torch.Tensor):
            values = values.detach().cpu().tolist()
        counts = Counter(str(value) for value in values)
        result[field] = dict(sorted(counts.items()))
    return result


def _pearson(x: torch.Tensor, y: torch.Tensor) -> float | None:
    if x.numel() < 3 or y.numel() != x.numel():
        return None
    x = x.to(torch.float64)
    y = y.to(torch.float64)
    x = x - x.mean()
    y = y - y.mean()
    denominator = torch.sqrt((x.square().sum()) * (y.square().sum()))
    if not torch.isfinite(denominator) or denominator <= 1e-12:
        return None
    value = (x * y).sum() / denominator
    return float(value) if torch.isfinite(value) else None


def _feature_target_correlations(store: Any) -> dict[str, Any]:
    x = getattr(store, "x", None)
    if not isinstance(x, torch.Tensor) or x.ndim != 2:
        return {}
    result = {}
    for name in REGRESSION_TARGETS:
        mask = getattr(store, f"{name}_mask", None)
        target = getattr(store, f"{name}_y", None)
        if mask is None or target is None:
            continue
        mask = _tensor_1d(mask)
        target = _tensor_1d(target)
        if mask is None or target is None:
            continue
        n = min(x.size(0), mask.numel(), target.numel())
        selected = mask[:n].bool() & torch.isfinite(target[:n])
        if int(selected.sum()) < 3:
            result[name] = {"valid_pairs": int(selected.sum()), "top_abs_correlations": []}
            continue
        features = x[:n][selected].detach().cpu().to(torch.float64)
        targets = target[:n][selected].detach().cpu().to(torch.float64)
        rows = []
        for column in range(features.size(1)):
            corr = _pearson(features[:, column], targets)
            if corr is not None:
                rows.append({"feature_index": column, "pearson_r": corr})
        rows.sort(key=lambda row: abs(row["pearson_r"]), reverse=True)
        result[name] = {
            "valid_pairs": int(selected.sum()),
            "target_used": "encoded_log1p",
            "top_abs_correlations": rows[:8],
        }
    return result


def audit_graph(path: str, class_names: dict[int, str]) -> dict[str, Any]:
    graph_path = Path(path)
    if not graph_path.is_file():
        raise FileNotFoundError(f"Graph file does not exist: {graph_path}")

    data = torch.load(graph_path, map_location="cpu", weights_only=False)
    metadata = _graph_metadata(data)
    node_types = list(getattr(data, "node_types", []))
    edge_types = list(getattr(data, "edge_types", []))

    node_summary = {}
    total_nodes = 0
    for node_type in node_types:
        store = _get_store(data, node_type)
        count = _store_num_nodes(store)
        total_nodes += count
        feature_summary = _feature_summary(getattr(store, "x", None))
        if node_type == "geometry" and feature_summary is not None:
            feature_names = metadata.get("geometry_feature_names", [])
            for index, name in enumerate(feature_names):
                if index < len(feature_summary["columns"]):
                    feature_summary["columns"][index]["name"] = str(name)
        node_summary[node_type] = {
            "count": count,
            "feature_summary": feature_summary,
        }

    edge_summary = {}
    total_edges = 0
    for edge_type in edge_types:
        store = data[edge_type]
        edge_index = getattr(store, "edge_index", None)
        count = int(edge_index.size(1)) if isinstance(edge_index, torch.Tensor) else 0
        total_edges += count
        edge_attr = getattr(store, "edge_attr", None)
        edge_summary["|".join(edge_type)] = {
            "count": count,
            "edge_feature_dim": (
                int(edge_attr.size(-1))
                if isinstance(edge_attr, torch.Tensor) and edge_attr.ndim > 1
                else None
            ),
            "edge_feature_non_finite_count": (
                int((~torch.isfinite(edge_attr)).sum().item())
                if isinstance(edge_attr, torch.Tensor) and edge_attr.is_floating_point()
                else 0
            ),
        }

    geometry = _get_store(data, "geometry")
    targets = {
        name: _target_summary(geometry, name)
        for name in REGRESSION_TARGETS
    } if geometry is not None else {}
    classes = _class_summary(geometry, class_names) if geometry is not None else {}
    text_links = _text_link_summary(data)

    return {
        "file": str(graph_path),
        "file_size_bytes": graph_path.stat().st_size,
        "feature_version": metadata.get("feature_version"),
        "geometry_feature_schema": metadata.get("geometry_feature_schema"),
        "geometry_feature_names": _plain(metadata.get("geometry_feature_names", [])),
        "target_encoding": metadata.get("target_encoding"),
        "target_validity": _plain(metadata.get("target_validity", {})),
        "target_provenance": metadata.get("target_provenance"),
        "graph_metadata": _plain(metadata),
        "scale_related_metadata": _find_scale_values(metadata),
        "node_types": node_types,
        "edge_types": ["|".join(edge_type) for edge_type in edge_types],
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "nodes": node_summary,
        "edges": edge_summary,
        "geometry_entity_summary": _geometry_metadata_summary(geometry),
        "classification": classes,
        "regression_targets": targets,
        "text_geometry_supervision": text_links,
        "feature_target_correlations": (
            _feature_target_correlations(geometry) if geometry is not None else {}
        ),
    }


def _aggregate(graph_reports: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "graphs": len(graph_reports),
        "nodes": sum(report["total_nodes"] for report in graph_reports),
        "edges": sum(report["total_edges"] for report in graph_reports),
    }
    target_totals = {}
    for name in REGRESSION_TARGETS:
        decoded_values = []
        encoded_values = []
        for report in graph_reports:
            target = report["regression_targets"].get(name, {})
            # Reconstruct aggregate distributions from per-graph quantiles is
            # not statistically sound, so aggregate only counts here.
            target_totals[name] = target_totals.get(name, 0) + int(target.get("label_count", 0))
            decoded = target.get("decoded_value", {})
            encoded = target.get("encoded_log1p", {})
            if decoded.get("count"):
                decoded_values.append(decoded)
            if encoded.get("count"):
                encoded_values.append(encoded)
    class_counts = Counter()
    for report in graph_reports:
        for class_id, record in report.get("classification", {}).get("class_counts", {}).items():
            class_counts[class_id] += int(record["count"])
    total_class_labels = sum(class_counts.values())
    majority = max(class_counts.values()) if class_counts else 0

    text = {
        key: sum(int(report["text_geometry_supervision"].get(key, 0)) for report in graph_reports)
        for key in (
            "candidate_edges", "labeled_edges", "positive_labels",
            "negative_labels", "unlabeled_candidate_edges",
        )
    }
    return {
        **totals,
        "regression_label_counts": target_totals,
        "classification_label_count": total_class_labels,
        "classification_class_counts": dict(class_counts),
        "majority_class_baseline_accuracy": (
            majority / total_class_labels if total_class_labels else None
        ),
        "text_geometry_supervision": {
            **text,
            "supervision_available": text["labeled_edges"] > 0,
        },
        "note": (
            "Per-graph target distributions are shown separately. "
            "Do not average per-graph medians/quantiles to estimate a dataset-wide distribution."
        ),
    }


def _print_distribution(title: str, summary: dict[str, Any], indent: str = "    ") -> None:
    if not summary or not summary.get("count"):
        print(f"{indent}{title:<12}: no valid labels")
        return
    print(
        f"{indent}{title:<12}: n={summary['count']:<5} "
        f"min={summary['min']:.6g} p50={summary['median']:.6g} "
        f"mean={summary['mean']:.6g} p95={summary['p95']:.6g} "
        f"max={summary['max']:.6g}"
    )


def print_report(report: dict[str, Any]) -> None:
    print("\n" + "=" * 88)
    print(f"GRAPH: {report['file']}")
    print("=" * 88)
    print(
        f"feature_version={report['feature_version']} "
        f"target_encoding={report['target_encoding']} "
        f"nodes={report['total_nodes']} edges={report['total_edges']} "
        f"size={report['file_size_bytes']:,} bytes"
    )
    print("Node counts:")
    for node_type, item in report["nodes"].items():
        feature = item.get("feature_summary") or {}
        shape = feature.get("shape")
        non_finite = feature.get("non_finite_count", 0)
        print(f"  {node_type:<12} {item['count']:>8,} nodes  x_shape={shape} non_finite={non_finite}")
    print("Geometry classes:")
    print(f"  labeled={report['classification'].get('label_count', 0)} "
          f"majority_baseline={report['classification'].get('majority_class_baseline_accuracy')}")
    for class_id, record in report["classification"].get("class_counts", {}).items():
        print(f"  {record['name']:<24} id={class_id:<4} count={record['count']}")
    print("Regression targets (decoded with expm1; drawing units):")
    for name in REGRESSION_TARGETS:
        item = report["regression_targets"].get(name, {})
        print(f"  {name}: labels={item.get('label_count', 0)} "
              f"invalid_masked={item.get('invalid_masked_values', 0)}")
        _print_distribution("decoded", item.get("decoded_value", {}), "      ")
        _print_distribution("log1p", item.get("encoded_log1p", {}), "      ")
    text = report["text_geometry_supervision"]
    print(
        "Text→Geometry: "
        f"candidates={text['candidate_edges']} labeled={text['labeled_edges']} "
        f"positive={text['positive_labels']} negative={text['negative_labels']} "
        f"unlabeled={text['unlabeled_candidate_edges']}"
    )
    print("Geometry entity types:", report.get("geometry_entity_summary", {}).get("entity_type", {}))
    print("Scale-related metadata:", report.get("scale_related_metadata", {}))
    print("Feature/target correlations (encoded log1p target; top |r|):")
    for name, item in report.get("feature_target_correlations", {}).items():
        print(f"  {name}: pairs={item.get('valid_pairs', 0)} {item.get('top_abs_correlations', [])[:5]}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit saved DXF semantic GNN graph files without modifying them."
    )
    parser.add_argument(
        "--graphs", nargs="+", default=DEFAULT_GRAPHS,
        help="One or more serialized PyTorch Geometric graph files.",
    )
    parser.add_argument(
        "--classes", default="storage/classes.json",
        help="Optional classes.json mapping class name to ID. Use an empty string to skip.",
    )
    parser.add_argument(
        "--json-out", default=None,
        help="Optional path to save the complete audit as JSON.",
    )
    args = parser.parse_args()

    class_path = args.classes if args.classes else None
    class_names = _class_mapping(class_path) if class_path and Path(class_path).exists() else {}
    reports = []
    errors = []

    print("DXF SEMANTIC GNN DATASET AUDIT")
    print(f"Graphs requested: {len(args.graphs)}")
    print(f"Class mapping: {class_path if class_names else 'not loaded'}")

    for graph_path in args.graphs:
        try:
            report = audit_graph(graph_path, class_names)
            reports.append(report)
            print_report(report)
        except Exception as exc:
            errors.append({"file": graph_path, "error": f"{type(exc).__name__}: {exc}"})
            print(f"\n[ERROR] {graph_path}: {type(exc).__name__}: {exc}")

    aggregate = _aggregate(reports)
    print("\n" + "=" * 88)
    print("DATASET SUMMARY")
    print("=" * 88)
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    if errors:
        print("\nFILES WITH ERRORS:")
        print(json.dumps(errors, ensure_ascii=False, indent=2))

    payload = {
        "dataset_summary": aggregate,
        "graphs": reports,
        "errors": errors,
    }
    if args.json_out:
        output_path = Path(args.json_out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n[JSON REPORT SAVED] {output_path.resolve()}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
