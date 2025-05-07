from rest_framework import serializers
from .models import (
    VanillaBondSecMaster,
    Curve,
CurvePoint,
    StressScenario,
Position,
    ScenarioPosition,
    Transaction,
    AborPnL,
)



class VanillaBondSecMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = VanillaBondSecMaster
        fields = "__all__"


class CurveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curve
        fields = ["id", "curve_name"]

class CurvePointSerializer(serializers.ModelSerializer):
    curve_name = serializers.CharField(source="curve.curve_name", read_only=True)

    class Meta:
        model = CurvePoint
        fields = ["id", "curve", "curve_name", "adate", "year", "rate"]

class CurveNestedSerializer(serializers.ModelSerializer):
    curve_name = CurveSerializer(source="curve",read_only=True)

    class Meta:
        model = CurvePoint
        fields = ["id", "curve_name", "adate", "year", "rate"]

class StressScenarioSerializer(serializers.ModelSerializer):
    curve_details = CurveNestedSerializer(source="curve", read_only=True)

    class Meta:
        model = StressScenario
        fields = [
            "id",
            "scenario_id",
            "period_number",
            "simulation_number",
            "curve",         # foreign key ID used when POSTing
            "curve_details", # nested object shown when GETting
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

    class Meta:
        model = ScenarioPosition
        fields = "__all__"


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
