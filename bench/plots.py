"""Wykresy i tabela zbiorcza z wyników bench/run.py (bench/results/*.csv).

Uruchomienie (na hoście, wymaga matplotlib):
    python bench/plots.py [--scale 10000]

Tworzy w bench/results/plots/ (PNG i SVG):
  warstwy_<skala>.png  - mediana czasu w kolejnych warstwach dla każdego punktu końcowego,
  narzut_<skala>.png   - z czego składa się czas żądania HTTP (silnik, sterownik, FastAPI, HTTPS, nginx),
  skala_czas.png       - czas żądania przez nginx i czas silnika w zależności od liczby studentów,
  skala_praca.png      - praca bazy (db hits / bloki bufora) względem najmniejszej skali,
  rozmiar.png          - rozmiar baz na dysku,
  import.png           - czas importu danych do każdej z baz,
  rozklad_<skala>.png  - rozkład czasu żądań HTTPS (wykres pudełkowy),
oraz bench/results/summary.csv (mediana, 95. percentyl i średnia dla każdej warstwy).
"""

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RES = Path(__file__).resolve().parent / "results"
OUT = RES / "plots"
BACKENDS = {"neo4j": ("Neo4j", "#2a78d6"), "postgres": ("PostgreSQL", "#eb6834")}
LAYERS = ["engine", "driver", "asgi", "https", "nginx"]
LAYER_LABELS = {"engine": "silnik bazy", "driver": "sterownik", "asgi": "FastAPI\n(w procesie)",
                "https": "HTTPS\ndo API", "nginx": "HTTPS\nprzez nginx"}
PARTS = [("engine", None, "wykonanie w silniku", "#1baf7a"),
         ("driver", "engine", "sterownik, protokół, sieć do bazy", "#eda100"),
         ("asgi", "driver", "FastAPI: autoryzacja, walidacja, serializacja", "#e87ba4"),
         ("https", "asgi", "uvicorn, TLS, sieć do API", "#6250d6"),
         ("nginx", "https", "nginx i drugie połączenie TLS", "#52514e")]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "figure.dpi": 100,
    "savefig.bbox": "tight", "axes.titlesize": 9, "axes.titleweight": "bold",
})


def load(name: str) -> list[dict]:
    with open(RES / name, newline="") as f:
        return list(csv.DictReader(f))


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=200)
    fig.savefig(OUT / f"{name}.svg")
    plt.close(fig)
    print("zapisano", OUT / f"{name}.png")


def p95(v: list[float]) -> float:
    return statistics.quantiles(v, n=20)[18] if len(v) >= 2 else v[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", help="skala dla wykresów warstw (domyślnie największa)")
    args = parser.parse_args()

    samples = defaultdict(list)  # (scale, endpoint, backend, layer) -> ms
    students = {}
    for r in load("samples.csv"):
        samples[(r["scale"], r["endpoint"], r["backend"], r["layer"])].append(float(r["ms"]))
        students[r["scale"]] = int(r["students"])
    scales = sorted(students, key=students.get)
    endpoints = list(dict.fromkeys(k[1] for k in samples))
    scale = args.scale or scales[-1]
    med = {k: statistics.median(v) for k, v in samples.items()}

    with open(RES / "summary.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["scale", "students", "endpoint", "backend", "layer", "n", "median_ms", "p95_ms", "mean_ms"])
        for (sc, ep, be, la), v in sorted(samples.items(), key=lambda kv: (students[kv[0][0]], kv[0][1:])):
            w.writerow([sc, students[sc], ep, be, la, len(v), round(statistics.median(v), 3), round(p95(v), 3),
                        round(statistics.mean(v), 3)])
    print("zapisano", RES / "summary.csv")

    for sc in dict.fromkeys([scales[0], scale]):
        layers_figure(sc, students[sc], endpoints, med)
        overhead_figure(sc, students[sc], endpoints, med)
        boxplot_figure(sc, students[sc], endpoints, samples)
    if len(scales) > 1:
        scaling_figure(scales, students, endpoints, med)
        work_figure(scales, students, endpoints)
        storage_figure(scales, students)


def layers_figure(sc, n, endpoints, med):
    cols = 4
    rows = -(-len(endpoints) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(11, 2.8 * rows))
    x = range(len(LAYERS))
    for ax, ep in zip(axes.flat, endpoints):
        for i, (be, (label, color)) in enumerate(BACKENDS.items()):
            vals = [med.get((sc, ep, be, la), 0) for la in LAYERS]
            ax.bar([j + (i - 0.5) * 0.38 for j in x], vals, width=0.36, color=color, label=label,
                   edgecolor="white", linewidth=1)
        ax.set_title(ep, loc="left")
        ax.set_xticks(list(x), [LAYER_LABELS[la] for la in LAYERS], fontsize=7)
        ax.set_ylabel("mediana [ms]")
    for ax in list(axes.flat)[len(endpoints):]:
        ax.axis("off")
    axes.flat[0].legend(loc="upper left")
    fig.suptitle(f"Czas żądania w kolejnych warstwach – {n} studentów", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, f"warstwy_{sc}")


def overhead_figure(sc, n, endpoints, med):
    """Udział kolejnych warstw w czasie żądania przez nginx (100%), z czasem całkowitym na końcu słupka.
    Udział, a nie skala logarytmiczna: na osi logarytmicznej długości odcinków nie odpowiadają czasom."""
    fig, ax = plt.subplots(figsize=(10, 0.5 * 2 * len(endpoints) + 1.2))
    labels, ys, y = [], [], 0.0
    for ep in endpoints:
        for be, (blabel, _) in BACKENDS.items():
            total = med.get((sc, ep, be, "nginx"), 0)
            left = 0.0
            for layer, prev, plabel, color in PARTS:
                part = max(0.0, med.get((sc, ep, be, layer), 0) - (med.get((sc, ep, be, prev), 0) if prev else 0))
                share = 100 * part / total if total else 0
                share = min(share, 100 - left)
                ax.barh(y, share, left=left, color=color, edgecolor="white", linewidth=1, height=0.8,
                        label=plabel if not labels else None)
                left += share
            ax.text(101, y, f"{total:.1f} ms", va="center", fontsize=7, color=INK)
            labels.append(f"{ep} – {blabel}")
            ys.append(y)
            y += 1
        y += 0.5
    ax.set_yticks(ys, labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("udział w medianie czasu żądania przez nginx [%]")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=7)
    ax.set_title(f"Z czego składa się czas żądania – {n} studentów (na prawo: czas całkowity)", loc="left")
    save(fig, f"narzut_{sc}")


def boxplot_figure(sc, n, endpoints, samples):
    fig, ax = plt.subplots(figsize=(10, 4))
    pos, data, colors, ticks = [], [], [], []
    for i, ep in enumerate(endpoints):
        for j, (be, (_, color)) in enumerate(BACKENDS.items()):
            v = samples.get((sc, ep, be, "https"))
            if v:
                pos.append(i * 3 + j)
                data.append(v)
                colors.append(color)
        ticks.append(i * 3 + 0.5)
    bp = ax.boxplot(data, positions=pos, widths=0.7, patch_artist=True, showfliers=True,
                    flierprops={"markersize": 2, "markeredgecolor": MUTED}, medianprops={"color": INK})
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor(color)
    ax.set_xticks(ticks, [e.replace(" /", "\n/") for e in endpoints], fontsize=7)
    ax.set_yscale("log")
    ax.set_ylabel("czas żądania HTTPS [ms], skala log.")
    for be, (label, color) in BACKENDS.items():
        ax.plot([], [], color=color, linewidth=6, label=label)
    ax.legend(loc="upper right")
    ax.set_title(f"Rozkład czasu żądań HTTPS do API – {n} studentów", loc="left")
    save(fig, f"rozklad_{sc}")


def scaling_figure(scales, students, endpoints, med):
    cols = 4
    rows = -(-len(endpoints) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(11, 2.8 * rows))
    xs = [students[s] for s in scales]
    for ax, ep in zip(axes.flat, endpoints):
        for be, (label, color) in BACKENDS.items():
            ax.plot(xs, [med.get((s, ep, be, "nginx"), float("nan")) for s in scales], color=color, linewidth=2,
                    marker="o", markersize=5, label=f"{label}: żądanie przez nginx")
            ax.plot(xs, [med.get((s, ep, be, "engine"), float("nan")) for s in scales], color=color, linewidth=1.5,
                    linestyle="--", marker="o", markersize=4, markerfacecolor="white",
                    label=f"{label}: silnik bazy")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(ep, loc="left")
        ax.set_xlabel("liczba studentów")
        ax.set_ylabel("mediana [ms]")
    for ax in list(axes.flat)[len(endpoints):]:
        ax.axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.98, 0.08), fontsize=8)
    fig.suptitle("Czas w zależności od rozmiaru danych (obie osie logarytmiczne)", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, "skala_czas")


def work_figure(scales, students, endpoints):
    work = defaultdict(float)  # (scale, endpoint, backend) -> suma pracy zapytań punktu końcowego
    for r in load("queries.csv"):
        work[(r["scale"], r["endpoint"], r["backend"])] += float(r["work"] or 0)
    base = scales[0] if scales[0] != "seed" or len(scales) == 1 else scales[1]
    used = [s for s in scales if students[s] >= students[base]]
    xs = [students[s] for s in used]
    cols = 4
    rows = -(-len(endpoints) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(11, 2.8 * rows))
    for ax, ep in zip(axes.flat, endpoints):
        for be, (label, color) in BACKENDS.items():
            b = work.get((base, ep, be)) or 1
            ax.plot(xs, [work.get((s, ep, be), float("nan")) / b for s in used], color=color, linewidth=2,
                    marker="o", markersize=5, label=label)
        ax.plot(xs, [x / xs[0] for x in xs], color=MUTED, linewidth=1, linestyle=":", label="wzrost liniowy")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(ep, loc="left")
        ax.set_xlabel("liczba studentów")
        ax.set_ylabel(f"praca / praca przy {students[base]}")
    for ax in list(axes.flat)[len(endpoints):]:
        ax.axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.98, 0.1), fontsize=8)
    fig.suptitle("Wzrost pracy bazy: db hits (Neo4j) i odczytane bloki bufora (PostgreSQL), względem "
                 f"{students[base]} studentów", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "skala_praca")


def storage_figure(scales, students):
    st = {(r["scale"], r["backend"], r["metric"]): float(r["value"]) for r in load("storage.csv")}
    xs = [students[s] for s in scales]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(xs, [st.get((s, "neo4j", "store_bytes"), float("nan")) / 2**20 for s in scales],
            color=BACKENDS["neo4j"][1], linewidth=2, marker="o", label="Neo4j: pliki magazynu")
    ax.plot(xs, [st.get((s, "postgres", "database_bytes"), float("nan")) / 2**20 for s in scales],
            color=BACKENDS["postgres"][1], linewidth=2, marker="o", label="PostgreSQL: baza (z indeksami)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("liczba studentów")
    ax.set_ylabel("rozmiar [MiB]")
    ax.legend()
    ax.set_title("Rozmiar danych na dysku", loc="left")
    save(fig, "rozmiar")

    fig, ax = plt.subplots(figsize=(6, 3.5))
    for i, (be, (label, color)) in enumerate(BACKENDS.items()):
        vals = [st.get((s, be, "import_s"), float("nan")) for s in scales]
        ax.bar([j + (i - 0.5) * 0.38 for j in range(len(scales))], vals, width=0.36, color=color, label=label,
               edgecolor="white", linewidth=1)
        for j, v in enumerate(vals):
            ax.text(j + (i - 0.5) * 0.38, v, f"{v:.0f} s" if v >= 1 else f"{v:.1f} s", ha="center", va="bottom",
                    fontsize=7, color=INK)
    ax.set_xticks(range(len(scales)), [str(students[s]) for s in scales])
    ax.set_yscale("log")
    ax.set_xlabel("liczba studentów")
    ax.set_ylabel("czas importu [s], skala log.")
    ax.legend()
    ax.set_title("Import danych przy pierwszym uruchomieniu", loc="left")
    save(fig, "import")


if __name__ == "__main__":
    main()
