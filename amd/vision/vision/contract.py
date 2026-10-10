"""Typed wire contract (docs/vision-contract.md, version 2026-10-10.vision.1)."""
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

Kind = Literal["auto", "thermal", "gauge", "acoustic_imager", "spectrogram", "orbit_screenshot", "visual"]


class Logged(BaseModel):
    model_config = ConfigDict(extra="ignore")
    reading_id: Optional[str] = Field(None, max_length=128)
    measurement_type: Optional[str] = Field(None, max_length=64)
    value: float
    unit: Optional[str] = Field(None, max_length=16)


class Hints(BaseModel):
    model_config = ConfigDict(extra="ignore")
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=16)
    sweep_deg: Optional[float] = Field(None, gt=10, le=360)


class VisionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    request_id: Optional[str] = Field(None, max_length=128)
    media_id: Optional[str] = Field(None, max_length=256)
    kind: Kind = "auto"
    action_type: Optional[str] = Field(None, max_length=64)
    image_b64: str
    logged: Optional[Logged] = None
    hints: Optional[Hints] = None
    annotate: bool = True


class OcrRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_b64: str
    upscale: Optional[bool] = None


class OcrWord(BaseModel):
    text: str
    bbox: List[int]
    conf: float


class Router(BaseModel):
    label: str
    method: Literal["kind", "action_type", "heuristic", "default"]
    confidence: float


class VisionReading(BaseModel):
    id: str
    quantity: str
    value: float
    unit: str
    confidence: float = Field(ge=0, le=1)
    method: str
    flags: List[str] = []
    bbox: Optional[List[int]] = None
    point: Optional[List[int]] = None
    note: Optional[str] = None


class KeyResult(BaseModel):
    name: str
    units: str
    value: Union[float, str, None]


class Comparison(BaseModel):
    logged_id: Optional[str]
    logged_value: float
    logged_unit: str
    vision_id: str
    vision_value: float
    delta: float
    tolerance: float
    agrees: Optional[bool]
    flags: List[str] = []


class Alert(BaseModel):
    title: str
    severity: int = Field(ge=0, le=4)
    source: str


class VisionResponse(BaseModel):
    media_id: str
    kind: str
    router: Router
    ocr: List[OcrWord]
    readings: List[VisionReading]
    key_results: List[KeyResult]
    comparison: Optional[Comparison]
    alert: Optional[Alert]
    flags: List[str]
    annotated_image_b64: Optional[str]
    annotated_mime: Optional[str]
    latency_ms: int
    version: dict


class OcrResponse(BaseModel):
    words: List[OcrWord]
    width: int
    height: int
    latency_ms: int
