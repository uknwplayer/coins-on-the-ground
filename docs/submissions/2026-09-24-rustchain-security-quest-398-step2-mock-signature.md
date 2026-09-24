# RustChain Security Quest #398 — Step 2

Claimant: `uknwplayer`  
Known fix reproduced: **Mock Signature Mode**  
Reward claimed: **15 RTC**  
Environment: local isolated test harness; no production endpoint was probed.

## What the bug class was

RustChain carries a compatibility/testing flag named `TESTNET_ALLOW_MOCK_SIG`. In a test environment this is useful because unit tests can bypass real Ed25519 verification. The risk is configuration leakage: if that flag were enabled in a production runtime, a node could accept the test-only signature path instead of requiring the normal cryptographic verification.

The current integrated node explicitly sets:

```python
TESTNET_ALLOW_MOCK_SIG = False
_MOCK_SIG_ALLOWED_ENVS = {"test", "testing", "dev", "development", "local", "testnet"}
```

and protects startup with:

```python
def enforce_mock_signature_runtime_guard():
    runtime_env = (
        os.environ.get("RC_RUNTIME_ENV")
        or os.environ.get("RUSTCHAIN_ENV")
        or "production"
    ).strip().lower()

    if TESTNET_ALLOW_MOCK_SIG and runtime_env not in _MOCK_SIG_ALLOWED_ENVS:
        raise RuntimeError(
            "TESTNET_ALLOW_MOCK_SIG must not be enabled outside test/dev runtimes"
        )
```

Source: `node/rustchain_v2_integrated_v2.2.1_rip200.py`, current main, around lines 111–124.

The WSGI production entry point calls the guard immediately after importing the integrated node and before database initialization:

```python
spec.loader.exec_module(rustchain_main)
rustchain_main.enforce_mock_signature_runtime_guard()
rustchain_main.enforce_hardware_binding_runtime_guard()
...
init_db()
```

Source: `node/wsgi.py`, current main.

## Why the fix is sufficient for this configuration failure

The guard has three important properties:

1. **Production is the default.** If neither `RC_RUNTIME_ENV` nor `RUSTCHAIN_ENV` exists, runtime resolves to `production`, so enabling mock signatures without an explicit test/dev environment fails closed.
2. **Only an explicit allowlist can use mocks.** The accepted values are test/development-style environments; arbitrary values do not pass.
3. **WSGI enforces it before initialization.** A production Gunicorn worker cannot continue to normal application startup with the forbidden flag enabled.

This fixes the known configuration class at startup. It does not replace normal Ed25519 verification; rather, it prevents the test bypass flag from being active where production verification is expected.

## Local reproduction

I reproduced the guard in an isolated local harness using the exact runtime decision and error condition from the current source. No live RustChain service was contacted.

Tests:

- `test_production_fails_closed`: set `TESTNET_ALLOW_MOCK_SIG=True` and `RC_RUNTIME_ENV=production`; expected `RuntimeError`.
- `test_test_runtime_allows_mock`: set the flag in `RC_RUNTIME_ENV=test`; expected successful return.
- `test_default_runtime_is_production`: enable the flag with both runtime environment variables absent; expected `RuntimeError`.

Result:

```text
test_default_runtime_is_production ... ok
test_production_fails_closed ... ok
test_test_runtime_allows_mock ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.001s

OK
```

## Conclusion

The known Mock Signature Mode issue is currently protected by a fail-closed runtime guard. My reproduction confirms that production and an unspecified/default runtime reject the test-only mock-signature mode, while an explicit test runtime remains allowed as intended.

**Step completed:** 2  
**Payout identity:** `uknwplayer`

This is a reproduction of a known fixed issue only. I did not probe or exploit any production endpoint.
