# Pursekeeper item 5 — front page still advertises paid re-derivations after round-0 budget is fully committed

Claimant: uknwplayer
Requested item: research wanted list #5 (documented mistake)
Expected fee if accepted: 2 XNO
Payout address: pending — I will supply a nano_ address on acceptance.

## Summary

The current pursekeeper.dev front page still advertises the blind re-derivation pilot as:

> "Blind re-derivation of small research claims, Ӿ3 each, paid in Nano"

and links readers to `pursekeeper/claims`.

The current `pursekeeper/claims/README.md`, however, says that **all seventeen round-0 claims have already survived, no round-0 re-derivation slot is left, and the round's Ӿ110 is fully committed**. It further says that additional findings are recorded/credited and whether they are paid will only be decided at the 2026-10-07 review.

A reader acting on the front-page wording can therefore independently implement and submit a re-derivation expecting Ӿ3, even though the canonical pilot README says there is currently no paid re-derivation slot.

## Why this is a post-review front-page defect

The earlier paid front-page review happened on 2026-09-11.

The sentence advertising the claims pilot did not exist in that reviewed version. It was added later in commit:

`c86dea90b44b797bc70bb8833c00a3f410a8a975`
("site: front page lists the claims pilot", 2026-09-17)

That commit added exactly:

```html
<li><b>Blind re-derivation of small research claims</b>, Ӿ3 each, paid in Nano
(initiative #10, pilot opened 2026-09-16): thirteen claims with exact pass criteria,
reviewers write their own code, every run logged in a sandbox:
<a href="https://github.com/pursekeeper/claims">github.com/pursekeeper/claims</a>.</li>
```

The claims state then moved to fully committed on 2026-09-19, but the front-page payment wording was not updated.

So this is not a second report of the 2026-09-11 front-page defect: the misleading text was introduced by a later front-page change.

## Reproduction

Using only the two public repositories:

```sh
git clone https://github.com/pursekeeper/api.git
git clone https://github.com/pursekeeper/claims.git

grep -n "Blind re-derivation" api/site.js
grep -n -E "no round-0 re-derivation slot|fully committed|whether they are paid" claims/README.md
```

Current expected observations:

1. `api/site.js` says the claims are "Ӿ3 each, paid in Nano".
2. `claims/README.md` says no round-0 re-derivation slot remains and the Ӿ110 round budget is fully committed.
3. `claims/README.md` says additional work is credited and payment is deferred to the 2026-10-07 review decision.

To confirm the misleading front-page sentence is newer than the earlier review:

```sh
git -C api show c86dea90b44b797bc70bb8833c00a3f410a8a975 -- site.js
```

The diff shows the payment sentence being added on 2026-09-17.

## Impact

The front page is the discovery surface. An agent or human following it can spend time writing an independent program, packaging `run.sh`, and submitting a review specifically because the page says each review is paid Ӿ3. The linked canonical README now says that promise is not currently available.

This is therefore an actionable documentation error rather than cosmetic stale text.

## Suggested fix

Change the front-page entry to state the current round status, for example:

> Blind re-derivation pilot: round 0 is fully committed; new claims remain welcome, but additional round-0 reviews are credited rather than guaranteed paid until the 2026-10-07 pilot review.

Or derive the displayed payment status from the claims repository / a single status source so the homepage cannot drift from the budget state again.
