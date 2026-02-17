# Fuel Route Planning API - Implementation Plan

Read `requirements.txt` and built a full implementation plan around it.

## Assumptions to lock before build
1. "Polars (NOT Pandas)" means "use Polars instead of `csv`/Pandas parsing," via Python Polars bindings.
2. Use OSRM public demo for development, with strict throttling and caching.
3. Runtime Python is `3.12+` if we use latest stable Django.
4. If runtime must stay on Python `3.10/3.11`, use Django `5.2.x` (LTS) instead of `6.0.x`.

As of **February 17, 2026**, latest stable Django is **6.0.2** (released Feb 3, 2026).

## Step-by-Step Plan
1. Freeze scope and API contract.  
Define input: `start_location`, `finish_location`, optional `start_fuel_percent`.  
Define output: full route geometry, ordered fuel stops, per-stop gallons/cost, total fuel cost, total distance, total gallons, assumptions.  
Verify by writing an example request/response JSON in `README`.

2. Initialize Django project with uv.  
Create project/app skeleton and settings for env vars.  
Add dependencies: Django, pydantic, polars, httpx, pytest, pytest-django, ruff, ty, and optional ortools.  
Verify with `uv sync`, `uvx ruff check .`, `uvx ty check`, `uvx pytest`.

3. Define typed domain schemas (Pydantic).  
Create request/response/domain models: `LocationInput`, `RouteLeg`, `FuelStation`, `FuelStopPlan`, `RoutePlanResult`.  
Add strict validation for numeric ranges and required fields.  
Verify with unit tests for valid/invalid payloads.

4. Build fuel-price ingestion pipeline using Polars.  
Read CSV with Polars, normalize text, parse numeric price, drop malformed rows, deduplicate station duplicates.  
Create canonical station key and keep cheapest valid price per location key.  
Verify with tests for row counts, null handling, dedupe behavior, and price parsing.

5. Add station geocoding enrichment (one-time/offline job).  
Because CSV has no lat/lon, geocode station addresses once and persist coordinates in DB/table.  
Persist geocode status and retry queue for unresolved rows.  
Verify by coverage metric (e.g., `% geocoded`) and sample spot checks.

6. Add user input geocoding + USA boundary validation.  
Geocode start/finish to coordinates.  
Reject requests not in USA with clear error payload.  
Verify with tests for US vs non-US addresses.

7. Integrate OSRM route fetch.  
Call OSRM route endpoint for driving route (`overview=full`, `geometries=geojson`).  
Extract route polyline/geometry, total distance, and cumulative-mile markers.  
Verify with integration tests (mocked and real-smoke optional).

8. Build station-on-route candidate selector.  
Project station points onto route corridor (e.g., distance-to-polyline threshold), then keep stations reachable in forward travel order.  
Attach each candidate's milepost and detour penalty.  
Verify with deterministic fixtures and edge-case tests.

9. Implement baseline fuel optimization (deterministic).  
Set constants: max range `500 miles`, mpg `10`, tank `50 gallons`.  
Compute cheapest feasible fueling plan along ordered candidates with fuel-balance constraints.  
Verify constraints in tests: never exceed tank, never run empty, all hops <= 500 miles.

10. Add OR-Tools optimizer (optional advanced mode).  
Model as optimization problem minimizing total fuel spend with same constraints.  
Use OR-Tools when candidate set is large/complex; otherwise use baseline solver.  
Verify by comparing OR-Tools result <= baseline cost on same fixtures.

11. Produce map-ready response.  
Return route GeoJSON + stop markers + popup metadata.  
Include summary totals and per-leg breakdown.  
Verify with snapshot tests on response schema.

12. Build Django API endpoints.  
`POST /api/v1/route-plan`  
`GET /api/v1/health`  
Return structured errors and traceable request IDs.  
Verify with API tests for success, validation errors, and upstream failures.

13. Add resilience and operational controls.  
OSRM request timeout/retry/backoff.  
Rate-limit outbound OSRM calls to respect demo policy.  
Cache geocoding and route responses for repeated inputs.  
Verify via failure-injection tests and latency checks.

14. Final quality gate and docs.  
Run lint/type/tests and add runbook.  
Document assumptions: mpg=10, tank=50 gallons, demo API limits, geocoding caveats.  
Verify CI passes and README includes example request/response + setup commands.

## Recommended execution order
1. Steps 1-4 (contracts + clean station dataset)
2. Steps 6-8 (geocoding + routing + candidate stations)
3. Steps 9-10 (optimization)
4. Steps 11-14 (API polish, reliability, docs)

## Sources
- `requirements.txt`
- Django download page (latest official version): https://www.djangoproject.com/download/
- Django 6.0 release notes (Python compatibility): https://docs.djangoproject.com/en/6.0/releases/6.0/
- Django install FAQ (version/Python matrix): https://docs.djangoproject.com/en/6.0/faq/install/
- PyPI Django release history: https://pypi.org/project/Django/
- OSRM-related public routing usage policy context: https://map.project-osrm.org/about.html
