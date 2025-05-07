from django.db import models


class VanillaBondSecMaster(models.Model):
    identifier_client = models.CharField(max_length=100)
    asset_name = models.CharField(max_length=100)

    fixed_coupon = models.DecimalField(max_digits=10, decimal_places=4)

    frequency = models.IntegerField(
        default=2, help_text="Number of coupon payments per year (default is 2)"
    )

    maturity = models.DateField()

    def __str__(self):
        return f"{self.asset_name} ({self.identifier_client})"

class RiskCore(models.Model):
    security = models.ForeignKey(
        VanillaBondSecMaster,
        on_delete=models.CASCADE,
        related_name="risk_core_data"
    )
    risk_date = models.DateField(help_text="As-of date for risk metrics")

    price = models.FloatField()
    yield_to_maturity = models.FloatField()
    oas = models.FloatField(help_text="Option-Adjusted Spread")
    discounted_pv = models.FloatField()

    def __str__(self):
        return f"RiskCore [{self.risk_date}] for {self.security.identifier_client} @ Price {self.price}"

class Curve(models.Model):
    curve_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.curve_name

class CurvePoint(models.Model):
    curve = models.ForeignKey(Curve, on_delete=models.CASCADE, related_name="points")
    adate = models.DateField(help_text="As-of date for this curve snapshot")
    year = models.IntegerField(help_text="Tenor in years (1–30)")
    rate = models.FloatField(help_text="Swap rate in percent")

    class Meta:
        unique_together = ("curve", "adate", "year")
        ordering = ["curve__curve_name", "adate", "year"]

    def __str__(self):
        return f"{self.curve.curve_name} on {self.adate} - Year {self.year}: {self.rate:.2f}%"

class StressScenario(models.Model):
    scenario_id = models.IntegerField()
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
        unique_together = ("scenario_id", "period_number", "simulation_number", "curve")

    def __str__(self):
        return f"Scenario {self.scenario_id} - Period {self.period_number} - Sim {self.simulation_number}"

class Position(models.Model):
    portfolio_name = models.CharField(max_length=100)
    position_date = models.DateField()
    lot_id = models.IntegerField()
    asset_name = models.CharField(max_length=100)
    identifier_client = models.CharField(max_length=100)
    identifier_isin = models.CharField(max_length=20, blank=True, null=True)
    identifier_cusip = models.CharField(max_length=20, blank=True, null=True)
    identifier_sedol = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    notional_amount = models.DecimalField(max_digits=20, decimal_places=4)
    par_value = models.DecimalField(max_digits=20, decimal_places=4)
    book_price = models.DecimalField(max_digits=10, decimal_places=4)
    book_value = models.DecimalField(max_digits=20, decimal_places=4)
    discounted_price = models.DecimalField(max_digits=10,decimal_places=4, blank=True, null=True)
    discounted_value = models.DecimalField(max_digits=20, decimal_places=4, blank=True, null=True)

    def __str__(self):
        return f"{self.portfolio_name} - {self.asset_name} [Lot {self.lot_id}]"

class ScenarioPosition(models.Model):
    portfolio_name = models.CharField(max_length=100)
    scenario = models.ForeignKey(StressScenario, on_delete=models.CASCADE)
    position_date = models.DateField()
    lot_id = models.IntegerField()
    asset_name = models.CharField(max_length=100)
    identifier_client = models.CharField(max_length=100)
    identifier_isin = models.CharField(max_length=20, blank=True, null=True)
    identifier_cusip = models.CharField(max_length=20, blank=True, null=True)
    identifier_sedol = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.DecimalField(max_digits=20, decimal_places=4)
    notional_amount = models.DecimalField(max_digits=20, decimal_places=4)
    par_value = models.DecimalField(max_digits=20, decimal_places=4)
    book_price = models.DecimalField(max_digits=20, decimal_places=4)
    book_value = models.DecimalField(max_digits=20, decimal_places=4)
    discounted_price = models.DecimalField(max_digits=10,decimal_places=4, blank=True, null=True)
    discounted_value = models.DecimalField(max_digits=20, decimal_places=4, blank=True, null=True)

    def __str__(self):
        return f"{self.portfolio_name} - {self.asset_name}"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
        ("CASH_IN", "Cash In"),
        ("CASH_OUT", "Cash Out"),
    ]

    portfolio_name = models.CharField(max_length=100)
    identifier_client = models.CharField(max_length=100)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    transaction_date = models.DateField()
    transaction_price = models.DecimalField(max_digits=20, decimal_places=4)
    lot_id = models.IntegerField()
    scenario = models.ForeignKey(StressScenario, on_delete=models.CASCADE)

    def __str__(self):
        return (
            f"{self.transaction_type} - {self.portfolio_name} ({self.transaction_date})"
        )


class AborPnL(models.Model):
    portfolio_name = models.CharField(max_length=100)
    identifier_client = models.CharField(max_length=100)
    scenario = models.ForeignKey(StressScenario, on_delete=models.CASCADE)
    period_date = models.DateField()
    begin_period_date = models.DateField()
    end_period_date = models.DateField()
    income_pnl = models.DecimalField(max_digits=20, decimal_places=4)
    amortization_accretion_pnl = models.DecimalField(max_digits=20, decimal_places=4)
    realized_gain_loss_pnl = models.DecimalField(max_digits=20, decimal_places=4)

    def __str__(self):
        return f"{self.portfolio_name} - PnL for Scenario {self.scenario.scenario_id}, Period {self.scenario.period_number}, Sim {self.scenario.simulation_number}"
