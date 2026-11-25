from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import torch
import torch.nn.functional as F

from .geometry_features import GEOMETRY_FEATURE_NAMES
from .graph_builder import TEXT_FEATURE_NAMES
from .model import DXFSemanticGNN


REGRESSION_TARGETS = ("length", "area", "radius")


def _input_dims(data):
    return {node_type: int(data[node_type].x.size(-1)) for node_type in data.node_types}


def _edge_dims(data):
    return {
        "|".join(edge_type): int(data[edge_type].edge_attr.size(-1))
        for edge_type in data.edge_types
    }


def _load_graphs(paths):
    graphs = []
    for path in paths:
        data = torch.load(path, map_location="cpu", weights_only=False)
        if (data.graph_metadata.get("feature_version") != 8
                or data.graph_metadata.get("measurement_derivation_schema") != "circle_arc_length_from_predicted_radius_v1"
                or data.graph_metadata.get("geometry_feature_schema") != "dxf_geometry_shape_v8"
                or data.graph_metadata.get("geometry_feature_names") != list(GEOMETRY_FEATURE_NAMES)
                or data.graph_metadata.get("geometry_feature_dimension") != 24 + len(GEOMETRY_FEATURE_NAMES)
                or data["geometry"].x.size(-1) != 24 + len(GEOMETRY_FEATURE_NAMES)
                or data["text"].x.size(-1) != len(TEXT_FEATURE_NAMES)
                or data.graph_metadata.get("text_feature_schema") != list(TEXT_FEATURE_NAMES)):
            raise ValueError(
                f"{path}: expected v8 graph with circle/arc deterministic-length metadata; rebuild this graph."
            )
        sweep_angles = getattr(data["geometry"], "arc_sweep_angle_rad", None)
        if sweep_angles is None or len(sweep_angles) != data["geometry"].x.size(0):
            raise ValueError(
                f"{path}: missing per-geometry arc_sweep_angle_rad metadata; rebuild this graph."
            )
        graphs.append((str(path), data))
    return graphs


def _validate_graph_compatibility(graphs, input_dims, edge_dims):
    for path, data in graphs:
        if _input_dims(data) != input_dims:
            raise ValueError(f"{path}: node feature dimensions differ from training graph.")
        if _edge_dims(data) != edge_dims:
            raise ValueError(f"{path}: relation/edge feature schema differs from training graph.")


def _has_supervision(data):
    return bool(_supervised_tasks(data))


def _supervised_tasks(data):
    geometry = data["geometry"]
    tasks = set()
    class_mask = getattr(geometry, "class_mask", None)
    if class_mask is not None and bool(class_mask.any()):
        tasks.add("classification")
    for name in REGRESSION_TARGETS:
        mask = getattr(geometry, f"{name}_mask", None)
        if mask is not None and bool(mask.any()):
            tasks.add(name)
    for edge_type in data.edge_types:
        if edge_type[0] == "text" and edge_type[2] == "geometry":
            match_mask = getattr(data[edge_type], "match_mask", None)
            if match_mask is not None and bool(match_mask.any()):
                tasks.add("text_geometry_matching")
                break
    return tasks


def _split_tasks(graphs):
    tasks = set()
    for _, data in graphs:
        tasks.update(_supervised_tasks(data))
    return tasks


def _compute_regression_scales(graphs):
    """Compute robust target scales from TRAIN graphs only.

    The validation selection score uses MAE / median(target) per task, so
    length, area, and radius contribute on comparable, dimensionless scales.
    Targets are stored as log1p values in the graph files.
    """
    scales = {}
    for name in REGRESSION_TARGETS:
        values = []
        for _, data in graphs:
            geometry = data["geometry"]
            mask = getattr(geometry, f"{name}_mask", None)
            target = getattr(geometry, f"{name}_y", None)
            if mask is None or target is None or not bool(mask.any()):
                continue
            raw = torch.expm1(target[mask].detach().float().clamp(min=0.0, max=30.0))
            raw = raw[torch.isfinite(raw) & (raw > 0)]
            if raw.numel():
                values.append(raw.cpu())
        if values:
            median = float(torch.cat(values).median().item())
            scales[name] = max(median, 1.0)
        else:
            scales[name] = 1.0
    return scales


def _loss_for_graph(logits, measurement_log, evidence, data, class_weight=1.0,
                    regression_weights=None):
    regression_weights = regression_weights or {
        "length": 1.0, "area": 1.0, "radius": 1.0
    }
    geometry = data["geometry"]
    losses = []
    details = {}

    class_mask = getattr(geometry, "class_mask", None)
    if class_mask is not None and bool(class_mask.any()):
        class_loss = F.cross_entropy(logits[class_mask], geometry.y[class_mask])
        losses.append(class_weight * class_loss)
        details["classification"] = class_loss.detach()

    for column, name in enumerate(REGRESSION_TARGETS):
        mask = getattr(geometry, f"{name}_mask", None)
        target = getattr(geometry, f"{name}_y", None)
        if mask is None or target is None or not bool(mask.any()):
            continue
        # For CIRCLE/ARC, the length output is derived from predicted radius.
        # Keep reviewed length targets in the loss: their gradient flows through
        # L=2*pi*r or L=r*theta into the radius prediction, not a length head.
        prediction = measurement_log[mask, column]
        task_loss = F.smooth_l1_loss(prediction, target[mask])
        weight = float(regression_weights.get(name, 1.0))
        if name in {"length", "radius"}:
            # Relationship-aware estimate is the primary objective. The
            # geometry-only branch remains a weak auxiliary baseline.
            direct_loss = F.smooth_l1_loss(
                evidence["direct_log"][mask, column], target[mask]
            )
            relation_loss = F.smooth_l1_loss(
                evidence["relation_log"][mask, column], target[mask]
            )
            losses.append(weight * (task_loss + 0.05 * direct_loss + 0.20 * relation_loss))
            details[f"{name}_direct_aux"] = direct_loss.detach()
            details[f"{name}_relation_aux"] = relation_loss.detach()
        else:
            # Area is derived from corrected length and raw Shapely shape scale;
            # it has no independent regression head or direct-area auxiliary.
            losses.append(weight * task_loss)
        details[name] = task_loss.detach()

    # Positive-only text/geometry supervision:
    # for each text with reviewed positive pairs, maximize the probability mass
    # assigned to its positive candidate(s) among all generated candidates.
    # Unreviewed pairs are ranking alternatives, NOT ground-truth negatives.
    all_match_logits = []
    all_text_indices = []
    all_match_targets = []
    all_match_masks = []
    for edge_type, match_logits in evidence.get("text_match_logits", {}).items():
        store = data[edge_type]
        edge_index = store.edge_index
        if edge_index.numel() == 0:
            continue
        all_match_logits.append(match_logits)
        all_text_indices.append(edge_index[0])
        all_match_targets.append(getattr(
            store, "match_y",
            torch.zeros(edge_index.size(1), dtype=match_logits.dtype, device=match_logits.device),
        ))
        all_match_masks.append(getattr(
            store, "match_mask",
            torch.zeros(edge_index.size(1), dtype=torch.bool, device=match_logits.device),
        ))

    if all_match_logits:
        candidate_logits = torch.cat(all_match_logits)
        candidate_text_indices = torch.cat(all_text_indices)
        candidate_targets = torch.cat(all_match_targets)
        candidate_masks = torch.cat(all_match_masks)
        positive_mask = candidate_masks & (candidate_targets > 0.5)
        ranking_losses = []
        for text_index in torch.unique(candidate_text_indices[positive_mask]).tolist():
            group = candidate_text_indices == int(text_index)
            positives = group & positive_mask
            if not bool(positives.any()):
                continue
            ranking_losses.append(
                torch.logsumexp(candidate_logits[group], dim=0)
                - torch.logsumexp(candidate_logits[positives], dim=0)
            )
        if ranking_losses:
            ranking_loss = torch.stack(ranking_losses).mean()
            positive_alignment = F.softplus(-candidate_logits[positive_mask]).mean()
            # Ranking is primary; a small positive attraction term still
            # provides a gradient when a reviewed pair is the only candidate.
            match_loss = ranking_loss + 0.10 * positive_alignment
            losses.append(1.0 * match_loss)
            details["text_geometry_positive_ranking"] = ranking_loss.detach()
            details["text_geometry_positive_alignment"] = positive_alignment.detach()

        # Explicitly reviewed negatives, if supplied, are used as such. No
        # unlabeled candidate is ever converted into a negative target.
        explicit_negative = candidate_masks & (candidate_targets <= 0.5)
        if bool(explicit_negative.any()):
            negative_loss = F.softplus(candidate_logits[explicit_negative]).mean()
            losses.append(0.25 * negative_loss)
            details["text_geometry_explicit_negative"] = negative_loss.detach()

    if not losses:
        raise ValueError("Graph contains no supervised classification, measurement, or positive text-link targets.")
    return torch.stack(losses).sum(), details


@torch.no_grad()
def _evaluate(model, graphs, device, class_weight, regression_weights,
              regression_scales=None):
    model.eval()
    loss_values = []
    class_correct = 0
    class_total = 0
    regression_errors = {name: [] for name in REGRESSION_TARGETS}
    regression_log_errors = {name: [] for name in REGRESSION_TARGETS}
    regression_scales = regression_scales or {name: 1.0 for name in REGRESSION_TARGETS}
    top1_hits = top5_hits = ranked_text_count = 0

    for _, cpu_data in graphs:
        data = cpu_data.to(device)
        logits, measurement_log, _, evidence = model(data)
        loss, _ = _loss_for_graph(
            logits, measurement_log, evidence, data,
            class_weight=class_weight,
            regression_weights=regression_weights,
        )
        loss_values.append(float(loss.detach().cpu()))

        graph_candidate_logits = []
        graph_candidate_text = []
        graph_candidate_positive = []
        for edge_type, match_logits in evidence.get("text_match_logits", {}).items():
            store = data[edge_type]
            edge_index = store.edge_index
            if edge_index.numel() == 0:
                continue
            match_mask = getattr(store, "match_mask", None)
            match_targets = getattr(store, "match_y", None)
            if match_mask is None or match_targets is None:
                continue
            positive = match_mask & (match_targets >= 0.5)
            if not bool(positive.any()):
                continue
            graph_candidate_logits.append(match_logits)
            graph_candidate_text.append(edge_index[0])
            graph_candidate_positive.append(positive)

        if graph_candidate_logits:
            candidate_logits = torch.cat(graph_candidate_logits)
            candidate_text = torch.cat(graph_candidate_text)
            candidate_positive = torch.cat(graph_candidate_positive)
            for text_index in torch.unique(candidate_text[candidate_positive]).tolist():
                group = candidate_text == int(text_index)
                positives = group & candidate_positive
                if not bool(positives.any()) or int(group.sum().item()) < 2:
                    continue
                ranked = torch.argsort(candidate_logits[group], descending=True)
                positive_positions = torch.nonzero(positives[group], as_tuple=False).flatten()
                top1_hits += int(bool((ranked[0] == positive_positions).any()))
                top5_hits += int(bool((ranked[:5, None] == positive_positions[None, :]).any()))
                ranked_text_count += 1

        geometry = data["geometry"]
        class_mask = getattr(geometry, "class_mask", None)
        if class_mask is not None and bool(class_mask.any()):
            predicted = logits[class_mask].argmax(dim=-1)
            class_correct += int((predicted == geometry.y[class_mask]).sum().item())
            class_total += int(class_mask.sum().item())

        for column, name in enumerate(REGRESSION_TARGETS):
            mask = getattr(geometry, f"{name}_mask", None)
            target = getattr(geometry, f"{name}_y", None)
            if mask is None or target is None or not bool(mask.any()):
                continue
            # Targets are log1p encoded. Report MAE in original drawing units.
            pred_log = measurement_log[mask, column].clamp(min=0.0, max=30.0)
            true_log = target[mask].clamp(min=0.0, max=30.0)
            pred_value = torch.expm1(pred_log)
            true_value = torch.expm1(true_log)
            regression_errors[name].extend(
                torch.abs(pred_value - true_value).detach().cpu().tolist()
            )
            regression_log_errors[name].extend(
                torch.abs(pred_log - true_log).detach().cpu().tolist()
            )

    metrics = {
        "loss": sum(loss_values) / max(1, len(loss_values)),
        "classification_accuracy": (
            class_correct / class_total if class_total else None
        ),
        "classification_count": class_total,
        "text_link_top1_accuracy": top1_hits / ranked_text_count if ranked_text_count else None,
        "text_link_hit_at_5": top5_hits / ranked_text_count if ranked_text_count else None,
        "text_link_count": ranked_text_count,
    }
    normalized_task_errors = []
    for name, errors in regression_errors.items():
        mae = sum(errors) / len(errors) if errors else None
        log_mae = (
            sum(regression_log_errors[name]) / len(regression_log_errors[name])
            if regression_log_errors[name] else None
        )
        metrics[f"{name}_mae"] = mae
        metrics[f"{name}_log_mae"] = log_mae
        metrics[f"{name}_count"] = len(errors)
        if mae is not None:
            scale = max(float(regression_scales.get(name, 1.0)), 1.0)
            normalized_mae = mae / scale
            metrics[f"{name}_normalized_mae"] = normalized_mae
            normalized_task_errors.append(normalized_mae)
        else:
            metrics[f"{name}_normalized_mae"] = None

    # Primary checkpoint-selection objective: equal-weight normalized MAE for
    # each available regression target. Unlike total val_loss, this score is
    # not affected by classification/text-link losses or arbitrary target units.
    metrics["regression_selection_score"] = (
        sum(normalized_task_errors) / len(normalized_task_errors)
        if normalized_task_errors else None
    )
    return metrics



def _cpu_state_dict(module):
    return {
        key: value.detach().cpu().clone()
        for key, value in module.state_dict().items()
    }


def _save_training_checkpoint(
    checkpoint_dir,
    epoch,
    model,
    optimizer,
    best_validation_score,
    best_state,
    epochs_without_improvement,
    class_to_id,
    input_dims,
    edge_dims,
    hidden_channels,
    num_layers,
    dropout,
    text_matching_trained,
    train_graph_paths,
    validation_graph_paths,
    test_graph_paths,
):
    """Atomically save a resumable training snapshot and retain numbered copies."""
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "checkpoint_version": 1,
        "epoch": int(epoch),
        "model_state_dict": _cpu_state_dict(model),
        "optimizer_state_dict": optimizer.state_dict(),
        "best_validation_score": float(best_validation_score),
        # Kept as a compatibility alias for older checkpoint readers.
        "best_validation_loss": float(best_validation_score),
        "validation_selection_metric": "mean_task_normalized_original_unit_mae_v1",
        "best_model_state_dict": best_state,
        "epochs_without_improvement": int(epochs_without_improvement),
        "class_to_id": class_to_id,
        "input_dims": input_dims,
        "edge_dims": edge_dims,
        "hidden_channels": hidden_channels,
        "num_layers": num_layers,
        "dropout": dropout,
        "text_matching_trained": bool(text_matching_trained),
        "feature_version": 8,
        "measurement_derivation_schema": "circle_arc_length_from_predicted_radius_v1",
        "geometry_feature_schema": "dxf_geometry_shape_v8",
        "geometry_feature_names": list(GEOMETRY_FEATURE_NAMES),
        "text_feature_schema": list(TEXT_FEATURE_NAMES),
        "architecture": "relation_aware_positive_text_rank_v5_geometry_v8_circle_arc_length_v1",
        "target_encoding": "log1p",
        "regression_targets": list(REGRESSION_TARGETS),
        "split": {
            "train_graphs": list(train_graph_paths),
            "validation_graphs": list(validation_graph_paths),
            "test_graphs": list(test_graph_paths),
        },
        "rng_state": {
            "python": random.getstate(),
            "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        },
    }

    latest_path = checkpoint_dir / "checkpoint_latest.pt"
    latest_tmp = checkpoint_dir / "checkpoint_latest.pt.tmp"
    torch.save(checkpoint, latest_tmp)
    os.replace(latest_tmp, latest_path)

    numbered_path = checkpoint_dir / f"checkpoint_epoch_{epoch:04d}.pt"
    numbered_tmp = checkpoint_dir / f"checkpoint_epoch_{epoch:04d}.pt.tmp"
    torch.save(checkpoint, numbered_tmp)
    os.replace(numbered_tmp, numbered_path)

    print(f"[CHECKPOINT SAVED] {numbered_path}")
    print(f"[LATEST CHECKPOINT] {latest_path}")


def _restore_training_checkpoint(
    checkpoint_path,
    model,
    optimizer,
    device,
    class_to_id,
    input_dims,
    edge_dims,
    hidden_channels,
    num_layers,
    dropout,
    text_matching_trained,
    train_graph_paths,
    validation_graph_paths,
    test_graph_paths,
):
    """Restore model, optimizer, early-stopping state, and RNG state."""
    checkpoint = torch.load(
        checkpoint_path, map_location=device, weights_only=False
    )

    expected = {
        "feature_version": 8,
        "measurement_derivation_schema": "circle_arc_length_from_predicted_radius_v1",
        "geometry_feature_schema": "dxf_geometry_shape_v8",
        "geometry_feature_names": list(GEOMETRY_FEATURE_NAMES),
        "text_feature_schema": list(TEXT_FEATURE_NAMES),
        "architecture": "relation_aware_positive_text_rank_v5_geometry_v8_circle_arc_length_v1",
        "input_dims": input_dims,
        "edge_dims": edge_dims,
        "hidden_channels": hidden_channels,
        "num_layers": num_layers,
        "dropout": dropout,
        "text_matching_trained": bool(text_matching_trained),
        "class_to_id": class_to_id,
        "split": {
            "train_graphs": list(train_graph_paths),
            "validation_graphs": list(validation_graph_paths),
            "test_graphs": list(test_graph_paths),
        },
    }
    for key, value in expected.items():
        if checkpoint.get(key) != value:
            raise ValueError(
                f"Resume checkpoint mismatch for '{key}'. "
                "Use the same model configuration, class mapping, and graph splits."
            )

    if "optimizer_state_dict" not in checkpoint:
        raise ValueError(
            "This file is not a resumable training checkpoint "
            "(optimizer_state_dict is missing)."
        )

    model.load_state_dict(checkpoint["model_state_dict"])
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    rng_state = checkpoint.get("rng_state", {})
    if rng_state.get("python") is not None:
        random.setstate(rng_state["python"])
    if rng_state.get("torch") is not None:
        torch.set_rng_state(rng_state["torch"].cpu())
    cuda_rng = rng_state.get("cuda")
    if cuda_rng is not None and torch.cuda.is_available():
        try:
            torch.cuda.set_rng_state_all(cuda_rng)
        except (RuntimeError, ValueError):
            print("[WARN] Could not restore CUDA RNG state; continuing.")

    best_state = checkpoint.get("best_model_state_dict")
    if best_state is None:
        raise ValueError("Resume checkpoint does not contain best-model weights.")

    print(
        f"[RESUME] Restored epoch {checkpoint['epoch']} from {checkpoint_path}; "
        f"best validation loss={checkpoint['best_validation_loss']:.6f}"
    )
    return (
        int(checkpoint["epoch"]),
        float(checkpoint["best_validation_loss"]),
        best_state,
        (
            int(checkpoint.get("epochs_without_improvement", 0))
            if checkpoint.get("validation_selection_metric") ==
            "mean_task_normalized_original_unit_mae_v1" else 0
        ),
    )


def train_model(
    train_graph_paths,
    validation_graph_paths,
    test_graph_paths,
    class_to_id: dict[str, int] | None,
    output_path: str,
    epochs: int = 200,
    learning_rate: float = 1e-3,
    hidden_channels: int = 96,
    num_layers: int = 2,
    dropout: float = 0.20,
    patience: int = 25,
    device: str | None = None,
    class_weight: float = 1.0,
    regression_weights: dict[str, float] | None = None,
    checkpoint_every: int = 100,
    resume_from: str | None = None,
):
    """Train on drawing-level train graphs, select by validation, test once.

    Split by complete drawing/project, never by geometry nodes from the same
    drawing. The test set is not used for optimization or checkpoint selection.
    """
    if checkpoint_every < 1:
        raise ValueError("checkpoint_every must be >= 1.")
    if not train_graph_paths or not validation_graph_paths or not test_graph_paths:
        raise ValueError(
            "Provide separate non-empty train, validation, and test graph lists."
        )
    train_graphs = _load_graphs(train_graph_paths)
    validation_graphs = _load_graphs(validation_graph_paths)
    test_graphs = _load_graphs(test_graph_paths)

    all_paths = (
        [p for p, _ in train_graphs]
        + [p for p, _ in validation_graphs]
        + [p for p, _ in test_graphs]
    )
    if len(set(all_paths)) != len(all_paths):
        raise ValueError("A graph file appears in more than one split.")

    input_dims = _input_dims(train_graphs[0][1])
    edge_dims = _edge_dims(train_graphs[0][1])
    _validate_graph_compatibility(
        train_graphs + validation_graphs + test_graphs,
        input_dims, edge_dims,
    )

    if not any(_has_supervision(data) for _, data in train_graphs):
        raise ValueError("Training split contains no supervised labels.")
    if not any(_has_supervision(data) for _, data in validation_graphs):
        raise ValueError("Validation split contains no supervised labels.")
    if not any(_has_supervision(data) for _, data in test_graphs):
        raise ValueError("Test split contains no supervised labels.")

    train_tasks = _split_tasks(train_graphs)
    validation_tasks = _split_tasks(validation_graphs)
    test_tasks = _split_tasks(test_graphs)
    required_measurements = {"length"}
    missing_train = required_measurements - train_tasks
    if missing_train:
        raise ValueError(
            "Training split needs independent ground-truth labels for: "
            + ", ".join(sorted(missing_train))
        )
    # Length is the stable regression anchor. Area/radius/classification are
    # optional auxiliary tasks; sparse availability must not block training.
    required_eval_tasks = {"length"}
    missing_validation = required_eval_tasks - validation_tasks
    missing_test = required_eval_tasks - test_tasks
    if missing_validation:
        raise ValueError(
            "Validation split has no labels for trained task(s): "
            + ", ".join(sorted(missing_validation))
        )
    if missing_test:
        raise ValueError(
            "Test split has no labels for trained task(s): "
            + ", ".join(sorted(missing_test))
        )

    class_to_id = {
        str(name): int(class_id)
        for name, class_id in (class_to_id or {}).items()
    }
    if "classification" in train_tasks and not class_to_id:
        raise ValueError(
            "Classification labels are attached, but no class_to_id mapping was provided."
        )
    num_classes = max(1, max(class_to_id.values(), default=-1) + 1)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    regression_weights = regression_weights or {
        "length": 1.0, "area": 1.0, "radius": 1.0
    }
    regression_scales = _compute_regression_scales(train_graphs)
    print("[REGRESSION SELECTION SCALES]", json.dumps(regression_scales, sort_keys=True))

    model = DXFSemanticGNN(
        metadata=train_graphs[0][1].metadata(),
        input_dims=input_dims,
        edge_dims=edge_dims,
        hidden_channels=hidden_channels,
        num_classes=num_classes,
        num_layers=num_layers,
        dropout=dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=1e-4
    )

    best_validation_score = float("inf")
    best_state = None
    epochs_without_improvement = 0
    start_epoch = 0

    if resume_from:
        (
            start_epoch,
            _legacy_best_value,
            best_state,
            epochs_without_improvement,
        ) = _restore_training_checkpoint(
            checkpoint_path=resume_from,
            model=model,
            optimizer=optimizer,
            device=device,
            class_to_id=class_to_id,
            input_dims=input_dims,
            edge_dims=edge_dims,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
            text_matching_trained=("text_geometry_matching" in train_tasks),
            train_graph_paths=[p for p, _ in train_graphs],
            validation_graph_paths=[p for p, _ in validation_graphs],
            test_graph_paths=[p for p, _ in test_graphs],
        )
        # Re-score the saved best weights using the current regression-first criterion.
        current_state = _cpu_state_dict(model)
        model.load_state_dict(best_state)
        restored_best_metrics = _evaluate(
            model, validation_graphs, device, class_weight, regression_weights,
            regression_scales=regression_scales,
        )
        restored_score = restored_best_metrics.get("regression_selection_score")
        if restored_score is None:
            raise ValueError("Validation graphs have no regression targets for checkpoint selection.")
        best_validation_score = float(restored_score)
        model.load_state_dict(current_state)
        print(f"[RESUME] Re-scored saved best model: regression_selection_score={best_validation_score:.6f}")
        if start_epoch >= epochs:
            print(
                f"[RESUME] Checkpoint is already at epoch {start_epoch}; "
                f"requested total epochs={epochs}. No additional epochs will run."
            )

    checkpoint_dir = Path(output_path).parent / "checkpoints_relation_aware_gnn_v8"

    for epoch in range(start_epoch + 1, epochs + 1):
        model.train()
        epoch_losses = []
        for _, cpu_data in train_graphs:
            data = cpu_data.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits, measurement_log, _, evidence = model(data)
            loss, _ = _loss_for_graph(
                logits, measurement_log, evidence, data,
                class_weight=class_weight,
                regression_weights=regression_weights,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))

        validation_metrics = _evaluate(
            model, validation_graphs, device, class_weight, regression_weights,
            regression_scales=regression_scales,
        )
        validation_loss = validation_metrics["loss"]
        validation_score = validation_metrics["regression_selection_score"]
        if validation_score is None:
            raise ValueError("Validation split has no measurable regression targets.")
        if validation_score < best_validation_score:
            best_validation_score = validation_score
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(
                f"epoch={epoch:03d} "
                f"train_loss={sum(epoch_losses)/max(1,len(epoch_losses)):.5f} "
                f"val_total_loss={validation_loss:.5f} "
                f"val_regression_score={validation_score:.6f} "
                f"val_len_MAE={validation_metrics['length_mae']} "
                f"val_area_MAE={validation_metrics['area_mae']} "
                f"val_radius_MAE={validation_metrics['radius_mae']} "
                f"val_len_nMAE={validation_metrics['length_normalized_mae']} "
                f"val_area_nMAE={validation_metrics['area_normalized_mae']} "
                f"val_radius_nMAE={validation_metrics['radius_normalized_mae']} "
                f"val_text_link_top1={validation_metrics['text_link_top1_accuracy']}"
            )
        if epoch % checkpoint_every == 0:
            _save_training_checkpoint(
                checkpoint_dir=checkpoint_dir,
                epoch=epoch,
                model=model,
                optimizer=optimizer,
                best_validation_score=best_validation_score,
                best_state=best_state,
                epochs_without_improvement=epochs_without_improvement,
                class_to_id=class_to_id,
                input_dims=input_dims,
                edge_dims=edge_dims,
                hidden_channels=hidden_channels,
                num_layers=num_layers,
                dropout=dropout,
                text_matching_trained=("text_geometry_matching" in train_tasks),
                train_graph_paths=[p for p, _ in train_graphs],
                validation_graph_paths=[p for p, _ in validation_graphs],
                test_graph_paths=[p for p, _ in test_graphs],
            )

        if epochs_without_improvement >= patience:
            print(
                f"Early stopping at epoch {epoch}; "
                f"best regression score={best_validation_score:.6f}"
            )
            break

    final_epoch = epoch if epochs > start_epoch else start_epoch
    if final_epoch > 0 and final_epoch % checkpoint_every != 0:
        _save_training_checkpoint(
            checkpoint_dir=checkpoint_dir,
            epoch=final_epoch,
            model=model,
            optimizer=optimizer,
            best_validation_score=best_validation_score,
            best_state=best_state,
            epochs_without_improvement=epochs_without_improvement,
            class_to_id=class_to_id,
            input_dims=input_dims,
            edge_dims=edge_dims,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            dropout=dropout,
            text_matching_trained=("text_geometry_matching" in train_tasks),
            train_graph_paths=[p for p, _ in train_graphs],
            validation_graph_paths=[p for p, _ in validation_graphs],
            test_graph_paths=[p for p, _ in test_graphs],
        )

    if best_state is None:
        raise RuntimeError("Training did not produce a valid checkpoint.")
    model.load_state_dict(best_state)

    # Evaluate test split only after selecting the checkpoint on validation.
    test_metrics = _evaluate(
        model, test_graphs, device, class_weight, regression_weights,
        regression_scales=regression_scales,
    )
    print("TEST METRICS:", json.dumps(test_metrics, indent=2))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state_dict": best_state,
        "class_to_id": class_to_id,
        "input_dims": input_dims,
        "edge_dims": edge_dims,
        "hidden_channels": hidden_channels,
        "num_layers": num_layers,
        "dropout": dropout,
        "text_matching_trained": ("text_geometry_matching" in train_tasks),
        "feature_version": 8,
        "measurement_derivation_schema": "circle_arc_length_from_predicted_radius_v1",
        "geometry_feature_schema": "dxf_geometry_shape_v8",
        "geometry_feature_names": list(GEOMETRY_FEATURE_NAMES),
        "text_feature_schema": list(TEXT_FEATURE_NAMES),
        "architecture": "relation_aware_positive_text_rank_v5_geometry_v8_circle_arc_length_v1",
        "target_encoding": "log1p",
        "regression_targets": list(REGRESSION_TARGETS),
        "best_validation_score": best_validation_score,
        "best_validation_loss": best_validation_score,
        "validation_selection_metric": "mean_task_normalized_original_unit_mae_v1",
        "regression_selection_scales": regression_scales,
        "test_metrics": test_metrics,
        "split": {
            "train_graphs": [p for p, _ in train_graphs],
            "validation_graphs": [p for p, _ in validation_graphs],
            "test_graphs": [p for p, _ in test_graphs],
        },
    }, output)
    return {
        "checkpoint": str(output),
        "best_validation_score": best_validation_score,
        "best_validation_loss": best_validation_score,
        "validation_selection_metric": "mean_task_normalized_original_unit_mae_v1",
        "regression_selection_scales": regression_scales,
        "test_metrics": test_metrics,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Train the DXF multi-task heterogeneous GNN."
    )
    parser.add_argument("--train-graphs", nargs="+", required=True)
    parser.add_argument("--val-graphs", nargs="+", required=True)
    parser.add_argument("--test-graphs", nargs="+", required=True)
    parser.add_argument("--classes", default=None, help="Optional classes.json")
    parser.add_argument("--output", default="models/dxf_semantic_gnn_multitask.pt")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=25)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--hidden-channels", type=int, default=96)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.20)
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument(
        "--resume-from",
        default=None,
        help="Resume from checkpoint_latest.pt or a numbered training checkpoint.",
    )
    args = parser.parse_args()
    classes = (
        json.loads(Path(args.classes).read_text(encoding="utf-8"))
        if args.classes else {}
    )
    train_model(
        args.train_graphs,
        args.val_graphs,
        args.test_graphs,
        classes,
        args.output,
        epochs=args.epochs,
        patience=args.patience,
        learning_rate=args.learning_rate,
        hidden_channels=args.hidden_channels,
        num_layers=args.num_layers,
        dropout=args.dropout,
        checkpoint_every=args.checkpoint_every,
        resume_from=args.resume_from,
    )


if __name__ == "__main__":
    main()
