"""How much of a Senate incumbent's over/under-performance carries into their next race?

Over-performance = candidate's two-party margin (D minus R) minus what the
environment predicted:
  * 2024 (presidential year): the same state's 2024 presidential margin.
  * 2018 (midterm): the state's 2016 presidential margin plus the national
    shift from 2016 (president, D+2.1) to 2018 (House vote, D+8.7).
Sign is flipped for Republican incumbents so positive = the incumbent ran ahead.

Sources: Senate votes, akashic.app (2018, 2024); presidential percentages,
UCSB American Presidency Project (2016, 2024).
"""
import statistics as st

tp = lambda d, r: (d - r) / (d + r) * 100
NAT_2016, NAT_2018 = 2.1, 8.7
# state: (party, sen18 D, sen18 R, sen24 D, sen24 R, pres16 D%, pres16 R%, pres24 D%, pres24 R%)
rows = {
 "CT Murphy":     ("D", 787685, 545717, 953646, 678256, 54.6, 40.9, 56.40, 41.89),
 "FL Scott":      ("R", 4089472, 4099505, 4603077, 5977706, 47.8, 49.0, 42.99, 56.09),
 "HI Hirono":     ("D", 276316, 112035, 324194, 160075, 62.2, 30.0, 60.59, 37.48),
 "MA Warren":     ("D", 1633371, 979210, 2041668, 1365440, 60.0, 32.8, 61.22, 36.02),
 "MN Klobuchar":  ("D", 1566174, 940437, 1792441, 1291712, 46.4, 44.9, 50.92, 46.68),
 "MO Hawley":     ("R", 1112935, 1254927, 1243728, 1651907, 38.1, 56.8, 40.08, 58.49),
 "MS Wicker":     ("R", 369567, 547619, 451981, 763420, 40.1, 57.9, 38.00, 60.89),
 "MT Tester":     ("D", 253876, 235963, 276305, 319682, 35.9, 56.5, 38.46, 58.39),
 "ND Cramer":     ("R", 144376, 179720, 121602, 241569, 27.2, 63.0, 30.51, 66.96),
 "NM Heinrich":   ("D", 376998, 212813, 497333, 405978, 48.3, 40.0, 51.85, 45.85),
 "NV Rosen":      ("D", 490071, 441202, 701105, 677046, 47.9, 45.5, 47.49, 50.59),
 "NY Gillibrand": ("D", 3755489, 1730439, 4711669, 3246690, 58.9, 36.6, 55.91, 43.31),
 "OH Brown":      ("D", 2355923, 2053963, 2650949, 2857383, 43.6, 51.7, 43.93, 55.14),
 "PA Casey":      ("D", 2777680, 2134848, 3384180, 3399295, 47.9, 48.6, 48.66, 50.37),
 "RI Whitehouse": ("D", 231477, 144421, 294665, 196039, 54.4, 38.9, 55.54, 41.76),
 "TN Blackburn":  ("R", 985450, 1227483, 1027461, 1918743, 34.7, 60.7, 34.47, 64.19),
 "TX Cruz":       ("R", 4045632, 4260553, 5031249, 5990741, 43.2, 52.2, 42.46, 56.14),
 "VA Kaine":      ("D", 1910370, 1374313, 2417115, 2019911, 49.8, 44.4, 51.83, 46.05),
 "WA Cantwell":   ("D", 1803364, 1282804, 2252577, 1549187, 54.3, 38.1, 57.23, 39.01),
 "WI Baldwin":    ("D", 1472914, 1184885, 1672777, 1643996, 46.5, 47.2, 48.84, 49.70),
 "WY Barrasso":   ("R", 61227, 136210, 63727, 198418, 21.9, 68.2, 25.84, 71.60),
}
xs, ys = [], []
for name, (party, d18, r18, d24, r24, p16d, p16r, p24d, p24r) in rows.items():
    sign = 1 if party == "D" else -1
    x = sign * (tp(d18, r18) - (tp(p16d, p16r) + NAT_2018 - NAT_2016))
    y = sign * (tp(d24, r24) - tp(p24d, p24r))
    xs.append(x); ys.append(y)
    print(f"{name:15s} 2018 {x:+6.1f}   2024 {y:+6.1f}")
k = sum(x * y for x, y in zip(xs, ys)) / sum(x * x for x in xs)
r = st.correlation(xs, ys)
slope, icpt = st.linear_regression(xs, ys)
print(f"\nn={len(xs)}  carry-forward (through origin) k={k:.2f}  correlation r={r:.2f}  OLS slope={slope:.2f} intercept={icpt:+.1f}")
resid = [y - k * x for x, y in zip(xs, ys)]
print(f"mean |2024 over-performance| = {st.mean(abs(y) for y in ys):.1f}; mean |error| using k*x = {st.mean(abs(e) for e in resid):.1f}; using 0 = {st.mean(abs(y) for y in ys):.1f}")
