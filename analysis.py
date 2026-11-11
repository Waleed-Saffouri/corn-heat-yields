"""How July heat and drought affect U.S. corn yields, 1960-2025.

Yield: U.S. corn (maize) yield, tonnes/hectare (FAO & USDA via Our World in Data).
Weather: NOAA NCEI Climate at a Glance, July average temperature and precipitation
for Iowa and Illinois, the two largest corn-producing states.
"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

y = pd.read_csv("data/us_corn_yield_owid_fao.csv").set_index("year")
w = pd.read_csv("data/noaa_july_weather_IA_IL.csv").set_index("year")
df = y.join(w, how="inner")
df["july_temp_F"] = df[["iowa_july_tavg_F", "illinois_july_tavg_F"]].mean(axis=1)
df["july_rain_in"] = df[["iowa_july_pcp_in", "illinois_july_pcp_in"]].mean(axis=1)

# Yields rise every decade from better seeds and farming, so remove that trend first
# (quadratic trend), then ask what weather explains the year-to-year gaps.
t = df.index.values - 1960
coef = np.polyfit(t, df["us_corn_yield_t_per_ha"], 2)
df["trend"] = np.polyval(coef, t)
df["dev_pct"] = (df["us_corn_yield_t_per_ha"] / df["trend"] - 1) * 100

df["temp_anom_F"] = df["july_temp_F"] - df["july_temp_F"].mean()
df["rain_anom_in"] = df["july_rain_in"] - df["july_rain_in"].mean()

# Linear model: yield deviation ~ temperature anomaly + rain anomaly
X = np.column_stack([np.ones(len(df)), df["temp_anom_F"], df["rain_anom_in"]])
beta, *_ = np.linalg.lstsq(X, df["dev_pct"], rcond=None)
pred = X @ beta
r2 = 1 - ((df["dev_pct"] - pred) ** 2).sum() / ((df["dev_pct"] - df["dev_pct"].mean()) ** 2).sum()
r_temp = df["dev_pct"].corr(df["temp_anom_F"]); r_rain = df["dev_pct"].corr(df["rain_anom_in"])

hot_dry = df[(df["temp_anom_F"] > 1.5) & (df["rain_anom_in"] < -0.5)]
normal = df.drop(hot_dry.index)
worst = df.nsmallest(6, "dev_pct")[["us_corn_yield_t_per_ha", "dev_pct", "july_temp_F", "july_rain_in"]].round(2)

stats = {
    "years": f"{df.index.min()}-{df.index.max()}",
    "yield_1960": round(df.loc[1960, "us_corn_yield_t_per_ha"], 2),
    "yield_2025": round(df.loc[2025, "us_corn_yield_t_per_ha"], 2),
    "yield_growth_x": round(df.loc[2025, "us_corn_yield_t_per_ha"] / df.loc[1960, "us_corn_yield_t_per_ha"], 1),
    "pct_per_degF": round(beta[1], 2),
    "pct_per_inch_rain": round(beta[2], 2),
    "r2": round(r2, 2), "r_temp": round(r_temp, 2), "r_rain": round(r_rain, 2),
    "mean_july_temp": round(df["july_temp_F"].mean(), 1), "mean_july_rain": round(df["july_rain_in"].mean(), 2),
    "n_hot_dry": len(hot_dry), "hot_dry_years": list(hot_dry.index),
    "hot_dry_avg_dev": round(hot_dry["dev_pct"].mean(), 1), "other_avg_dev": round(normal["dev_pct"].mean(), 1),
}
pd.Series(stats).to_csv("data/key_stats.csv", header=False)
worst.to_csv("data/worst_years.csv")
df.round(3).to_csv("data/merged_analysis.csv")
print(pd.Series(stats).to_string()); print(); print(worst.to_string())

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
SRC = "Sources: FAO/USDA via Our World in Data (yield); NOAA NCEI Climate at a Glance (July weather, Iowa & Illinois)."

fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(df.index, df["us_corn_yield_t_per_ha"], color="#2d6a4f", lw=2, label="Actual yield")
ax.plot(df.index, df["trend"], color="#999", lw=1.2, ls="--", label="Long-term trend")
for yr in worst.index[:4]:
    ax.annotate(str(yr), (yr, df.loc[yr, "us_corn_yield_t_per_ha"]), xytext=(0, -16), textcoords="offset points", ha="center", fontsize=9, color="#b5442c")
    ax.scatter(yr, df.loc[yr, "us_corn_yield_t_per_ha"], color="#b5442c", zorder=3)
ax.set_title("U.S. corn yield, 1960-2025: steady gains, sharp weather shocks")
ax.set_ylabel("Tonnes per hectare"); ax.legend(frameon=False, loc="upper left")
fig.text(0.01, 0.01, SRC, fontsize=6.5, color="#666")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("charts/1_yield_trend.png", dpi=200)

fig, ax = plt.subplots(figsize=(8, 4.4))
sc = ax.scatter(df["july_temp_F"], df["dev_pct"], c=df["july_rain_in"], cmap="BrBG", s=38, edgecolor="#333", lw=0.3)
for yr in [1983, 1988, 2012, 1993, 2011]:
    ax.annotate(str(yr), (df.loc[yr, "july_temp_F"], df.loc[yr, "dev_pct"]), xytext=(5, 3), textcoords="offset points", fontsize=8.5)
ax.axhline(0, color="#bbb", lw=0.8)
ax.set_xlabel("Average July temperature, Iowa & Illinois (°F)"); ax.set_ylabel("Yield vs. trend (%)")
ax.set_title("Hotter Julys mean lower corn yields")
cb = fig.colorbar(sc, ax=ax); cb.set_label("July rainfall (inches)")
fig.text(0.01, 0.01, SRC, fontsize=6.5, color="#666")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("charts/2_heat_vs_yield.png", dpi=200)
print("charts saved")
