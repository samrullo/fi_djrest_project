import os
import logging
import django

# Set the path to your settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Setup Django
django.setup()

from sampytools.logging_utils import init_logging
import pandas as pd
from dateutil.relativedelta import relativedelta
import pdb
from fixed_income.models import (
    Position,
    StressScenarioDescription,
    StressScenario,
    CurvePointShock,
    ScenarioPosition,
    RiskScenario,
)
from fi_utils.bond_valuation import (
    calc_ytm_of_bond,
    calc_accrued_interest,
    calc_pv_of_vanilla_bond,
)
from fi_utils.abor_utils import compute_linear_amortization_schedule
# Mock or real imports for models and functions
# from your_app.models import Position, StressScenarioDescription, StressScenario, CurvePointShock, ScenarioPosition, RiskScenario
# from your_app.utils import compute_linear_amortization_schedule, calc_accrued_interest, calc_ytm_of_bond, calc_pv_of_vanilla_bond

init_logging(level=logging.INFO)

try:
    request_data = {
        "portfolio_name": "USIG01",
        "position_date": "2025-05-20",
        "scenario_name": "USD_SWAP_SHIFT_04",
    }

    portfolio_name = request_data.get("portfolio_name")
    position_date = request_data.get("position_date")
    scenario_name = request_data.get("scenario_name")

    if not (portfolio_name and position_date and scenario_name):
        raise ValueError(
            "portfolio_name, position_date, and scenario_name are required."
        )

    position_date = pd.to_datetime(position_date).date()

    # Get positions
    positions = Position.objects.filter(
        portfolio_name=portfolio_name, position_date=position_date
    )
    if not positions.exists():
        raise ValueError("No positions found for given portfolio and date.")

    # Get scenario description
    try:
        scenario_description = StressScenarioDescription.objects.get(name=scenario_name)
    except StressScenarioDescription.DoesNotExist:
        raise ValueError(f"ScenarioDescription '{scenario_name}' not found.")

    scenarios = StressScenario.objects.filter(scenario=scenario_description)
    if not scenarios.exists():
        raise ValueError(
            f"No StressScenario entries found for scenario '{scenario_name}'."
        )

    security_amortization_schedules = {}
    for pos in positions:
        sec = pos.security
        total_periods, change_per_period = compute_linear_amortization_schedule(
            pos.book_price, sec.maturity, position_date, period_length_years=1.0
        )
        security_amortization_schedules[sec] = {
            "total_periods": total_periods,
            "change_per_period": change_per_period,
        }

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

        period_end_date = position_date + relativedelta(
            years=(scenario.period_number + 1) * scenario.period_length
        )

        for pos in positions:
            sec = pos.security

            if sec.maturity >= period_end_date:
                book_price = (
                    pos.book_price
                    + (scenario.period_number + 1)
                    * security_amortization_schedules[sec]["change_per_period"]
                )
                notional_amount = book_price * pos.quantity / 100
                book_value = notional_amount
                par_value = pos.quantity

                scen_pos = ScenarioPosition(
                    portfolio_name=pos.portfolio_name,
                    scenario=scenario,
                    position_date=position_date,
                    period_end_date=period_end_date,
                    lot_id=pos.lot_id,
                    security=sec,
                    quantity=pos.quantity,
                    notional_amount=notional_amount,
                    par_value=par_value,
                    book_price=book_price,
                    book_value=book_value,
                )
                scen_pos.save()

                ai = calc_accrued_interest(
                    period_end_date, sec.maturity, sec.fixed_coupon, sec.frequency
                )
                dirty_price = pos.book_price + ai
                try:
                    ytm = calc_ytm_of_bond(
                        dirty_price,
                        sec.fixed_coupon,
                        period_end_date,
                        sec.maturity,
                        freq=sec.frequency,
                    )
                except ValueError as e:
                    logging.info(f"got Value error : {e}")
                    ytm = 1e-7
                pv = calc_pv_of_vanilla_bond(
                    period_end_date,
                    sec.maturity,
                    sec.fixed_coupon,
                    curve,
                    freq=sec.frequency,
                )

                risk_scenario = RiskScenario.objects.create(
                    security=sec,
                    scenario=scenario,
                    price=pos.book_price,
                    yield_to_maturity=ytm,
                    discounted_pv=pv,
                    oas=0.0,
                    accrued_interest=ai,
                )

                scen_pos.risk_scenario = risk_scenario
                scen_pos.discounted_value = pv * pos.quantity / 100
                scen_pos.save()

    print("ScenarioPositions successfully created.")

except Exception as e:
    print(f"Error occurred: {str(e)}")
