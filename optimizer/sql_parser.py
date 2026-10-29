import sqlglot
from sqlglot import exp

def analyze_query(query: str) -> dict:
    tree = sqlglot.parse_one(query, dialect="postgres")

    if not isinstance(tree, exp.Select):
        raise ValueError("Review 2 prototype supports SELECT queries only.")

    tables = list(tree.find_all(exp.Table))
    joins = list(tree.find_all(exp.Join))
    predicates = list(tree.find_all(exp.Where))

    return {
        "number_of_tables": len(tables),
        "number_of_joins": len(joins),
        "number_of_predicates": len(predicates),
        "has_group_by": int(tree.args.get("group") is not None),
        "has_order_by": int(tree.args.get("order") is not None),
        "has_limit": int(tree.args.get("limit") is not None),
    }

def validate_select(query: str) -> None:
    analyze_query(query)
