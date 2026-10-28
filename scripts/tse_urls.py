"""Write the list of TSE 2026 files to download as <dataset>\t<url> lines.

usage: python -I scripts/tse_urls.py > scripts/tse_urls.tsv
"""
import json
import sys
import urllib.request

ODSELE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
API = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id="
UFS = "AC AL AM AP BA BR CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split()


def package(pid):
    with urllib.request.urlopen(API + pid, timeout=60) as r:
        return [res["url"] for res in json.load(r)["result"]["resources"]]


rows = [("votacao_secao", f"{ODSELE}/votacao_secao/votacao_secao_2026_{uf}.zip") for uf in UFS]
rows += [
    ("eleitorado_local_votacao", f"{ODSELE}/eleitorado_locais_votacao/eleitorado_local_votacao_2026.zip"),
    ("consulta_vagas", f"{ODSELE}/consulta_vagas/consulta_vagas_2026.zip"),
    ("consulta_coligacao", f"{ODSELE}/consulta_coligacao/consulta_coligacao_2026.zip"),
]
# boletins de urna and photos carry timestamps/UF lists, so read them from the portal
rows += [("boletim_urna", u) for u in package("resultados-2026-boletim-de-urna") if u.endswith(".zip")]
rows += [("foto_cand", u) for u in package("candidatos-2026") if "/fotos/" in u]
rows += [("relatorio_totalizacao", u) for u in package("resultados-2026") if "relatorio_resultado" in u]
rows += [("perfil_eleitor_secao", u) for u in package("eleitorado-2026") if "perfil_eleitor_secao" in u]

out = open(sys.stdout.fileno(), "w", newline="\n", closefd=False)
for ds, url in rows:
    out.write(f"{ds}\t{url.strip()}\n")
