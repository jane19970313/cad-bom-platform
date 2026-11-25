from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable

from app.services.dxf_engine.extraction.reader import open_dxf
from app.services.dxf_engine.extraction.entities import extract_modelspace
from app.services.dxf_engine.extraction.dimensions import (
    extract_dimension_and_text_element,
    extract_scale_from_dimensions,
)

from app.services.dxf_engine.geometry.converter import convert_geometry
from app.services.dxf_engine.geometry.filter import filter_entities
from app.services.dxf_engine.spatial.index import SpatialIndex
from app.services.dxf_engine.bom.bom_extract import extract_bom
from app.services.dxf_engine.topology.graph_builder import (
    build_connectivity_graph,
)

from app.services.dxf_engine.classification.engineering import (
    classify_element,
)

from pathlib import Path
import torch
from app.services.dxf_engine.ai_gnn import build_semantic_graph


ENGINE_VERSION = "0.3.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _report_progress(
    callback: Callable[[dict[str, Any]], None] | None,
    event: dict[str, Any],
) -> None:
    """
    Report a progress event without coupling the DXF engine
    to FastAPI, SQLAlchemy, or Celery.
    """
    if callback is not None:
        callback(event)


def _run_stage(
    stage_name: str,
    operation: Callable[[], Any],
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    input_count: int | None = None,
    output_count: Callable[[Any], int | None] | None = None,
    warning_count: Callable[[Any], int | None] | None = None,
    details: Callable[[Any], dict[str, Any]] | None = None,
) -> Any:
    """
    Execute one pipeline stage and report its lifecycle.

    Counts are supplied by the caller so the engine never
    invents progress metrics.
    """
    started_at = _utc_now()
    start_clock = perf_counter()

    _report_progress(
        progress_callback,
        {
            "event": "stage_started",
            "name": stage_name,
            "status": "running",
            "started_at": started_at,
            "completed_at": None,
            "duration_ms": None,
            "input_count": input_count,
            "output_count": None,
            "warning_count": None,
            "error": None,
        },
    )

    try:
        result = operation()

        duration_ms = round(
            (perf_counter() - start_clock) * 1000
        )

        actual_output_count = (
            output_count(result)
            if output_count is not None
            else None
        )

        actual_warning_count = (
            warning_count(result)
            if warning_count is not None
            else None
        )

        event = {
            "event": "stage_completed",
            "name": stage_name,
            "status": "completed",
            "started_at": started_at,
            "completed_at": _utc_now(),
            "duration_ms": duration_ms,
            "input_count": input_count,
            "output_count": actual_output_count,
            "warning_count": actual_warning_count,
            "error": None,
        }

        if details is not None:
            event["details"] = details(result)

        _report_progress(progress_callback, event)

        return result

    except Exception as exc:
        duration_ms = round(
            (perf_counter() - start_clock) * 1000
        )

        _report_progress(
            progress_callback,
            {
                "event": "stage_failed",
                "name": stage_name,
                "status": "failed",
                "started_at": started_at,
                "completed_at": _utc_now(),
                "duration_ms": duration_ms,
                "input_count": input_count,
                "output_count": None,
                "warning_count": None,
                "error": str(exc)[:2000],
            },
        )

        raise


def _serialize_raw_entity(entity):
    return {
        "source": {
            "entity_handle": entity.source.entity_handle,
            "entity_type": entity.source.entity_type,
            "layer": entity.source.layer,
            "layout": entity.source.layout,
            "block_path": list(entity.source.block_path),
        },
        "attributes": entity.attributes,
        "text": entity.text,
        "warnings": entity.warnings,
    }


def _serialize_geometry_element(element):
    return {
        "element_id": element.element_id,
        "source_handle": element.source.entity_handle,
        "source_type": element.source.entity_type,
        "layer": element.source.layer,
        "layout": element.source.layout,
        "block_path": list(element.source.block_path),

        "geometry_type": element.geometry_type,
        "caption": element.caption,
        "text": element.text,
        "text_handle": element.text_handle,
        "is_closed": element.is_closed,
        "is_valid": element.is_valid,

        "coordinates_3d": element.coordinates_3d if len(element.coordinates_3d)<20 else [],

        "center": (
            {
                "x": element.center.x,
                "y": element.center.y,
            }
            if element.center else None
        ),

        "radius": element.radius_measured,
        "start_angle": element.start_angle,
        "end_angle": element.end_angle,

        "length": element.length,
        "area": element.area,

        "warnings": element.warnings,
    }

def _serialize_bom_element(element):
    return {
        "caption": element.caption,
        "length": element.length,
        "area": element.area,
        "count": element.count,
        "material": element.material,
        "volume": element.volume,
        "mass": element.mass,
        "source_handles": list(element.source_handles),
    }


def analyze_dxf(
    dxf_path: str,
    flattening_distance: float = 0.1,
    connectivity_tolerance: float = 300.0,
    nearby_distance: float = 0.0,
    dimension_search_distance: float = 2000.0,
    dimension_endpoint_tolerance: float = 300.0,
    text_search_distance: float = 300.0,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ai_graph_output_path: str | None = None,
    ai_graph_options: dict[str, Any] | None = None,
) -> dict:

    print("========== ANALYZE_DXF STARTED ==========", flush=True)
    if flattening_distance <= 0:
        raise ValueError(
            "flattening_distance must be greater than zero"
        )

    if connectivity_tolerance < 0:
        raise ValueError(
            "connectivity_tolerance cannot be negative"
        )

    if nearby_distance < 0:
        raise ValueError(
            "nearby_distance cannot be negative"
        )

    # 1. Read the DXF file.
    dxf_document = _run_stage(
        stage_name="dxf_reading",
        operation=lambda: open_dxf(dxf_path),
        progress_callback=progress_callback,
    )

    document = dxf_document.document

    # 2. Extract original modelspace entities.
    raw_entities = _run_stage(
        stage_name="entity_extraction",
        operation=lambda: extract_modelspace(document),
        progress_callback=progress_callback,
        output_count=lambda result: len(result),
        warning_count=lambda result: sum(
            len(entity.warnings) for entity in result
        ),
    )

    # Materialize modelspace once for the next processing stages.
    modelspace_entities = list(document.modelspace())
    remove_handles = filter_entities(modelspace_entities)
    for (index, raw_entity) in enumerate(raw_entities):
        if raw_entity.source.entity_handle in remove_handles:
            raw_entities[index].warnings.append("invalid")
    
    dimension_elements, text_elements = extract_dimension_and_text_element(raw_entities, remove_handles)
    scale = extract_scale_from_dimensions(dimension_elements)   
    print(f"[DEBUG] SCALE: {scale:.2f}", flush=True)

    # 3. Convert supported entities to geometry.
    diagnostics = []
    geometry_elements = _run_stage(
        stage_name="geometry_conversion",
        operation=lambda: convert_geometry(
            modelspace_entities=modelspace_entities,
            scale = scale,
            remove_handles=remove_handles,
            dimension_elements=dimension_elements,
            text_elements=text_elements,
            flattening_distance=flattening_distance,
            diagnostics=diagnostics,
        ),
        progress_callback=progress_callback,
        input_count=len(modelspace_entities),
        output_count=lambda result: len(result),
        warning_count=lambda result: len(diagnostics) + sum(
            len(element.warnings) for element in result
        ),
    )

    # 4. Build spatial index.
    spatial_index = _run_stage(
        stage_name="spatial_indexing",
        operation=lambda: SpatialIndex(geometry_elements, dimension_elements, text_elements),
        progress_callback=progress_callback,
        input_count=len(geometry_elements),
    )

    # 5. Build connectivity graph.
    graph = _run_stage(
        stage_name="connectivity_graph",

        operation=lambda: build_connectivity_graph(
            elements=geometry_elements,
            dimensions=dimension_elements,
            texts=text_elements,

            spatial_index=spatial_index,

            connectivity_tolerance=connectivity_tolerance,

            dimension_search_distance=dimension_search_distance,
            dimension_endpoint_tolerance=dimension_endpoint_tolerance,

            text_search_distance=text_search_distance,
        ),

        progress_callback=progress_callback,

        input_count=(
            len(geometry_elements)
            + len(dimension_elements)
            + len(text_elements)
        ),

        output_count=lambda result: result.number_of_nodes(),
    )

    # Optional AI graph export. The analytical graph and all existing
    # downstream calculations remain unchanged. Save PyG separately so the
    # regular analysis response stays JSON serializable.
    ai_graph_summary = None
    if ai_graph_output_path:
        def build_and_save_ai_graph():
            options = dict(ai_graph_options or {})
            options.setdefault("spatial_tolerance", connectivity_tolerance)
            options.setdefault("connection_tolerance", connectivity_tolerance)
            semantic_graph = build_semantic_graph(
                geometry_elements=geometry_elements,
                dimension_elements=dimension_elements,
                text_elements=text_elements,
                raw_entities=raw_entities,
                # The existing topology graph uses ("G", element_id) node
                # keys, while the AI graph maps by source_handle. Keep it
                # separate for now; reuse the already-built STRtree instead.
                spatial_index=spatial_index,
                scale=scale,
                **options,
            )
            output_path = Path(ai_graph_output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(semantic_graph, output_path)
            return {
                "saved_path": str(output_path),
                "metadata": semantic_graph.graph_metadata,
                "node_types": list(semantic_graph.node_types),
                "edge_types": [str(edge_type) for edge_type in semantic_graph.edge_types],
            }

        ai_graph_summary = _run_stage(
            stage_name="ai_semantic_graph",
            operation=build_and_save_ai_graph,
            progress_callback=progress_callback,
            input_count=len(geometry_elements) + len(dimension_elements) + len(text_elements),
            output_count=lambda result: sum(result["metadata"]["node_counts"].values()),
        )

    # 6. Classify geometry.
    def classify_geometry():
        classified_elements = []

        for element in geometry_elements:
            nearby = spatial_index.nearby(
                element.geometry_2d,
                distance=nearby_distance,
                exclude_handle=element.source.entity_handle,
            )

            classification = classify_element(
                element,
                nearby_elements=nearby,
            )

            classified_elements.append({
                "element_id": element.element_id,
                "source_handle": element.source.entity_handle,
                "source_type": element.source.entity_type,
                "layer": element.source.layer,
                "layout": element.source.layout,
                "block_path": list(element.source.block_path),

                "geometry_type": element.geometry_type,
                "is_closed": element.is_closed,
                "is_valid": element.is_valid,

                "engineering_type": classification.engineering_type,
                "confidence": classification.confidence,
                "status": classification.status,
                "evidence": classification.evidence,

                "area": element.area,
                "length": element.length,

                "coordinates_3d": element.coordinates_3d,
                "warnings": element.warnings,

                "nearby_element_count": len(nearby),

                "caption": element.caption,
            })

        return classified_elements

    classified_elements = _run_stage(
        stage_name="engineering_classification",
        operation=classify_geometry,
        progress_callback=progress_callback,
        input_count=len(geometry_elements),
        output_count=lambda result: len(result),
        warning_count=lambda result: sum(
            len(element["warnings"]) for element in result
        ),
    )

    bom_elements = extract_bom(classified_elements)

    # 7. Serialize connectivity relationships.
    relationships = _run_stage(
        stage_name="relationship_serialization",
        operation=lambda: [
            {
                "source": source,
                "target": target,
                "edge_key": key,
                **data,
            }
            for source, target, key, data in graph.edges(keys=True, data=True)
        ],
        progress_callback=progress_callback,
        input_count=graph.number_of_edges(),
        output_count=lambda result: len(result),
    )

    # 8. Build summary.
    summary = _run_stage(
        stage_name="summary_generation",
        operation=lambda: {
            "raw_entity_count": len(raw_entities),
            "geometry_element_count": len(geometry_elements),
            "classified_element_count": len(classified_elements),
            "bom_element_count": len(bom_elements),
            "geometry_conversion_failure_count": len(diagnostics),
            "connectivity_node_count": graph.number_of_nodes(),
            "connectivity_edge_count": graph.number_of_edges(),
        },
        progress_callback=progress_callback,
    )

    # 9. Return JSON-compatible analysis.
    return {
        "engine_version": ENGINE_VERSION,

        "drawing": {
            "path": dxf_document.path,
            "version": dxf_document.version,
            "units_code": dxf_document.units_code,
            "units_name": dxf_document.units_name,
            "warnings": dxf_document.warnings,
        },

        "settings": {
            "flattening_distance": flattening_distance,
            "connectivity_tolerance": connectivity_tolerance,
            "nearby_distance": nearby_distance,
            "dimension_search_distance": dimension_search_distance,
            "dimension_endpoint_tolerance": dimension_endpoint_tolerance,
            "text_search_distance": text_search_distance,
        },

        "summary": summary,

        "raw_entities": [
            _serialize_raw_entity(entity)
            for entity in raw_entities
        ],

        "geometry_elements": [
            _serialize_geometry_element(element)
            for element in geometry_elements
        ],

        "spatial_index": {
            "indexed_element_count": len(geometry_elements),
        },

        "connectivity_nodes": [
            str(node)
            for node in graph.nodes
        ],

        "elements": classified_elements,

        "bom_elements": [
            _serialize_bom_element(element)
            for element in bom_elements
        ],

        "relationships": relationships,

        "ai_graph": ai_graph_summary,

        "diagnostics": diagnostics,
    }
