from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import pandas as pd

from .models import (
    VanillaBondSecMaster,
    SecurityIdentifier,
    RiskCore,
    RiskScenario,
    CurveDescription,
    CurvePoint,
    StressScenario,
    Position,
    ScenarioPosition,
    Transaction,
    AborPnL,
    StressScenarioDescription,
)

from .serializers import (
    VanillaBondSecMasterSerializer,
    SecurityIdentifierSerializer,
    RiskCoreSerializer,
    RiskScenarioSerializer,
    CurveDescriptionSerializer,
    CurvePointSerializer,
    StressScenarioSerializer,
    PositionSerializer,
    ScenarioPositionSerializer,
    TransactionSerializer,
    AborPnLSerializer,
    StressScenarioDescriptionSerializer,
)


class VanillaBondSecMasterViewSet(viewsets.ModelViewSet):
    queryset = VanillaBondSecMaster.objects.all()
    serializer_class = VanillaBondSecMasterSerializer


class SecurityIdentifierViewSet(viewsets.ModelViewSet):
    queryset = SecurityIdentifier.objects.all()
    serializer_class = SecurityIdentifierSerializer


class RiskCoreViewSet(viewsets.ModelViewSet):
    queryset = RiskCore.objects.all()
    serializer_class = RiskCoreSerializer


class RiskScenarioViewSet(viewsets.ModelViewSet):
    queryset = RiskScenario.objects.all()
    serializer_class = RiskScenarioSerializer


class CurveDescriptionViewSet(viewsets.ModelViewSet):
    queryset = CurveDescription.objects.all()
    serializer_class = CurveDescriptionSerializer


class CurvePointViewSet(viewsets.ModelViewSet):
    queryset = CurvePoint.objects.all()
    serializer_class = CurvePointSerializer

    def create(self, request, *args, **kwargs):
        print("📦 Incoming data:", request.data)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("❌ Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StressScenarioDescriptionViewSet(viewsets.ModelViewSet):
    queryset = StressScenarioDescription.objects.all()
    serializer_class = StressScenarioDescriptionSerializer


class StressScenarioViewSet(viewsets.ModelViewSet):
    queryset = StressScenario.objects.all()
    serializer_class = StressScenarioSerializer


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer


class ScenarioPositionViewSet(viewsets.ModelViewSet):
    queryset = ScenarioPosition.objects.all()
    serializer_class = ScenarioPositionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class AborPnLViewSet(viewsets.ModelViewSet):
    queryset = AborPnL.objects.all()
    serializer_class = AborPnLSerializer


class PositionUploadCSV(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_csv(file_obj)

            required_columns = [
                "portfolio_name", "scenario_id", "period_number", "simulation_number",
                "position_date", "lot_id", "asset_name", "identifier_client",
                "quantity", "notional_amount", "par_value", "book_price", "book_value",
            ]

            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return Response({"error": f"Missing required columns: {missing}"}, status=400)

            records = []
            for _, row in df.iterrows():
                records.append(
                    ScenarioPosition(
                        portfolio_name=row["portfolio_name"],
                        scenario_id=int(row["scenario_id"]),
                        period_number=int(row["period_number"]),
                        simulation_number=int(row["simulation_number"]),
                        position_date=pd.to_datetime(row["position_date"]).date(),
                        lot_id=int(row["lot_id"]),
                        asset_name=row["asset_name"],
                        identifier_client=row["identifier_client"],
                        identifier_isin=row.get("identifier_isin"),
                        identifier_cusip=row.get("identifier_cusip"),
                        identifier_sedol=row.get("identifier_sedol"),
                        quantity=row["quantity"],
                        notional_amount=row["notional_amount"],
                        par_value=row["par_value"],
                        book_price=row["book_price"],
                        book_value=row["book_value"],
                    )
                )

            ScenarioPosition.objects.bulk_create(records)
            return Response({"status": "Upload successful", "rows": len(records)}, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CurveUploadCSV(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_csv(file_obj)

            required_columns = ["adate", "curve_name", "year", "rate"]
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return Response({"error": f"Missing columns: {missing}"}, status=400)

            # Optional column: curve_description
            if "curve_description" not in df.columns:
                df["curve_description"] = df["curve_name"]
            else:
                df["curve_description"] = df["curve_description"].fillna(df["curve_name"])

            df["adate"] = pd.to_datetime(df["adate"]).dt.date

            # Get unique (name, description) pairs
            curve_info = df[["curve_name", "curve_description"]].drop_duplicates()
            existing = {
                c.name: c
                for c in CurveDescription.objects.filter(name__in=curve_info["curve_name"].unique())
            }

            new = [
                CurveDescription(name=row.curve_name, description=row.curve_description)
                for row in curve_info.itertuples(index=False)
                if row.curve_name not in existing
            ]
            CurveDescription.objects.bulk_create(new)

            all_curves = {
                c.name: c for c in CurveDescription.objects.filter(name__in=curve_info["curve_name"].unique())
            }

            points = []
            for _, row in df.iterrows():
                points.append(
                    CurvePoint(
                        curve_description=all_curves[row["curve_name"]],
                        adate=row["adate"],
                        year=int(row["year"]),
                        rate=float(row["rate"]),
                    )
                )

            CurvePoint.objects.bulk_create(points)

            return Response(
                {"status": "Upload successful", "curves": len(all_curves), "points": len(points)},
                status=201
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class FilteredCurveView(APIView):
    def get(self, request, curve_name, adate):
        try:
            points = CurvePoint.objects.filter(
                curve_description__name=curve_name,
                adate=adate
            ).order_by("year")

            serializer = CurvePointSerializer(points, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StressScenarioUploadCSV(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_csv(file_obj)

            required_columns = [
                "scenario_name", "period_number", "simulation_number",
                "curve_name", "curve_adate", "curve_year",
                "period_length", "parallel_shock_size"
            ]
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return Response({"error": f"Missing required columns: {missing}"}, status=400)

            df["curve_adate"] = pd.to_datetime(df["curve_adate"]).dt.date

            records = []
            for _, row in df.iterrows():
                scenario_desc, _ = StressScenarioDescription.objects.get_or_create(name=row["scenario_name"])

                try:
                    curve_desc = CurveDescription.objects.get(name=row["curve_name"])
                    curve_point = CurvePoint.objects.get(
                        curve_description=curve_desc,
                        adate=row["curve_adate"],
                        year=int(row["curve_year"])
                    )
                except CurvePoint.DoesNotExist:
                    return Response({
                        "error": f"CurvePoint not found for {row['curve_name']} {row['curve_adate']} y{row['curve_year']}"},
                        status=400)

                record = StressScenario(
                    scenario=scenario_desc,
                    period_number=int(row["period_number"]),
                    simulation_number=int(row["simulation_number"]),
                    curve=curve_point,
                    period_length=float(row["period_length"]),
                    parallel_shock_size=float(row["parallel_shock_size"]),
                )
                records.append(record)

            StressScenario.objects.bulk_create(records)
            return Response({"status": "Upload successful", "rows": len(records)}, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
