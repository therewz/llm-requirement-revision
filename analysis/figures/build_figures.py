"""Draw compact paper figures from the released program outcomes and statistical comparisons."""
import argparse
from collections import defaultdict
import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import os

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
WIDTH = 7.14  # IEEEtran 10pt conference text width, in inches.
COLORS = {"RR": "#777777", "SA": "#D55E00", "EW": "#0072B2"}
MARKERS = {"RR": "s", "SA": "^", "EW": "o"}
STRATA = [
    ("A", "openai", "Task A · GPT", 35),
    ("A", "anthropic", "Task A · Claude", 35),
    ("B", "openai", "Task B · GPT", 34),
    ("B", "anthropic", "Task B · Claude", 34),
]
GROUPS = ("G1", "G2", "G3")
plt = None
Line2D = None
np = None


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def plot_values(package):
    results = package / "analysis"
    view = "primary69__main"
    means = [dict(r, record="condition_mean") for r in read_csv(results/"descriptive/arm_summary.csv")
             if r["view"] == view]
    effects = [dict(r, record="paired_effect") for r in read_csv(results/"statistics/reporting/paired_all_views.csv")
               if r["view"] == view and r["metric"] == "core_loss_rate" and r["contrast"] == "EW minus SA"]
    baseline = {(r["task"], r["group"]): r for r in read_csv(results/"descriptive/baseline_groups.csv")
                if r["view"] == view}
    groups = defaultdict(list)
    for row in read_csv(results/"descriptive/session_metrics.csv"):
        if row["view"] == view and row["condition"] in ("SA", "EW"):
            groups[row["task"], row["provider"], row["group"], row["condition"]].append(row)
    points = []
    for (task, provider, group, condition), rows in groups.items():
        for row in sorted(rows, key=lambda item: item["participant_id"]):
            points.append(dict(task=task, provider=provider, group=group, condition=condition,
                               participant_id=row["participant_id"], group_n=len(rows),
                               core_loss_percent=100*float(row["core_loss_rate"]),
                               baseline_pass_mean=baseline[task, group]["core_baseline_pass_mean"]))
    return {"preservation_effects": means + effects, "group_preservation": points}


def write_plot_data(stem, rows, directory):
    if stem == "preservation_effects":
        fields = ["record", "task", "provider", "condition", "programs", "core_loss_rate_mean",
                  "n_pairs", "difference_percentage_points", "ci_low_pp", "ci_high_pp", "exact_holm_p"]
    else:
        fields = ["task", "provider", "group", "condition", "participant_id", "group_n",
                  "core_loss_percent", "baseline_pass_mean"]
    rows = sorted(rows, key=lambda r: tuple(str(r.get(k, "")) for k in fields[:5]))
    with (directory/(stem+".csv")).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean(ax):
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#bfc4c9", alpha=.53, linewidth=.48)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=2.8)


def legend_handles(arms):
    return [Line2D([], [], linestyle="", color=COLORS[arm], marker=MARKERS[arm],
                   label=arm, markersize=4.6) for arm in arms]


def pformat(text):
    number = float(text)
    exponent = int(np.floor(np.log10(number)))
    mantissa = number / 10**exponent
    return rf"${mantissa:.2f}\times 10^{{{exponent}}}$"


def draw_preservation(rows):
    means = {}
    pairs = {}
    for row in rows:
        stratum = (row["task"], row["provider"])
        if row["record"] == "condition_mean":
            means[(*stratum, row["condition"])] = row
        elif row["record"] == "paired_effect":
            pairs[stratum] = row
        else:
            raise ValueError(f"Unexpected record {row['record']!r}")
    assert len(rows) == 16 and len(means) == 12 and len(pairs) == 4

    fig = plt.figure(figsize=(WIDTH, 2.59))
    left = fig.add_axes([.155, .165, .325, .677])
    right = fig.add_axes([.550, .165, .276, .677])
    positions = (3, 2, 1, 0)
    for y, (task, provider, _, n) in zip(positions, STRATA):
        for arm, offset in (("RR", .25), ("SA", 0), ("EW", -.25)):
            row = means[task, provider, arm]
            assert int(row["programs"]) == n
            x = 100 * float(row["core_loss_rate_mean"])
            left.scatter(x, y + offset, color=COLORS[arm], marker=MARKERS[arm], s=20, zorder=3)
            left.annotate(f"{x:.1f}", (x, y + offset), xytext=(5, 0), textcoords="offset points",
                          ha="left", va="center", color=COLORS[arm], fontsize=7.5)
        row = pairs[task, provider]
        assert int(row["n_pairs"]) == n
        effect = float(row["difference_percentage_points"])
        low, high = float(row["ci_low_pp"]), float(row["ci_high_pp"])
        right.errorbar(effect, y, xerr=[[effect - low], [high - effect]], fmt="D",
                       color=COLORS["EW"], markersize=3.7, elinewidth=1.15, capsize=2.8, zorder=3)
        right.annotate(f"{effect:.1f}", (effect, y), xytext=(0, 5), textcoords="offset points",
                       ha="center", va="bottom", color=COLORS["EW"], fontsize=7.6)
        right.text(1.177, y, pformat(row["exact_holm_p"]), transform=right.get_yaxis_transform(),
                   ha="left", va="center", fontsize=7.6)

    left.set_yticks(positions, [f"{label}\n(n={n})" for _, _, label, n in STRATA])
    left.tick_params(axis="y", pad=6)
    left.set(xlim=(0, 50), xticks=range(0, 51, 10), xlabel="Prior core-test passes lost (%)")
    right.set(yticks=positions, yticklabels=[], xlim=(-40, 4), xticks=range(-40, 1, 10),
              xlabel="EW − SA (percentage points)")
    right.axvline(0, color="#54585d", linestyle="--", linewidth=.75)
    for axis in (left, right):
        axis.set_ylim(-.48, 3.48)
        clean(axis)
    left.set_title("(a) Mean loss of prior core-test passes", loc="left", pad=6, weight="bold")
    right.set_title("(b) Paired difference", loc="left", pad=6, weight="bold")
    right.text(1.177, 1.037, "Adjusted $p$", transform=right.transAxes, ha="left", va="bottom", fontsize=7.6)
    fig.legend(handles=legend_handles(("RR", "SA", "EW")), loc="upper left", bbox_to_anchor=(.142, 1),
               ncol=3, frameon=False, columnspacing=1.1, handletextpad=.32, fontsize=7.7)
    return fig


def offsets(values, step=.065):
    """Spread observations at identical nonzero values without changing x."""
    by_value = defaultdict(list)
    result = np.zeros(len(values))
    for i, value in enumerate(values):
        if value != 0:
            by_value[round(value, 10)].append(i)
    for indexes in by_value.values():
        for j, i in enumerate(indexes):
            result[i] = (j - (len(indexes) - 1) / 2) * step
    return result


def draw_groups(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["task"], row["provider"], row["group"], row["condition"]].append(row)
    assert len(rows) == 276 and len(groups) == 24
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 3.55), sharex=True)
    fig.subplots_adjust(left=.07, right=.988, top=.863, bottom=.215, wspace=.225, hspace=.43)
    for ax, (task, provider, label, n) in zip(axes.flat, STRATA):
        ax.set_title(label, loc="left", weight="bold", pad=4)
        for j, group in enumerate(GROUPS):
            for arm, offset in (("SA", -.152), ("EW", .152)):
                members = sorted(groups[task, provider, group, arm], key=lambda r: r["participant_id"])
                values = [float(row["core_loss_percent"]) for row in members]
                assert len(values) == int(members[0]["group_n"])
                zero_n = sum(value == 0 for value in values)
                y = 2 - j + offset
                ax.scatter(values, y + offsets(values), color=COLORS[arm], marker=MARKERS[arm],
                           s=11, edgecolors="white", linewidths=.15, alpha=.83, zorder=3)
                if zero_n > 1:
                    ax.annotate(f"×{zero_n}", (0, y), xytext=(-3.4, 0), textcoords="offset points",
                                ha="right", va="center", fontsize=7.15, color=COLORS[arm], zorder=5)
                ax.scatter([np.mean(values)], [y], marker="D", s=27, facecolor="none",
                           edgecolor=COLORS[arm], linewidths=1.12, zorder=4)
        ax.set(xlim=(-10, 103), ylim=(-.44, 2.44), xticks=range(0, 101, 25),
               yticks=[2, 1, 0], yticklabels=GROUPS)
        ax.tick_params(axis="y", pad=5)
        clean(ax)
    handles = legend_handles(("SA", "EW"))
    handles.append(Line2D([], [], color="#333333", marker="D", markerfacecolor="white", linestyle="",
                          label="Group mean", markersize=4.5))
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.53, 1), ncol=3, frameon=False,
               columnspacing=1.4, handletextpad=.4)
    fig.text(.53, .099, "Prior core-test passes lost (%)", ha="center", va="center", fontsize=8.1)
    fig.text(.53, .032, "G1 Unstructured   ·   G2 Structured   ·   G3 Constraint-complete",
             ha="center", va="center", fontsize=7.8)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=PACKAGE, help="Frozen replication package")
    parser.add_argument("--output", type=Path, default=PACKAGE / "outputs/figures")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    observations = plot_values(args.package)
    with TemporaryDirectory(prefix="figure-font-cache-") as cache:
        os.environ.setdefault("MPLCONFIGDIR", cache)
        os.environ.setdefault("XDG_CACHE_HOME", cache)
        import matplotlib
        matplotlib.use("Agg")
        global plt, Line2D, np
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
        import numpy as np
        plt.rcParams.update({
            "font.family": "DejaVu Sans", "font.size": 8.1, "axes.titlesize": 8.7, "axes.labelsize": 8.1,
            "xtick.labelsize": 7.6, "ytick.labelsize": 7.9, "pdf.fonttype": 42, "axes.linewidth": .6,
            "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "white",
        })
        for stem, draw in (("preservation_effects", draw_preservation), ("group_preservation", draw_groups)):
            write_plot_data(stem, observations[stem], args.output)
            fig = draw(observations[stem])
            fig.savefig(args.output / f"{stem}.pdf", metadata={"CreationDate": None, "ModDate": None})
            plt.close(fig)
            print(f"{stem}.pdf")


if __name__ == "__main__":
    main()
