"""Unit tests for metadata → SQL compilation (no Django)."""

from qngin import (
    AggregateDef,
    FieldDef,
    Flow,
    FlowType,
    JoinConditionDef,
    JoinDef,
    OperandKind,
    PostgresDialect,
    QueryEngine,
    ClickHouseDialect,
)


def _orders_flow() -> Flow:
    return Flow(
        code="orders_export",
        base_table="orders",
        fields=[
            FieldDef(
                code="id",
                column="id",
                table="orders",
                selectable=True,
                filterable=True,
                orderable=True,
            ),
            FieldDef(
                code="customer_name",
                column="name",
                table="customers",
                selectable=True,
                filterable=True,
            ),
            FieldDef(
                code="amount",
                column="amount",
                table="orders",
                selectable=True,
                filterable=True,
                data_type="FLOAT",
            ),
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
        aggregates=[
            AggregateDef(
                code="total_amount",
                function="sum",
                table="orders",
                column="amount",
                alias="total_amount",
            ),
            AggregateDef(code="row_count", function="count", alias="row_count"),
        ],
    )


def test_compile_select_join_and_where():
    engine = QueryEngine(dialect=PostgresDialect())
    compiled = engine.compile(
        _orders_flow(),
        {
            "select": ["id", "customer_name"],
            "where": {
                "logic": "AND",
                "items": [{"field": "id", "op": "=", "value": 7}],
            },
            "order_by": ["-id"],
            "limit": 10,
            "offset": 5,
        },
    )

    sql = compiled.sql
    assert "SELECT" in sql
    assert "orders.id AS id" in sql
    assert "customers.name AS customer_name" in sql
    assert "LEFT JOIN customers customers ON" in sql
    assert "orders.customer_id = customers.id" in sql
    assert "WHERE" in sql
    assert "orders.id = %s" in sql
    assert "ORDER BY orders.id DESC" in sql
    assert "LIMIT %s" in sql
    assert "OFFSET %s" in sql
    assert compiled.params == (7, 10, 5)


def test_static_where_and_extra_where_merge():
    flow = _orders_flow()
    flow.static_where = {
        "logic": "AND",
        "items": [{"field": "amount", "op": ">", "value": 0}],
    }
    engine = QueryEngine(dialect=PostgresDialect())
    compiled = engine.compile(
        flow,
        {"select": ["id"]},
        extra_where={"field": "id", "op": "IN", "value": [1, 2]},
    )
    assert compiled.sql.count("%s") >= 3
    assert 0 in compiled.params
    assert 1 in compiled.params and 2 in compiled.params


def test_aggregates_and_group_by():
    engine = QueryEngine(dialect=PostgresDialect())
    compiled = engine.compile(
        _orders_flow(),
        {
            "select": ["id"],
            "aggregates": ["total_amount", "row_count"],
        },
    )
    assert "SUM(orders.amount) AS total_amount" in compiled.sql
    assert "COUNT(*) AS row_count" in compiled.sql
    assert "GROUP BY orders.id" in compiled.sql


def test_join_literal_operand():
    flow = Flow(
        code="lit",
        base_table="orders",
        fields=[
            FieldDef(code="id", column="id", table="orders", selectable=True),
        ],
        joins=[
            JoinDef(
                table="statuses",
                alias="statuses",
                conditions=[
                    JoinConditionDef(
                        left="orders.status_id",
                        operator="=",
                        right="active",
                        right_kind=OperandKind.VALUE,
                    )
                ],
            )
        ],
    )
    compiled = QueryEngine().compile(flow, {"select": ["id"]})
    assert "orders.status_id = %s" in compiled.sql
    assert "active" in compiled.params


def test_view_flow_clickhouse():
    flow = Flow(
        code="v",
        flow_type=FlowType.VIEW,
        view_name="orders_view",
        fields=[
            FieldDef(
                code="id",
                column="id",
                view_column="id",
                selectable=True,
                filterable=True,
            ),
        ],
    )
    engine = QueryEngine(dialect=ClickHouseDialect())
    compiled = engine.compile(
        flow,
        {
            "select": ["id"],
            "where": {"field": "id", "op": "=", "value": 3},
        },
    )
    assert "`orders_view`" in compiled.sql
    assert compiled.params == (3,)


def test_compile_count_strips_limit():
    engine = QueryEngine()
    count = engine.compile_count(
        _orders_flow(),
        {"select": ["id"], "limit": 10, "offset": 2},
    )
    assert "COUNT(*)" in count.sql
    assert "LIMIT" not in count.sql.upper().split("FROM")[0]
    assert count.params == ()


def test_contains_uses_bind_param():
    engine = QueryEngine()
    compiled = engine.compile(
        _orders_flow(),
        {
            "select": ["id"],
            "where": {"field": "customer_name", "op": "CONTAINS", "value": "acme"},
        },
    )
    assert "ILIKE %s" in compiled.sql
    assert compiled.params == ("%acme%",)


def test_mandatory_field_enforced():
    flow = _orders_flow()
    flow.fields[0].is_mandatory = True
    engine = QueryEngine()
    try:
        engine.compile(flow, {"select": ["customer_name"]})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "mandatory" in str(exc).lower()


def test_compile_raw_physical_json():
    engine = QueryEngine()
    compiled = engine.compile_raw(
        {
            "from": {"table_name": "orders", "alias": "orders"},
            "select": ["orders.id"],
            "where": {"left": "orders.id", "operator": "=", "right": 9},
            "limit": 1,
        }
    )
    assert "FROM orders orders" in compiled.sql
    assert compiled.params == (9, 1)


def test_dbapi_executor_sqlite():
    import sqlite3

    from qngin.executors import DbapiExecutor

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE orders (id INTEGER, amount REAL)")
    conn.execute("INSERT INTO orders VALUES (1, 10.5), (2, 20.0)")
    conn.commit()

    # SQLite uses ? — adapt %s for this smoke test
    class SqliteExecutor(DbapiExecutor):
        def execute(self, sql, params=None):
            sql = sql.replace("%s", "?")
            return super().execute(sql, params)

    flow = Flow(
        code="s",
        base_table="orders",
        fields=[
            FieldDef(
                code="id",
                column="id",
                table="orders",
                selectable=True,
                filterable=True,
            ),
        ],
    )
    engine = QueryEngine()
    rows = list(
        engine.execute(
            flow,
            {"select": ["id"], "where": {"field": "id", "op": "=", "value": 2}},
            executor=SqliteExecutor(conn),
        )
    )
    assert rows == [{"id": 2}]
    conn.close()
