import ast
from collections import defaultdict


def collect_grouped_imports(ast_code: ast.AST):

    grouped = defaultdict(
        lambda: {
            "type": "import_from",
            "module": None,
            "level": None,
            "names": [],  # list of {name, alias}
        }
    )

    imports = []  # final result

    for node in ast.walk(ast_code):

        # --- Case 1: plain `import x, y`
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    {"type": "import", "module": alias.name, "alias": alias.asname}
                )

        # --- Case 2: `from x import a, b`
        elif isinstance(node, ast.ImportFrom):
            key = (node.module, node.level)

            group = grouped[key]
            group["module"] = node.module
            group["level"] = node.level

            for alias in node.names:
                group["names"].append({"name": alias.name, "alias": alias.asname})

    # append grouped import_from entries
    imports.extend(grouped.values())

    return imports


def classify_imports(imports, repo_modules):
    codebase_imports = []
    library_imports = []

    for item in imports:

        # --- Case 1: plain `import x`
        if item["type"] == "import":
            module = item["module"]

            if module in repo_modules:
                codebase_imports.append(item)
            else:
                library_imports.append(item)

        # --- Case 2: from X import a, b
        elif item["type"] == "import_from":
            module = item["module"]

            # sometimes module may be None (rare)
            if module and module in repo_modules:
                codebase_imports.append(item)
            else:
                library_imports.append(item)

    return codebase_imports, library_imports
