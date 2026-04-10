"""
Generate project figures for SUMMS product overview.
Outputs PNG files to figures/ directory.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)

STYLE = {
    "bg":      "#ffffff",
    "fg":      "#1a1a1a",
    "accent":  "#ff6b1a",
    "accent2": "#0077cc",
    "grid":    "#e8e8e8",
    "bar_a":   "#ff6b1a",
    "bar_b":   "#4a90d9",
    "bar_c":   "#5cb85c",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.facecolor":  STYLE["bg"],
    "figure.facecolor": STYLE["bg"],
    "axes.edgecolor":  STYLE["fg"],
    "axes.labelcolor": STYLE["fg"],
    "xtick.color":     STYLE["fg"],
    "ytick.color":     STYLE["fg"],
    "text.color":      STYLE["fg"],
    "axes.grid":       True,
    "grid.color":      STYLE["grid"],
    "grid.linewidth":  0.6,
    "axes.axisbelow":  True,
})

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 1 — Lines of Code by module
# ─────────────────────────────────────────────────────────────────────────────

modules = [
    ("external_services",     806),
    ("trip_strategies",       287),
    ("models (booking)",      247),
    ("observers",             197),
    ("provider_views",        177),
    ("dashboard_service",     154),
    ("vehicle_views",         139),
    ("map_views",             119),
    ("users/views",           115),
    ("sustainability",        111),
    ("analytics_service",     110),
    ("states",                107),
    ("trip_views",             95),
    ("vehicle_service",        63),
    ("reservation_views",      82),
    ("rewards_service",        65),
    ("reservation_service",    60),
    ("users/models",           53),
    ("analytics_views",        40),
    ("factories",              30),
]
modules.sort(key=lambda x: x[1])

labels = [m[0] for m in modules]
values = [m[1] for m in modules]
colors = [STYLE["bar_a"] if v >= 200 else STYLE["bar_b"] if v >= 100 else STYLE["bar_c"] for v in values]

fig, ax = plt.subplots(figsize=(10, 7))
bars = ax.barh(labels, values, color=colors, height=0.65, edgecolor="none")
for bar, val in zip(bars, values):
    ax.text(val + 8, bar.get_y() + bar.get_height() / 2,
            str(val), va="center", ha="left", fontsize=8.5, color=STYLE["fg"])

ax.set_xlabel("Lines of Code", fontsize=11)
ax.set_title("Lines of Code by Module  (Python source, excl. migrations)", fontsize=13, fontweight="bold", pad=14)
ax.set_xlim(0, max(values) * 1.15)
ax.tick_params(axis="y", labelsize=9)

legend_patches = [
    mpatches.Patch(color=STYLE["bar_a"], label="≥ 200 lines (large)"),
    mpatches.Patch(color=STYLE["bar_b"], label="100–199 lines (medium)"),
    mpatches.Patch(color=STYLE["bar_c"], label="< 100 lines (small)"),
]
ax.legend(handles=legend_patches, fontsize=9, loc="lower right")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig1_loc_by_module.png"), dpi=150)
plt.close()
print("fig1_loc_by_module.png saved")

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 2 — Classes by module
# ─────────────────────────────────────────────────────────────────────────────

class_data = [
    ("external_services",    12),
    ("states",                6),
    ("models (booking)",      6),
    ("pricing",               4),
    ("trip_strategies",       4),
    ("observers",             5),
    ("factories",             3),
    ("users/views",           2),
    ("users/models",          1),
    ("dashboard_service",     1),
    ("reservation_service",   1),
    ("vehicle_service",       1),
    ("analytics_service",     1),
    ("rewards_service",       1),
]
class_data.sort(key=lambda x: x[1])

clabels = [c[0] for c in class_data]
cvalues = [c[1] for c in class_data]

fig, ax = plt.subplots(figsize=(9, 5.5))
bars = ax.barh(clabels, cvalues, color=STYLE["accent2"], height=0.6, edgecolor="none")
for bar, val in zip(bars, cvalues):
    ax.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
            str(val), va="center", ha="left", fontsize=9, color=STYLE["fg"])

ax.set_xlabel("Number of Classes", fontsize=11)
ax.set_title("Classes by Module  (Python source)", fontsize=13, fontweight="bold", pad=14)
ax.set_xlim(0, max(cvalues) * 1.2)
ax.tick_params(axis="y", labelsize=9)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig2_classes_by_module.png"), dpi=150)
plt.close()
print("fig2_classes_by_module.png saved")

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 3 — LOC breakdown by layer (pie)
# ─────────────────────────────────────────────────────────────────────────────

layers = {
    "External Integration\nexternal_services.py":    806,
    "Domain & Patterns\n(models, states, pricing,\nobservers, factories,\ntrip_strategies, sustainability)": 247+107+70+197+30+287+111,
    "Presentation\n(views)":                          82+95+71+119+40+139+177+115,
    "Service Layer":                                  60+63+110+65,
    "Users Module\n(models, views,\ndashboard_service)": 53+115+154,
}

layer_labels = list(layers.keys())
layer_values = list(layers.values())
layer_colors = ["#ff6b1a", "#4a90d9", "#5cb85c", "#f0ad4e", "#9b59b6"]
explode = [0.03] * len(layer_labels)

fig, ax = plt.subplots(figsize=(9, 6))
wedges, texts, autotexts = ax.pie(
    layer_values, labels=None, colors=layer_colors,
    autopct="%1.1f%%", startangle=140, explode=explode,
    pctdistance=0.78, wedgeprops={"edgecolor": "white", "linewidth": 1.5}
)
for at in autotexts:
    at.set_fontsize(9)
    at.set_color("white")
    at.set_fontweight("bold")

legend_labels = [f"{l.replace(chr(10), ' ')}  ({v} lines)" for l, v in zip(layer_labels, layer_values)]
ax.legend(wedges, legend_labels, loc="lower center", bbox_to_anchor=(0.5, -0.22),
          fontsize=8.5, ncol=2, frameon=False)
ax.set_title("LOC Distribution by Architectural Layer  (Python, 6,440 total)",
             fontsize=12, fontweight="bold", pad=16)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig3_loc_by_layer.png"), dpi=150, bbox_inches="tight")
plt.close()
print("fig3_loc_by_layer.png saved")

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 4 — Tech stack overview (horizontal grouped bars)
# ─────────────────────────────────────────────────────────────────────────────

tech = [
    ("STM GTFS-RT Feed",          "External API",   3),
    ("Nominatim",                  "External API",   3),
    ("Overpass API",               "External API",   3),
    ("OSRM",                       "External API",   3),
    ("OpenRouteService",           "External API",   3),
    ("Docker",                     "DevOps",         2),
    ("gtfs-realtime-bindings",     "Python Library", 2),
    ("django-phonenumber-field",   "Python Library", 2),
    ("django-address",             "Python Library", 2),
    ("Bootstrap 5",                "Frontend",       3),
    ("Leaflet.js 1.9.4",           "Frontend",       3),
    ("SQLite3",                    "Database",       2),
    ("Django 6.0.2",               "Framework",      4),
]
tech_labels  = [t[0] for t in tech]
tech_cats    = [t[1] for t in tech]
tech_weights = [t[2] for t in tech]

cat_color = {
    "Framework":      "#ff6b1a",
    "Database":       "#e74c3c",
    "Frontend":       "#3498db",
    "Python Library": "#2ecc71",
    "DevOps":         "#9b59b6",
    "External API":   "#95a5a6",
}
bar_colors = [cat_color[c] for c in tech_cats]

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(tech_labels, tech_weights, color=bar_colors, height=0.6, edgecolor="none")

role_labels = {1: "Optional", 2: "Supporting", 3: "Integration", 4: "Core"}
for bar, w, label in zip(bars, tech_weights, tech_labels):
    ax.text(w + 0.05, bar.get_y() + bar.get_height() / 2,
            role_labels.get(w, ""), va="center", ha="left", fontsize=8.5, color="#555555")

ax.set_xlim(0, 5.5)
ax.set_xticks([])
ax.set_title("Technology Stack  —  SUMMS", fontsize=13, fontweight="bold", pad=14)

legend_patches = [mpatches.Patch(color=v, label=k) for k, v in cat_color.items()]
ax.legend(handles=legend_patches, fontsize=9, loc="lower right", frameon=True)
ax.tick_params(axis="y", labelsize=9.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig4_tech_stack.png"), dpi=150)
plt.close()
print("fig4_tech_stack.png saved")

print(f"\nAll figures saved to: {OUT}")
