import os
import csv
import django
import pathlib
import pandas as pd

data_folder = pathlib.Path(r"/Users/samrullo/programming/pyprojects/fi_djrest_project/data")

# Setup Django environment manually
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from fixed_income.models import Curve


def generate_scenarios(adate, curve_name, scenario_id, periods_with_shocks: dict):
    # Query relevant curves
    curves = Curve.objects.filter(adate=adate, curve_name=curve_name).order_by("year")
    if not curves.exists():
        print("No curves found for the given date and name.")
        return

    output_file = f"stress_scenarios_{curve_name}_{adate}.csv"
    ss_records = []
    for period, shock in periods_with_shocks.items():
        for curve in curves:
            record = {"scenario_id": scenario_id, "period_number": period, "parallel_shock_size": shock,
                      "curve": curve.id, "period_length": 1.0, "simulation_number": 0}
            ss_records.append(record)
    ssdf = pd.DataFrame(ss_records)
    ssdf.to_csv(data_folder / output_file, index=False)
    print(f"CSV saved to {data_folder / output_file}")

if __name__=="__main__":
    adate="2025-04-30"
    curve_name="USD_SWAP"
    period_with_shocks={0:-0.25,1:-0.25,2:-0.05,3:-0.1,4:-0.05,5:-0.1,6:-0.1, 7:-0.25,8:-0.25,9:-0.25}
    generate_scenarios(adate,curve_name,scenario_id=0,periods_with_shocks=period_with_shocks)