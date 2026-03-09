# Headline Training Notes

File: `docs/headline_training_examples.jsonl`

Purpose:
- Provide stronger reference pairs for catchy but factual English title/body generation.
- Push the model toward sharper hooks and tighter descriptions.

Recommended use:
- Add 3 to 5 of the closest examples into the summarizer style bank.
- Keep title patterns focused on: actor + action + consequence.
- Keep body patterns focused on: key development + quick context + why it matters.

Target behavior:
- No vague openings.
- No generic filler like "This development...".
- No overhype or tabloid wording.
- Strong first sentence and cleaner second sentence.

Suggested expansion next:
- Add 50 more examples split across `Politics`, `Technology`, `Environment`, `Crime`, `Sports`, `Finance`, and `Entertainment`.
- Add both weak and strong pairs so prompt rewrites can learn what to avoid.
