import networkx as nx


def validate_connectivity_graph(graph):

    issues = []

    valid_node_types = {
        "geometry",
        "dimension",
        "text",
    }

    for node_id, data in graph.nodes(data=True):

        if data.get("node_type") not in valid_node_types:
            issues.append({
                "type": "invalid_node_type",
                "node": node_id,
            })

    for source, target, data in graph.edges(data=True):

        source_type = graph.nodes[source].get("node_type")
        target_type = graph.nodes[target].get("node_type")

        relationship = data.get("relationship")

        if source_type == "geometry" and target_type == "geometry":
            allowed = {
                "endpoint_connected",
                "boundary_connected",
                "intersects",
                "crosses",
                "overlaps",
                "near",
            }

        elif {source_type, target_type} == {
            "geometry",
            "dimension",
        }:
            allowed = {"dimension_of"}

        elif {source_type, target_type} == {
            "geometry",
            "text",
        }:
            allowed = {"associated_text"}

        else:
            issues.append({
                "type": "invalid_node_relationship",
                "source": source,
                "target": target,
            })
            continue

        if relationship not in allowed:
            issues.append({
                "type": "invalid_relationship_type",
                "source": source,
                "target": target,
                "relationship": relationship,
            })

    isolated_nodes = list(nx.isolates(graph))

    return {
        "is_valid": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
        "isolated_nodes": isolated_nodes,
        "connected_component_count": nx.number_connected_components(
            graph
        ),
    }