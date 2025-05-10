from rest_framework import serializers
from .models import (
    VanillaBondSecMaster,
    SecurityIdentifier,
    CurveDescription,
    CurvePoint,
    StressScenario,
    Position,
    ScenarioPosition,
    Transaction,
    AborPnL,
    StressScenarioDescription,
    RiskCore,
    RiskScenario,
)

class VanillaBondSecMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = VanillaBondSecMaster
        fields = "__all__"


class SecurityIdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityIdentifier
        fields = "__all__"


class CurveDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurveDescription
        fields = ["id", "name", "description"]


class CurvePointSerializer(serializers.ModelSerializer):
    curve_name = serializers.CharField(source="curve_description.name", read_only=True)
    curve_desc = serializers.CharField(source="curve_description.description", read_only=True)

    class Meta:
        model = CurvePoint
        fields = ["id", "curve_description", "curve_name", "curve_desc", "adate", "year", "rate"]


class CurveNestedSerializer(serializers.ModelSerializer):
    curve_name = CurveDescriptionSerializer(source="curve_description", read_only=True)

    class Meta:
        model = CurvePoint
        fields = ["id", "curve_name", "adate", "year", "rate"]


class StressScenarioDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StressScenarioDescription
        fields = ['id', 'name', 'description']


class StressScenarioSerializer(serializers.ModelSerializer):
    curve_details = CurveNestedSerializer(source="curve", read_only=True)
    scenario_details = StressScenarioDescriptionSerializer(source="scenario", read_only=True)

    class Meta:
        model = StressScenario
        fields = [
            "id",
            "scenario",
            "scenario_details",
            "period_number",
            "simulation_number",
            "curve",
            "curve_details",
            "period_length",
            "parallel_shock_size",
        ]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = "__all__"


class ScenarioPositionSerializer(serializers.ModelSerializer):
    scenario = StressScenarioSerializer(read_only=True)
    scenario_id = serializers.PrimaryKeyRelatedField(
        queryset=StressScenario.objects.all(), source="scenario", write_only=True
    )

    security = VanillaBondSecMasterSerializer(read_only=True)
    security_id = serializers.PrimaryKeyRelatedField(
        queryset=VanillaBondSecMaster.objects.all(), source="security", write_only=True
    )

    class Meta:
        model = ScenarioPosition
        fields = [
            "id",
            "scenario", "scenario_id",
            "security", "security_id",
            "portfolio_name",
            "position_date",
            "lot_id",
            "quantity",
            "notional_amount",
            "par_value",
            "book_price",
            "book_value",
            "discounted_price",
            "discounted_value",
        ]

class TransactionSerializer(serializers.ModelSerializer):
    scenario = StressScenarioSerializer(read_only=True)
    scenario_id = serializers.PrimaryKeyRelatedField(
        queryset=StressScenario.objects.all(), source="scenario", write_only=True
    )

    class Meta:
        model = Transaction
        fields = "__all__"


class AborPnLSerializer(serializers.ModelSerializer):
    scenario = StressScenarioSerializer(read_only=True)
    scenario_id = serializers.PrimaryKeyRelatedField(
        queryset=StressScenario.objects.all(), source="scenario", write_only=True
    )

    class Meta:
        model = AborPnL
        fields = "__all__"


class RiskCoreSerializer(serializers.ModelSerializer):
    security_name = serializers.CharField(source="security.asset_name", read_only=True)
    identifier_client = serializers.CharField(source="security.identifier_client", read_only=True)
    curve_name = serializers.CharField(source="curve_description.name", read_only=True)

    class Meta:
        model = RiskCore
        fields = [
            "id", "security", "security_name", "identifier_client", "risk_date",
            "price","accrued_interest", "yield_to_maturity", "oas", "discounted_pv","curve_description","curve_name"
        ]


class RiskScenarioSerializer(serializers.ModelSerializer):
    security_name = serializers.CharField(source="security.asset_name", read_only=True)
    identifier_client = serializers.CharField(source="security.identifier_client", read_only=True)
    scenario_details = StressScenarioSerializer(source="scenario", read_only=True)

    class Meta:
        model = RiskScenario
        fields = [
            "id", "security", "security_name", "identifier_client", "scenario", "scenario_details",
            "price", "yield_to_maturity", "oas", "discounted_pv"
        ]
