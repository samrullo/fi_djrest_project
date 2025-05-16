from rest_framework import serializers
from .models import (
    VanillaBondSecMaster,
    SecurityIdentifier,
    CurveDescription,
    CurvePoint,
CurvePointShock,
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

class CurvePointShockSerializer(serializers.ModelSerializer):
    curve_point_details = serializers.SerializerMethodField()
    stress_scenario_details = serializers.SerializerMethodField()

    class Meta:
        model = CurvePointShock
        fields = [
            "id",
            "curve_point",
            "curve_point_details",
            "shock_size",
            "stress_scenario",  # assuming this field exists
            "stress_scenario_details",
        ]

    def get_curve_point_details(self, obj):
        return {
            "curve_name": obj.curve_point.curve_description.name,
            "adate": obj.curve_point.adate,
            "year": obj.curve_point.year,
            "rate": obj.curve_point.rate,
        }

    def get_stress_scenario_details(self, obj):
        scenario = obj.stress_scenario
        return {
            "scenario_name": scenario.scenario.name,
            "period_number": scenario.period_number,
            "simulation_number": scenario.simulation_number,
        }
class StressScenarioSerializer(serializers.ModelSerializer):
    scenario_details = StressScenarioDescriptionSerializer(source="scenario", read_only=True)
    curve_point_shocks = CurvePointShockSerializer(many=True, read_only=True)

    class Meta:
        model = StressScenario
        fields = [
            "id",
            "scenario",
            "scenario_details",
            "period_number",
            "simulation_number",
            "period_length",
            "curve_point_shocks"
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

class PositionSerializer(serializers.ModelSerializer):
    security = VanillaBondSecMasterSerializer(read_only=True)
    security_id = serializers.PrimaryKeyRelatedField(
        queryset=VanillaBondSecMaster.objects.all(), source="security", write_only=True
    )

    risk_core = RiskCoreSerializer(read_only=True)
    risk_core_id = serializers.PrimaryKeyRelatedField(
        queryset=RiskCore.objects.all(), source="risk_core", write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Position
        fields = [
            "id",
            "security", "security_id",
            "risk_core", "risk_core_id",
            "portfolio_name",
            "position_date",
            "lot_id",
            "quantity",
            "notional_amount",
            "par_value",
            "book_price",
            "book_value",
            "discounted_value",
        ]

class ScenarioPositionSerializer(serializers.ModelSerializer):
    scenario = StressScenarioSerializer(read_only=True)
    scenario_id = serializers.PrimaryKeyRelatedField(
        queryset=StressScenario.objects.all(), source="scenario", write_only=True
    )

    security = VanillaBondSecMasterSerializer(read_only=True)
    security_id = serializers.PrimaryKeyRelatedField(
        queryset=VanillaBondSecMaster.objects.all(), source="security", write_only=True
    )

    risk_scenario = RiskScenarioSerializer(read_only=True)
    risk_scenario_id = serializers.PrimaryKeyRelatedField(
        queryset=RiskScenario.objects.all(), source="risk_scenario", write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = ScenarioPosition
        fields = [
            "id",
            "scenario", "scenario_id",
            "security", "security_id",
            "risk_scenario", "risk_scenario_id",
            "portfolio_name",
            "position_date",
            "lot_id",
            "quantity",
            "notional_amount",
            "par_value",
            "book_price",
            "book_value",
            "discounted_value",
        ]
