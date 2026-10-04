"""Explicit commands for the synthetic ANVAYA demo dataset.

Run from the backend directory:
    python -m seed.manage seed
    python -m seed.manage reset --confirm-reset-demo-data
"""

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

from seed.seeder import seed_database, seed_phase5_demo_data, seed_phase6_demo_data


def _alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    return Config(str(backend_root / "alembic.ini"))


def seed() -> None:
    """Apply migrations, then insert data only if the database is empty."""
    command.upgrade(_alembic_config(), "head")
    seed_database()


def reset() -> None:
    """Explicitly rebuild the configured database through Alembic, then seed it."""
    config = _alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    seed_database()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage fictional ANVAYA demo data.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("seed", help="Migrate and seed only an empty database.")
    subcommands.add_parser("seed-phase5", help="Add Phase 5 synthetic data to an existing base demo exactly once.")
    subcommands.add_parser("seed-phase6", help="Add idempotent Phase 6 synthetic catalog and portal workflow data.")
    reset_command = subcommands.add_parser("reset", help="Replace all data in the configured database.")
    reset_command.add_argument("--confirm-reset-demo-data", action="store_true", help="Required acknowledgement for the destructive reset.")
    args = parser.parse_args()

    if args.command == "seed":
        seed()
    elif args.command == "seed-phase5":
        command.upgrade(_alembic_config(), "head")
        seed_phase5_demo_data()
    elif args.command == "seed-phase6":
        command.upgrade(_alembic_config(), "head")
        seed_phase6_demo_data()
    elif args.confirm_reset_demo_data:
        reset()
    else:
        parser.error("reset requires --confirm-reset-demo-data")


if __name__ == "__main__":
    main()
