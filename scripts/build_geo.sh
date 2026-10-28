#!/bin/bash
# Build the map geometries served by the site from the IBGE meshes in data/geo.
# usage: bash scripts/build_geo.sh   (run from the repo root)
set -euo pipefail
export PATH="/c/Program Files/nodejs:$PATH"
MS="node_modules/.bin/mapshaper"
SRC="data/geo/municipios_uf"
OUT="public/data/geo"
mkdir -p "$OUT/uf" data/geo/full

# 1. every municipality in one layer, full IBGE detail (also used by the Python
#    pipeline to clip the approximate zone areas). The per-state meshes don't share
#    vertices exactly, so snap them and fill the tiny gaps between neighbours.
$MS -i $SRC/*.topo.json combine-files snap -merge-layers force name=municipios \
  -clean gap-fill-area=1km2 \
  -each 'ibge=+codarea, uf=+codarea.slice(0,2)' -filter-fields ibge,uf \
  -o data/geo/full/municipios.geojson precision=0.00001

# 2. national views: light municipalities + states dissolved from them, so borders match
$MS -i data/geo/full/municipios.geojson snap name=municipios \
  -simplify 6% weighted keep-shapes \
  -o "$OUT/municipios.json" format=topojson quantization=1e5 id-field=ibge
$MS -i data/geo/full/municipios.geojson snap name=ufs \
  -dissolve2 uf -filter-slivers -simplify 2% weighted keep-shapes \
  -o "$OUT/ufs.json" format=topojson quantization=1e5 id-field=uf

# 3. one file per state with more detail, for the state and municipal levels
for f in $SRC/*.topo.json; do
  sg=$(basename "$f" .topo.json)
  code=$(python -I -c "import json;print(json.load(open('$f'))['objects'].popitem()[0][2:4])")
  $MS -i data/geo/full/municipios.geojson snap name=municipios \
    -filter "uf === $code" \
    -simplify 25% weighted keep-shapes \
    -o "$OUT/uf/$sg.json" format=topojson quantization=1e5 id-field=ibge
done
ls -la --block-size=K "$OUT" "$OUT/uf" | awk '{print $5, $9}'
