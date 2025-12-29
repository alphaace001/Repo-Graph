import ast
from function_metadata import extract_function_metadata


def classify_call(name, codebase_lookup, library_lookup):
    """
    Resolve symbol to either codebase or library lookup.
    Returns tuple: (group_name, fq_name) or (None, None)
    """

    if name in codebase_lookup:
        return "codebase", codebase_lookup[name]

    if name in library_lookup:
        return "library", library_lookup[name]

    return None, None


def extract_method_metadata_from_body(body, lookup_codebase, lookup_library):
    """Run your function extractor on function nodes inside a class body."""
    fake_module = ast.Module(body=body, type_ignores=[])
    return extract_function_metadata(fake_module, lookup_codebase, lookup_library)


def get_base_name(node):
    # Base
    if isinstance(node, ast.Name):
        return node.id

    # package.Base
    if isinstance(node, ast.Attribute):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        parts.reverse()
        return ".".join(parts)

    return None


def extract_class_metadata(tree, lookup_codebase, lookup_library, current_file):
    # First pass: collect ALL classes in the file (including nested ones)
    lookup = lookup_codebase | lookup_library
    local_classes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            local_classes.add(node.name)

    classes = []

    # Walk entire tree to find all ClassDef nodes
    for node in ast.walk(tree):

        # Only process ClassDef nodes
        if not isinstance(node, ast.ClassDef):
            continue

        class_info = {
            "name": node.name,
            "docstring": ast.get_docstring(node),
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", None),
            "decorators": [],
            "base_classes": [],
            "attributes": [],  # NEW: class-level attributes
            "methods": [],
        }

        # -------- class decorators --------
        for dec in node.decorator_list:

            if isinstance(dec, ast.Name):
                name = dec.id
            elif isinstance(dec, ast.Attribute):
                name = dec.attr
            else:
                continue

            group, fq = classify_call(name, lookup_codebase, lookup_library)

            if fq:
                class_info["decorators"].append(
                    {
                        "name": name,
                        "scope": group,
                        "importing_from": fq,
                    }
                )

        # -------- base classes --------
        for base in node.bases:

            base_name = get_base_name(base)

            if not base_name:
                continue

            # Check if base class is defined in the same file
            if base_name in local_classes:
                importing_from = current_file  # local class
            else:
                # Otherwise check the lookup (imported or external)
                importing_from = lookup.get(base_name)

            class_info["base_classes"].append(
                {
                    "name": base_name,
                    "importing_from": importing_from,
                }
            )

        # -------- class attributes --------
        for item in node.body:
            if isinstance(item, ast.Assign):
                # Handle: name = value
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attr_name = target.id
                        attr_value = ast.unparse(item.value)

                        class_info["attributes"].append(
                            {
                                "name": attr_name,
                                "value": attr_value,
                                "lineno": item.lineno,
                            }
                        )

            elif isinstance(item, ast.AnnAssign):
                # Handle: name: Type = value (annotated assignment)
                if isinstance(item.target, ast.Name):
                    attr_name = item.target.id
                    attr_type = (
                        ast.unparse(item.annotation) if item.annotation else None
                    )
                    attr_value = ast.unparse(item.value) if item.value else None

                    class_info["attributes"].append(
                        {
                            "name": attr_name,
                            "annotation": attr_type,
                            "value": attr_value,
                            "lineno": item.lineno,
                        }
                    )

        # -------- methods (reuse your function extractor) --------
        class_info["methods"] = extract_method_metadata_from_body(
            node.body,
            lookup_codebase,
            lookup_library,
        )

        classes.append(class_info)

    return classes
