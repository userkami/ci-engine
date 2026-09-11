"""Atomic credit ledger operations.

The credit balance is the platform's money: every mutation goes through a
single-writer pattern using ``SELECT ... FOR UPDATE`` (pessimistic row
locking) so concurrent requests can never double-spend or push a balance
below zero. See SPEC.md section 4 "Transaction Constraint".
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JOB_COST_CREDITS, UserCredit

__all__ = [
    "CreditError",
    "InsufficientCreditsError",
    "NoCreditProfileError",
    "JOB_COST_CREDITS",
    "deduct_credits",
    "restore_credits",
    "get_credit_balance",
]


class CreditError(Exception):
    """Base class for credit ledger domain errors."""


class NoCreditProfileError(CreditError):
    """Raised when a user has no matching ``user_credits`` row."""


class InsufficientCreditsError(CreditError):
    """Raised when a deduction would take the balance below zero."""


async def deduct_credits(
    session: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
) -> bool:
    """Atomically deduct ``amount`` credits from ``user_id``.

    The target row is locked with ``FOR UPDATE`` for the lifetime of the
    transaction, serialising concurrent deductions and guaranteeing the
    ``balance >= 0`` invariant.

    Returns ``True`` when the deduction was applied and the transaction
    committed. Returns ``False`` when the user has no credit profile or an
    insufficient balance; in both failure cases the (no-op) transaction is
    rolled back so no partial state is persisted and the lock is released.

    Raises ``ValueError`` when ``amount`` is not a positive integer.
    Database errors propagate to the caller for retry handling.
    """
    if amount <= 0:
        raise ValueError("amount must be a positive integer")

    result = await session.execute(
        select(UserCredit)
        .where(UserCredit.user_id == user_id)
        .with_for_update()
    )
    row = result.scalar_one_or_none()

    if row is None or row.balance < amount:
        # Nothing was changed; roll back to release the row lock and abort
        # the implicit transaction.
        await session.rollback()
        return False

    try:
        row.balance -= amount
        # ``updated_at`` is refreshed automatically via ``onupdate``.
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return True


async def restore_credits(
    session: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
) -> None:
    """Atomically add ``amount`` back to ``user_id`` (compensation).

    Used to refund a deduction when job dispatch fails (POST
    ``/api/jobs/create``). Locks the row the same way as
    :func:`deduct_credits` so concurrent ledger operations stay safe.
    Creates the profile row when missing so refunds never get lost.

    Raises ``ValueError`` when ``amount`` is not a positive integer.
    """
    if amount <= 0:
        raise ValueError("amount must be a positive integer")

    result = await session.execute(
        select(UserCredit)
        .where(UserCredit.user_id == user_id)
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserCredit(user_id=user_id, balance=0)
        session.add(row)
        await session.flush()
    row.balance += amount
    await session.commit()


async def get_credit_balance(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """Return the current credit balance for ``user_id``.

    Raises :class:`NoCreditProfileError` when the user has no row yet;
    balance defaults are applied on profile creation.
    """
    result = await session.execute(
        select(UserCredit.balance).where(UserCredit.user_id == user_id)
    )
    balance = result.scalar_one_or_none()
    if balance is None:
        raise NoCreditProfileError(
            f"no credit profile found for user {user_id}"
        )
    return balance