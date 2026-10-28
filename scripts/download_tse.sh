#!/bin/bash
# Download every file listed in tse_urls.tsv into data/_zips/<dataset>/ (resumable).
# usage: bash scripts/download_tse.sh scripts/tse_urls.tsv data
DATA="$2"
dl() {
  ds="$1"; url="$2"; out="$DATA/_zips/$ds/$(basename "$url")"
  mkdir -p "$(dirname "$out")"
  for i in 1 2 3 4 5; do
    code=$(curl -sL --retry 3 -C - -o "$out" -w "%{http_code}" "$url"); rc=$?
    # a dropped connection still reports HTTP 200, so also require curl's exit status
    # and a local size matching the server's Content-Length (416 = already complete)
    want=$(curl -sIL "$url" | grep -i '^content-length' | tail -1 | tr -dc 0-9)
    have=$(stat -c %s "$out" 2>/dev/null)
    if { [ $rc = 0 ] || [ "$code" = 416 ]; } && [ "$have" = "$want" ]; then echo "OK $ds $(basename "$url")"; return; fi
    sleep 5
  done
  echo "FAIL $ds $url (HTTP $code)"
}
export -f dl; export DATA
tr -d '\r' < "$1" | tr '\t' ' ' | xargs -P 6 -L 1 bash -c 'dl "$0" "$1"'
echo DOWNLOADS_DONE
