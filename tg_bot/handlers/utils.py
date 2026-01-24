from __future__ import annotations

def format_accounts(accounts: list[str]) -> str:
    if not accounts:
        return "(пока нет аккаунтов)"
    return "\n".join(f"• {name}" for name in accounts)
