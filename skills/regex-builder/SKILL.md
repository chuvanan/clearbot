---
name: regex-builder
description: Build and explain regular expressions step by step from a plain-English description
---
# Building a regular expression

When asked to build a regex, follow this process:

1. Restate the matching goal in one sentence so the user can confirm intent.
2. Build the pattern incrementally, naming each piece (anchors, character
   classes, quantifiers, groups) and what it matches.
3. Present the final pattern in a code block.
4. Give 2-3 example strings that match and 1-2 that do NOT match.
5. Note the regex flavor assumed (default: PCRE / Python `re`) and flag any
   feature that differs across engines.

Prefer readable patterns over clever ones. If a non-regex approach would be
clearly better (e.g. a real parser for nested structures), say so.
