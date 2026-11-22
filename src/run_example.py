import sys
import base64
from pathlib import Path

from thumbnail_service import InfraiClient, MaintenanceRequest, ThumbnailService


# Keep the documented zero-argument example runnable without a checked-in binary asset.
DEFAULT_IMAGE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def main() -> None:
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("kitchen.jpg")
    request = MaintenanceRequest(image_path.name, "lease.pdf", "2026-11-01")
    service = ThumbnailService(InfraiClient(), __import__("os").environ["INFRAI_BUCKET"])
    image_bytes = image_path.read_bytes() if image_path.exists() else DEFAULT_IMAGE
    result = service.create(request, image_bytes)
    print({"image_id": result.image_id, "download_url": result.download_url})


if __name__ == "__main__":
    main()
