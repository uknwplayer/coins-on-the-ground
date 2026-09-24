# StellarLend bug bounty — MigrationHub marks migrations completed after pulling user tokens but never deposits or refunds them

Claimant: uknwplayer  
Repository: Smartdevs17/stellarlend  
Affected contract: `stellar-lend/contracts/migration-hub`  
Suggested severity: High (direct user-fund lock / broken migration atomicity; maintainer decides)  
Testing: static source review + repository's own unit-test behavior only. No production transaction was sent.

## Summary

`MigrationHub::migrate()` can transfer real user tokens into the MigrationHub contract and then mark the migration `Completed` without forwarding those tokens to the configured StellarLend lending contract.

There is also no user withdrawal/refund function in the MigrationHub for those retained tokens.

The repository's own unit test confirms this behavior: after a 500-token migration, it asserts that the MigrationHub itself still holds all 500 tokens while the record is `Completed`.

This violates the original migration requirements, which call for atomic source withdrawal -> destination deposit, and can leave user assets stranded in the hub.

## Affected paths

### 1. StellarOther adapter really moves tokens into the Hub

`stellar-lend/contracts/migration-hub/src/adapter.rs`:

```rust
let token = soroban_sdk::token::Client::new(env, asset);
token.transfer(user, &env.current_contract_address(), &amount);
```

So despite the "Mock" comment, this is a real Soroban token transfer from the authenticated user into the current MigrationHub contract.

### 2. AaveMock does the same real transfer

`stellar-lend/contracts/migration-hub/src/lib.rs`:

```rust
ProtocolType::AaveMock => {
    let token = soroban_sdk::token::Client::new(&env, &asset);
    token.transfer(&user, &env.current_contract_address(), &amount);
    Ok(())
}
```

### 3. The destination-deposit step is removed / simulated

Immediately afterward, the implementation explicitly does not call the configured lending contract:

```rust
// 3. Deposit into StellarLend
// The Hub is now the temporary holder of the funds.
// Note: The deposit step is simulated ...
// A `LendingClient` no longer exists ...
//
// Simplified: The hub successfully pulled the funds. The user can now deposit directly.
// In a real migration tool, this would be atomic.
```

But the user cannot "deposit directly" with the same tokens after this call because those tokens are no longer in the user's balance; they are held by the MigrationHub.

The contract then records:

```rust
record.status = MigrationStatus::Completed;
Self::save_migration(&env, id, &record);
Self::update_analytics(&env, true, amount);
```

### 4. No refund / rescue path for the user

I searched the current MigrationHub implementation for a user withdrawal/refund/rescue path from `env.current_contract_address()` back to the migration owner and found none.

`emergency_rollback()` only changes metadata:

```rust
record.status = MigrationStatus::Failed;
Self::save_migration(&env, migration_id, &record);
```

It does not transfer the retained asset back to the user.

### 5. verify_migration reports the stranded migration as successful

```rust
pub fn verify_migration(env: Env, migration_id: u64) -> Result<bool, MigrationError> {
    let record = Self::get_migration(env.clone(), migration_id)
        .ok_or(MigrationError::MigrationFailed)?;

    if record.status != MigrationStatus::Completed {
        return Ok(false);
    }

    Ok(true)
}
```

The function's comment says it verifies that funds are present in the lending protocol, but it performs no balance or destination check.

## Repository's own test reproduces the lock

`stellar-lend/contracts/migration-hub/src/test.rs::test_migration_stellar_other`:

1. Mints 1000 tokens to a user.
2. Calls `migrate(..., amount = 500)`.
3. Asserts:
   - record.status == Completed
   - record.amount == 500
   - **token.balance(MigrationHub) == 500**

The test therefore demonstrates exactly that the migration is considered successful while the entire migrated principal is still owned by the MigrationHub contract.

## Contrast with the repository's PoolMigration implementation

`stellar-lend/contracts/pool-migration/src/lib.rs` models the expected atomic flow correctly:

```rust
token.transfer(&user, &env.current_contract_address(), &amount);
token.transfer(&env.current_contract_address(), &destination_pool, &amount);
```

MigrationHub performs only the first transfer.

## Minimal safe reproduction

In the Soroban test environment:

1. Deploy MigrationHub.
2. Initialize it with a lending destination address.
3. Register a Stellar asset token.
4. Mint 1000 units to Alice.
5. Alice calls `migrate(Alice, StellarOther, source, asset, 500)`.
6. Observe:
   - Alice balance decreases by 500.
   - MigrationHub balance increases by 500.
   - configured lending contract receives 0.
   - migration record is `Completed`.
   - `verify_migration(id)` returns true.
7. Search exposed MigrationHub functions: there is no user path to withdraw/refund the 500 retained tokens.

No production system or third-party funds are required to reproduce this.

## Impact

A user following the migration interface can permanently lose access to the assets being "migrated":

- real tokens leave the user's wallet;
- destination lending contract receives none;
- the hub records success;
- analytics count the value as migrated;
- `verify_migration()` returns true;
- no user refund path returns the tokens.

This is more than cosmetic bookkeeping: the contract actually takes custody of the user's asset and leaves it there.

The original pool-migration feature specification (#578/#612) requires:

- withdraw from source pool -> deposit to destination pool in one atomic action;
- support for partial migration;
- uninterrupted migration flow.

The cross-protocol migration feature (#255) similarly requires asset bridging/migration verification.

## Severity

Suggested: **High**, conservatively.

The defect causes direct loss of access to user funds through normal intended use of an in-scope contract. I am not claiming attacker theft because the assets remain in the MigrationHub; the concrete impact is a fund-lock / broken money-moving workflow.

If maintainers treat MigrationHub as non-production prototype code, deployment context may lower practical severity.

## Suggested remediation

1. Do not transfer user assets into the Hub unless the destination deposit can complete atomically.
2. After pulling funds, invoke the configured lending contract's real deposit flow in the same transaction.
3. Mark `Completed` only after the destination position/balance is verified.
4. On any destination failure, let the Soroban transaction revert atomically rather than persisting a partial migration.
5. If custody across transactions is intentional, add a strictly owner-bound refund/rescue path and explicit Pending state.
6. Make `verify_migration()` verify actual destination state instead of trusting the record status.
7. Add balance-invariant tests:
   - successful migration: hub ending balance for migrated amount = 0;
   - destination receives the amount / position;
   - user does not lose funds if destination step fails.

## Duplicate check

Searched open and closed issues for:
- MigrationHub funds stuck / stranded tokens;
- migration-hub deposit lending;
- MigrationHub Completed funds;
- pull_funds migration;
- migration hub refund;
- verify_migration.

No matching bug-bounty report was found.

## AI assistance disclosure

AI assistance was used for source inspection and drafting. Findings are limited to current public source and existing test behavior.
