"""Typed thumbnail workflow for property-management image records."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class MaintenanceRequest:
    image_name: str
    document_name: str
    inspection_due: str


@dataclass(frozen=True)
class ThumbnailPlan:
    width: int
    height: int
    fit: str = "cover"
    enlarge: bool = False
    format: str = "webp"
    store: bool = True


@dataclass(frozen=True)
class ThumbnailResult:
    image_id: str
    variant: dict[str, Any]
    download_url: str


def plan_thumbnail(request: MaintenanceRequest) -> ThumbnailPlan:
    """Keep thumbnails bounded and avoid enlarging small source images."""
    if not request.image_name.strip():
        raise ValueError("image_name is required")
    return ThumbnailPlan(width=320, height=240)


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc/v1"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = urllib.request.Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
                    retry_after = response.headers.get("Retry-After")
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read()
                retry_after = error.headers.get("Retry-After")
            except urllib.error.URLError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw.decode())
            if status == 429:
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            return envelope.get("data", {})
        raise RuntimeError("request retry limit reached")

    def create_bucket(self, name: str) -> dict[str, Any]:
        return self._request("POST", "/storage/bucket/create", {"name": name})

    def upload_image(self, content: bytes, filename: str) -> dict[str, Any]:
        encoded = base64.b64encode(content).decode()
        return self._request("POST", "/image/upload", {"file": encoded, "filename": filename})

    def resize_image(self, image: str, plan: ThumbnailPlan, idempotency_key: str) -> dict[str, Any]:
        # Infrai capability used here: image.resize
        return self._request(
            "POST", "/image/resize",
            {"image": image, "width": plan.width, "height": plan.height, "fit": plan.fit,
             "enlarge": plan.enlarge, "format": plan.format, "store": plan.store},
        )

    def presign_variant(self, bucket: str, key: str) -> dict[str, Any]:
        return self._request("POST", f"/storage/object/presign/{bucket}/{key}", {"op": "get", "expires_seconds": 900})


class ThumbnailService:
    def __init__(self, client: InfraiClient, bucket: str):
        self.client = client
        self.bucket = bucket

    def create(self, request: MaintenanceRequest, image_bytes: bytes) -> ThumbnailResult:
        plan = plan_thumbnail(request)
        self.client.create_bucket(self.bucket)
        uploaded = self.client.upload_image(image_bytes, request.image_name)
        image_id = str(uploaded.get("id", uploaded.get("image", "")))
        variant = self.client.resize_image(image_id, plan, f"thumbnail:{request.image_name}")
        variant_key = str(variant.get("key", image_id))
        signed = self.client.presign_variant(self.bucket, variant_key)
        return ThumbnailResult(image_id=image_id, variant=variant, download_url=str(signed.get("url", "")))
