def build_codebase_symbol_lookup(codebase_imports):
    """
    Maps locally-imported names to fully-qualified symbols.

    Example:
      from fastapi.cli import main
      -> "main" -> "fastapi.cli.main"
    """
    lookup = {}

    for item in codebase_imports:

        # Case 1: plain `import module`
        if item["type"] == "import":
            local = item["alias"] or item["module"]
            lookup[local] = item["module"]

        # Case 2: `from module import a, b as x`
        elif item["type"] == "import_from":
            module = item.get("resolved_module") or item["module"]

            for n in item["names"]:
                local = n["alias"] or n["name"]
                lookup[local] = f"{module}.{n['name']}"

    return lookup
