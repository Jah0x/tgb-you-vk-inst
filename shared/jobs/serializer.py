from __future__ import annotations

import json
from dataclasses import asdict

from shared.jobs.models import Job


def to_json(job: Job) -> str:
    return json.dumps(asdict(job), ensure_ascii=False)


def from_json(payload: str) -> Job:
    data = json.loads(payload)
    return Job(**data)
