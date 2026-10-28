"""Convert the raw TSE CSVs (latin-1, ';') into typed Parquet files in data/_parquet/.

Only the columns the site needs are kept; personal data of candidates
(CPF, e-mail, título eleitoral) is never copied.

usage: .venv/Scripts/python -I scripts/stage_parquet.py data [dataset ...]
"""
import glob
import os
import sys
import time

import duckdb

data = sys.argv[1]
only = set(sys.argv[2:])
out_root = os.path.join(data, "_parquet")
CSV = "delim=';', header=true, encoding='latin-1', all_varchar=true, quote='\"'"

INT = "INTEGER"
BIG = "BIGINT"

# dataset -> (glob, columns {name: type or None for text}, exclude-pattern)
DATASETS = {
    "bu": ("boletim_urna/bweb_*.csv", {
        "NR_TURNO": INT, "SG_UF": None, "CD_MUNICIPIO": INT, "NM_MUNICIPIO": None,
        "NR_ZONA": INT, "NR_SECAO": INT, "NR_LOCAL_VOTACAO": INT,
        "CD_CARGO_PERGUNTA": INT, "NR_PARTIDO": INT, "SG_PARTIDO": None,
        "QT_APTOS": INT, "QT_COMPARECIMENTO": INT, "QT_ABSTENCOES": INT,
        "CD_TIPO_URNA": INT, "DS_TIPO_URNA": None,
        "CD_TIPO_VOTAVEL": INT, "DS_TIPO_VOTAVEL": None, "NR_VOTAVEL": INT, "NM_VOTAVEL": None, "QT_VOTOS": INT,
        "NR_URNA_EFETIVADA": None, "CD_CARGA_1_URNA_EFETIVADA": None, "CD_CARGA_2_URNA_EFETIVADA": None,
        "CD_FLASHCARD_URNA_EFETIVADA": None, "DT_CARGA_URNA_EFETIVADA": None,
        "DS_SECOES_AGREGADAS": None, "DT_ABERTURA": None, "DT_ENCERRAMENTO": None,
        "QT_ELEI_BIOM_SEM_HABILITACAO": INT, "DT_EMISSAO_BU": None, "DT_BU_RECEBIDO": None,
        "NR_JUNTA_APURADORA": INT, "NR_TURMA_APURADORA": INT,
    }, None),
    "locais": ("eleitorado_local_votacao/eleitorado_local_votacao_2026_*.csv", {
        "NR_TURNO": INT, "SG_UF": None, "CD_MUNICIPIO": INT, "NM_MUNICIPIO": None,
        "NR_ZONA": INT, "NR_SECAO": INT, "CD_TIPO_SECAO_AGREGADA": INT, "NR_SECAO_PRINCIPAL": INT,
        "NR_LOCAL_VOTACAO": INT, "NM_LOCAL_VOTACAO": None, "DS_TIPO_LOCAL": None,
        "DS_ENDERECO": None, "NM_BAIRRO": None, "NR_CEP": None,
        "NR_LATITUDE": None, "NR_LONGITUDE": None, "DS_SITU_SECAO_ACESSIBILIDADE": None,
        "QT_ELEITOR_SECAO": INT,
    }, "BRASIL"),
    "cand_munzona": ("votacao_candidato_munzona_2026_*.csv", {
        "NR_TURNO": INT, "SG_UF": None, "SG_UE": None, "CD_MUNICIPIO": INT, "NM_MUNICIPIO": None, "NR_ZONA": INT,
        "CD_CARGO": INT, "SQ_CANDIDATO": BIG, "NR_CANDIDATO": INT, "NM_URNA_CANDIDATO": None,
        "NR_PARTIDO": INT, "SG_PARTIDO": None, "NM_PARTIDO": None, "SG_FEDERACAO": None,
        "NM_COLIGACAO": None, "DS_COMPOSICAO_COLIGACAO": None, "ST_VOTO_EM_TRANSITO": None,
        "QT_VOTOS_NOMINAIS": INT, "QT_VOTOS_NOMINAIS_VALIDOS": INT, "DS_SIT_TOT_TURNO": None,
    }, "BRASIL"),
    "partido_munzona": ("votacao_partido_munzona_2026_*.csv", {
        "NR_TURNO": INT, "SG_UF": None, "SG_UE": None, "CD_MUNICIPIO": INT, "NR_ZONA": INT, "CD_CARGO": INT,
        "NR_PARTIDO": INT, "SG_PARTIDO": None, "SG_FEDERACAO": None, "ST_VOTO_EM_TRANSITO": None,
        "QT_VOTOS_LEGENDA_VALIDOS": INT, "QT_TOTAL_VOTOS_LEG_VALIDOS": INT, "QT_VOTOS_NOMINAIS_VALIDOS": INT,
    }, "BRASIL"),
    "detalhe_munzona": ("detalhe_votacao_munzona_2026_*.csv", {
        "NR_TURNO": INT, "SG_UF": None, "SG_UE": None, "CD_MUNICIPIO": INT, "NM_MUNICIPIO": None, "NR_ZONA": INT,
        "CD_CARGO": INT, "ST_VOTO_EM_TRANSITO": None, "QT_APTOS": INT, "QT_TOTAL_SECOES": INT,
        "QT_COMPARECIMENTO": INT, "QT_ABSTENCOES": INT, "QT_VOTOS": INT,
        "QT_TOTAL_VOTOS_VALIDOS": INT, "QT_VOTOS_BRANCOS": INT, "QT_TOTAL_VOTOS_NULOS": INT,
        "QT_TOTAL_VOTOS_ANULADOS": INT,
    }, "BRASIL"),
    "cand": ("consulta_cand_2026_*.csv", {
        "NR_TURNO": INT, "SG_UF": None, "SG_UE": None, "CD_CARGO": INT, "DS_CARGO": None,
        "SQ_CANDIDATO": BIG, "NR_CANDIDATO": INT, "NM_CANDIDATO": None, "NM_URNA_CANDIDATO": None,
        "DS_SITUACAO_CANDIDATURA": None, "NR_PARTIDO": INT, "SG_PARTIDO": None, "NM_PARTIDO": None,
        "SG_FEDERACAO": None, "NM_COLIGACAO": None, "DS_COMPOSICAO_COLIGACAO": None,
        "DS_GENERO": None, "DS_GRAU_INSTRUCAO": None, "DS_COR_RACA": None, "DS_OCUPACAO": None,
        "DT_NASCIMENTO": None, "DS_SIT_TOT_TURNO": None,
    }, "BRASIL"),
    "vagas": ("consulta_vagas/consulta_vagas_2026_*.csv", {
        "SG_UF": None, "SG_UE": None, "CD_CARGO": INT, "DS_CARGO": None, "QT_VAGA": INT,
    }, "BRASIL"),
}

con = duckdb.connect()
con.execute("SET threads=12")
con.execute("SET preserve_insertion_order=false")
for ds, (pattern, cols, exclude) in DATASETS.items():
    if only and ds not in only:
        continue
    files = sorted(f for f in glob.glob(os.path.join(data, pattern)) if not (exclude and exclude in f))
    dest = os.path.join(out_root, ds)
    os.makedirs(dest, exist_ok=True)
    for f in files:
        target = os.path.join(dest, os.path.basename(f).replace(".csv", ".parquet"))
        if os.path.exists(target):
            continue
        t = time.time()
        # -1 / #NULO are TSE's "missing" markers; keep them as NULL for numbers
        sel = ", ".join(
            f"TRY_CAST(NULLIF(\"{c}\", '#NULO') AS {typ}) AS {c}" if typ else f"NULLIF(\"{c}\", '#NULO') AS {c}"
            for c, typ in cols.items()
        )
        tmp = target + ".tmp"
        con.execute(f"COPY (SELECT {sel} FROM read_csv('{f}', {CSV})) TO '{tmp}' (FORMAT parquet, COMPRESSION zstd)")
        os.replace(tmp, target)
        print(f"{ds} {os.path.basename(f)} {time.time() - t:.0f}s", flush=True)
print("STAGE_DONE")
