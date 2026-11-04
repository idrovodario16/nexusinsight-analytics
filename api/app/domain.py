from datetime import datetime
from typing import List, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Operation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
    organization_id: UUID
    title: str = Field(min_length=3, max_length=120)
    sector: Literal['logistics', 'retail', 'services']
    status: Literal['pending', 'in_progress', 'completed', 'cancelled']
    amount_cents: int = Field(strict=True, ge=0, le=1000000000)
    revision: int = Field(strict=True, ge=1)
    created_at: datetime
    updated_at: datetime

    @field_validator('created_at', 'updated_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Timestamp must include a timezone')
        return value

    @field_validator('title')
    @classmethod
    def trimmed_title(cls, value):
        if len(value.strip()) < 3:
            raise ValueError('Title is too short')
        return value.strip()

class Event(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_id: UUID
    type: Literal['operation.upserted.v1']
    schema_version: Literal[1]
    source: Literal['nexuscore']
    organization_id: UUID
    occurred_at: datetime
    data: Operation

    @model_validator(mode='after')
    def same_tenant(self):
        if self.organization_id != self.data.organization_id:
            raise ValueError('Organization mismatch')
        if self.occurred_at.tzinfo is None:
            raise ValueError('Timestamp must include a timezone')
        return self

def metrics(rows: List[Operation]):
    done = [r for r in rows if r.status == 'completed']
    return {'total': len(rows), 'completed': len(done),
            'open': sum(r.status in ('pending', 'in_progress') for r in rows),
            'completion': round(len(done) / len(rows) * 100, 2) if rows else 0,
            'value_cents': sum(r.amount_cents for r in done)}
