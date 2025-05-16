# Position and ScenarioPosition models design
- Associate Position model with RiskCore model. RiskCore price will equal Position book_price. risk_core of Position will be foreign field based on position date, security.
- Associate ScenarioPosition model with RiskScenario model. RiskScenario price will equal ScenarioPosition book_price. risk_scenario foreign field will be based on scenario, security.RiskScenario doesn't have risk_date because scenario has adate and period number and simulation number.

# Transactions
Ability to buy, sell securities across periods, simulations.
For that building ```Transaction``` model that will be linked to ```scenario```.
In addition to ```BUY``` and ```SELL``` transactions, there can be ```CASH_IN``` and ```CASH_OUT``` transactions.
When I Buy a security, I log it to Transaction table, simultaneously I update ScenarioPosition table security quantity.
We run stress test on an initial positions, with certain period number and simulation number.
We calculate PVs of securities in positions and save their PVs into RiskScenario table with scenario foreign key.
We also add positions to ScenarioPosition table with new period number and simulation number.
We layer on transactions (Buy, Sells) to ScenarioPosition.
We query target record in ScenarioPosition based on Transaction security, scenario foreign keys and lot_id.
Supposing we found a single record in ScenarioPosition, we update its Quantity, and we also updated 
its discounted_value by multiplying Quantity with security PV.

When running stress test for a period we upload CASH_IN transactions mainly due to coupon payments.
Each bond will pay coupon.

```Transaction``` should have transaction_price, quantity and principal.

# Position uploading and RiskCore calculation
Upload positions from csv with below fields
- portfolio_name
- position_date in YYYY-MM-DD format
- identifier_client to query security from VanillaBondSecMaster
- quantity
- book_price
- curve_name : will use it later when calculating RiskCore record

Django API view should upload positions to Position table.
It will calculate following fields
- notional_amount equals quantity times book_price/100
- par_value equals quantity
- book_value also equals quantity times book_price/100 

For each security it should populate RiskCore record with below logic
- security : query it from VanillaBondSecMaster based on identifier_client column in the csv file
- risk_date equals position_date
- curve_description : query it based on curve_name
- price equals book_price
- accrued_interest : calculate it using ```calc_accrued_interest(adate, maturity, coupon)```. adate is position_date, maturity and coupon get from security information
- yield_to_maturity : calculate based on price
- discounted_pv : calculate it by querying CurvePoint using position_date and curve_description. Use below code as reference when calculating discounted_pv
```python
dirty_price = price + ai
ytm = calc_ytm_of_bond(dirty_price, coupon, adate, maturity)
pv = calc_pv_of_vanilla_bond(adate, maturity, coupon, curve)
```

Once you populate RiskCore record associate it with risk_core field of Position record.
Then calculate ```discounted_value``` of Position using below logic
- discounted_value : ```quantity * risk_core.discounted_pv/100```

# ScenarioPositions based on Position
We will create Django API view function that will take ```portfolio``` and ```position_date``` as input.
It will also take ```scenario_name``` as input to query ```ScenarioDescription``` and then ```StressScenario``` using scenario description foreign key.
Then for each period number, simulation number in ```StressScenario``` we will populate ```ScenarioPositions```.
For each combination of period number, simulation number, retrieve ```curve_point_shocks``` and use that 
to construct new curve which will be used to calculate PVs for that period and simulation.
A ```curve_point_shock``` represents a shock in percentages to a curve point. 
For instance, a curve_point_shock mmight mean something like USD_SWAP curve as of 4/30/2025, year 1 rate, apply shock of 0.25 or -0.25 percent.
We will use ```curve_point_shocks``` to construct a new curve and calculate Present Values of positions using new curve for each period number and simulation number.

Based on portfolio and position_date query Position records and populate ScenarioPositions for each period and simulation.
For a given period number and simulation number first insert ScenarioPosition records with below fields. discounted_value will be calculated after populating RiskScenarios
ScenarioPosition records to populate first
- portfolio_name : from Position.portfolio_name
- scenario : foreign key to StressScenario.
- position_date : specified position date
- lot_id : lot_id from Position table.
- security : security from Position
- quantity : quantity from Position
- notional_amount : book_price/100 * quantity
- par_value : quantity
- book_price : book_price from Position record
- book_value : book_price/100 * quantity


After querying Positions and inserting ScenarioPosition record above
populate RiskScenario for each period number and simulation number as below
- security : security from Positions
- scenario : reference to StressScenario record for a given period number and simulation number
- price : book_price from ScenarioPositions 
- accrued_interest : calculate it using ```calc_accrued_interest(adate, maturity, coupon)```. adate is position_date, maturity and coupon get from security information
- yield_to_maturity : calculate based on price
- discounted_pv : calculate it by using reconstructed curve above. Use below code as reference when calculating discounted_pv
```python
dirty_price = price + ai
ytm = calc_ytm_of_bond(dirty_price, coupon, adate, maturity)
pv = calc_pv_of_vanilla_bond(adate, maturity, coupon, curve)
``` 

Finally populate remaining columns of ScenarioPosition record
- risk_scenario : reference to RiskScenario record above
- discounted_value : risk_scenario.discounted_pv/100 * quantity

# Designing Stress Scenarios
I am building models to define simple stress scenarios where I will define shocks for each point on a curve.
First I will define ```StressScenarioDescription``` model with name and description fields. 
This table will simply define scenario name and description.
Next I will define ```StressScenario``` model. 
This model will have foreign key to StressScenarioDescription.
It will have period_number, simulation_number, period_length fields.
Then it will have one to many relationship to ```CurvePointShock``` model.
```CurvePointShock``` will have foreign key referencing ```StressScenario```.
One ```StressScenario``` record with the combination of scenario name, period number, simulation number will point to multiple CurvePointShock records.
I should be able to access ```CurvePointShock``` records from single ```StressScenario``` record 
using code like ```stress_scenario.curve_point_shocks```

Each record of ```CurvePointShock``` will define shock to a single point of the curve.
```CurvePointShock``` will have foreign key to ```CurvePoint``` model. 
One record of ```CurvePointShock``` will define shock to one record of ```CurvePoint```.
A curve point is represented by curve name, adate, year, rate.

```python
class StressScenarioDescription(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class StressScenario(models.Model):
    scenario = models.ForeignKey(
        StressScenarioDescription,
        on_delete=models.CASCADE,
        related_name="scenarios"
    )
    period_number = models.IntegerField()
    simulation_number = models.IntegerField()
    curve = models.ForeignKey(
        CurvePoint,
        on_delete=models.CASCADE,
        help_text="Reference to curve point for given name/date/year",
    )
    period_length = models.FloatField(help_text="Length in years")
    parallel_shock_size = models.FloatField(help_text="Shock size in percentages")

    class Meta:
        unique_together = ("scenario", "period_number", "simulation_number", "curve")

    def __str__(self):
        return f"{self.scenario.name} - Period {self.period_number} - Sim {self.simulation_number}"
```