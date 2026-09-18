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

`GitHubBountyScout` is a broad discovery source.

It queries public, open GitHub issues containing the word `bounty`, then keeps only candidates
with an explicit fiat-denominated amount in the issue title or body.

The filter is intentionally conservative. Bare numbers are ignored, and the scout does not yet
attempt to value crypto-token rewards.

Because generic GitHub search can surface aggregators, mirrors, or incomplete terms, every
candidate begins as `CIVIL_REVIEW`.

```bash
cog scan github-bounties --limit 25
```

## Frantic Bounties

`FranticBountyScout` is the first source-specific Scout.

It reads structured public mirror issues from `auscaster/frantic-board` and only emits a
candidate when all of these conditions are visible:

- `Worker price` is greater than zero;
- `Status` is `Available`;
- at least one slot remains available;
- a HTTPS claim URL points to `gofrantic.com/bounties/...`.

The mirror itself states that Frantic is the source of truth. Therefore the claim page must still
be checked before work begins, and these candidates also remain `CIVIL_REVIEW` for now.

```bash
cog scan frantic --limit 25
```

This source is intentionally narrow: stronger evidence is preferred over a high candidate count.

## Authentication

Optional authentication increases GitHub API rate limits:

```bash
export GITHUB_TOKEN=...
cog scan frantic
```

Do not commit the token. `.env` files are ignored by Git.

## Persisting observations

Either Scout can write JSONL without taking any action:

```bash
cog scan frantic --limit 50 --output data/frantic.jsonl
cog scan github-bounties --limit 50 --output data/github-bounties.jsonl
```

The CLI prints a final summary with `execution_performed=false`.
