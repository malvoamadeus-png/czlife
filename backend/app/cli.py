from __future__ import annotations

import asyncio

import typer

from .config import get_settings
from .db import Database
from .domain.validator import validate_plan
from .seed import build_demo_plan, demo_nodes, demo_rules
from .store import StoryStore

cli = typer.Typer(help="CZ Life private operator commands")


def get_store() -> StoryStore:
    settings = get_settings()
    store = StoryStore(Database(settings))
    store.init()
    return store


@cli.command("init-demo")
def init_demo() -> None:
    store = get_store()
    plan = build_demo_plan()
    plan_hash = validate_plan(plan, demo_nodes())
    store.save_plan(plan, demo_nodes(), demo_rules(), plan_hash)
    typer.echo(f"seeded {plan.plan_id} v{plan.version} hash={plan_hash}")


@cli.command("lock")
def lock() -> None:
    store = get_store()
    plan = build_demo_plan()
    plan_hash = validate_plan(plan, demo_nodes())
    store.lock_plan(plan.plan_id, plan.version, plan_hash)
    typer.echo(f"locked {plan.plan_id} v{plan.version}")


@cli.command("status")
def status() -> None:
    typer.echo_json(get_store().snapshot())


@cli.command("worker")
def worker() -> None:
    from .worker import main as worker_main

    asyncio.run(worker_main())


def main() -> None:
    cli()


if __name__ == "__main__":
    main()

