from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DeviceIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=120)
    counter_capacity: int = Field(gt=0)
    max_rate_per_sec: int = Field(gt=0)
    shifts: Optional[list[dict]] = None

    @field_validator('code', 'name')
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('不能为空')
        return v


class ReadingRow(BaseModel):
    """单条带时点读数；时间接受 ISO 8601（带/不带时区均按 Asia/Shanghai 朴素值处理）。"""
    read_at: datetime
    total_input: int = Field(ge=0)
    total_good: int = Field(ge=0)
    meter_changed: bool = False
    handover_input: Optional[int] = Field(default=None, ge=0)
    handover_good: Optional[int] = Field(default=None, ge=0)

    @field_validator('meter_changed', mode='before')
    @classmethod
    def _boolish(cls, v):
        if isinstance(v, str):
            if v.strip().lower() in ('1', 'true', 'yes', 'y', '是', '换表'):
                return True
            if v.strip().lower() in ('0', 'false', 'no', 'n', '否', ''):
                return False
        return v


class ImportPayload(BaseModel):
    idempotency_key: str = Field(min_length=4, max_length=80)
    device_code: Optional[str] = Field(default=None, max_length=60)  # 单设备导入；CSV 多设备可在每行携带
    actor: str = Field(default='operator', max_length=120)
    readings: list[ReadingRow] = Field(min_length=1)
