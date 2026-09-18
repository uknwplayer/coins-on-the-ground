# Scouts

Scouts are read-only source adapters. They discover public candidates and normalize them into the
canonical Opportunity model.

A scout must not:

- claim a reward;
- move money or assets;
- submit work;
- use leaked credentials;
- authenticate as another party;
- infer ownership from technical accessibility.

## GitHub Bounties

The first real source is `GitHubBountyScout`.

It queries public, open GitHub issues containing the word `bounty`, then keeps only candidates
with an explicit fiat-denominated amount in the issue title or body.

The filter is intentionally conservative. Bare numbers are ignored, and the scout does not yet
attempt to value crypto-token rewards.

All GitHub candidates begin as `CIVIL_REVIEW`, not `CLEAR`, because the issue text may not contain
all eligibility, acceptance, payout, jurisdiction, or expiration terms.

### Run

```bash
python -m pip install -e ".[dev]"
cog scan github-bounties --limit 25
```

Optional authentication increases GitHub API rate limits:

```bash
export GITHUB_TOKEN=...
cog scan github-bounties
```

Do not commit the token. `.env` files are ignored by Git.

To preserve a scan as JSONL:

```bash
cog scan github-bounties --limit 50 --output data/github-bounties.jsonl
```

The CLI prints a final summary with `execution_performed=false`.
