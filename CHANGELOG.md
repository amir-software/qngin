# Changelog

## 0.1.0 — 2026-07-29

Initial public release.

- Framework-agnostic query engine (`QueryEngine`)
- Plain metadata dataclasses: `Flow`, `FieldDef`, `JoinDef`, `JoinConditionDef`, `AggregateDef`
- PostgreSQL and ClickHouse dialects with parameterized SQL (`%s`)
- `DbapiExecutor` for any DB-API 2.0 connection
- Optional host `extra_where` for auth / policy filters
