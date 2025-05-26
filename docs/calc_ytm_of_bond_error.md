Great, now we’re getting closer. You’re seeing this error from SciPy:

_minpack.error: Result from function call is not a proper array of floats.

This error typically occurs when the objective function passed to fsolve() returns a non-float or something that cannot be interpreted as a float array, such as:
	•	None
	•	np.nan
	•	A complex number
	•	A Python object
	•	Or a float wrapped in an unexpected container

⸻

🔍 Let’s look at the key part:

def objective_func(ytm: np.ndarray):
    ytm = float(ytm)
    return (
        price
        - calculate_pv_from_ytm(
            ytm, coupon_rate, adate, maturity, days_per_year, freq, principal_amount
        )
    ) ** 2

⚠️ Likely causes:

❌ calculate_pv_from_ytm(...) is returning a complex number, None, or other invalid type
	•	Then objective_func(...) is returning a complex number squared, i.e. complex or float + j.
	•	fsolve() cannot process complex values and crashes with the message you saw.

⸻

✅ Quick Fix: Check return value of calculate_pv_from_ytm

Add a print/debug check like this:

def objective_func(ytm: np.ndarray):
    ytm = float(ytm)
    pv = calculate_pv_from_ytm(
        ytm, coupon_rate, adate, maturity, days_per_year, freq, principal_amount
    )
    print(f"YTM: {ytm}, PV: {pv}, Type(PV): {type(pv)}")

    if isinstance(pv, complex):
        raise ValueError(f"PV is complex for ytm={ytm}: {pv}")
    return (price - pv) ** 2

This will:
	•	Confirm whether calculate_pv_from_ytm() is the source of the complex value
	•	Help you identify which inputs trigger it

⸻

🔬 What to check in calculate_pv_from_ytm():

This function likely contains something like:
	•	A discount_factor = 1 / (1 + ytm / freq) ** (n_periods)
	•	If ytm < -freq, this expression can explode or go complex
	•	Or maybe it uses np.sqrt(...) of a negative number

✅ Best practice:

To harden calc_ytm_of_bond(), catch invalid output like this:

solved_ytm = fsolve(objective_func, np.array(1))

if np.iscomplexobj(solved_ytm) or np.isnan(solved_ytm).any():
    raise ValueError(f"Invalid YTM: {solved_ytm}")

return float(solved_ytm[0])


⸻

🚑 Final Fix Recommendation

Until you patch calculate_pv_from_ytm() itself:
	1.	Print out all inputs to it when it fails
	2.	Add assert or if checks to guard against returning complex or nan
	3.	Add raise in objective_func if the output is not float

⸻

Let me know if you can share the implementation of calculate_pv_from_ytm() — I can pinpoint exactly what to fix inside it.