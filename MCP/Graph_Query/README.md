# Graph Query MCP - Knowledge Graph Traversal Agent

## Overview

The Graph Query MCP specializes in knowledge graph traversal and relationship queries. It provides tools to execute Cypher queries against Neo4j and analyze the codebase's structural relationships.

## Features

- **Entity Discovery**: Find classes, functions, and modules by name
- **Dependency Analysis**: Trace what entities depend on others and vice versa
- **Import Tracing**: Follow complete import chains through modules
- **Relationship Queries**: Query any relationship type in the graph
- **Usage Pattern Detection**: Understand how entities are used across the codebase
- **Circular Dependency Detection**: Identify problematic dependency cycles
- **Custom Query Execution**: Run custom read-only Cypher queries with safety constraints
- **Codebase Statistics**: Get overview metrics about the indexed codebase

## Available Tools

### 1. `find_entity(name, entity_type)`

Locate a class, function, or module by name.

**Parameters:**

- `name` (string): Name or partial name of the entity
- `entity_type` (string, optional): Filter by type (Function, Class, Module)

**Returns:** Matching entities with their properties

**Example:**

```json
{
  "name": "routing",
  "entity_type": "Function"
}
```

### 2. `get_dependencies(entity_name)`

Find what an entity depends on.

**Parameters:**

- `entity_name` (string): Name of the entity to analyze

**Returns:** List of all entities this one depends on

**Example:** Find what the `APIRouter` class depends on

```json
{
  "entity_name": "APIRouter"
}
```

### 3. `get_dependents(entity_name)`

Find what depends on an entity.

**Parameters:**

- `entity_name` (string): Name of the entity to analyze

**Returns:** List of all entities that depend on this one

**Example:** Find all functions that use `Request`

```json
{
  "entity_name": "Request"
}
```

### 4. `trace_imports(module_name, max_depth)`

Follow import chain for a module.

**Parameters:**

- `module_name` (string): Module to trace imports for
- `max_depth` (integer, optional): Maximum traversal depth (1-10, default: 5)

**Returns:** All import paths from the module

**Example:** Trace all imports in the routing module

```json
{
  "module_name": "fastapi/routing.py",
  "max_depth": 3
}
```

### 5. `find_related(entity_name, relationship_type)`

Get entities related by specified relationship type.

**Parameters:**

- `entity_name` (string): Source entity name
- `relationship_type` (string): Relationship type (IMPORTS, INHERITS_FROM, DECORATED_BY, DEPENDS_ON, etc.)

**Returns:** Entities connected via the specified relationship

**Example:** Find all classes that inherit from a base class

```json
{
  "entity_name": "BaseModel",
  "relationship_type": "INHERITS_FROM"
}
```

### 6. `execute_query(query, parameters)`

Run custom Cypher query with safety constraints.

**Parameters:**

- `query` (string): Cypher query (READ-ONLY operations only)
- `parameters` (string, optional): JSON string with query parameters

**Returns:** Query results

**Safety Constraints:**

- Only read-only operations (MATCH, RETURN, WHERE, etc.)
- No DELETE, REMOVE, SET, CREATE, or MERGE operations
- No system procedure calls

**Example:** Find all functions in a module

```json
{
  "query": "MATCH (m:Module {name: $module})-[:CONTAINS]->(f:Function) RETURN f.name as name",
  "parameters": "{\"module\": \"fastapi/routing.py\"}"
}
```

### 7. `find_usage_patterns(entity_name)`

Identify usage patterns across the codebase.

**Parameters:**

- `entity_name` (string): Entity to analyze

**Returns:** Comprehensive usage pattern data including dependencies, decorators, and inheritance

**Example:** Analyze how `Request` is used

```json
{
  "entity_name": "Request"
}
```

### 8. `get_code_statistics()`

Get statistics about the indexed codebase.

**Parameters:** None

**Returns:** Overall metrics about modules, functions, classes, and relationships

**Example:**

```json
{
  "module_count": 45,
  "function_count": 320,
  "class_count": 87,
  "dependency_count": 1250,
  "import_count": 450
}
```

### 9. `find_circular_dependencies()`

Find circular dependencies in the codebase.

**Parameters:** None

**Returns:** List of circular dependency chains

**Example:** Returns circular paths where entities depend on each other

### 10. `find_entity_by_type(entity_type)`

Find all entities of a specific type.

**Parameters:**

- `entity_type` (string): Type to search (Function, Class, Module)

**Returns:** All entities of the specified type (limited to 100)

## Usage Examples

### Find all functions that import a specific module

```
1. Use `find_related` with relationship_type="IMPORTS"
2. Find all modules that import the target module
```

### Trace dependencies in a function call chain

```
1. Start with `find_entity` to locate the target function
2. Use `get_dependencies` to see what it calls
3. For each dependency, use `get_dependencies` again (recursion)
4. Or use `execute_query` with a path query for deeper analysis
```

### Identify highly coupled modules

```
1. Get codebase statistics with `get_code_statistics`
2. Use `find_circular_dependencies` to find problematic patterns
3. Investigate specific modules with `get_dependencies` and `get_dependents`
```

### Analyze inheritance hierarchies

```
1. Use `find_related` with relationship_type="INHERITS_FROM"
2. For each found class, recursively trace inheritance
```

## Graph Schema

### Nodes

- **Module**: Represents Python modules/packages
- **Class**: Represents classes
- **Function**: Represents functions and methods
- **Parameter**: Function parameters
- **Docstring**: Documentation strings
- **Import**: Import statements

### Relationships

- **IMPORTS**: Module imports another module
- **CONTAINS**: Module/Class contains Function/Class
- **DEPENDS_ON**: Entity depends on another entity
- **INHERITS_FROM**: Class inherits from another class
- **DECORATED_BY**: Function/Class is decorated by another function
- **HAS_PARAMETER**: Function has parameters
- **DOCUMENTED_BY**: Entity has documentation

## Configuration

### Environment Variables

Set in `.env`:

```
NEO4J_URL=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

## Error Handling

All tools return JSON responses with a status field:

- `"status": "success"` - Operation succeeded
- `"status": "error"` - Operation failed (see message field)

Example error response:

```json
{
  "status": "error",
  "message": "Entity 'unknown_function' not found"
}
```

## Performance Considerations

- Queries are limited to prevent timeout
- Large result sets are limited (max 100-1000 items depending on query)
- Use `max_depth` parameter to limit traversal depth
- For complex analysis, consider using `execute_query` with optimized Cypher

## Security

The `execute_query` tool includes safety constraints:

- Prevents destructive operations (DELETE, REMOVE, SET)
- Blocks system procedure calls
- Only allows read-only operations
- Parameters are properly escaped

## Integration with Other MCPs

This Graph Query MCP works in conjunction with:

- **Indexer MCP**: Builds the knowledge graph by analyzing code
- **Analysis MCP**: Performs higher-level analysis using graph data
