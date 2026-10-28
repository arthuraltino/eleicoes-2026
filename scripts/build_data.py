"""Build the JSON files the site loads, from the Parquet staged by stage_parquet.py.

Source of every vote is the boletim de urna (BU): it matches the official
municipality/zone totals exactly; votes for candidates whose registration was
annulled are kept apart as "anulados".

Output (public/data):
  meta.json                     elections, UFs, municipalities, colors
  r/{eid}/BR.json               national level (all UFs + light municipal summary)
  r/{eid}/{UF}.json             one race: candidates/parties, UF + municipal results
  m/{mun}.json                  voting places, their results per election, zone areas
  u/{mun}/{zona}.json           every ballot box (BU metadata + votes per election)
  s/{UF}.json                   search index of voting places
  fotos/{sq}.webp               photos of every candidate with votes, 112 px wide

usage: .venv/Scripts/python -I scripts/build_data.py data public/data
"""
import collections
import json
import multiprocessing as mp
import os
import re
import shutil
import sys
import time
import unicodedata

import duckdb
import shapely
from PIL import Image
from shapely.geometry import MultiPoint, mapping, shape
from shapely.ops import unary_union

DATA, OUT = sys.argv[1], sys.argv[2]
PQ = os.path.join(DATA, "_parquet")
WORK = os.path.join(DATA, "_work")
DB = os.path.join(WORK, "build.duckdb")

ELECTIONS = [
    {"id": "presidente-1", "cargo": 1, "turno": 1, "label": "Presidente", "race": "BR"},
    {"id": "presidente-2", "cargo": 1, "turno": 2, "label": "Presidente", "race": "BR"},
    {"id": "governador-1", "cargo": 3, "turno": 1, "label": "Governador", "race": "UF"},
    {"id": "governador-2", "cargo": 3, "turno": 2, "label": "Governador", "race": "UF"},
    {"id": "senador-1", "cargo": 5, "turno": 1, "label": "Senador", "race": "UF"},
    {"id": "deputado-federal-1", "cargo": 6, "turno": 1, "label": "Deputado federal", "race": "UF", "prop": True},
    # DF elects deputados distritais (cargo 8) in place of estaduais
    {"id": "deputado-estadual-1", "cargo": 7, "turno": 1, "label": "Deputado estadual", "race": "UF", "prop": True},
]
EIDX = {(e["cargo"], e["turno"]): i for i, e in enumerate(ELECTIONS)}
PT, PL = 13, 22
# kinds of a vote line
NOMINAL, ANULADO, BRANCO, NULO, LEGENDA = 0, 1, 2, 3, 4


# ---------------------------------------------------------------- text helpers
LOWER = {"de", "da", "do", "das", "dos", "e", "em", "na", "no", "nas", "nos", "a", "o", "à", "ao"}
KEEP_UPPER = {
    "EE", "EM", "EMEF", "EMEI", "EEEF", "EEEM", "EEF", "CEU", "CIEP", "SESI", "SENAI", "SESC", "SENAC",
    "IFAC", "IFPE", "IFBA", "IFCE", "UFPE", "UFBA", "UFC", "UNEB", "UFMG", "USP", "UNESP", "UNICAMP",
    "ETEC", "FATEC", "CEFET", "CAIC", "CMEI", "CEI", "CE", "UE", "EMEB", "EMEIEF", "EEB", "CAP", "APAE",
    "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "XV", "XX", "JK", "BR", "SP", "RJ", "MG",
    "PT", "PL", "UBS", "CRAS", "CIEE", "IEMA", "IFMA", "IFPA", "UEPA", "UFPA", "UFAM", "UEA", "PSD",
    "PUC", "PUCRS", "PUCPR", "FMU", "FAAP", "UNIP", "UNINOVE", "CIEJA", "ETE", "IFSP", "UNIFESP", "UFRJ", "UERJ",
    "UFF", "UFRGS", "UFSC", "UDESC", "UFPR", "UTFPR", "UEL", "UEM", "UFG", "UNB", "UFS", "UFAL", "UFPB", "UFRN",
    "UFPI", "UFMA", "UFT", "UNIR", "UFAC", "UFRR", "UNIFAP", "UFMT", "UFMS", "UFES", "UFJF", "UFU", "UFV", "UFLA",
    "IFMG", "IFRJ", "IFRS", "IFSC", "IFPR", "IFG", "IFB", "IFAM", "IFRO", "IFAL", "IFPB", "IFRN", "IFPI", "IFS",
    "IFTO", "IFMT", "IFMS", "IFES", "CEMEI", "EEEFM", "EEFM", "EEM", "CETI", "CEJA", "EJA", "CAPS", "SEST", "SENAT",
    "CTG", "AABB", "ACM", "SESI", "CEEJA", "EMEFM", "EMEIF", "EMEFI", "UMEI", "CEMEB", "CIEM", "CEFAM", "UNESC",
    "FURB", "UNIVALI", "UNOESC", "UPF", "URI", "UNISC", "UCS", "FEEVALE", "UNISINOS", "ULBRA", "UFPEL", "UFSM",
    "FURG", "UNIPAMPA", "UFFS", "UNICENTRO", "UNIOESTE", "UEPG", "UENP", "UNESPAR", "UEMS", "UNEMAT", "UEG", "UNEAL",
    "UEPB", "UERN", "UESPI", "UEMA", "UESC", "UEFS", "UESB", "UFRB", "UFOB", "UNIVASF", "UPE", "UFRPE", "UFCG",
    "UFERSA", "UFCA", "UECE", "URCA", "UVA", "UNILAB", "UFOPA", "UNIFESSPA", "UFRA", "UNIFAL", "UFTM", "UFSJ",
    "UFOP", "UFVJM", "UEMG", "UNIMONTES", "UENF", "UNIRIO", "UFRRJ", "CEDERJ", "FAETEC", "SENAC", "SESC", "SEBRAE",
    "UNICAMP", "UFSCAR", "UFABC", "FATEC", "ETEC", "FEI", "FGV", "FECAP", "ESPM", "UNIFOR", "UNIT", "UNAMA", "CESUPA",
}


def title(s):
    """'ESCOLA ESTADUAL DE SÃO JOSÉ' -> 'Escola Estadual de São José', keeping acronyms."""
    if not s:
        return s
    out = []
    for i, w in enumerate(s.split()):
        bare = re.sub(r"[^\wÀ-ÿ]", "", w)
        if bare.upper() in KEEP_UPPER or (len(bare) <= 3 and not re.search(r"[AEIOUÁÉÍÓÚÂÊÔÃÕ]", bare.upper())):
            out.append(w.upper())
        elif i and w.lower() in LOWER:
            out.append(w.lower())
        else:
            out.append("-".join(p[:1].upper() + p[1:].lower() for p in w.split("-")))
    return " ".join(out)


def norm(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def coord(s):
    try:
        v = float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return None if v in (0, -1) else round(v, 5)


# ---------------------------------------------------------------- phase 1: DuckDB work tables
def prepare():
    os.makedirs(WORK, exist_ok=True)
    if os.path.exists(DB):
        os.remove(DB)
    con = duckdb.connect(DB)
    con.execute("SET threads=6")
    con.execute("SET memory_limit='8GB'")
    eid_case = "CASE " + " ".join(
        f"WHEN cargo={c} AND turno={t} THEN {i}" for (c, t), i in EIDX.items()
    ) + " END"
    # one row per (ballot box, office, votable); cargo 8 (distrital) folds into 7
    con.execute(f"""
        CREATE TABLE b AS
        WITH x AS (
          SELECT NR_TURNO turno, CASE WHEN CD_CARGO_PERGUNTA=8 THEN 7 ELSE CD_CARGO_PERGUNTA END cargo, *
          FROM '{PQ}/bu/*.parquet' WHERE CD_CARGO_PERGUNTA IN (1,3,5,6,7,8) OR CD_CARGO_PERGUNTA=-1)
        SELECT {eid_case} e, SG_UF uf, CD_MUNICIPIO mun, NR_ZONA z, NR_SECAO s, NR_LOCAL_VOTACAO l,
               CD_TIPO_VOTAVEL tv, NR_VOTAVEL nr, NR_PARTIDO np, QT_VOTOS q, QT_APTOS ap, QT_COMPARECIMENTO cp
        FROM x
    """)
    # sections with no turnout at all appear only with cargo -1: give them a presidente row
    con.execute(f"UPDATE b SET e={EIDX[(1, 2)]}, tv=-1 WHERE e IS NULL")
    # valid candidates = the ones with valid votes in the official municipality/zone totals
    # (some are listed there with all their votes annulled)
    con.execute(f"""
        CREATE TABLE valid AS SELECT {eid_case.replace('cargo', 'k').replace('turno', 't')} e,
          CASE WHEN k=1 THEN 'BR' ELSE SG_UF END race, NR_CANDIDATO nr
        FROM (SELECT NR_TURNO t, CASE WHEN CD_CARGO=8 THEN 7 ELSE CD_CARGO END k, SG_UF, NR_CANDIDATO, QT_VOTOS_NOMINAIS_VALIDOS q
              FROM '{PQ}/cand_munzona/*.parquet')
        GROUP BY ALL HAVING sum(q) > 0
    """)
    con.execute(f"""
        CREATE TABLE bv AS
        SELECT b.e, b.uf, CASE WHEN b.e IN ({EIDX[(1, 1)]},{EIDX[(1, 2)]}) THEN 'BR' ELSE b.uf END race,
               b.mun, b.z, b.s, b.l, b.ap, b.cp, b.q, b.nr, b.np,
               CASE WHEN b.tv=1 AND v.nr IS NOT NULL THEN {NOMINAL} WHEN b.tv=1 THEN {ANULADO}
                    WHEN b.tv=2 THEN {BRANCO} WHEN b.tv=3 THEN {NULO} WHEN b.tv=4 THEN {LEGENDA} ELSE -1 END kind
        FROM b LEFT JOIN valid v ON v.e=b.e AND v.race=(CASE WHEN b.e IN ({EIDX[(1, 1)]},{EIDX[(1, 2)]}) THEN 'BR' ELSE b.uf END) AND v.nr=b.nr
    """)
    con.execute("DROP TABLE b")
    con.execute("CREATE TABLE racetot AS SELECT e, race, kind, nr, np, sum(q) q FROM bv WHERE kind IN (0,1,4) GROUP BY ALL")
    con.close()


# ---------------------------------------------------------------- races (candidate/party lists and colors)
def assign_colors(items, key_party):
    """PT red and PL blue everywhere; the next two strongest get ochre and aqua; the rest gray."""
    free, used = ["o", "a"], set()
    for it in items:
        p = key_party(it)
        want = "r" if p == PT else "b" if p == PL else None
        if want and want not in used:
            it["cor"] = want
            used.add(want)
        elif free:
            it["cor"] = free.pop(0)
        else:
            it["cor"] = "g"


def build_races(con):
    cand = con.execute(f"""
        SELECT NR_TURNO, CASE WHEN CD_CARGO=8 THEN 7 ELSE CD_CARGO END, CASE WHEN CD_CARGO=1 THEN 'BR' ELSE SG_UF END,
               NR_CANDIDATO, SQ_CANDIDATO, NM_URNA_CANDIDATO, NM_CANDIDATO, NR_PARTIDO, SG_PARTIDO, SG_FEDERACAO,
               NM_COLIGACAO, DS_COMPOSICAO_COLIGACAO, DS_SIT_TOT_TURNO, DS_GENERO, DS_OCUPACAO, DS_GRAU_INSTRUCAO, DT_NASCIMENTO, SG_UE
        FROM '{PQ}/cand/*.parquet' WHERE CD_CARGO IN (1,3,5,6,7,8)
    """).fetchall()
    info = collections.defaultdict(list)
    for r in cand:
        e = EIDX.get((r[1], r[0]))
        if e is not None:
            info[(e, r[2], r[3])].append(r)
    tot = con.execute("SELECT e, race, kind, nr, np, q FROM racetot").fetchall()
    vagas = {(r[0], r[1]): r[2] for r in con.execute(
        f"SELECT CASE WHEN CD_CARGO=8 THEN 7 ELSE CD_CARGO END, SG_UE, sum(QT_VAGA) FROM '{PQ}/vagas/*.parquet' GROUP BY ALL").fetchall()}
    party_names = {r[0]: (r[1], r[2], r[3]) for r in con.execute(
        f"SELECT NR_PARTIDO, any_value(SG_PARTIDO), any_value(NM_PARTIDO), any_value(SG_FEDERACAO) FROM '{PQ}/cand/*.parquet' GROUP BY 1").fetchall()}

    races = {}
    by_race = collections.defaultdict(list)
    for e, race, kind, nr, np_, q in tot:
        by_race[(e, race)].append((kind, nr, np_, q))
    for (e, race), rows in by_race.items():
        el = ELECTIONS[e]
        cands = []
        for kind, nr, np_, q in rows:
            if kind not in (NOMINAL, ANULADO):
                continue
            opts = info.get((e, race, nr), [])
            # a number can be reused after a substitution: prefer the candidate still in the race
            best = sorted(opts, key=lambda r: (r[12] is None, r[12] == "#NULO"))[0] if opts else None
            c = {"n": nr, "q": q}
            if best:
                c.update({
                    "sq": best[4], "nome": title(best[5]), "civil": title(best[6]), "pn": best[7],
                    "p": best[8], "fed": best[9] if best[9] and best[9] != "#NULO" else None,
                    "col": best[11] if best[11] and best[11] not in ("#NULO", best[8]) else None,
                    "sit": title(best[12]) if best[12] else None, "gen": title(best[13]),
                    "ocup": title(best[14]), "esc": title(best[15]), "nasc": best[16], "ue": best[17],
                })
            else:
                c.update({"nome": f"Candidato {nr}", "pn": int(str(nr)[:2]), "p": "?"})
            if kind == ANULADO:
                c["anulado"] = 1
            cands.append(c)
        cands.sort(key=lambda c: (c.get("anulado", 0), -c["q"]))
        if not el.get("prop"):
            assign_colors([c for c in cands if not c.get("anulado")], lambda c: c["pn"])
        parties = None
        if el.get("prop"):
            pv = collections.Counter()
            for kind, nr, np_, q in rows:
                if kind == NOMINAL:
                    pv[int(str(nr)[:2])] += q
                elif kind == LEGENDA:
                    pv[nr] += q
            parties = [{"n": n, "q": q, "p": party_names.get(n, ("?",))[0], "nome": title(party_names.get(n, (None, "?"))[1]),
                        "fed": (party_names.get(n, (None, None, None))[2] or None)} for n, q in pv.most_common()]
            for p in parties:
                if p["fed"] == "#NULO":
                    p["fed"] = None
            assign_colors(parties, lambda p: p["n"])
            # elected first, then by votes; drop the long tail of zero-vote rows
            cands = [c for c in cands if c["q"] > 0 or (c.get("sit") or "").startswith("Eleito")]
        races[(e, race)] = {
            "e": el["id"], "race": race, "c": cands, "parties": parties,
            "vagas": vagas.get((el["cargo"], race)),
            "cidx": {c["n"]: i for i, c in enumerate(cands)},
            "pidx": {p["n"]: i for i, p in enumerate(parties)} if parties else None,
        }
    return races


# ---------------------------------------------------------------- unit records
class Acc:
    __slots__ = ("ap", "cp", "br", "nu", "an", "leg", "c", "p")

    def __init__(self):
        self.ap = self.cp = self.br = self.nu = self.an = self.leg = 0
        self.c = collections.Counter()
        self.p = collections.Counter()

    def add(self, kind, nr, q, prop):
        if kind == NOMINAL:
            self.c[nr] += q
            if prop:
                self.p[int(str(nr)[:2])] += q
        elif kind == BRANCO:
            self.br += q
        elif kind == NULO:
            self.nu += q
        elif kind == ANULADO:
            self.an += q
        elif kind == LEGENDA:
            self.leg += q
            self.p[nr] += q

    def merge(self, o):
        self.ap += o.ap
        self.cp += o.cp
        self.br += o.br
        self.nu += o.nu
        self.an += o.an
        self.leg += o.leg
        self.c.update(o.c)
        self.p.update(o.p)

    def record(self, race, top=None):
        """s = [aptos, comparecimento, brancos, nulos, anulados, legenda]
        majoritarian: v = votes per candidate (race order)
        proportional: p = votes per party (race order), t = [cand idx, votes, cand idx, votes, ...] best first"""
        rec = {"s": [self.ap, self.cp, self.br, self.nu, self.an, self.leg]}
        if race["parties"] is None:
            v = [0] * len(race["c"])
            for nr, q in self.c.items():
                i = race["cidx"].get(nr)
                if i is not None:
                    v[i] = q
            while v and v[-1] == 0:
                v.pop()
            rec["v"] = v
        else:
            p = [0] * len(race["parties"])
            for n, q in self.p.items():
                i = race["pidx"].get(n)
                if i is not None:
                    p[i] = q
            while p and p[-1] == 0:
                p.pop()
            rec["p"] = p
            t = sorted(((race["cidx"][nr], q) for nr, q in self.c.items() if q and nr in race["cidx"]), key=lambda x: -x[1])
            rec["t"] = [n for pair in (t[:top] if top else t) for n in pair]
        return rec


def summary(rec, race):
    """[winner idx, winner share ‰ of valid votes, margin ‰ over the runner-up] for map coloring."""
    vec = rec.get("v") if "v" in rec else rec.get("p")
    if not vec:
        return None
    valid = sum(vec) if "v" in rec else sum(vec)
    if not valid:
        return None
    order = sorted(range(len(vec)), key=lambda i: -vec[i])
    first = vec[order[0]]
    second = vec[order[1]] if len(order) > 1 else 0
    return [order[0], round(1000 * first / valid), round(1000 * (first - second) / valid)]


# ---------------------------------------------------------------- per-UF worker
def mun_key(uf, tse, tse_ibge):
    if uf == "ZZ":
        return f"zz{tse}"
    return tse_ibge[f"{tse:05d}"]


def zone_areas(mun_geom, pts):
    """Approximate zone areas: Voronoi cells of the voting places, clipped to the
    municipality and merged per zone. pts: {(lon,lat): zona}"""
    if len({z for z in pts.values()}) < 2 or len(pts) < 3:
        return None
    mp_ = MultiPoint([shapely.Point(xy) for xy in pts])
    cells = shapely.get_parts(shapely.voronoi_polygons(mp_, extend_to=mun_geom.envelope.buffer(0.5)))
    keys = list(pts)
    points = shapely.points(keys)
    tree = shapely.STRtree(points)
    per_zone = collections.defaultdict(list)
    for cell in cells:
        hit = tree.query(cell, predicate="contains")
        if len(hit):
            per_zone[pts[keys[hit[0]]]].append(cell)
    feats = []
    for z, cs in sorted(per_zone.items()):
        g = unary_union(cs).intersection(mun_geom).simplify(0.0004)
        if not g.is_empty:
            feats.append({"type": "Feature", "properties": {"z": z},
                          "geometry": json.loads(json.dumps(mapping(shapely.set_precision(g, 0.00001))))})
    return {"type": "FeatureCollection", "features": feats} if feats else None


def process_uf(args):
    uf, races_by_e, ctx = args
    t0 = time.time()
    con = duckdb.connect(DB, read_only=True)
    con.execute("SET threads=2")
    con.execute("SET memory_limit='2GB'")
    tse_ibge = ctx["tse_ibge"]
    centers = ctx["centers"]
    geoms = ctx["geoms"]
    out = ctx["out"]

    # voting places of this UF (union of both rounds; round 1 wins on conflicts)
    locais = {}
    for r in con.execute(f"""
        SELECT CD_MUNICIPIO, NR_ZONA, NR_LOCAL_VOTACAO, NR_TURNO, NM_LOCAL_VOTACAO, DS_ENDERECO, NM_BAIRRO, NR_CEP,
               DS_TIPO_LOCAL, NR_LATITUDE, NR_LONGITUDE, DS_SITU_SECAO_ACESSIBILIDADE, NR_SECAO, CD_TIPO_SECAO_AGREGADA,
               NR_SECAO_PRINCIPAL, QT_ELEITOR_SECAO
        FROM '{PQ}/locais/*.parquet' WHERE SG_UF='{uf}' ORDER BY NR_TURNO DESC
    """).fetchall():
        k = (r[0], r[1], r[2])
        d = locais.setdefault(k, {"secoes": {}, "acc": 0})
        d.update({"nm": title(r[4]), "end": title(r[5]), "bairro": title(r[6]), "cep": r[7], "tipo": r[8],
                  "lat": coord(r[9]), "lon": coord(r[10])})
        d["secoes"][r[12]] = {"el": r[15], "agr": r[13] == 2, "princ": r[14] if r[14] and r[14] > 0 else None}
        if r[11] and "Com acessibilidade" in r[11]:
            d["acc"] += 1

    # ballot-box metadata (one per round and section)
    bu_meta = collections.defaultdict(dict)
    for r in con.execute(f"""
        SELECT NR_TURNO, CD_MUNICIPIO, NR_ZONA, NR_SECAO, any_value(NR_URNA_EFETIVADA), any_value(CD_CARGA_1_URNA_EFETIVADA),
               any_value(CD_CARGA_2_URNA_EFETIVADA), any_value(CD_FLASHCARD_URNA_EFETIVADA), any_value(DT_CARGA_URNA_EFETIVADA),
               any_value(DS_SECOES_AGREGADAS), any_value(DT_ABERTURA), any_value(DT_ENCERRAMENTO),
               max(QT_ELEI_BIOM_SEM_HABILITACAO), any_value(DT_EMISSAO_BU), any_value(DT_BU_RECEBIDO),
               any_value(NR_JUNTA_APURADORA), any_value(NR_TURMA_APURADORA), any_value(DS_TIPO_URNA)
        FROM '{PQ}/bu/*.parquet' WHERE SG_UF='{uf}' GROUP BY 1,2,3,4
    """).fetchall():
        agr = r[9] if r[9] and r[9] != "#NULO#" else None
        # positional to keep the files small; order documented in BU_FIELDS (meta.json)
        meta = [r[4], r[5], r[6], r[7], r[8], r[10], r[11], r[12], r[13], r[14],
                # e.g. "238 / 239 / 243"
                [int(x) for x in re.findall(r"\d+", agr)] if agr else None,
                r[15] if r[15] and r[15] > 0 else None, r[16] if r[16] and r[16] > 0 else None]
        while meta and meta[-1] is None:
            meta.pop()
        bu_meta[(r[1], r[2], r[3])][r[0]] = meta

    # stream every vote line of the UF, ordered so each (municipality, zone) is contiguous
    cur = con.execute(f"""
        SELECT mun, z, s, l, e, kind, nr, np, q, ap, cp FROM bv WHERE uf='{uf}' ORDER BY mun, z, s, e
    """)
    mun_acc = {}          # (e, mun) -> Acc
    loc_acc = {}          # (e, mun, z, l) -> Acc
    sec_local = {}        # (mun, z, s) -> l
    urnas = {}            # s -> {e: Acc}
    seen_stats = set()
    cur_mz = None

    def flush_zone(mz):
        if not mz or not urnas:
            return
        mun, z = mz
        mk = mun_key(uf, mun, tse_ibge)
        recs = []
        for s in sorted(urnas):
            l = sec_local[(mun, z, s)]
            meta = bu_meta.get((mun, z, s), {})
            rec = {"s": s, "l": l, "bu": {str(t): m for t, m in sorted(meta.items())}, "e": {}}
            for e, acc in sorted(urnas[s].items()):
                race = races_by_e[e]
                rec["e"][ELECTIONS[e]["id"]] = acc.record(race)
            recs.append(rec)
        dump(os.path.join(out, "u", str(mk), f"{z}.json"), {"mun": mk, "z": z, "urnas": recs})
        urnas.clear()

    while True:
        rows = cur.fetchmany(200_000)
        if not rows:
            break
        for mun, z, s, l, e, kind, nr, np_, q, ap, cp in rows:
            if (mun, z) != cur_mz:
                flush_zone(cur_mz)
                cur_mz = (mun, z)
            if e not in races_by_e:
                continue
            prop = races_by_e[e]["parties"] is not None
            sec_local[(mun, z, s)] = l
            a = urnas.setdefault(s, {}).get(e)
            if a is None:
                a = urnas[s][e] = Acc()
            if (e, mun, z, s) not in seen_stats:
                seen_stats.add((e, mun, z, s))
                a.ap, a.cp = ap or 0, cp or 0
            if kind >= 0:
                a.add(kind, nr, q or 0, prop)
    flush_zone(cur_mz)

    # roll ballot boxes up to voting places and municipalities by re-reading the zone files
    # would be wasteful; aggregate in DuckDB instead (exact same numbers)
    for mun, z, l, e, kind, nr, q in con.execute(f"""
        SELECT mun, z, l, e, kind, nr, sum(q) FROM bv WHERE uf='{uf}' AND kind>=0 GROUP BY ALL
    """).fetchall():
        if e not in races_by_e:
            continue
        prop = races_by_e[e]["parties"] is not None
        loc_acc.setdefault((e, mun, z, l), Acc()).add(kind, nr, q, prop)
    for mun, z, l, e, ap, cp in con.execute(f"""
        SELECT mun, z, l, e, sum(ap), sum(cp) FROM (SELECT DISTINCT mun, z, s, l, e, ap, cp FROM bv WHERE uf='{uf}') GROUP BY ALL
    """).fetchall():
        if e not in races_by_e:
            continue
        a = loc_acc.setdefault((e, mun, z, l), Acc())
        a.ap, a.cp = ap or 0, cp or 0
    for (e, mun, z, l), a in loc_acc.items():
        mun_acc.setdefault((e, mun), Acc()).merge(a)

    # municipality files: voting places + their results + zone areas
    search = []
    muns = sorted({m for (_, m) in mun_acc})
    for mun in muns:
        mk = mun_key(uf, mun, tse_ibge)
        keys = sorted({(z, l) for (e, m, z, l) in loc_acc if m == mun})
        center = centers.get(mk)
        places = []
        pts = {}
        for z, l in keys:
            d = locais.get((mun, z, l), {})
            lat, lon = d.get("lat"), d.get("lon")
            approx = lat is None or lon is None
            if approx and center:
                lon, lat = center
            p = {"z": z, "l": l, "nm": d.get("nm") or f"Local {l}", "end": d.get("end"), "bairro": d.get("bairro"),
                 "cep": d.get("cep"), "lat": lat, "lon": lon,
                 "el": sum(x["el"] or 0 for x in d.get("secoes", {}).values()), "acc": d.get("acc", 0)}
            if approx:
                p["aprox"] = 1
            places.append(p)
            if not approx and lat is not None:
                pts.setdefault((lon, lat), z)
            search.append([mk, z, l, p["nm"], p["bairro"]])
        res = {}
        for e in races_by_e:
            per = {}
            for z, l in keys:
                a = loc_acc.get((e, mun, z, l))
                if a:
                    per[f"{z}-{l}"] = a.record(races_by_e[e], top=5)
            if per:
                res[ELECTIONS[e]["id"]] = per
        zonas = sorted({z for z, _ in keys})
        doc = {"mun": mk, "uf": uf, "zonas": zonas, "locais": places, "r": res}
        if len(zonas) > 1 and mk in geoms:
            doc["zg"] = zone_areas(shape(geoms[mk]), pts)
        dump(os.path.join(out, "m", f"{mk}.json"), doc)

    # aggregated municipal records for the race files (returned to the parent)
    mun_recs = {}
    for (e, mun), a in mun_acc.items():
        mun_recs.setdefault(e, {})[mun_key(uf, mun, tse_ibge)] = a
    con.close()
    dump(os.path.join(out, "s", f"{uf}.json"), search)
    print(f"{uf}: {len(muns)} municípios, {len(loc_acc)} locais×eleição, {time.time() - t0:.0f}s", flush=True)
    return uf, mun_recs


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    if "--skip-prepare" not in sys.argv:
        prepare()
        print(f"prepare {time.time() - t0:.0f}s", flush=True)
    con = duckdb.connect(DB, read_only=True)
    races = build_races(con)
    ufs = [r[0] for r in con.execute("SELECT DISTINCT uf FROM bv ORDER BY 1").fetchall()]
    con.close()
    # --only AC,DF processes just those UFs (for quick tests)
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].split(",")
        ufs = [u for u in ufs if u in only]

    tse_ibge = {k: int(v) for k, v in json.load(open(os.path.join(DATA, "geo", "tse_ibge.json"))).items()}
    ibge_names, uf_names = {}, {}
    for m in json.load(open(os.path.join(DATA, "geo", "ibge_municipios.json"), encoding="utf-8")):
        ibge_names[m["id"]] = m["nome"]
        u = (m.get("microrregiao") or {}).get("mesorregiao", {}).get("UF") or m["regiao-imediata"]["regiao-intermediaria"]["UF"]
        uf_names[u["sigla"]] = {"nome": u["nome"], "ibge": u["id"], "regiao": u["regiao"]["nome"]}
    gj = json.load(open(os.path.join(DATA, "geo", "full", "municipios.geojson")))
    geoms, centers = collections.defaultdict(dict), {}
    for f in gj["features"]:
        g = shape(f["geometry"])
        k = f["properties"]["ibge"]
        pt = g.representative_point()
        centers[k] = [round(pt.x, 5), round(pt.y, 5)]
        geoms[k // 100000][k] = f["geometry"]

    # photos first, so the candidate lists can say which ones have a picture.
    # Every candidate with votes gets one, resized to what the site shows (≤ 52 px,
    # 2x for dense screens) and stored as WebP.
    fotos = os.path.join(OUT, "fotos")
    shutil.rmtree(fotos, ignore_errors=True)
    os.makedirs(fotos)
    done, n = set(), 0
    for (e, race), r in races.items():
        for c in r["c"]:
            if "sq" not in c:
                continue
            if c["sq"] in done:
                c["foto"] = 1
                continue
            ue = "BR" if c["ue"] == "BR" else race
            src = os.path.join(DATA, "foto_cand", f"foto_cand2026_{ue}_div", f"F{ue}{c['sq']}_div.jpg")
            if not os.path.exists(src):
                continue
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.thumbnail((112, 160), Image.LANCZOS)
                im.save(os.path.join(fotos, f"{c['sq']}.webp"), "WEBP", quality=72, method=6)
            done.add(c["sq"])
            c["foto"] = 1
            n += 1
    print(f"{n} fotos", flush=True)

    for sub in ("r", "m", "u", "s"):
        shutil.rmtree(os.path.join(OUT, sub), ignore_errors=True)

    jobs = []
    for uf in ufs:
        races_by_e = {}
        for e, el in enumerate(ELECTIONS):
            race = races.get((e, "BR" if el["race"] == "BR" else uf))
            if race:
                races_by_e[e] = race
        code = uf_names.get(uf, {}).get("ibge")
        ctx = {"tse_ibge": tse_ibge, "centers": centers, "geoms": geoms.get(code, {}), "out": OUT}
        jobs.append((uf, races_by_e, ctx))
    # biggest states first so the pool finishes evenly
    weight = {"SP": 0, "MG": 1, "RJ": 2, "BA": 3, "RS": 4, "PR": 5, "PE": 6, "CE": 7}
    jobs.sort(key=lambda j: weight.get(j[0], 99))
    with mp.Pool(3) as pool:
        results = dict(pool.imap_unordered(process_uf, jobs))

    # race files: one per election and UF, plus the national file
    for e, el in enumerate(ELECTIONS):
        national = {"e": el["id"], "ufs": {}, "mun": {}}
        br_acc = Acc()
        race_br = races.get((e, "BR"))
        for uf in ufs:
            recs = results.get(uf, {}).get(e)
            if not recs:
                continue
            race = race_br or races[(e, uf)]
            uf_acc = Acc()
            for a in recs.values():
                uf_acc.merge(a)
            br_acc.merge(uf_acc)
            uf_rec = uf_acc.record(race, top=None if race["parties"] is None else 20)
            mun_full = {k: a.record(race, top=5) for k, a in recs.items()}
            head = {k: race[k] for k in ("e", "race", "parties", "vagas")}
            head["c"] = race["c"] if race_br is None else None
            dump(os.path.join(OUT, "r", el["id"], f"{uf}.json"), {**head, "uf": uf, "total": uf_rec, "mun": mun_full})
            # national: UF results + a light municipal summary for the "all municipalities" view
            national["ufs"][uf] = {"total": uf_rec if race_br else {"s": uf_rec["s"]}, "w": summary(uf_rec, race)}
            if not race_br:
                lead = race["parties"] if race["parties"] else race["c"]
                w = national["ufs"][uf]["w"]
                if w:
                    x = lead[w[0]]
                    national["ufs"][uf]["lead"] = {k: x.get(k) for k in ("n", "nome", "p", "cor", "sq", "fed")}
                    if not race["parties"]:
                        national["ufs"][uf]["eleitos"] = [
                            {k: c.get(k) for k in ("n", "nome", "p", "cor", "sq", "sit")}
                            for c in race["c"] if (c.get("sit") or "").startswith(("Eleito", "2º Turno"))]
            for k, a in recs.items():
                if race_br:
                    national["mun"][k] = mun_full[k]
                else:
                    w = summary(mun_full[k], race)
                    if w:
                        lead = race["parties"] if race["parties"] else race["c"]
                        national["mun"][k] = [lead[w[0]]["cor"], w[1], w[2], lead[w[0]]["p"]]
        if race_br:
            national["c"] = race_br["c"]
            national["total"] = br_acc.record(race_br)
        else:
            national["total"] = {"s": [br_acc.ap, br_acc.cp, br_acc.br, br_acc.nu, br_acc.an, br_acc.leg]}
        dump(os.path.join(OUT, "r", el["id"], "BR.json"), national)

    # meta
    con = duckdb.connect(DB, read_only=True)
    muns = {}
    for uf, tse, nm in con.execute(f"SELECT DISTINCT SG_UF, CD_MUNICIPIO, NM_MUNICIPIO FROM '{PQ}/locais/*.parquet'").fetchall():
        mk = mun_key(uf, tse, tse_ibge)
        muns[str(mk)] = [ibge_names.get(mk) or title(nm), uf, tse]
    elections_meta = []
    for e, el in enumerate(ELECTIONS):
        present = sorted({race for (ee, race) in races if ee == e})
        elections_meta.append({k: el[k] for k in ("id", "cargo", "turno", "label")} | {
            "prop": bool(el.get("prop")), "ufs": present if el["race"] == "UF" else None})
    dump(os.path.join(OUT, "meta.json"), {
        "bu": ["urna", "carga1", "carga2", "flash", "dtcarga", "abertura", "encerramento", "biosem",
               "emissao", "recebido", "agregadas", "junta", "turma"],
        "elections": elections_meta, "ufs": uf_names, "municipios": muns, "centros": centers,
        "gerado": time.strftime("%Y-%m-%d %H:%M"),
    })
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
