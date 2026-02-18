"""Django settings for route planner project."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "route_planner",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": PROJECT_ROOT / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "route-planner-cache",
    }
}

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
OSRM_TIMEOUT_SECONDS = float(os.getenv("OSRM_TIMEOUT_SECONDS", "12"))
OSRM_RETRY_COUNT = int(os.getenv("OSRM_RETRY_COUNT", "2"))

GEOCODING_BASE_URL = os.getenv("GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org")
GEOCODING_USER_AGENT = os.getenv("GEOCODING_USER_AGENT", "spotter-ai-route-planner/1.0")
GEOCODING_TIMEOUT_SECONDS = float(os.getenv("GEOCODING_TIMEOUT_SECONDS", "12"))
GEOCODING_RETRY_COUNT = int(os.getenv("GEOCODING_RETRY_COUNT", "2"))

ROUTE_CACHE_TTL_SECONDS = int(os.getenv("ROUTE_CACHE_TTL_SECONDS", "600"))
GEOCODE_CACHE_TTL_SECONDS = int(os.getenv("GEOCODE_CACHE_TTL_SECONDS", "86400"))

MAX_RANGE_MILES = float(os.getenv("MAX_RANGE_MILES", "500"))
VEHICLE_MPG = float(os.getenv("VEHICLE_MPG", "10"))
FUEL_TANK_GALLONS = float(os.getenv("FUEL_TANK_GALLONS", "50"))
DEFAULT_CORRIDOR_MILES = float(os.getenv("DEFAULT_CORRIDOR_MILES", "8"))
MAX_CANDIDATE_STATIONS = int(os.getenv("MAX_CANDIDATE_STATIONS", "600"))
