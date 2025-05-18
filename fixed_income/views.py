from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import pandas as pd
import datetime
from fi_utils.bond_valuation import calc_ytm_of_bond, calc_accrued_interest, calc_pv_of_vanilla_bond
from django.db.models import Sum
from datetime import timedelta
import pdb

from .models import (
    VanillaBondSecMaster,
    SecurityIdentifier,
    RiskCore,
    RiskScenario,
    CurveDescription,
    CurvePoint,
    CurvePointShock,
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
    CurvePointShockSerializer,
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


class UploadVanillaBondsCSV(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_csv(file_obj)

            required_columns = ["identifier_client", "asset_name", "fixed_coupon", "maturity"]
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return Response({"error": f"Missing columns: {missing}"}, status=status.HTTP_400_BAD_REQUEST)

            # Optional column
            if "frequency" not in df.columns:
                df["frequency"] = 2
            else:
                df["frequency"] = df["frequency"].fillna(2)

            df["maturity"] = pd.to_datetime(df["maturity"]).dt.date

            bonds = [
                VanillaBondSecMaster(
                    identifier_client=row["identifier_client"],
                    asset_name=row["asset_name"],
                    fixed_coupon=float(row["fixed_coupon"]),
                    frequency=int(row["frequency"]),
                    maturity=row["maturity"],
                )
                for _, row in df.iterrows()
            ]

            VanillaBondSecMaster.objects.bulk_create(bonds)

            return Response(
                {"status": "Upload successful", "records_created": len(bonds)},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SecurityIdentifierViewSet(viewsets.ModelViewSet):
    queryset = SecurityIdentifier.objects.all()
    serializer_class = SecurityIdentifierSerializer


class RiskCoreViewSet(viewsets.ModelViewSet):
    queryset = RiskCore.objects.all()
    serializer_class = RiskCoreSerializer


class RiskCoreUploadCSV(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=400)

        try:
            df = pd.read_csv(file_obj)
            required_cols = ["identifier_client", "adate", "price", "curve_name"]
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                return Response({"error": f"Missing columns: {missing}"}, status=400)

            df["adate"] = pd.to_datetime(df["adate"]).dt.date
            adate = df["adate"].iloc[0]

            # Fetch curve points
            curve_name = df["curve_name"].iloc[0]
            try:
                curve_desc = CurveDescription.objects.get(name=curve_name)
            except CurveDescription.DoesNotExist:
                return Response({"error": f"CurveDescription '{curve_name}' not found."}, status=400)

            curve_points = CurvePoint.objects.filter(curve_description=curve_desc, adate=adate)
            curve = {float(p.year): p.rate for p in curve_points}

            records = []
            for _, row in df.iterrows():
                try:
                    bond = VanillaBondSecMaster.objects.get(identifier_client=row["identifier_client"])
                except VanillaBondSecMaster.DoesNotExist:
                    continue  # skip unknown bonds

                maturity = bond.maturity
                coupon = float(bond.fixed_coupon)
                price = float(row["price"])

                ai = calc_accrued_interest(adate, maturity, coupon)
                dirty_price = price + ai
                ytm = calc_ytm_of_bond(dirty_price, coupon, adate, maturity)
                pv = calc_pv_of_vanilla_bond(adate, maturity, coupon, curve)

                rc = RiskCore(
                    security=bond,
                    risk_date=adate,
                    price=price,
                    yield_to_maturity=ytm,
                    oas=0.0,  # Placeholder unless provided
                    discounted_pv=pv,
                    accrued_interest=ai
                )
                records.append(rc)

            RiskCore.objects.bulk_create(records)

            return Response({
                "status": "Upload successful",
                "records_created": len(records)
            }, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


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


class CurvePointShockViewSet(viewsets.ModelViewSet):
    queryset = CurvePointShock.objects.all()
    serializer_class = CurvePointShockSerializer


class StressScenarioViewSet(viewsets.ModelViewSet):
    queryset = StressScenario.objects.all()
    serializer_class = StressScenarioSerializer


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("❌ Validation errors in ScenarioPosition:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ScenarioPositionViewSet(viewsets.ModelViewSet):
    queryset = ScenarioPosition.objects.all()
    serializer_class = ScenarioPositionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("❌ Validation errors in ScenarioPosition:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
                "portfolio_name", "position_date", "identifier_client",
                "quantity", "book_price", "curve_name"
            ]
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                return Response({"error": f"Missing required columns: {missing}"}, status=400)

            df["position_date"] = pd.to_datetime(df["position_date"]).dt.date
            position_records = []

            for _, row in df.iterrows():
                identifier = row["identifier_client"]
                curve_name = row["curve_name"]
                position_date = row["position_date"]

                try:
                    security = VanillaBondSecMaster.objects.get(identifier_client=identifier)
                except VanillaBondSecMaster.DoesNotExist:
                    return Response({"error": f"Security with identifier '{identifier}' not found."}, status=400)

                try:
                    curve_desc = CurveDescription.objects.get(name=curve_name)
                except CurveDescription.DoesNotExist:
                    return Response({"error": f"Curve '{curve_name}' not found."}, status=400)

                curve_points_qs = CurvePoint.objects.filter(
                    curve_description=curve_desc,
                    adate=position_date
                )
                if not curve_points_qs.exists():
                    return Response({"error": f"No curve points for {curve_name} on {position_date}."}, status=400)

                curve_points = list(curve_points_qs.order_by("year"))
                curve_dict = {float(cp.year): cp.rate for cp in curve_points}

                quantity = float(row["quantity"])
                book_price = float(row["book_price"])

                notional_amount = quantity * book_price / 100
                par_value = quantity
                book_value = notional_amount

                ai = calc_accrued_interest(position_date, security.maturity, security.fixed_coupon)
                dirty_price = book_price + ai
                ytm = calc_ytm_of_bond(dirty_price, security.fixed_coupon, position_date, security.maturity)
                pv = calc_pv_of_vanilla_bond(position_date, security.maturity, security.fixed_coupon, curve_dict, freq=security.frequency)

                risk_core = RiskCore.objects.create(
                    security=security,
                    risk_date=position_date,
                    curve_description=curve_desc,
                    price=book_price,
                    accrued_interest=ai,
                    yield_to_maturity=ytm,
                    discounted_pv=pv,
                    oas=0.0
                )

                discounted_value = quantity * pv / 100

                position = Position(
                    security=security,
                    portfolio_name=row["portfolio_name"],
                    position_date=position_date,
                    lot_id=0,  # <-- Set lot_id to 0
                    quantity=quantity,
                    notional_amount=notional_amount,
                    par_value=par_value,
                    book_price=book_price,
                    book_value=book_value,
                    discounted_value=discounted_value,
                    risk_core=risk_core
                )

                position_records.append(position)

            Position.objects.bulk_create(position_records)
            return Response({"status": "Upload successful", "rows": len(position_records)}, status=201)

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


from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from .models import (
    StressScenarioDescription,
    StressScenario,
    CurvePoint,
    CurvePointShock,
    CurveDescription,
)


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

            scenario_cache = {}
            shock_records = []

            for _, row in df.iterrows():
                # Get or create StressScenarioDescription
                scenario_desc, _ = StressScenarioDescription.objects.get_or_create(
                    name=row["scenario_name"]
                )

                key = (scenario_desc.id, row["period_number"], row["simulation_number"])

                # Cache StressScenario to avoid redundant DB calls
                if key not in scenario_cache:
                    stress_scenario, _ = StressScenario.objects.get_or_create(
                        scenario=scenario_desc,
                        period_number=row["period_number"],
                        simulation_number=row["simulation_number"],
                        defaults={"period_length": row["period_length"]}
                    )
                    scenario_cache[key] = stress_scenario
                else:
                    stress_scenario = scenario_cache[key]

                # Get CurvePoint
                try:
                    curve_desc = CurveDescription.objects.get(name=row["curve_name"])
                    curve_point = CurvePoint.objects.get(
                        curve_description=curve_desc,
                        adate=row["curve_adate"],
                        year=int(row["curve_year"])
                    )
                except CurvePoint.DoesNotExist:
                    return Response({
                        "error": f"CurvePoint not found: {row['curve_name']} - {row['curve_adate']} - Year {row['curve_year']}"
                    }, status=400)

                # Create CurvePointShock (no bulk_create because we might want unique_together constraints to raise)
                shock = CurvePointShock(
                    stress_scenario=stress_scenario,
                    curve_point=curve_point,
                    shock_size=row["parallel_shock_size"]
                )
                shock_records.append(shock)

            CurvePointShock.objects.bulk_create(shock_records, ignore_conflicts=True)

            return Response({"status": "Upload successful", "rows": len(shock_records)}, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class GenerateScenarioPositions(APIView):
    parser_classes = [JSONParser]

    def post(self, request):
        try:
            portfolio_name = request.data.get("portfolio_name")
            position_date = request.data.get("position_date")
            scenario_name = request.data.get("scenario_name")

            if not (portfolio_name and position_date and scenario_name):
                return Response({"error": "portfolio_name, position_date, and scenario_name are required."}, status=400)

            position_date = pd.to_datetime(position_date).date()
            positions = Position.objects.filter(portfolio_name=portfolio_name, position_date=position_date)
            if not positions.exists():
                return Response({"error": "No positions found for given portfolio and date."}, status=404)

            try:
                scenario_description = StressScenarioDescription.objects.get(name=scenario_name)
            except StressScenarioDescription.DoesNotExist:
                return Response({"error": f"ScenarioDescription '{scenario_name}' not found."}, status=404)

            scenarios = StressScenario.objects.filter(scenario=scenario_description)
            if not scenarios.exists():
                return Response({"error": f"No StressScenario entries found for scenario '{scenario_name}'."}, status=404)

            for scenario in scenarios:
                shocks = CurvePointShock.objects.filter(stress_scenario=scenario)
                if not shocks.exists():
                    continue

                # Create curve dict
                curve = {}
                for shock in shocks:
                    cp = shock.curve_point
                    shocked_rate = cp.rate + shock.shock_size
                    curve[float(cp.year)] = shocked_rate

                scenario_positions = []
                risk_scenarios = []
                for pos in positions:
                    sec = pos.security

                    notional_amount = pos.book_price * pos.quantity / 100
                    book_value = notional_amount
                    par_value = pos.quantity

                    scen_pos = ScenarioPosition(
                        portfolio_name=pos.portfolio_name,
                        scenario=scenario,
                        position_date=position_date,
                        lot_id=pos.lot_id,
                        security=sec,
                        quantity=pos.quantity,
                        notional_amount=notional_amount,
                        par_value=par_value,
                        book_price=pos.book_price,
                        book_value=book_value
                    )
                    scen_pos.save()

                    ai = calc_accrued_interest(position_date, sec.maturity, sec.fixed_coupon, sec.frequency)
                    dirty_price = pos.book_price + ai
                    ytm = calc_ytm_of_bond(dirty_price, sec.fixed_coupon, position_date, sec.maturity, freq=sec.frequency)
                    pv = calc_pv_of_vanilla_bond(position_date, sec.maturity, sec.fixed_coupon, curve, freq=sec.frequency)

                    risk_scenario = RiskScenario.objects.create(
                        security=sec,
                        scenario=scenario,
                        price=pos.book_price,
                        yield_to_maturity=ytm,
                        discounted_pv=pv,
                        oas=0.0,
                        accrued_interest=ai
                    )

                    scen_pos.risk_scenario = risk_scenario
                    scen_pos.discounted_value = pv * pos.quantity / 100
                    scen_pos.save()

            return Response({"status": "ScenarioPositions successfully created."}, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=500)



class PortfolioStressTrendView(APIView):
    parser_classes = [JSONParser]
    def post(self, request):
        portfolio = request.data.get("portfolio")
        position_date = request.data.get("position_date")
        scenario_name = request.data.get("scenario_name")
        # pdb.set_trace()


        if not (portfolio and position_date and scenario_name):
            return Response(
                {"error": "portfolio, position_date, and scenario_name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            base_date = datetime.datetime.strptime(position_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid position_date format. Use YYYY-MM-DD."}, status=400)

        try:
            scenario_desc = StressScenarioDescription.objects.get(name=scenario_name)
        except StressScenarioDescription.DoesNotExist:
            return Response({"error": f"Scenario '{scenario_name}' not found."}, status=404)

        scenarios = StressScenario.objects.filter(scenario=scenario_desc).order_by("period_number", "simulation_number")

        results = []
        for scenario in scenarios:
            total_mv = ScenarioPosition.objects.filter(
                scenario=scenario,
                portfolio_name=portfolio,
                position_date=base_date,
            ).aggregate(total=Sum("discounted_value"))["total"] or 0

            date_shift = timedelta(days=round(scenario.period_length * 365))
            asof_date = base_date + date_shift

            results.append({
                "date": asof_date.isoformat(),
                "market_value": total_mv,
                "period_number": scenario.period_number,
                "simulation_number": scenario.simulation_number,
            })

        return Response(results, status=200)