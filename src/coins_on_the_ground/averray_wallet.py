from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

_DEFAULT_API_BASE = "https://api.averray.com"


@dataclass(frozen=True, slots=True)
class AverrayAuth:
    wallet: str
    token: str
    expires_at: str


def default_wallet_path() -> Path:
    return Path.home() / ".config" / "coins-on-the-ground" / "averray-wallet.json"


def _wallet_backend():
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError as exc:
        raise RuntimeError(
            'wallet support is not installed; run: pip install "coins-on-the-ground[wallet]"'
        ) from exc
    return Account, encode_defunct


def create_encrypted_wallet(path: Path, password: str) -> str:
    if len(password) < 12:
        raise ValueError("wallet password must be at least 12 characters")
    if path.exists():
        raise FileExistsError(f"wallet file already exists: {path}")

    Account, _ = _wallet_backend()
    account = Account.create()
    keystore = Account.encrypt(account.key, password)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(keystore, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return account.address


def load_account(path: Path, password: str):
    if not path.exists():
        raise FileNotFoundError(f"wallet file not found: {path}")

    Account, _ = _wallet_backend()
    keystore = json.loads(path.read_text(encoding="utf-8"))
    private_key = Account.decrypt(keystore, password)
    return Account.from_key(private_key)


async def authenticate_averray(
    path: Path,
    password: str,
    *,
    api_base: str = _DEFAULT_API_BASE,
) -> AverrayAuth:
    account = load_account(path, password)
    _, encode_defunct = _wallet_backend()

    async with httpx.AsyncClient(
        timeout=20.0,
        headers={"User-Agent": "coins-on-the-ground/0.1"},
        follow_redirects=False,
    ) as client:
        nonce_response = await client.post(
            f"{api_base.rstrip('/')}/auth/nonce",
            json={"wallet": account.address},
        )
        nonce_response.raise_for_status()
        nonce_payload = nonce_response.json()

        message = nonce_payload.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Averray nonce response did not contain a SIWE message")

        signed = account.sign_message(encode_defunct(text=message))
        signature = signed.signature.hex()

        verify_response = await client.post(
            f"{api_base.rstrip('/')}/auth/verify",
            json={"message": message, "signature": signature},
        )
        verify_response.raise_for_status()
        verify_payload = verify_response.json()

    token = verify_payload.get("token")
    wallet = verify_payload.get("wallet")
    expires_at = verify_payload.get("expiresAt")
    if not isinstance(token, str) or not token:
        raise ValueError("Averray verify response did not contain a bearer token")

    return AverrayAuth(
        wallet=wallet if isinstance(wallet, str) and wallet else account.address,
        token=token,
        expires_at=expires_at if isinstance(expires_at, str) else "",
    )


async def preflight_averray_jobs(
    path: Path,
    password: str,
    job_ids: tuple[str, ...],
    *,
    api_base: str = _DEFAULT_API_BASE,
) -> list[dict[str, Any]]:
    if not job_ids:
        raise ValueError("at least one job id is required")

    auth = await authenticate_averray(path, password, api_base=api_base)
    headers = {
        "Authorization": f"Bearer {auth.token}",
        "User-Agent": "coins-on-the-ground/0.1",
    }

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(
        timeout=20.0,
        headers=headers,
        follow_redirects=False,
    ) as client:
        for job_id in job_ids:
            response = await client.get(
                f"{api_base.rstrip('/')}/jobs/preflight",
                params={"jobId": job_id},
            )
            row: dict[str, Any] = {
                "job_id": job_id,
                "wallet": auth.wallet,
                "http_status": response.status_code,
            }
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text[:500]}
            row["preflight"] = payload
            results.append(row)

    return results
