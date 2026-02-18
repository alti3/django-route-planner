from __future__ import annotations

import pytest


@pytest.fixture
def api_client():
    from django.test import Client

    return Client()
