from django.urls import path

from route_planner import views

urlpatterns = [
    path("", views.route_map_view, name="route-map"),
    path("api/v1/health", views.health_view, name="health"),
    path("api/v1/route-plan", views.route_plan_view, name="route-plan"),
]
