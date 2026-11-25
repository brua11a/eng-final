"""Wykresy i tabela zbiorcza z wyników bench/run.py (bench/results/*.csv).

Uruchomienie (na hoście, wymaga matplotlib):
    python bench/plots.py [--scale 10000]

Tworzy w bench/results/plots/ (PNG i SVG):
  warstwy_<skala>.png  - mediana czasu w kolejnych warstwach dla każdego punktu końcowego,
  narzut_<skala>.png   - z czego składa się czas żądania HTTP (silnik, sterownik, FastAPI, sieć i TLS),
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
import matplotlib.font_manager  # noqa: E402
import matplotlib.ticker  # noqa: E402

RES = Path(__file__).resolve().parent / "results"
OUT = RES / "plots"
# Kolory rozróżnialne także w druku czarno-białym (luminancja ok. 67 vs 166) oraz dodatkowe kodowanie kształtem/kreskowaniem
BACKENDS = {"neo4j": ("Neo4j", "#184a8c"), "postgres": ("PostgreSQL", "#f29340")}
MARKERS = {"neo4j": "o", "postgres": "s"}
HATCHES = {"neo4j": "", "postgres": "///"}
HATCH_EDGES = {"neo4j": "white", "postgres": "#8f4408"}
LAYERS = ["engine", "driver", "asgi", "https", "nginx"]
LAYER_LABELS = {"engine": "silnik bazy", "driver": "sterownik", "asgi": "FastAPI\n(w procesie)",
                "https": "HTTPS\ndo API", "nginx": "HTTPS\nprzez nginx"}
# Odcinki wykresu udziałów: różnice median sąsiednich warstw. Warstwy HTTPS i nginx są połączone:
# każdą warstwę mierzy osobna seria żądań, a narzut samego nginx (ok. 0,1-1 ms) mieści się w rozrzucie,
# więc różnica median HTTPS - FastAPI lub nginx - HTTPS wychodzi czasem ujemna.
PARTS = [("engine", None, "wykonanie w silniku", "#184a8c", "", "white"),
         ("driver", "engine", "sterownik, protokół, sieć do bazy", "#f29340", "///", "#8f4408"),
         ("asgi", "driver", "FastAPI: autoryzacja, walidacja, serializacja", "#e6edf5", "...", "#4a6a91"),
         ("nginx", "asgi", "uvicorn, TLS, nginx, sieć", "#767572", "\\\\\\", "#262523")]
# Punkty końcowe pominięte na wykresie udziałów: logowanie to w ok. 99% bcrypt (FastAPI), a katalog
# przedmiotów to w większości czas silnika - narzuty pozostałych warstw toną w rozrzucie pomiarów.
OVERHEAD_SKIP = {"POST /login", "GET /subjects"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

# Czcionka szeryfowa jak w tekście pracy (pakiet tgtermes = TeX Gyre Termes). Pliki OTF są brane
# z dystrybucji TeX-a; gdy ich brak, matplotlib użyje kolejnej czcionki z listy font.serif.
for _style in ("regular", "bold", "italic", "bolditalic"):
    for _dir in ("/usr/share/texmf-dist", "/usr/share/texlive/texmf-dist"):
        _f = Path(_dir) / "fonts/opentype/public/tex-gyre" / f"texgyretermes-{_style}.otf"
        if _f.exists():
            matplotlib.font_manager.fontManager.addfont(str(_f))
            break

FS, FS_SMALL = 11, 9.5  # rozmiar podstawowy i etykiet pomocniczych [pt] (nie większy niż 12 pt tekstu pracy)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["TeX Gyre Termes", "Times New Roman", "Liberation Serif", "STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "font.size": FS, "legend.fontsize": FS_SMALL, "xtick.labelsize": FS_SMALL, "ytick.labelsize": FS_SMALL,
    "figure.titlesize": FS + 1, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "figure.dpi": 100,
    "savefig.bbox": "tight", "axes.titlesize": FS, "axes.titleweight": "bold",
    "hatch.linewidth": 0.6,
})


def _num(v: float, _pos=None) -> str:
    """Liczba w zapisie polskim (przecinek dziesiętny, spacja tysięcy) bez zbędnych zer."""
    s = f"{v:,.0f}" if v >= 10 else f"{v:.3g}"
    return s.replace(",", " ").replace(".", ",")


def log_axes(ax, xs) -> None:
    """Osie logarytmiczne z czytelnymi etykietami: na osi X dokładnie badane skale, na osi Y
    wartości 1-2-5 w zwykłym zapisie zamiast potęg dziesięciu."""
    ax.set_xscale("log")
    ax.set_xticks(xs, [_num(x) for x in xs], rotation=45, ha="right", rotation_mode="anchor", fontsize=FS_SMALL)
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    log_y(ax)


def log_y(ax) -> None:
    ax.set_yscale("log")
    lo, hi = ax.get_ylim()
    # przy szerokim zakresie (więcej niż 3 rzędy wielkości) podziałki 1-2-5 nachodzą na siebie
    subs = (1, 2, 5) if hi / lo <= 1e3 else (1,)
    ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(subs=subs))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_num))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())


def load(name: str) -> list[dict]:
    with open(RES / name, newline="") as f:
        return list(csv.DictReader(f))


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=200)
    fig.savefig(OUT / f"{name}.svg")
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)
    print("zapisano", OUT / f"{name}.pdf")


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
        ax.set_xticks(list(x), [LAYER_LABELS[la] for la in LAYERS], fontsize=FS_SMALL)
        ax.set_ylabel("mediana [ms]")
    for ax in list(axes.flat)[len(endpoints):]:
        ax.axis("off")
    axes.flat[0].legend(loc="upper left")
    fig.suptitle(f"Czas żądania w kolejnych warstwach – {_num(n)} studentów", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, f"warstwy_{sc}")


def overhead_figure(sc, n, endpoints, med):
    """Udział kolejnych warstw w czasie żądania przez nginx (100%), z czasem całkowitym na końcu słupka.
    Udział, a nie skala logarytmiczna: na osi logarytmicznej długości odcinków nie odpowiadają czasom.
    Odcinki to różnice median, więc nie muszą się sumować dokładnie do mediany całości: ujemna różnica
    oznacza narzut mniejszy niż rozrzut pomiarów i jest zgłaszana, a nie ukrywana."""
    eps = [ep for ep in endpoints if ep not in OVERHEAD_SKIP]
    fig, ax = plt.subplots(figsize=(7.6, 0.44 * 2 * len(eps) + 0.9))
    labels, ys, y = [], [], 0.0
    for ep in eps:
        for be, (blabel, _) in BACKENDS.items():
            total = med[(sc, ep, be, "nginx")]
            parts = [med[(sc, ep, be, layer)] - (med[(sc, ep, be, prev)] if prev else 0)
                     for layer, prev, _, _, _, _ in PARTS]
            for (layer, prev, _, _, _, _), part in zip(PARTS, parts):
                if part < 0:
                    raise SystemExit(f"{sc} {ep} {be}: ujemna różnica {layer} - {prev} = {part:.3f} ms")
            left = 0.0
            for (layer, prev, plabel, color, hatch, hedge), part in zip(PARTS, parts):
                share = 100 * part / total
                ax.barh(y, share, left=left, color=color, edgecolor=hedge, hatch=hatch, linewidth=0.7, height=0.78,
                        label=plabel if not labels else None)
                left += share
            ax.text(101.5, y, f"{total:.1f} ms".replace(".", ","), va="center", fontsize=FS_SMALL, color=INK)
            labels.append(f"{ep} – {blabel}")
            ys.append(y)
            y += 1
        y += 0.45
    ax.text(101.5, -0.75, "razem", va="bottom", fontsize=FS_SMALL, color=MUTED, style="italic")
    ax.set_yticks(ys, labels, fontsize=FS_SMALL)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("udział w medianie czasu żądania przez nginx [%]")
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.14), ncol=2, fontsize=FS_SMALL, columnspacing=1.2)
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
    ax.set_xticks(ticks, [e.replace(" /", "\n/") for e in endpoints], fontsize=FS_SMALL)
    log_y(ax)
    ax.set_ylabel("czas żądania HTTPS [ms], skala log.")
    for be, (label, color) in BACKENDS.items():
        ax.plot([], [], color=color, linewidth=6, label=label)
    ax.legend(loc="upper right")
    ax.set_title(f"Rozkład czasu żądań HTTPS do API – {_num(n)} studentów", loc="left")
    save(fig, f"rozklad_{sc}")


def scaling_figure(scales, students, endpoints, med):
    cols = 4
    rows = -(-len(endpoints) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(11, 2.7 * rows))
    xs = [students[s] for s in scales]
    for ax, ep in zip(axes.flat, endpoints):
        for be, (label, color) in BACKENDS.items():
            mk = MARKERS[be]
            ax.plot(xs, [med.get((s, ep, be, "nginx"), float("nan")) for s in scales], color=color, linewidth=2,
                    marker=mk, markersize=5, label=f"{label}: żądanie przez nginx")
            ax.plot(xs, [med.get((s, ep, be, "engine"), float("nan")) for s in scales], color=color, linewidth=1.5,
                    linestyle="--", marker=mk, markersize=4.5, markerfacecolor="white",
                    label=f"{label}: silnik bazy")
        log_axes(ax, xs)
        ax.set_title(ep, loc="left")
        ax.set_xlabel("liczba studentów")
        ax.set_ylabel("mediana [ms]")
    for ax in list(axes.flat)[len(endpoints):]:
        ax.axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.98, 0.08), fontsize=FS_SMALL)
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
        log_axes(ax, xs)
        ax.set_title(ep, loc="left")
        ax.set_xlabel("liczba studentów")
        ax.set_ylabel(f"praca / praca przy {_num(students[base])}")
    for ax in list(axes.flat)[len(endpoints):]:
        ax.axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.98, 0.1), fontsize=FS_SMALL)
    fig.suptitle("Wzrost pracy bazy: db hits (Neo4j) i odczytane bloki bufora (PostgreSQL), względem "
                 f"{_num(students[base])} studentów", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "skala_praca")


def storage_figure(scales, students):
    st = {(r["scale"], r["backend"], r["metric"]): float(r["value"]) for r in load("storage.csv")}
    xs = [students[s] for s in scales]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(xs, [st.get((s, "neo4j", "store_bytes"), float("nan")) / 1e6 for s in scales],
            color=BACKENDS["neo4j"][1], linewidth=2, marker="o", label="Neo4j: pliki magazynu")
    ax.plot(xs, [st.get((s, "postgres", "database_bytes"), float("nan")) / 1e6 for s in scales],
            color=BACKENDS["postgres"][1], linewidth=2, marker="o", label="PostgreSQL: baza (z indeksami)")
    log_axes(ax, xs)
    ax.set_xlabel("liczba studentów")
    ax.set_ylabel("rozmiar [MB]")
    ax.legend()
    ax.set_title("Rozmiar danych na dysku", loc="left")
    save(fig, "rozmiar")

    fig, ax = plt.subplots(figsize=(6, 3.4))
    for i, (be, (label, color)) in enumerate(BACKENDS.items()):
        vals = [st.get((s, be, "import_s"), float("nan")) for s in scales]
        ax.bar([j + (i - 0.5) * 0.38 for j in range(len(scales))], vals, width=0.36, color=color, label=label,
               edgecolor=HATCH_EDGES[be], linewidth=0.8, hatch=HATCHES[be])
        for j, v in enumerate(vals):
            ax.text(j + (i - 0.5) * 0.38, v, (f"{v:.0f} s" if v >= 1 else f"{v:.1f} s").replace(".", ","), ha="center", va="bottom",
                    fontsize=FS_SMALL, color=INK)
    ax.set_xticks(range(len(scales)), [_num(students[s]) for s in scales])
    log_y(ax)
    ax.set_xlabel("liczba studentów")
    ax.set_ylabel("czas importu [s], skala log.")
    ax.legend()
    save(fig, "import")


if __name__ == "__main__":
    main()
