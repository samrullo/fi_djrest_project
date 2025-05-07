from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import pandas as pd

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
from .serializers import (
    VanillaBondSecMasterSerializer,
    CurveSerializer,CurvePointSerializer,
    StressScenarioSerializer,
PositionSerializer,
    ScenarioPositionSerializer,
    TransactionSerializer,
    AborPnLSerializer,
)


class VanillaBondSecMasterViewSet(viewsets.ModelViewSet):
    queryset = VanillaBondSecMaster.objects.all()
    serializer_class = VanillaBondSecMasterSerializer


class CurveViewSet(viewsets.ModelViewSet):
    queryset = Curve.objects.all()
    serializer_class = CurveSerializer

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
            return Response(
                {"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            df = pd.read_csv(file_obj)

            required_columns = [
                "portfolio_name",
                "scenario_id",
                "period_number",
                "simulation_number",
                "position_date",
                "lot_id",
                "asset_name",
                "identifier_client",
                "quantity",
                "notional_amount",
                "par_value",
                "book_price",
                "book_value",
            ]

            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return Response(
                    {"error": f"Missing required columns: {missing}"}, status=400
                )

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
            return Response(
                {"status": "Upload successful", "rows": len(records)}, status=201
            )

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

            df["adate"] = pd.to_datetime(df["adate"]).dt.date

            # Ensure all Curve names exist or are created
            curve_names = df["curve_name"].unique()
            existing_curves = {c.curve_name: c for c in Curve.objects.filter(curve_name__in=curve_names)}

            new_curves = [
                Curve(curve_name=name)
                for name in curve_names
                if name not in existing_curves
            ]

            Curve.objects.bulk_create(new_curves)

            # Refresh curve dict after creation
            all_curves = {c.curve_name: c for c in Curve.objects.filter(curve_name__in=curve_names)}

            # Create CurvePoint records
            curve_points = []
            for _, row in df.iterrows():
                curve = all_curves[row["curve_name"]]
                curve_points.append(
                    CurvePoint(
                        curve=curve,
                        adate=row["adate"],
                        year=int(row["year"]),
                        rate=float(row["rate"])
                    )
                )

            CurvePoint.objects.bulk_create(curve_points)

            return Response(
                {"status": "Upload successful", "curves": len(all_curves), "points": len(curve_points)},
                status=201,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class FilteredCurveView(APIView):
    def get(self, request, curve_name, adate):
        try:
            curve_points = CurvePoint.objects.filter(
                curve__curve_name=curve_name,
                adate=adate
            ).order_by("year")

            serializer = CurvePointSerializer(curve_points, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# view to bulk upload stress scenarios
# curve id refers to combination of adate, curve name and year
# so if I have a curve with 30 years, then to define one period scenario where I shock the curve by 0.25 pct, I add 30 records with the same scenario_id, period_number, simulation_number
class StressScenarioUploadCSV(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            df = pd.read_csv(file_obj)

            required_columns = [
                "scenario_id",
                "period_number",
                "simulation_number",
                "curve",
                "period_length",
                "parallel_shock_size",
            ]

            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return Response(
                    {"error": f"Missing required columns: {missing}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            records = []
            for _, row in df.iterrows():
                try:
                    curve = Curve.objects.get(id=int(row["curve"]))  # lookup FK
                except Curve.DoesNotExist:
                    return Response(
                        {"error": f"Curve ID {row['curve']} not found."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                record = StressScenario(
                    scenario_id=int(row["scenario_id"]),
                    period_number=int(row["period_number"]),
                    simulation_number=int(row["simulation_number"]),
                    curve=curve,  # assign the actual object, not curve_id
                    period_length=float(row["period_length"]),
                    parallel_shock_size=float(row["parallel_shock_size"]),
                )
                records.append(record)

            StressScenario.objects.bulk_create(records)
            return Response(
                {"status": "Upload successful", "rows": len(records)}, status=201
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)