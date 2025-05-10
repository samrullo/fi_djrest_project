from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (VanillaBondSecMasterViewSet, RiskCoreViewSet, RiskScenarioViewSet,
                    PositionViewSet,
                    ScenarioPositionViewSet,
                    TransactionViewSet,
                    CurveDescriptionViewSet,
                    CurvePointViewSet,
                    FilteredCurveView,
                    StressScenarioViewSet,
                    AborPnLViewSet,
                    PositionUploadCSV,
                    CurveUploadCSV,
                    StressScenarioUploadCSV
                    )
from .views import StressScenarioDescriptionViewSet

router = DefaultRouter()
router.register(r"vanilla-bonds", VanillaBondSecMasterViewSet, "vanilla-bond")
router.register(r"risk-cores", RiskCoreViewSet, "risk-core")
router.register(r"risk-scenarios", RiskScenarioViewSet, "risk-scenario")
router.register(r"positions", PositionViewSet, "position")
router.register(r"scenario-positions", ScenarioPositionViewSet, "scenario-position")
router.register(r"transactions", TransactionViewSet, "transaction")
router.register(r"curve-descriptions", CurveDescriptionViewSet, "curve-description")
router.register(r"curve-points", CurvePointViewSet, "curve-point")

router.register(
    r"stress-scenario-descriptions",
    StressScenarioDescriptionViewSet,
    basename="stress-scenario-description"
)
router.register(r"stress-scenarios", StressScenarioViewSet, "stress-scenario")
router.register(r"aborpnls", AborPnLViewSet, "aborpnl")

urlpatterns = [
    path("", include(router.urls)),
    path("upload-positions/", PositionUploadCSV.as_view(), name="upload-positions"),
    path('upload-curve/', CurveUploadCSV.as_view(), name='upload-curve'),
    path("curve-points/by-date/<str:curve_name>/<str:adate>/", FilteredCurveView.as_view(), name="filtered-curve"),
    path("upload-stress-scenarios/", StressScenarioUploadCSV.as_view(), name="upload-stress-scenarios"),

]
