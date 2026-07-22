---
name: data-cleaning-checklist
description: Systematic checklist for cleaning a messy dataset before analysis
---
# Cleaning a dataset before analysis

When asked to clean or prepare a dataset, work through this checklist and
report what you find/do at each step — do not skip a step silently just
because it seems clean at a glance:

1. **Missing values**: identify which columns have them, how many, and
   propose a strategy per column (drop row, drop column, impute with
   mean/median/mode, or leave as a flagged "unknown" category) with a reason
   for the choice.
2. **Duplicates**: check for exact duplicate rows and duplicate keys (same
   identifier, different data) separately — they imply different fixes.
3. **Type coercion**: flag columns stored as the wrong type (numbers as
   strings, dates as strings, booleans as "Y"/"N" or 0/1) and state the target
   type.
4. **Outliers**: identify statistical outliers in numeric columns and decide,
   per case, whether they're data errors (fix/remove) or legitimate extreme
   values (keep, note for the analysis stage).
5. **Categorical normalization**: find inconsistent labels for the same
   category (casing, abbreviations, trailing whitespace, synonyms) and propose
   a canonical mapping.
6. **Document every transformation**: list each change made (or proposed) in
   order, so the cleaning is reproducible and auditable — never silently
   mutate data without a corresponding note.

End with a short summary of the dataset's readiness for analysis and any
remaining caveats.
