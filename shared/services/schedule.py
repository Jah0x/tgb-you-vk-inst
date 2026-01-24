from __future__ import annotations

from dataclasses import dataclass

from shared.models import ScheduleRule
from shared.storage import Storage


@dataclass(frozen=True)
class ScheduleRuleList:
    rules: list[ScheduleRule]


def list_active_rules(store: Storage) -> ScheduleRuleList:
    return ScheduleRuleList(rules=store.list_active_schedule_rules())


def get_schedule_state(store: Storage, rule_id: int) -> str | None:
    return store.get_schedule_state(rule_id)


def update_schedule_state(store: Storage, rule_id: int, last_run_at: str) -> None:
    store.update_schedule_state(rule_id, last_run_at)
