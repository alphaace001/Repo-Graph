def _create_class_node(graph, cls):
    """Creates a Class node in the graph and returns its ID."""
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
    return result[0]["class_id"]


def _create_docstring_node(graph, entity_id, entity_type, docstring):
    """Creates a Docstring node and links it to the given entity."""
    if not docstring or not docstring.strip():
        return

    graph.query(
        f"""
        MATCH (e:{entity_type})
        WHERE elementId(e) = $entity_id
        MERGE (d:Docstring {{name: $doc_name}})
        SET d.content = $doc_text
        MERGE (e)-[:DOCUMENTED_BY]->(d)
        """,
        {
            "entity_id": entity_id,
            "doc_name": f"{entity_type.lower()}_{entity_id}_docstring",
            "doc_text": docstring,
        },
    )


def _create_decorator_relationship(graph, entity_id, entity_type, decorator, file_dict):
    """Creates a DECORATED_BY relationship between an entity and a decorator."""
    importing_from = decorator["importing_from"]
    module_path, symbol_name = importing_from.rsplit(".", 1)
    module_path = file_dict.get(module_path)

    entity_match = "c:Class" if entity_type == "Class" else "meth:Method"
    entity_var = "c" if entity_type == "Class" else "meth"

    graph.query(
        f"""
        MATCH ({entity_match})
        WHERE elementId({entity_var}) = $entity_id
        
        MATCH (m:Module {{name: $module_path}})
        
        OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {{name: $symbol_name}})
        WHERE target_func.parent_function IS NULL
        
        OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {{name: $symbol_name}})
        
        WITH {entity_var}, target_func, target_class
        WHERE target_func IS NOT NULL OR target_class IS NOT NULL
        
        FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
            MERGE ({entity_var})-[:DECORATED_BY]->(target_func)
        )
        
        FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
            MERGE ({entity_var})-[:DECORATED_BY]->(target_class)
        )
        """,
        {
            "entity_id": entity_id,
            "module_path": module_path,
            "symbol_name": symbol_name,
        },
    )


def _create_method_node(graph, class_id, class_name, method):
    """Creates a Method node in the graph and returns its ID."""
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
            "class_name": class_name,
            "name": method["name"],
            "start": method["start_line"],
            "end": method["end_line"],
        },
    )
    return method_result[0]["method_id"]


def _create_parameter_nodes(graph, method_id, args):
    """Creates Parameter nodes for method arguments."""
    for arg in args:
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


def _ingest_class_methods(graph, class_id, class_name, methods, file_dict):
    """Ingests all methods of a class into the graph."""
    for method in methods:
        method_id = _create_method_node(graph, class_id, class_name, method)

        # Create method docstring
        _create_docstring_node(graph, method_id, "Method", method.get("docstring"))

        # Create parameter nodes
        _create_parameter_nodes(graph, method_id, method.get("args", []))

        # Create decorator relationships
        for dec in method.get("decorators", []):
            _create_decorator_relationship(graph, method_id, "Method", dec, file_dict)


def _create_module_class_relationship(graph, class_id, module_id):
    """Create MODULE-[:CONTAINS]->CLASS relationship."""
    graph.query(
        """
        MATCH (c:Class)
        WHERE elementId(c) = $class_id
        
        MATCH (m:Module)
        WHERE elementId(m) = $module_id
        
        MERGE (m)-[:CONTAINS]->(c)
        """,
        {
            "class_id": class_id,
            "module_id": module_id,
        },
    )


def ingest_classes_to_graph(classes, graph, file_dict, module_id):
    """
    Creates Class, Method, Docstring, Parameter nodes and relationships
    from extracted class metadata.
    """
    for cls in classes:
        # Create Class node
        class_id = _create_class_node(graph, cls)

        # Create class docstring
        _create_docstring_node(graph, class_id, "Class", cls.get("docstring"))

        # Create class decorator relationships
        # for dec in cls.get("decorators", []):
        #     _create_decorator_relationship(graph, class_id, "Class", dec, file_dict)

        # Ingest all methods
        _ingest_class_methods(
            graph, class_id, cls["name"], cls.get("methods", []), file_dict
        )

        # Create module-class relationship
        _create_module_class_relationship(graph, class_id, module_id)
