"""
Diverging bar chart of country fixed effects (real-world vs. WLTP fuel
consumption, % deviation from the EU/EEA sample average for the same
vehicle model). Reads db/country_effects_ref_EU.csv, produces light and
dark PNGs for docs/images/, embedded in README.md via a <picture> tag.
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "docs" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "db" / "country_effects_ref_EU.csv")
df["country"] = df["Coefficient"].str.extract(r"S\.([A-Z]{2})")
df = df.sort_values("pct_vs_ref", ascending=True).reset_index(drop=True)

BLUE = "#2a78d6"
RED = "#e34948"

THEMES = {
    "light": dict(
        surface="#fcfcfb", primary="#0b0b0b", secondary="#52514e",
        muted="#898781", grid="#e1e0d9", baseline="#c3c2b7",
        blue=BLUE, red=RED,
    ),
    "dark": dict(
        surface="#1a1a19", primary="#ffffff", secondary="#c3c2b7",
        muted="#898781", grid="#2c2c2a", baseline="#383835",
        blue="#3987e5", red="#e66767",
    ),
}

for mode, c in THEMES.items():
    fig, ax = plt.subplots(figsize=(8, 9), dpi=180)
    fig.patch.set_facecolor(c["surface"])
    ax.set_facecolor(c["surface"])

    colors = [c["blue"] if v < 0 else c["red"] for v in df["pct_vs_ref"]]
    y = range(len(df))
    ax.barh(y, df["pct_vs_ref"], color=colors, height=0.62, zorder=3)

    # error bars (95% CI), thin and muted
    ax.errorbar(
        df["pct_vs_ref"], y,
        xerr=[df["pct_vs_ref"] - df["ci_low_pct"], df["ci_high_pct"] - df["pct_vs_ref"]],
        fmt="none", ecolor=c["muted"], elinewidth=0.8, capsize=1.5, zorder=4, alpha=0.7,
    )

    ax.set_yticks(list(y))
    ax.set_yticklabels(df["country"], fontsize=9, color=c["secondary"])
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-1, len(df))
    ax.set_xlim(df["ci_low_pct"].min() - 3.5, df["ci_high_pct"].max() + 3.5)

    # value labels beyond the CI whisker, with a surface-color halo so any
    # gridline/whisker crossing under the text stays hidden
    for yi, v, lo, hi in zip(y, df["pct_vs_ref"], df["ci_low_pct"], df["ci_high_pct"]):
        if v >= 0:
            x_label, ha = hi + 0.35, "left"
        else:
            x_label, ha = lo - 0.35, "right"
        ax.text(x_label, yi, f"{v:+.1f}%", va="center", ha=ha,
                 fontsize=7.5, color=c["secondary"], zorder=6,
                 bbox=dict(facecolor=c["surface"], edgecolor="none", pad=0.6))

    ax.axvline(0, color=c["baseline"], linewidth=1, zorder=2)
    ax.grid(axis="x", color=c["grid"], linewidth=0.6, zorder=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("% deviation from EU/EEA sample average (same vehicle model)",
                   fontsize=9, color=c["muted"])
    ax.tick_params(axis="x", labelsize=8, colors=c["muted"])

    ax.set_title("Real-world vs. official fuel consumption, by country",
                  fontsize=13, color=c["primary"], loc="left", pad=28, fontweight="bold")
    fig.text(0.125, 0.935,
              "Same vehicle model across countries · negative = more economical than average",
              fontsize=9, color=c["secondary"])
    fig.text(0.125, 0.01,
              "Source: JRC OBFCM 2021–2023 · vehicle-family fixed effects, clustered SE · EuroFuelEconomy",
              fontsize=7.5, color=c["muted"])

    fig.tight_layout(rect=[0, 0.02, 1, 0.93])
    out = IMG_DIR / f"country_effects_{mode}.png"
    fig.savefig(out, facecolor=c["surface"])
    plt.close(fig)
    print(f"Wrote {out}")
