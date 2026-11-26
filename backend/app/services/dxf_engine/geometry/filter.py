import numpy as np

from ezdxf.path import make_path
from ezdxf.layouts import Modelspace
from ezdxf import bbox

from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

from sklearn.cluster import DBSCAN
from scipy.sparse import coo_matrix


def entity_to_geometry(entity, flattening_distance=1.0):
    """Convert a DXF entity into a Shapely geometry."""

    try:
        dxftype = entity.dxftype()

        if dxftype in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
            extents = bbox.extents([entity])

            if not extents.has_data:
                return None

            min_x, min_y, _ = extents.extmin
            max_x, max_y, _ = extents.extmax

            if min_x == max_x and min_y == max_y:
                return Point(min_x, min_y)

            return Polygon([
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
            ])

        path = make_path(entity)

        vertices = path.flattening(
            distance=flattening_distance
        )

        coords = [(v.x, v.y) for v in vertices]

        if len(coords) >= 2:
            if path.is_closed and coords[0] != coords[-1]:
                coords.append(coords[0])

            return LineString(coords)

        if coords:
            return Point(coords[0])

    except Exception:
        return None

    return None


def filter_entities(
    entities,
    eps: float = 1000,
    min_samples: int = 3,
    min_cluster_size: int = 50,
    flattening_distance: float = 1.0,
) -> list[str]:

    entities = list(entities)

    geometries = [
        entity_to_geometry(entity, flattening_distance)
        for entity in entities
    ]

    valid_indices = [
        i for i, geometry in enumerate(geometries)
        if geometry is not None
    ]

    if not valid_indices:
        return []

    valid_geometries = [
        geometries[i] for i in valid_indices
    ]

    n = len(valid_geometries)

    # Build spatial index.
    tree = STRtree(valid_geometries)

    # Find nearby geometry pairs.
    pairs = tree.query(
        valid_geometries,
        predicate="dwithin",
        distance=eps,
    )

    row, col = pairs

    # Keep unique pairs, including diagonal entries.
    mask = row <= col
    row = row[mask]
    col = col[mask]

    # Calculate exact distances.
    distances = np.fromiter(
        (
            valid_geometries[i].distance(valid_geometries[j])
            for i, j in zip(row, col)
        ),
        dtype=np.float64,
        count=len(row),
    )

    # Construct symmetric sparse distance matrix.
    sparse_distances = coo_matrix(
        (
            np.concatenate((distances, distances)),
            (
                np.concatenate((row, col)),
                np.concatenate((col, row)),
            ),
        ),
        shape=(n, n),
    ).tocsr()

    # DBSCAN clustering.
    labels = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric="precomputed",
    ).fit_predict(sparse_distances)

    # Count entities in each cluster.
    cluster_sizes = np.bincount(
        labels[labels >= 0]
    )

    # Identify all sufficiently large clusters.
    valid_clusters = {
        cluster_id
        for cluster_id, size in enumerate(cluster_sizes)
        if size >= min_cluster_size
    }

    # Map valid cluster labels back to original entity indices.
    keep_indices = {
        valid_indices[i]
        for i, label in enumerate(labels)
        if label in valid_clusters
    }

    # Preserve entities without calculable geometries.
    keep_indices.update(
        i
        for i, geometry in enumerate(geometries)
        if geometry is None
    )

    # Return handles of entities to remove.
    return [
        entity.dxf.handle
        for i, entity in enumerate(entities)
        if i not in keep_indices
        or entity.dxftype() == "INSERT"
    ]