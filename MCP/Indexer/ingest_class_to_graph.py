def ingest_classes_to_graph(classes, graph, file_dict):
    """
    Creates Class, Method, Docstring, Parameter nodes and relationships
    from extracted class metadata.
    """

    for cls in classes:

        # ----------- create Class node -----------
        result = graph.query(
            """
            MERGE (c:Class {name: $name})
            SET c.start_line = $start,
                c.end_line = $end
            RETURN elementId(c) as class_id
            """,
            {
                "name": cls["name"],
                "start": cls["start_line"],
                "end": cls["end_line"],
            },
        )
        class_id = result[0]["class_id"]

        # ----------- optional class Docstring -----------
        doc = cls.get("docstring")
        if doc and doc.strip():
            graph.query(
                """
                MATCH (c:Class)
                WHERE elementId(c) = $class_id
                MERGE (d:Docstring {name: $doc_name})
                SET d.content = $doc_text
                MERGE (c)-[:DOCUMENTED_BY]->(d)
                """,
                {
                    "class_id": class_id,
                    "doc_name": f"class_{class_id}_docstring",
                    "doc_text": doc,
                },
            )

        # ----------- class decorators -----------
        for dec in cls.get("decorators", []):
            decorator_name = dec["name"]
            importing_from = dec["importing_from"]

            module_path, symbol_name = importing_from.rsplit(".", 1)
            module_path = file_dict.get(module_path)

            # Create DECORATED_BY relationship to Function or Class in the target module
            graph.query(
                """
                MATCH (c:Class)
                WHERE elementId(c) = $class_id
                
                MATCH (m:Module {name: $module_path})
                
                OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {name: $symbol_name})
                WHERE target_func.parent_function IS NULL
                
                OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {name: $symbol_name})
                
                WITH c, target_func, target_class
                WHERE target_func IS NOT NULL OR target_class IS NOT NULL
                
                FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (c)-[:DECORATED_BY]->(target_func)
                )
                
                FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (c)-[:DECORATED_BY]->(target_class)
                )
                """,
                {
                    "class_id": class_id,
                    "module_path": module_path,
                    "symbol_name": symbol_name,
                },
            )

        # ----------- methods (as Method nodes) -----------
        for method in cls.get("methods", []):

            # create Method node
            method_result = graph.query(
                """
                MATCH (c:Class)
                WHERE elementId(c) = $class_id

                MERGE (m:Method {
                  name: $name,
                  parent_class: $class_name
                })
                SET m.start_line = $start,
                    m.end_line = $end

                MERGE (c)-[:CONTAINS]->(m)
                RETURN elementId(m) as method_id
                """,
                {
                    "class_id": class_id,
                    "class_name": cls["name"],
                    "name": method["name"],
                    "start": method["start_line"],
                    "end": method["end_line"],
                },
            )
            method_id = method_result[0]["method_id"]

            # ----------- optional method Docstring -----------
            mdoc = method.get("docstring")
            if mdoc and mdoc.strip():
                graph.query(
                    """
                    MATCH (m:Method)
                    WHERE elementId(m) = $method_id
                    MERGE (d:Docstring {name: $doc_name})
                    SET d.content = $doc_text
                    MERGE (m)-[:DOCUMENTED_BY]->(d)
                    """,
                    {
                        "method_id": method_id,
                        "doc_name": f"method_{method_id}_docstring",
                        "doc_text": mdoc,
                    },
                )

            # ----------- method parameters -----------
            for arg in method.get("args", []):

                # store list of "key=value" strings (Neo4j-safe)
                kv_pair = f"{arg['name']}={arg.get('annotation_display') or ''}"

                graph.query(
                    """
                    MATCH (m:Method)
                    WHERE elementId(m) = $method_id

                    MERGE (p:Parameter {
                      name: $param_group
                    })

                    SET p.pairs = coalesce(p.pairs, []) + $pair

                    MERGE (m)-[:HAS_PARAMETER]->(p)
                    """,
                    {
                        "method_id": method_id,
                        "param_group": f"method_{method_id}_parameters",
                        "pair": [kv_pair],
                    },
                )

            # ----------- method decorators -----------
            for dec in method.get("decorators", []):
                decorator_name = dec["name"]
                importing_from = dec["importing_from"]

                module_path, symbol_name = importing_from.rsplit(".", 1)
                module_path = file_dict.get(module_path)

                # Create DECORATED_BY relationship to Function or Class in the target module
                graph.query(
                    """
                    MATCH (meth:Method)
                    WHERE elementId(meth) = $method_id
                    
                    MATCH (m:Module {name: $module_path})
                    
                    OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {name: $symbol_name})
                    WHERE target_func.parent_function IS NULL
                    
                    OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {name: $symbol_name})
                    
                    WITH meth, target_func, target_class
                    WHERE target_func IS NOT NULL OR target_class IS NOT NULL
                    
                    FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (meth)-[:DECORATED_BY]->(target_func)
                    )
                    
                    FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (meth)-[:DECORATED_BY]->(target_class)
                    )
                    """,
                    {
                        "method_id": method_id,
                        "module_path": module_path,
                        "symbol_name": symbol_name,
                    },
                )
