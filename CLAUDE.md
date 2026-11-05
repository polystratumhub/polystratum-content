# Rules for agents working in this repo

- Never push to `main`. Every change goes through a pull request. KV's merge is the only approval to publish.
- Never commit personal data: no lead names, emails, phone numbers or Lead IDs. Counts only. KV's own business email is the one exception.
- Never commit secrets. Tokens live in GitHub Actions secrets, never in files.
- A drafting PR contains the day's items, their media, and `approved/<date>.json` from `python -m gate manifest content/<date>`. Regenerate the manifest after any edit.
- Run `python -m pytest -q`, `python -m gate check` and `python -m gate verify` before opening a PR. All three must pass.
- Write the failing test first when adding or changing a rule, and show the rule can fail.
- Every statistic needs an https source in `sources` that maps 1:1 to the claim. The safe default is no statistics.
- Northern Trust appears in the past tense only. No logo.
- Never call the business "Cognix".
