# Pursekeeper item 2(a) — iLands native iLander workspace

Status: hold requested by email on 2026-09-25; firsthand testing has not yet been performed.

## Scope

Only the native hosted iLander workspace counts. BYOA Codex/Claude Code is excluded because it
brings an outside runtime. Public documentation is context only; the paid report must be firsthand.

## Safety constraints

- Fresh throwaway Nano test key only.
- Never place the user's real wallet seed in iLands.
- Do not send funds.
- Prefer deterministic offline signing.
- Network tests are harmless reads or deliberately non-settling probes.
- Capture timestamps, product/app version, plan, prompts/actions and exact responses.

## Five-point test

1. **Exact hosted surface** — app version, OS, plan/tier, native model/runtime, UTC timestamp.
2. **Persistence/confidentiality** — store a throwaway seed-shaped marker, start a later run,
   read it back, and determine whether owner/editor/export/public surfaces can inspect it.
3. **Nano signing** — inside the native workspace derive a test account and sign a deterministic
   Nano state block with Ed25519-Blake2b; capture block fields, hash, signature and code; verify
   independently outside iLands. Do not broadcast.
4. **Outbound HTTPS** — harmless POST to pursekeeper /v1/account_info; test /v1/process only with
   an explicitly safe non-settling fixture. Capture exact status/response or refusal.
5. **No-click autonomy** — configure a native recurring action that performs a harmless check;
   record trigger creation, human approvals, execution timestamp and resulting artifact/log.

## Verdict template

```text
Product/version:
Plan:
Native surface:
Persistence:
Who can read stored material:
Nano signing:
Outbound HTTPS:
Recurring/no-click execution:
Human actions required:
Verdict:
Limitations:
```

Requested listed fee: 3 XNO on acceptance.
