# qngin

Python query engine. You describe **query templates** as plain dataclasses (`Flow`, fields, joins), pass a **JSON-like payload**, and qngin builds parameterized SQL for PostgreSQL or ClickHouse.

usable from scripts, FastAPI, Flask, or any host that can open a DB-API connection.

## Install

From PyPI (after the first release):

```bash
pip install qngin
```

From a local checkout (development):

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from qngin import (
    AggregateDef,
    FieldDef,
    Flow,
    JoinConditionDef,
    JoinDef,
    QueryEngine,
    PostgresDialect,
)
from qngin.executors import DbapiExecutor

flow = Flow(
    code="orders_export",
    base_table="orders",
    fields=[
        FieldDef(code="id", column="id", table="orders", selectable=True, filterable=True),
        FieldDef(code="customer_name", column="name", table="customers",
                 selectable=True, filterable=True),
    ],
    joins=[
        JoinDef(
            table="customers",
            alias="customers",
            join_type="left",
            conditions=[
                JoinConditionDef(
                    left="orders.customer_id",
                    operator="=",
                    right="customers.id",
                )
            ],
        )
    ],
)

engine = QueryEngine(dialect=PostgresDialect())
compiled = engine.compile(
    flow,
    {
        "select": ["id", "customer_name"],
        "where": {
            "logic": "AND",
            "items": [{"field": "id", "op": "=", "value": 42}],
        },
        "limit": 50,
    },
)
print(compiled.sql)    # SELECT ... WHERE orders.id = %s LIMIT %s
print(compiled.params) # (42, 50)

# Optional: run against any DB-API connection
# rows = list(engine.execute(flow, payload, executor=DbapiExecutor(conn)))
```

Host-supplied filters (e.g. auth / BAC) go through `extra_where`:

```python
engine.compile(flow, payload, extra_where={
    "logic": "AND",
    "items": [{"field": "id", "op": "IN", "value": [1, 2, 3]}],
})
```

## Payload schema

Business-level keys match `FieldDef.code` / `AggregateDef.code` (or their aliases):

```json
{
  "select": ["id", "customer_name"],
  "aggregates": ["total"],
  "where": {
    "logic": "AND",
    "items": [
      {"field": "id", "op": "=", "value": 1},
      {"field": "customer_name", "op": "CONTAINS", "value": "acme"}
    ]
  },
  "having": {"field": "total", "op": ">", "value": 10},
  "order_by": ["id", "-customer_name"],
  "limit": 20,
  "offset": 0
}
```

Supported operators: `=`, `!=`, `<`, `>`, `<=`, `>=`, `IN`, `NOT_IN`, `CONTAINS`, `STARTS_WITH`, `ENDS_WITH`, `IS_NULL`, `IS_NOT_NULL`.

Omit `select` to select all selectable fields on the flow.

## View-based flows

```python
from qngin import Flow, FlowType, FieldDef

flow = Flow(
    code="orders_v",
    flow_type=FlowType.VIEW,
    view_name="orders_view",
    fields=[
        FieldDef(code="id", column="id", view_column="id", selectable=True, filterable=True),
    ],
)
```

## Dialects & execution

| Class | Role |
|-------|------|
| `PostgresDialect` | PostgreSQL SQL (`ILIKE`, `CAST(... AS ...)`) |
| `ClickHouseDialect` | ClickHouse SQL (backtick ids, `toInt64`, …) |
| `DbapiExecutor` | Any DB-API 2.0 connection using `%s` placeholders |
| `CompiledQuery` | `(sql, params)` returned by `compile` / `translate` |

Placeholders are positional `%s` (psycopg style). `compile_count` wraps the query for totals.

## Physical JSON (no Flow)

```python
engine.compile_raw({
    "from": {"table_name": "orders", "alias": "orders"},
    "select": ["orders.id"],
    "where": {"left": "orders.id", "operator": "=", "right": 1},
    "limit": 10,
})
```

## Persistence

qngin does **not** store flows. Serialize `Flow` to JSON / your ORM and map back into the dataclasses. A Django host can keep existing `ConsumerFlow` models and convert them at the boundary.

## Layout

```
src/qngin/
  metadata/   # Flow, FieldDef, JoinDef, AggregateDef
  domain/     # QueryModel AST
  builders/   # Flow + payload → QueryModel
  dialects/   # SQL translators
  executors/  # DbapiExecutor
  engine.py   # public façade
```

## License

MIT — see [LICENSE](LICENSE).
