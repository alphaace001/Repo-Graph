import ast
from pathlib import Path
from utils import discover_py_files, load_code, convert_file_paths_to_modules
from import_utils import collect_grouped_imports, classify_imports
from function_utils import build_codebase_symbol_lookup
from function_metadata import extract_function_metadata
from ingest_function_to_graph import ingest_functions_to_graph
from extract_class_metadata import extract_class_metadata
from ingest_class_to_graph import ingest_classes_to_graph

from langchain_neo4j import Neo4jGraph

graph = Neo4jGraph(
    url="neo4j+s://b1ae48ed.databases.neo4j.io",
    username="neo4j",
    password="vNUM9ZLYSJjKLEaL_TTQIJ7vLbr8fbWK7TQ-hU4Ms5I",
)

path = "D:\\KGassign\\fastapi"
files = discover_py_files(path)
file_dict = convert_file_paths_to_modules(files)

current_file = "fastapi\\routing.py"
code = load_code(Path(path) / current_file)

ast_code = ast.parse(code)
file_docstring = ast.get_docstring(ast_code)


def build_module_node(
    graph: Neo4jGraph, current_file: str, code: str, module_docstring: str
):
    query = """
    MERGE (m:Module {name: $name})
    SET m.content = $content

    WITH m, $doc_text AS doc_text, $doc_name AS doc_name
    WHERE doc_text IS NOT NULL AND doc_text <> ""

    MERGE (d:Docstring {name: doc_name})
    SET d.text = doc_text

    MERGE (m)-[:DOCUMENTED_BY]->(d)

    RETURN m
    """
    module_name = current_file
    content = code
    doc_name = f"{module_name}_docstring"
    doc_text = module_docstring
    graph.query(
        query,
        {
            "name": module_name,
            "content": content,
            "doc_name": doc_name,
            "doc_text": doc_text,
        },
    )


build_module_node(graph, current_file, code, file_docstring)

imports = collect_grouped_imports(ast_code)
codebase_imports, library_imports = classify_imports(imports, file_dict)

lookup_codebase = build_codebase_symbol_lookup(codebase_imports)
lookup_library = build_codebase_symbol_lookup(library_imports)
# print(lookup_codebase)

# function_metadata = extract_function_metadata(ast_code, lookup_codebase, lookup_library)
# # print(function_metadata)
# ingest_functions_to_graph(function_metadata, graph, file_dict)

class_metadata = extract_class_metadata(
    ast_code, lookup_codebase, lookup_library, current_file
)
ingest_classes_to_graph(class_metadata, graph, file_dict)


def function_to_function_relationships(graph, function_metadata, file_dict):
    for fn in function_metadata:
        calls = fn.get("calls", {})
        codebase_imports = calls.get("codebase", [])
        import_and_fn = {}
        for imp in codebase_imports:
            lib, fn_name = imp.rsplit(".", 1)
            import_and_fn[lib] = fn_name

        # creating a relationship
        for lib, fn_name in import_and_fn.items():
            graph.query(
                """
                        MATCH (f:Function {name: $fn_name})
                        WHERE ($parent IS NULL AND f.parent_function IS NULL)
                        OR ($parent IS NOT NULL AND f.parent_function = $parent)
                        
                        MATCH (m:Module {name: $target_module})
                        
                        OPTIONAL MATCH (m)-[:CONTAINS]->(target_func:Function {name: $symbol_name})
                        WHERE target_func.parent_function IS NULL
                        
                        OPTIONAL MATCH (m)-[:CONTAINS]->(target_class:Class {name: $symbol_name})
                        
                        WITH f, target_func, target_class
                        WHERE target_func IS NOT NULL OR target_class IS NOT NULL
                        
                        FOREACH (_ IN CASE WHEN target_func IS NOT NULL THEN [1] ELSE [] END |
                            MERGE (f)-[:DEPENDS_ON]->(target_func)
                        )
                        
                        FOREACH (_ IN CASE WHEN target_class IS NOT NULL THEN [1] ELSE [] END |
                            MERGE (f)-[:DEPENDS_ON]->(target_class)
                        )
                        """,
                {
                    "fn_name": fn["name"],
                    "parent": fn.get("parent_function"),
                    "target_module": file_dict[lib],
                    "symbol_name": fn_name,
                },
            )


def module_function_relationships(
    current_file: str, function_metadata: list[dict], graph: Neo4jGraph
):
    for fn in function_metadata:
        if fn.get("parent_function") is not None:
            continue  # skip nested functions
        query = """
        MATCH (f:Module {name: $Mod})
        MATCH (fn:Function {name: $func})
        MERGE (f)-[:CONTAINS]->(fn)
        """

        graph.query(
            query,
            {
                "Mod": current_file,
                "func": fn["name"],
            },
        )


def module_class_relationships(
    current_file: str, classes: list[dict], graph: Neo4jGraph
):
    for cl in classes:
        query = """
        MATCH (f:Module {name: $Mod})
        MATCH (cl:Class {name: $class})
        MERGE (f)-[:CONTAINS]->(cl)
        """

        graph.query(
            query,
            {
                "Mod": current_file,
                "class": cl["name"],
            },
        )
