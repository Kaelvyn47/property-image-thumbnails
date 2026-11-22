import pytest

from src.thumbnail_service import MaintenanceRequest, plan_thumbnail


def test_property_request_gets_bounded_webp_thumbnail():
    request = MaintenanceRequest("unit-12-kitchen.jpg", "lease.pdf", "2026-11-01")

    plan = plan_thumbnail(request)

    assert (plan.width, plan.height, plan.format) == (320, 240, "webp")
    assert plan.enlarge is False


def test_thumbnail_requires_an_image_name():
    with pytest.raises(ValueError):
        plan_thumbnail(MaintenanceRequest(" ", "lease.pdf", "2026-11-01"))
