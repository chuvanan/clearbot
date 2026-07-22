---
name: schema-design-review
description: Review or design a relational database schema for normalization, keys, and indexing
---
# Reviewing or designing a relational schema

When asked to design or review a database schema, work through this
checklist:

1. **Normalization**: check for 1NF (atomic columns, no repeating groups),
   2NF (no partial dependency on a composite key), and 3NF (no transitive
   dependencies). Call out any violation and what table split would fix it.
2. **Keys**: confirm every table has a clear primary key, and that foreign
   keys correctly reference the tables they depend on. Flag any relationship
   that's ambiguous (e.g. a column that looks like it should be a foreign key
   but isn't declared as one).
3. **Indexing**: identify columns that need an index — foreign keys, columns
   used in frequent `WHERE`/`JOIN`/`ORDER BY` clauses — and note the trade-off
   (faster reads, slower writes, more storage).
4. **Naming conventions**: check for consistency (singular vs. plural table
   names, casing, consistent `id`/`_id` suffixes) and flag inconsistencies.
5. **Denormalization**: if the schema is fully normalized, consider whether a
   specific, high-traffic query would benefit from denormalizing — state the
   trade-off explicitly (read speed vs. update anomalies/duplication) rather
   than recommending it by default.

Present the recommended schema (or changes) as a list of tables with their
columns, types, and keys — not just prose.
