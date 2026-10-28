"""Check that the site's files add up at every level and match the official TSE totals.

  official munzona totals == r/{eid}/{UF}.json total   (valid votes per candidate)
  sum of municipalities   == UF total
  sum of voting places    == municipality             (every municipality)
  sum of ballot boxes     == voting place             (every voting place)

usage: .venv/Scripts/python -I scripts/validate_output.py data public/data
"""
import collections
import glob
import json
import os
import sys

import duckdb

DATA, OUT = sys.argv[1], sys.argv[2]
errors = []


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def add(a, b):
    for i, x in enumerate(b):
        if i < len(a):
            a[i] += x
        else:
            a.append(x)
    return a


def vec(rec):
    return rec.get("v") if "v" in rec else rec.get("p", [])


def trim(v):
    v = list(v)
    while v and v[-1] == 0:
        v.pop()
    return v


meta = load(os.path.join(OUT, "meta.json"))
con = duckdb.connect()
official = collections.defaultdict(int)
for t, k, race, nr, q in con.execute(f"""
    SELECT NR_TURNO, CASE WHEN CD_CARGO=8 THEN 7 ELSE CD_CARGO END, CASE WHEN CD_CARGO=1 THEN 'BR' ELSE SG_UF END,
           NR_CANDIDATO, sum(QT_VOTOS_NOMINAIS_VALIDOS)
    FROM '{DATA}/_parquet/cand_munzona/*.parquet' GROUP BY ALL""").fetchall():
    official[(t, k, race, nr)] = q

checked = collections.Counter()
for el in meta["elections"]:
    eid, cargo, turno = el["id"], el["cargo"], el["turno"]
    nat = load(os.path.join(OUT, "r", eid, "BR.json"))
    br_c = nat.get("c")
    for path in sorted(glob.glob(os.path.join(OUT, "r", eid, "*.json"))):
        uf = os.path.basename(path)[:-5]
        if uf == "BR":
            continue
        race = load(path)
        cands = br_c or race["c"]
        # 1. official totals (majoritarian: per candidate)
        if not el["prop"]:
            tot = race["total"]["v"]
            if cargo != 1:
                for i, c in enumerate(cands):
                    if c.get("anulado"):
                        continue
                    got = tot[i] if i < len(tot) else 0
                    want = official.get((turno, cargo, uf, c["n"]), 0)
                    if got != want:
                        errors.append(f"{eid} {uf} cand {c['n']}: site {got} x oficial {want}")
        # 2. municipalities add up to the UF
        s, v = [0] * 6, []
        for rec in race["mun"].values():
            add(s, rec["s"])
            add(v, vec(rec))
        if s != race["total"]["s"] or trim(v) != trim(vec(race["total"])):
            errors.append(f"{eid} {uf}: soma dos municípios difere do total da UF")
        checked["uf"] += 1
        # 3. voting places add up to each municipality; 4. ballot boxes to each place
        for mk, mrec in race["mun"].items():
            mf = load(os.path.join(OUT, "m", f"{mk}.json"))
            per = mf["r"].get(eid, {})
            s, v = [0] * 6, []
            for rec in per.values():
                add(s, rec["s"])
                add(v, vec(rec))
            if s != mrec["s"] or trim(v) != trim(vec(mrec)):
                errors.append(f"{eid} {uf} {mk}: soma dos locais difere do município")
            checked["mun"] += 1
            byloc = collections.defaultdict(lambda: ([0] * 6, []))
            for z in mf["zonas"]:
                for u in load(os.path.join(OUT, "u", str(mk), f"{z}.json"))["urnas"]:
                    rec = u["e"].get(eid)
                    if rec:
                        acc = byloc[f"{z}-{u['l']}"]
                        add(acc[0], rec["s"])
                        add(acc[1], vec(rec))
                        checked["urna"] += 1
            for key, rec in per.items():
                s, v = byloc.get(key, ([0] * 6, []))
                if s != rec["s"] or trim(v) != trim(vec(rec)):
                    errors.append(f"{eid} {uf} {mk} local {key}: soma das urnas difere do local")
            checked["local"] += len(per)
    # national presidente totals vs official
    if cargo == 1:
        tot = nat["total"]["v"]
        for i, c in enumerate(br_c):
            if not c.get("anulado") and tot[i] != official.get((turno, 1, "BR", c["n"]), 0):
                errors.append(f"{eid} BR cand {c['n']}: site {tot[i]} x oficial {official.get((turno, 1, 'BR', c['n']))}")
    print(f"{eid}: ok até aqui ({dict(checked)})", flush=True)

print("\nERROS:" if errors else "\nNenhuma divergência.", *errors[:50], sep="\n")
print(f"{len(errors)} divergências; verificados {dict(checked)}")
sys.exit(1 if errors else 0)
