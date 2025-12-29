import ast


def extract_arg_annotation(arg, lookup):
    if not arg.annotation:
        return {
            "annotation_display": None,
        }

    # names = collect_annotation_symbol_candidates(arg.annotation)

    return {
        # <-- NEW readable string
        "annotation_display": ast.unparse(arg.annotation),
    }


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


def extract_nested_functions(node, codebase_lookup, library_lookup, parent_name):
    """
    Extract metadata for functions defined inside another function.
    """

    nested_functions = []

    for inner in node.body:

        if not isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        fn = {
            "name": inner.name,
            "parent_function": parent_name,
            "docstring": ast.get_docstring(inner),
            "start_line": inner.lineno,
            "end_line": getattr(inner, "end_lineno", None),
            "args": [],
            "decorators": [],
            "calls": {
                "codebase": [],
                "library": [],
            },
            "depends": [],
        }

        # ---------- arguments ----------
        for arg in inner.args.args + inner.args.kwonlyargs:
            fn["args"].append(
                {"name": arg.arg, **extract_arg_annotation(arg, codebase_lookup)}
            )

        # ---------- decorators ----------
        for dec in inner.decorator_list:

            if isinstance(dec, ast.Name):
                name = dec.id
            elif isinstance(dec, ast.Attribute):
                name = dec.attr
            else:
                continue

            group, fq = classify_call(name, codebase_lookup, library_lookup)

            if fq:
                fn["decorators"].append(
                    {
                        "name": name,
                        "scope": group,
                        "importing_from": fq,
                    }
                )

        # ---------- function body calls ----------
        used_codebase = set()
        used_library = set()

        for n in ast.walk(inner):

            symbol = None

            if isinstance(n, ast.Name):
                symbol = n.id

            elif isinstance(n, ast.Attribute):
                symbol = n.attr

            if not symbol:
                continue

            group, fq = classify_call(symbol, codebase_lookup, library_lookup)

            if not fq:
                continue

            if group == "codebase":
                used_codebase.add(fq)

            elif group == "library":
                used_library.add(fq)

        fn["calls"]["codebase"] = sorted(used_codebase)
        fn["calls"]["library"] = sorted(used_library)

        # ---------- recurse ----------
        new_parent_path = f"{parent_name}/{inner.name}" if parent_name else inner.name

        deeper = extract_nested_functions(
            inner,
            codebase_lookup,
            library_lookup,
            parent_name=new_parent_path,  # <-- important change
        )

        fn["depends"] = [d["name"] for d in deeper]

        nested_functions.append(fn)
        nested_functions.extend(deeper)

    return nested_functions


def extract_function_metadata(tree, codebase_lookup, library_lookup):
    functions = []

    for node in tree.body:

        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        func_info = {
            "name": node.name,
            "docstring": ast.get_docstring(node),
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", None),
            "args": [],
            "decorators": [],
            "calls": {
                "codebase": [],
                "library": [],
            },
            "depends": [],
        }

        # ---------- arguments ----------
        for arg in node.args.args + node.args.kwonlyargs:
            func_info["args"].append(
                {"name": arg.arg, **extract_arg_annotation(arg, codebase_lookup)}
            )

        if node.args.vararg:
            func_info["args"].append(
                {
                    "name": "*" + node.args.vararg.arg,
                    **extract_arg_annotation(node.args.vararg, codebase_lookup),
                }
            )

        if node.args.kwarg:
            func_info["args"].append(
                {
                    "name": "**" + node.args.kwarg.arg,
                    **extract_arg_annotation(node.args.kwarg, codebase_lookup),
                }
            )

        # ---------- decorators ----------
        for dec in node.decorator_list:

            if isinstance(dec, ast.Name):
                name = dec.id
            elif isinstance(dec, ast.Attribute):
                name = dec.attr
            else:
                continue

            group, fq = classify_call(name, codebase_lookup, library_lookup)

            if fq:
                func_info["decorators"].append(
                    {
                        "name": name,
                        "scope": group,
                        "importing_from": fq,
                    }
                )

        # ---------- collect calls ----------
        used_codebase = set()
        used_library = set()

        for inner in ast.walk(node):

            symbol = None

            if isinstance(inner, ast.Name):
                symbol = inner.id

            elif isinstance(inner, ast.Attribute):
                symbol = inner.attr

            if not symbol:
                continue

            group, fq = classify_call(symbol, codebase_lookup, library_lookup)

            if not fq:
                continue

            if group == "codebase":
                used_codebase.add(fq)

            elif group == "library":
                used_library.add(fq)

        func_info["calls"]["codebase"] = sorted(used_codebase)
        func_info["calls"]["library"] = sorted(used_library)

        # ---------- nested functions ----------
        nested = extract_nested_functions(
            node,
            codebase_lookup,
            library_lookup,
            parent_name=node.name,
        )

        func_info["depends"] = [f["name"] for f in nested]

        functions.append(func_info)
        functions.extend(nested)

    return functions
