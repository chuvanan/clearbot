---
name: chart-recommender
description: Recommend and sketch the right chart type for a data visualization question
---
# Recommending a chart

When asked to visualize data or choose a chart type, follow this process:

1. Restate the question being answered and identify the shape of the data:
   number of variables, their types (categorical/numeric/date/text), and
   approximate cardinality (few categories vs. many, short vs. long time
   series).
2. Recommend a chart type based on that shape, and say why, e.g.:
   - Comparing categories → bar chart
   - Trend over time → line chart
   - Relationship between two numeric variables → scatter plot
   - Distribution of one numeric variable → histogram
   - Correlation across many variables → heatmap
   - Part-to-whole with few categories → stacked bar (avoid pie/3D pie for
     more than ~5 categories)
3. Provide example plotting code (matplotlib by default, unless the user
   specifies another library) that produces the recommended chart from a
   plausible dataframe shape.
4. Note labeling and accessibility considerations: axis labels with units, a
   title stating the takeaway (not just the variable names), a colorblind-safe
   palette, and avoiding distorted axes (e.g. a truncated y-axis that
   exaggerates differences).

If the request is ambiguous about what should be compared, ask one clarifying
question before recommending a chart rather than guessing.
