---
name: commit-messages
description: Write clear, conventional git commit messages from a description of changes
---
# Writing good commit messages

When asked to write a git commit message, follow these rules:

1. **Subject line**: imperative mood, lower-case after the type, no trailing
   period, max ~50 characters. Use a Conventional Commits prefix:
   - `feat:` a new feature
   - `fix:` a bug fix
   - `refactor:` code change that neither fixes a bug nor adds a feature
   - `docs:` documentation only
   - `test:` adding or fixing tests
   - `chore:` tooling, deps, or housekeeping

2. **Body** (optional, separated by a blank line): explain *what* changed and
   *why*, not *how*. Wrap at ~72 characters. Use bullet points for multiple
   distinct changes.

3. Do not invent changes that were not described. If the description is vague,
   write the best subject line you can and note what is unclear.

Output only the commit message, formatted in a code block.
