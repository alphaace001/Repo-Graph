import ast


def extract_arg_annotation(arg, lookup):
    """Extract annotation display string from function argument."""
    if not arg.annotation:
        return {
            "annotation_display": None,
        }

    return {
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


def _create_function_info_structure(node, parent_function=None):
    """Create the base structure for function metadata."""
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

    if parent_function:
        func_info["parent_function"] = parent_function

    return func_info


def _extract_function_arguments(node, codebase_lookup):
    """Extract all arguments from a function node."""
    args = []

    # Regular and keyword-only arguments
    for arg in node.args.args + node.args.kwonlyargs:
        args.append({"name": arg.arg, **extract_arg_annotation(arg, codebase_lookup)})

    # *args
    if node.args.vararg:
        args.append(
            {
                "name": "*" + node.args.vararg.arg,
                **extract_arg_annotation(node.args.vararg, codebase_lookup),
            }
        )

    # **kwargs
    if node.args.kwarg:
        args.append(
            {
                "name": "**" + node.args.kwarg.arg,
                **extract_arg_annotation(node.args.kwarg, codebase_lookup),
            }
        )

    return args


def _extract_decorators(node, codebase_lookup, library_lookup):
    """Extract decorator information from a function node."""
    decorators = []

    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            name = dec.id
        elif isinstance(dec, ast.Attribute):
            name = dec.attr
        else:
            continue

        group, fq = classify_call(name, codebase_lookup, library_lookup)

        if fq:
            decorators.append(
                {
                    "name": name,
                    "scope": group,
                    "importing_from": fq,
                }
            )

    return decorators


def _extract_function_calls(node, codebase_lookup, library_lookup):
    """Extract all function/symbol calls from the function body."""
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

    return {
        "codebase": sorted(used_codebase),
        "library": sorted(used_library),
    }


def extract_nested_functions(node, codebase_lookup, library_lookup, parent_name):
    """
    Extract metadata for functions defined inside another function.
    """
    nested_functions = []

    for inner in node.body:
        if not isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Create function info structure
        fn = _create_function_info_structure(inner, parent_function=parent_name)

        # Extract arguments (nested functions don't have vararg/kwarg typically, but handle them)
        for arg in inner.args.args + inner.args.kwonlyargs:
            fn["args"].append(
                {"name": arg.arg, **extract_arg_annotation(arg, codebase_lookup)}
            )

        # Extract decorators
        fn["decorators"] = _extract_decorators(inner, codebase_lookup, library_lookup)

        # Extract function calls
        fn["calls"] = _extract_function_calls(inner, codebase_lookup, library_lookup)

        # Recurse for deeper nested functions
        new_parent_path = f"{parent_name}/{inner.name}" if parent_name else inner.name

        deeper = extract_nested_functions(
            inner,
            codebase_lookup,
            library_lookup,
            parent_name=new_parent_path,
        )

        fn["depends"] = [d["name"] for d in deeper]

        nested_functions.append(fn)
        nested_functions.extend(deeper)

    return nested_functions


def extract_function_metadata(tree, codebase_lookup, library_lookup):
    """Extract metadata for all top-level functions in the AST tree."""
    functions = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Create function info structure
        func_info = _create_function_info_structure(node)

        # Extract arguments
        func_info["args"] = _extract_function_arguments(node, codebase_lookup)

        # Extract decorators
        func_info["decorators"] = _extract_decorators(
            node, codebase_lookup, library_lookup
        )

        # Extract function calls
        func_info["calls"] = _extract_function_calls(
            node, codebase_lookup, library_lookup
        )

        # Extract nested functions
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
