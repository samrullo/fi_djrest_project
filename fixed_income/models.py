from django.db import models


class VanillaBondSecMaster(models.Model):
    identifier_client = models.CharField(max_length=100)
    asset_name = models.CharField(max_length=100)
    fixed_coupon = models.FloatField()
    frequency = models.IntegerField(
        default=2, help_text="Number of coupon payments per year (default is 2)"
    )
    maturity = models.DateField()
    currency = models.CharField(max_length=10, default="USD")

    def __str__(self):
        return f"{self.asset_name} ({self.identifier_client})"


class SecurityIdentifier(models.Model):
    security = models.ForeignKey(
        VanillaBondSecMaster,
        on_delete=models.CASCADE,
        related_name="security_identifier_data"
    )
    identifier_type = models.CharField(max_length=50)
    identifier_value = models.CharField(max_length=100)


class CurveDescription(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class CurvePoint(models.Model):
    curve_description = models.ForeignKey(
        CurveDescription,
        on_delete=models.CASCADE,
        related_name="points"
    )
    adate = models.DateField(help_text="As-of date for this curve snapshot")
    year = models.IntegerField(help_text="Tenor in years (1–30)")
    rate = models.FloatField(help_text="Swap rate in percent")

    class Meta:
        unique_together = ("curve_description", "adate", "year")
        ordering = ["curve_description__name", "adate", "year"]

    def __str__(self):
        return f"{self.curve_description.name} on {self.adate} - Year {self.year}: {self.rate:.2f}%"


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
    period_length = models.FloatField(help_text="Length in years")

    class Meta:
        unique_together = ("scenario", "period_number", "simulation_number")

    def __str__(self):
        return f"{self.scenario.name} - Period {self.period_number} - Sim {self.simulation_number}"


class CurvePointShock(models.Model):
    stress_scenario = models.ForeignKey(
        StressScenario,
        on_delete=models.CASCADE,
        related_name="curve_point_shocks"
    )
    curve_point = models.ForeignKey(
        CurvePoint,
        on_delete=models.CASCADE,
        help_text="Reference to curve point (curve_name, adate, year, rate)"
    )
    shock_size = models.FloatField(help_text="Shock size in percentages")

    class Meta:
        unique_together = ("stress_scenario", "curve_point")

    def __str__(self):
        return f"Shock {self.shock_size}% on {self.curve_point} in {self.stress_scenario}"


class RiskCore(models.Model):
    security = models.ForeignKey(
        VanillaBondSecMaster,
        on_delete=models.CASCADE,
        related_name="risk_core_data"
    )
    curve_description = models.ForeignKey(
        CurveDescription,
        on_delete=models.CASCADE,
        related_name="risk_core_entries"
    )
    risk_date = models.DateField(help_text="As-of date for risk metrics")
    price = models.FloatField()
    yield_to_maturity = models.FloatField()
    oas = models.FloatField(help_text="Option-Adjusted Spread")
    discounted_pv = models.FloatField()
    accrued_interest = models.FloatField(help_text="Accrued interest as of risk_date")

    def __str__(self):
        return f"RiskCore [{self.risk_date}] for {self.security.identifier_client} using {self.curve_description.name}"


class RiskScenario(models.Model):
    security = models.ForeignKey(
        VanillaBondSecMaster,
        on_delete=models.CASCADE,
        related_name="scenario_risk_data"
    )
    scenario = models.ForeignKey(
        StressScenario,
        on_delete=models.CASCADE,
        related_name="risk_analytics"
    )
    price = models.FloatField()
    yield_to_maturity = models.FloatField()
    oas = models.FloatField(help_text="Option-Adjusted Spread")
    discounted_pv = models.FloatField()
    accrued_interest = models.FloatField(help_text="Accrued interest as of risk_date")

    def __str__(self):
        return (
            f"RiskScenario - {self.security.identifier_client} "
            f"for {self.scenario.scenario.name} P{self.scenario.period_number} S{self.scenario.simulation_number}"
        )


class Position(models.Model):
    portfolio_name = models.CharField(max_length=100)
    position_date = models.DateField()
    lot_id = models.IntegerField()
    security = models.ForeignKey(
        VanillaBondSecMaster,
        on_delete=models.CASCADE,
        related_name="positions"
    )
    risk_core = models.ForeignKey(
        "RiskCore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
        help_text="Linked RiskCore based on position_date and security"
    )
    quantity = models.FloatField()
    notional_amount = models.FloatField()
    par_value = models.FloatField()
    book_price = models.FloatField()
    book_value = models.FloatField()
    discounted_value = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.portfolio_name} - {self.security.asset_name} [Lot {self.lot_id}]"


class ScenarioPosition(models.Model):
    portfolio_name = models.CharField(max_length=100)
    scenario = models.ForeignKey(StressScenario, on_delete=models.CASCADE)
    position_date = models.DateField()
    period_end_date = models.DateField()
    lot_id = models.IntegerField()
    security = models.ForeignKey(
        VanillaBondSecMaster,
        on_delete=models.CASCADE,
        related_name="scenario_positions"
    )
    quantity = models.FloatField()
    notional_amount = models.FloatField()
    par_value = models.FloatField()
    book_price = models.FloatField()
    book_value = models.FloatField()
    discounted_value = models.FloatField(blank=True, null=True)
    risk_scenario = models.ForeignKey(
        'RiskScenario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Linked RiskScenario based on scenario and security."
    )

    def __str__(self):
        return f"{self.portfolio_name} - {self.security.asset_name} [Lot {self.lot_id}]"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
        ("CASH_IN", "Cash In"),
        ("CASH_OUT", "Cash Out"),
    ]
    portfolio_name = models.CharField(max_length=100)
    security = models.ForeignKey(
        VanillaBondSecMaster,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    transaction_date = models.DateField()
    transaction_price = models.FloatField()
    quantity = models.FloatField()
    amount = models.FloatField()
    lot_id = models.IntegerField()
    scenario = models.ForeignKey(StressScenario, on_delete=models.CASCADE)

    def __str__(self):
        return (
            f"{self.transaction_type} - {self.portfolio_name} ({self.transaction_date})"
        )


class AborPnL(models.Model):
    portfolio_name = models.CharField(max_length=100)
    security = models.ForeignKey(
        VanillaBondSecMaster,
        on_delete=models.CASCADE,
        related_name="abor_pnls"
    )
    scenario = models.ForeignKey(StressScenario, on_delete=models.CASCADE)
    period_date = models.DateField()
    begin_period_date = models.DateField()
    end_period_date = models.DateField()
    income_pnl = models.FloatField()
    amortization_accretion_pnl = models.FloatField()
    realized_gain_loss_pnl = models.FloatField()

    def __str__(self):
        return f"{self.portfolio_name} - PnL for Scenario {self.scenario.scenario_id}, Period {self.scenario.period_number}, Sim {self.scenario.simulation_number}"
