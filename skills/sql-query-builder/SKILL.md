---
name: sql-query-builder
description: Build and explain a SQL query step by step from a plain-English request
---
# Building a SQL query

When asked to write a SQL query, follow this process:

1. Restate the question being answered in one sentence so the user can
   confirm intent, and note any assumptions about the schema (table/column
   names) if they weren't given explicitly.
2. Build the query incrementally, naming each clause and what it contributes:
   `SELECT` (columns/aggregates), `FROM`/`JOIN` (tables and join conditions),
   `WHERE` (row filters), `GROUP BY`/`HAVING` (aggregation), `ORDER BY`/`LIMIT`
   (result shaping).
3. Present the final query in a single code block.
4. Note any indexing or performance considerations (e.g. "this JOIN benefits
   from an index on `orders.customer_id`") and call out anything that could be
   slow on a large table (unindexed filters, `SELECT *`, correlated
   subqueries).
5. State the SQL dialect assumed (default: ANSI SQL / PostgreSQL) and flag any
   syntax that differs across engines (e.g. `LIMIT` vs `TOP`, date functions).

Prefer explicit column lists over `SELECT *`, and explicit `JOIN ... ON` over
implicit comma joins.
