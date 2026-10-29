from collections import Counter

def _walk_plan(node, depth=1, rows=None):
    rows = rows if rows is not None else []

    if not isinstance(node, dict):
        return

    rows.append({
        "node_type": node.get("Node Type"),
        "startup_cost": node.get("Startup Cost", 0.0),
        "total_cost": node.get("Total Cost", 0.0),
        "plan_rows": node.get("Plan Rows", 0),
        "plan_width": node.get("Plan Width", 0),
        "depth": depth,
    })

    for child in node.get("Plans", []):
        _walk_plan(child, depth + 1, rows)

def parse_plan(explain_json: list) -> dict:
    root = explain_json[0]["Plan"]
    nodes = []
    _walk_plan(root, rows=nodes)

    types = Counter(n["node_type"] for n in nodes)

    return {
        "root_node": root.get("Node Type"),
        "estimated_startup_cost": float(root.get("Startup Cost", 0.0)),
        "estimated_total_cost": float(root.get("Total Cost", 0.0)),
        "estimated_rows": float(root.get("Plan Rows", 0)),
        "plan_width": float(root.get("Plan Width", 0)),
        "plan_depth": max((n["depth"] for n in nodes), default=0),
        "operator_count": len(nodes),
        "join_count": sum(
            types[k] for k in ("Hash Join", "Merge Join", "Nested Loop")
        ),
        "hash_join_count": types["Hash Join"],
        "merge_join_count": types["Merge Join"],
        "nested_loop_count": types["Nested Loop"],
        "seq_scan_count": types["Seq Scan"],
        "index_scan_count": types["Index Scan"],
        "index_only_scan_count": types["Index Only Scan"],
        "bitmap_scan_count": types["Bitmap Heap Scan"] + types["Bitmap Index Scan"],
        "sort_count": types["Sort"],
        "aggregate_count": (
            types["Aggregate"] + types["GroupAggregate"] + types["HashAggregate"]
        ),
    }

def plan_fingerprint(explain_json: list) -> str:
    root = explain_json[0]["Plan"]
    parts = []

    def visit(node):
        if not isinstance(node, dict):
            return
        parts.append(str(node.get("Node Type", "")))
        for child in node.get("Plans", []):
            visit(child)

    visit(root)
    return " > ".join(parts)
