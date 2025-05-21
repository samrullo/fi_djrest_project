import datetime
from sampytools.datetime_utils import to_yyyymmdd
import pathlib
import pandas as pd
import logging
from sampytools.logging_utils import init_logging

init_logging(level=logging.INFO)

file=pathlib.Path(r"/Users/samrullo/programming/pyprojects/fi_djrest_project/data/stress_scenario_usd_shift_01_updated.csv")
df=pd.read_csv(file)
periodzerodf=df[df["period_number"]==0]
starting_curve_shocks={year:shock for year,shock in zip(periodzerodf["curve_year"],periodzerodf["parallel_shock_size"])}
cumulative_curve_shocks=starting_curve_shocks

for period in range(1, 10):
    perioddf = df[df["period_number"] == period]
    curve_shocks = {year: shock for year, shock in zip(perioddf["curve_year"], perioddf["parallel_shock_size"])}
    cumulative_curve_shocks = {year: shock + curve_shocks[year] for year, shock in cumulative_curve_shocks.items()}
    for year, shock in cumulative_curve_shocks.items():
        df.loc[(df["period_number"] == period) & (df["curve_year"] == year),"parallel_shock_size"] = shock

print(df.head().to_string())

new_scenario_name="USD_SWAP_SHIFT_02"
df["scenario_name"]=new_scenario_name
adate=datetime.date(2025,4,30)
new_filename=f"stress_scenario_{new_scenario_name.lower()}_{to_yyyymmdd(adate)}.csv"
data_folder=file.parent
df.to_csv(data_folder/new_filename,index=False)
logging.info(f"Saved new stress scenario to {data_folder/new_filename}")