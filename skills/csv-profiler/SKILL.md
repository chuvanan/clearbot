---
name: csv-profiler
description: Profile a CSV or tabular data file to summarize structure, quality issues, and notable patterns
---
# Profiling a tabular dataset

When asked to explore or profile a dataset, follow this process:

1. **Locate and read the file.** If filesystem tools are available, use
   `list_dir` to find the file and `read_text_file` to read it. If the file is
   large, read enough of it (header plus a representative sample of rows) to
   profile accurately without assuming you've seen every row.
2. **Describe the structure**: column names, inferred data type per column
   (numeric, categorical, date, text, boolean), and row count (exact if known,
   otherwise "at least N from the sample read").
3. **Flag data quality issues**: missing/blank values per column, duplicate
   rows or duplicate keys, inconsistent categorical labels (e.g. "NY" vs "New
   York"), and any column that doesn't match its inferred type (e.g. numbers
   stored as text).
4. **Compute quick summary stats** for numeric columns (min, max, mean,
   notable outliers) and cardinality for categorical columns (number of
   distinct values, most common values).
5. **Report 3-5 notable patterns or anomalies** worth investigating further —
   correlations, skew, unexpected concentrations — stated as observations, not
   conclusions.

Be explicit about what you actually read vs. inferred. Do not fabricate exact
statistics for rows you did not see — say "based on the first N rows" when
sampling.
