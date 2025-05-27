from fi_utils.bond_valuation import calc_ytm_of_bond, calculate_pv_from_ytm
import datetime

price = 103.43794520547945
adate = datetime.date(2027, 5, 20)
maturity = datetime.date(2027, 5, 21)
coupon_rate = 5.41

# ytm=1.1
# days_per_year=365
# freq=2
# principal_amount=100
# pv = calculate_pv_from_ytm(
#                 ytm, coupon_rate, adate, maturity, days_per_year, freq, principal_amount
#             )
# print(f"pv : {pv}")


ytm = calc_ytm_of_bond(104.3, coupon_rate, adate, maturity)
print(f"ytm : {ytm}")
