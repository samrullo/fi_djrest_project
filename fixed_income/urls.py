from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PositionViewSet,
    ScenarioPositionViewSet,
    TransactionViewSet,
    CurveViewSet,
CurvePointViewSet,
    FilteredCurveView,
    StressScenarioViewSet,
    AborPnLViewSet,
    PositionUploadCSV,
    CurveUploadCSV,
    StressScenarioUploadCSV
)

router = DefaultRouter()
router.register(r"positions", PositionViewSet, "position")
router.register(r"scenario-positions", ScenarioPositionViewSet, "scenario-position")
router.register(r"transactions", TransactionViewSet, "transaction")
router.register(r"curves", CurveViewSet, "curve")
router.register(r"curve-points",CurvePointViewSet,"curve-point")
router.register(r"stress-scenarios", StressScenarioViewSet, "stress-scenario")
router.register(r"aborpnls", AborPnLViewSet, "aborpnl")

urlpatterns = [
    path("", include(router.urls)),
    path("upload-positions/", PositionUploadCSV.as_view(), name="upload-positions"),
    path('upload-curve/', CurveUploadCSV.as_view(), name='upload-curve'),
    path("curves/by-date/<str:curve_name>/<str:adate>/", FilteredCurveView.as_view(), name="filtered-curve"),
    path("upload-stress-scenarios/", StressScenarioUploadCSV.as_view(), name="upload-stress-scenarios"),

]
