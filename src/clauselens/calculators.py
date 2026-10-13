"""Small, exact calculators that sit on top of extracted facts."""

from __future__ import annotations


def bond_cost(
    bond_amount: float, bond_months: float, months_served: float, mode: str = "pro_rata"
) -> dict[str, float | str]:
    """What an employee would owe on leaving after `months_served` of a service bond.

    mode "pro_rata": the unserved share of the amount; "full": the whole amount unless the
    bond period is completed. The clause text decides the mode, not this function.
    """
    if bond_amount < 0 or bond_months <= 0 or months_served < 0:
        raise ValueError("bond_amount must be >= 0, bond_months > 0 and months_served >= 0")
    if mode not in ("pro_rata", "full"):
        raise ValueError("mode must be 'pro_rata' or 'full'")
    remaining = max(0.0, bond_months - months_served)
    if remaining == 0:
        payable = 0.0
    elif mode == "full":
        payable = bond_amount
    else:
        payable = bond_amount * remaining / bond_months
    return {
        "payable": round(payable),
        "mode": mode,
        "remaining_months": round(remaining, 2),
        "bond_amount": round(bond_amount),
    }


def suggest_mode(flags: list[str]) -> str:
    return "full" if "full_amount_regardless" in flags else "pro_rata"
