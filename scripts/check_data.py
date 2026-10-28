"""Sanity checks on the raw TSE files before building the site.

1. President votes per candidate: sum of votacao_secao (per ballot box) vs
   votacao_candidato_munzona (official per municipality/zone totals).
2. Coverage: how many sections in votacao_secao have a voting place with
   latitude/longitude in eleitorado_local_votacao.

usage: python -I scripts/check_data.py data
"""
import collections
import csv
import glob
import os
import sys

data = sys.argv[1]
csv.field_size_limit(10**7)


def rows(path):
    with open(path, encoding="latin1", newline="") as f:
        yield from csv.DictReader(f, delimiter=";")


# 1. president totals
secao = collections.Counter()
for r in rows(os.path.join(data, "votacao_secao", "votacao_secao_2026_BR.csv")):
    secao[(r["NR_TURNO"], r["NR_VOTAVEL"])] += int(r["QT_VOTOS"])
munzona = collections.Counter()
names = {}
for r in rows(os.path.join(data, "votacao_candidato_munzona_2026_BR.csv")):
    munzona[(r["NR_TURNO"], r["NR_CANDIDATO"])] += int(r["QT_VOTOS_NOMINAIS"])
    names[r["NR_CANDIDATO"]] = r["NM_URNA_CANDIDATO"]
print("== Presidente: soma por seção x total por município/zona")
for key in sorted(munzona, key=lambda k: (k[0], -munzona[k])):
    a, b = secao[key], munzona[key]
    print(f"  T{key[0]} {key[1]:>3} {names[key[1]]:<30} seções {a:>12,}  munzona {b:>12,}  {'OK' if a == b else 'DIFERENÇA ' + str(a - b)}")
extra = {k: v for k, v in secao.items() if k not in munzona}
print("  brancos/nulos/outros só nas seções:", {f"T{t} {n}": v for (t, n), v in sorted(extra.items())})

# 2. geographic coverage of sections
geo = {}
for path in glob.glob(os.path.join(data, "eleitorado_local_votacao", "*.csv")):
    for r in rows(path):
        lat = r["NR_LATITUDE"].replace(",", ".")
        ok = lat not in ("", "-1") and float(lat) != 0
        geo[(r["NR_TURNO"], r["SG_UF"], r["CD_MUNICIPIO"].lstrip("0"), r["NR_ZONA"], r["NR_SECAO"])] = ok
total = with_geo = 0
missing = collections.Counter()
seen = set()
for r in rows(os.path.join(data, "votacao_secao", "votacao_secao_2026_BR.csv")):
    k = (r["NR_TURNO"], r["SG_UF"], r["CD_MUNICIPIO"].lstrip("0"), r["NR_ZONA"], r["NR_SECAO"])
    if k in seen:
        continue
    seen.add(k)
    total += 1
    if geo.get(k):
        with_geo += 1
    else:
        missing[(r["NR_TURNO"], r["SG_UF"])] += 1
print(f"\n== Seções (Presidente) com coordenadas: {with_geo:,} de {total:,} ({100 * with_geo / total:.2f}%)")
print("  sem coordenada por turno/UF:", dict(missing.most_common(12)))
