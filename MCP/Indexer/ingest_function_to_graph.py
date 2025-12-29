def ingest_functions_to_graph(functions, graph, file_dict):
    index = {}

    for fn in functions:
        key = (fn["name"], fn.get("parent_function"))
        index.setdefault(key, []).append(fn)

    processed = set()

    def merge_function_node(fn):
        parent = fn.get("parent_function")

        if parent is None:
            # ---- top-level function ----
            result = graph.query(
                """
                MERGE (f:Function {name: $name})
                SET f.start_line = $start,
                    f.end_line = $end,
                    f.parent_function = NULL
                RETURN elementId(f) as func_id
                """,
                {
                    "name": fn["name"],
                    "start": fn["start_line"],
                    "end": fn["end_line"],
                },
            )
        else:
            # ---- nested function ----
            result = graph.query(
                """
                MERGE (f:Function {
                  name: $name,
                  parent_function: $parent
                })
                SET f.start_line = $start,
                    f.end_line = $end
                RETURN elementId(f) as func_id
                """,
                {
                    "name": fn["name"],
                    "parent": parent,
                    "start": fn["start_line"],
                    "end": fn["end_line"],
                },
            )

        return result[0]["func_id"]

    func_id_cache = {}

    def ensure_function(fn, file_dict):
        key = (fn["name"], fn.get("parent_function"))
        if key in processed:
            return func_id_cache.get(key)

        processed.add(key)

        func_id = merge_function_node(fn)
        func_id_cache[key] = func_id

        parent = fn.get("parent_function")

        # -------- docstring --------
        doc = fn.get("docstring")
        if doc and doc.strip():
            graph.query(
                """
                MATCH (f:Function)
                WHERE elementId(f) = $func_id

                MERGE (d:Docstring {name: $doc_name})
                SET d.content = $doc_text

                MERGE (f)-[:DOCUMENTED_BY]->(d)
                """,
                {
                    "func_id": func_id,
                    "doc_name": f"func_{func_id}_docstring",
                    "doc_text": doc,
                },
            )

        # -------- parameters --------
        for arg in fn.get("args", []):
            kv_pair = f"{arg['name']}={arg.get('annotation_display') or ''}"

            graph.query(
                """
                MATCH (f:Function)
                WHERE elementId(f) = $func_id

                MERGE (p:Parameter {name: $param_name})

                // store list of key=value strings
                SET p.pairs = coalesce(p.pairs, []) + $pair

                MERGE (f)-[:HAS_PARAMETER]->(p)
                """,
                {
                    "func_id": func_id,
                    "param_name": f"func_{func_id}_parameter",
                    "pair": [kv_pair],
                },
            )

        # -------- decorators --------
        for dec in fn.get("decorators", []):
            decorator_name = dec["name"]
            importing_from = dec["importing_from"]

            # # Convert module path to file path (e.g., contextlib.asynccontextmanager -> contextlib.py)
            # if "." in importing_from:
            #     # Split and get everything before the last dot as module path
            #     parts = importing_from.rsplit(".", 1)
            #     module_path = parts[0] + ".py"
            #     symbol_name = parts[1]
            # else:
            #     # If no dot, it's already just the symbol name
            #     module_path = importing_from + ".py"
            #     symbol_name = importing_from
            module_path, symbol_name = importing_from.rsplit(".", 1)
            module_path = file_dict.get(module_path)

            # Create DECORATED_BY relationship to Function or Class in the target module
            graph.query(
                """
                MATCH (f:Function)
                WHERE elementId(f) = $func_id
                
                MATCH (m:Module {name: $module_path})
                
                OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {name: $symbol_name})
                WHERE target_func.parent_function IS NULL
                
                OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {name: $symbol_name})
                
                WITH f, target_func, target_class
                WHERE target_func IS NOT NULL OR target_class IS NOT NULL
                
                FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (f)-[:DECORATED_BY]->(target_func)
                )
                
                FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (f)-[:DECORATED_BY]->(target_class)
                )
                """,
                {
                    "func_id": func_id,
                    "module_path": module_path,
                    "symbol_name": symbol_name,
                },
            )

        # -------- DEPENDS_ON resolution --------
        for dep_name in fn.get("depends", []):
            dep_key = (dep_name, fn["name"])
            for child in index.get(dep_key, []):
                child_func_id = ensure_function(child, file_dict)

                graph.query(
                    """
                    MATCH (p:Function)
                    WHERE elementId(p) = $parent_id

                    MATCH (c:Function)
                    WHERE elementId(c) = $child_id

                    MERGE (p)-[:DEPENDS_ON]->(c)
                    """,
                    {
                        "parent_id": func_id,
                        "child_id": child_func_id,
                    },
                )

        return func_id

    for fn in functions:
        ensure_function(fn, file_dict)
