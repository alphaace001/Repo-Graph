"""
Code Analysis Service - Provides deep code understanding and pattern analysis.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from logger import setup_logger
from Utils.db_connection import Neo4jConnection

logger = setup_logger(__name__)


class CodeAnalysisService:
    """Service for deep code analysis and pattern detection."""

    def __init__(self, db_connection: Neo4jConnection):
        """Initialize with an established database connection."""
        self.db = db_connection
        if self.db is None:
            raise ValueError("Database connection cannot be None")

    def get_dependencies(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Find what an entity depends on (DEPENDS_ON relationships).

        Args:
            entity_id: Name of the entity

        Returns:
            List of dependencies
        """
        query = """
        MATCH (source)-[rel:DEPENDS_ON]->(target)
        WHERE elementId(source) = $entity_id
        RETURN 
            source.name AS source_name,
            labels(source)[0] AS source_type,
            type(rel) AS relationship,
            target.name AS target_name,
            labels(target)[0] AS target_type,
            elementId(target) AS target_id
        """
        try:
            results = self.db.execute_query(query, {"entity_id": entity_id})
            logger.info(f"Found {len(results)} dependencies for '{entity_id}'")
            return results
        except Exception as e:
            logger.error(f"Error getting dependencies for '{entity_id}': {str(e)}")
            return []

    def analyze_function(
        self,
        function_id: str,
        include_calls: bool = True,
        context_lines: int = 5,
    ) -> Dict[str, Any]:
        """
        Deep analysis of a function's logic and implementation.
        """

        query = """
            MATCH (m:Module)-[:CONTAINS]->(f:Function)
            WHERE elementId(f) = $function_id

            OPTIONAL MATCH (f)-[:DOCUMENTED_BY]->(doc:Docstring)
            OPTIONAL MATCH (f)-[:HAS_PARAMETER]->(param:Parameter)
            OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:Function)
            OPTIONAL MATCH (caller)-[:DEPENDS_ON]->(f)

            RETURN
            f.name AS function_name,
            elementId(f) AS function_elem_id,
            f.start_line AS start_line,
            f.end_line AS end_line,

            doc.content AS doc_content,

            m.name AS file_path,
            m.content AS module_code,

            collect(DISTINCT param.pairs) AS parameters,

            collect(DISTINCT {
                name: dep.name,
                type: labels(dep)[0],
                id: elementId(dep)
            }) AS dependencies,

            collect(DISTINCT {
                name: caller.name,
                type: labels(caller)[0],
                id: elementId(caller)
            }) AS called_by
            """

        try:
            results = self.db.execute_query(query, {"function_id": function_id})
            if not results:
                return {"error": f"Function with id '{function_id}' not found"}

            f = results[0]

            # --------------------------------------------------
            # CODE SNIPPET EXTRACTION
            # --------------------------------------------------
            module_code = f.get("module_code") or ""
            lines = module_code.split("\n") if module_code else []

            start = f.get("start_line")
            end = f.get("end_line")

            code_snippet = ""
            lines_of_code = 0

            if start is not None and end is not None:
                start = int(start)
                end = int(end)

                context_start = max(0, start - context_lines - 1)
                context_end = min(len(lines), end + context_lines)

                code_snippet = "\n".join(lines[context_start:context_end])
                lines_of_code = max(0, end - start + 1)

            # --------------------------------------------------
            # PARAMETERS — flatten + dedupe
            # --------------------------------------------------
            raw_param_groups = f.get("parameters", [])

            flat_params = []
            for group in raw_param_groups:
                if group:
                    flat_params.extend(group)

            flat_params = sorted(set(p for p in flat_params if p))

            # --------------------------------------------------
            # BASIC DEPENDENCY + CALLER SETS
            # --------------------------------------------------
            dependencies = [d for d in f.get("dependencies", []) if d and d.get("name")]

            called_by = [c for c in f.get("called_by", []) if c and c.get("name")]

            # --------------------------------------------------
            # EXPANDED DEPENDENCY ANALYSIS
            # --------------------------------------------------
            detailed_calls = []
            if include_calls:
                try:
                    detailed_calls = self.get_dependencies(function_id)
                except Exception as e:
                    print(f"[warn] dependency expansion failed for {function_id}: {e}")
                    detailed_calls = []

            # --------------------------------------------------
            # FINAL ANALYSIS OBJECT
            # --------------------------------------------------
            analysis = {
                "name": f["function_name"],
                "file_path": f["file_path"],
                "location": {
                    "start_line": start,
                    "end_line": end,
                    "lines_of_code": lines_of_code,
                },
                "docstring": f.get("doc_content"),
                "parameters": flat_params,
                "parameter_count": len(flat_params),
                "dependencies": {
                    "depends_on": dependencies,
                    "dependency_count": len(dependencies),
                    "detailed_calls": detailed_calls,
                },
                "called_by": called_by,
                "call_count": len(called_by),
                "code": code_snippet,
            }

            print(f"Completed analysis of function '{f['function_name']}'")
            return analysis

        except Exception as e:
            print(f"Error analyzing function '{function_id}': {e}")
            raise

    def analyze_class(
        self,
        class_id: str,
        include_calls: bool = True,
        context_lines: int = 5,
    ) -> Dict[str, Any]:

        query = """
            MATCH (m:Module)-[:CONTAINS]->(c:Class)
            WHERE elementId(c) = $class_id

            OPTIONAL MATCH (c)-[:DOCUMENTED_BY]->(doc:Docstring)

            OPTIONAL MATCH (c)-[:CONTAINS]->(mth)
            WHERE mth:Method OR mth:Function

            OPTIONAL MATCH (c)-[:INHERITS_FROM]->(parent:Class)

            OPTIONAL MATCH (child:Class)-[:INHERITS_FROM]->(c)

            RETURN
            c.name AS class_name,
            elementId(c) AS class_elem_id,
            c.start_line AS start_line,
            c.end_line AS end_line,

            doc.content AS doc_content,

            m.name AS file_path,
            m.content AS module_code,

            collect(DISTINCT {
                id: elementId(mth),
                name: mth.name,
                start_line: mth.start_line,
                end_line: mth.end_line
            }) AS methods,

            collect(DISTINCT {
                id: elementId(parent),
                name: parent.name
            }) AS parent_classes,

            collect(DISTINCT {
                id: elementId(child),
                name: child.name
            }) AS subclasses
            """

        try:
            results = self.db.execute_query(query, {"class_id": class_id})
            if not results:
                return {"error": f"Class with id '{class_id}' not found"}

            c = results[0]

            # ---------------------------------------
            # CODE SNIPPET EXTRACTION
            # ---------------------------------------
            module_code = c.get("module_code") or ""
            lines = module_code.split("\n") if module_code else []

            start = c.get("start_line")
            end = c.get("end_line")

            code_snippet = ""
            lines_of_code = 0

            if start is not None and end is not None:
                start = int(start)
                end = int(end)

                context_start = max(0, start - context_lines - 1)
                context_end = min(len(lines), end + context_lines)

                code_snippet = "\n".join(lines[context_start:context_end])
                lines_of_code = max(0, end - start + 1)

            # ---------------------------------------
            # METHODS
            # ---------------------------------------
            methods = [m for m in c.get("methods", []) if m and m.get("name")]

            # ---------------------------------------
            # INHERITANCE
            # ---------------------------------------
            parent_classes = [
                p for p in c.get("parent_classes", []) if p and p.get("name")
            ]

            subclasses = [s for s in c.get("subclasses", []) if s and s.get("name")]

            # ---------------------------------------
            # OPTIONAL — CLASS DEPENDENCY EXPANSION
            # ---------------------------------------
            detailed_calls = []
            if include_calls:
                try:
                    detailed_calls = self.get_dependencies(class_id)
                except Exception as e:
                    print(
                        f"[warn] dependency expansion failed for class {class_id}: {e}"
                    )

            # ---------------------------------------
            # RESULT
            # ---------------------------------------
            analysis = {
                "name": c["class_name"],
                "file_path": c["file_path"],
                "location": {
                    "start_line": start,
                    "end_line": end,
                    "lines_of_code": lines_of_code,
                },
                "docstring": c.get("doc_content"),
                "methods": methods,
                "method_count": len(methods),
                "inheritance": {
                    "parents": parent_classes,
                    "parent_count": len(parent_classes),
                    "subclasses": subclasses,
                    "subclass_count": len(subclasses),
                },
                "dependencies": {
                    "detailed_calls": detailed_calls if include_calls else [],
                },
                "code": code_snippet,
            }

            print(f"Completed analysis of class '{c['class_name']}'")
            return analysis

        except Exception as e:
            print(f"Error analyzing class '{class_id}': {e}")
            raise

    def get_code_snippet(
        self, entity_id: str, context_lines: int = 5
    ) -> Dict[str, Any]:
        """
        Extract code snippet with surrounding context.

        Args:
            entity_id: Name of the entity
            context_lines: Number of context lines

        Returns:
            Dictionary containing code snippet and metadata
        """

        query = """
        MATCH (entity)
        WHERE elementId(entity) = $entity_id
        AND (entity:Function OR entity:Class OR entity:Method)

        OPTIONAL MATCH (entity)<-[:CONTAINS]-(module:Module)

        RETURN 
            entity.name AS name,
            labels(entity)[0] AS type,
            module.content AS code,
            entity.start_line AS start_line,
            entity.end_line AS end_line,
            module.name AS file_path
        LIMIT 1
        """

        try:
            results = self.db.execute_query(query, {"entity_id": entity_id})
            if not results:
                return {"error": f"Entity '{entity_id}' not found"}

            entity_data = results[0]
            module_code = entity_data.get("code", "")

            # Calculate context boundaries
            context_start = max(0, entity_data["start_line"] - context_lines - 1)
            lines = module_code.split("\n") if module_code else []
            context_end = min(len(lines), entity_data["end_line"] + context_lines)

            # Extract code with context if available
            code_with_context = ""
            if lines:
                code_with_context = "\n".join(lines[context_start:context_end])

            snippet_data = {
                "entity_id": entity_data["name"],
                "entity_type": entity_data["type"],
                "file_path": entity_data["file_path"],
                "start_line": context_start + 1,
                "end_line": context_end,
                "code": code_with_context,
            }

            logger.info(f"Retrieved code snippet for '{entity_id}'")
            return snippet_data

        except Exception as e:
            logger.error(f"Error getting code snippet for '{entity_id}': {str(e)}")
            raise
