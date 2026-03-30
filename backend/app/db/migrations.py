from __future__ import annotations

import logging

from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def migrate_sqlite_schema(engine: Engine) -> None:
    """Apply lightweight SQLite migrations for local-dev DBs.

    This project uses `Base.metadata.create_all()` (no Alembic), so we need
    one-off migrations when models change but a developer keeps an existing
    `expense_tracker.db`.

    Currently handles:
    - Legacy recurring tables created with columns:
      - interval_unit -> unit
      - interval_value -> interval
      - next_charge_at -> next_due_at
      - ends_at -> end_at
    - Adds missing `updated_at` column
    - Ensures unique index for (recurring_expense_id, due_at)
    """

    if not str(engine.url).startswith("sqlite"):
        return

    with engine.connect() as conn:
        # Does recurring_expenses exist?
        table_exists = conn.exec_driver_sql(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='recurring_expenses'"
        ).fetchone()
        if not table_exists:
            return

        cols = [
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(recurring_expenses)").fetchall()
        ]

        # Rename legacy columns if present.
        renames = {
            "interval_unit": "unit",
            "interval_value": "interval",
            "next_charge_at": "next_due_at",
            "ends_at": "end_at",
        }

        for old, new in renames.items():
            if old in cols and new not in cols:
                logger.info("Migrating recurring_expenses: renaming %s -> %s", old, new)
                conn.exec_driver_sql(f"ALTER TABLE recurring_expenses RENAME COLUMN {old} TO {new}")

        # Refresh columns after renames
        cols = [
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(recurring_expenses)").fetchall()
        ]

        # Add missing updated_at column (newer model writes to it).
        if "updated_at" not in cols:
            logger.info("Migrating recurring_expenses: adding updated_at column")
            conn.exec_driver_sql("ALTER TABLE recurring_expenses ADD COLUMN updated_at DATETIME")

        # Ensure unique index for idempotency on instances.
        instances_exist = conn.exec_driver_sql(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='recurring_expense_instances'"
        ).fetchone()
        if instances_exist:
            logger.info("Ensuring unique index uq_recurring_due_at")
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_recurring_due_at "
                "ON recurring_expense_instances (recurring_expense_id, due_at)"
            )

        conn.commit()
