"""Extract data/_zips/<dataset>/*.zip into data/<dataset>/, verifying integrity.

usage: python -I scripts/extract_tse.py data
"""
import os
import sys
import zipfile

data = os.path.abspath(sys.argv[1])
zroot = os.path.join(data, "_zips")
# zips already extracted successfully, so a rerun only does what is missing
done_path = os.path.join(zroot, "extracted.txt")
done = set(open(done_path).read().split()) if os.path.exists(done_path) else set()
bad = []
for ds in sorted(os.listdir(zroot)):
    if not os.path.isdir(os.path.join(zroot, ds)):
        continue
    dest = os.path.join(data, ds)
    os.makedirs(dest, exist_ok=True)
    for name in sorted(os.listdir(os.path.join(zroot, ds))):
        if not name.endswith(".zip") or name in done:
            continue
        path = os.path.join(zroot, ds, name)
        # photos: one folder per UF so filenames (SQ_CANDIDATO) don't collide across states
        target = os.path.join(dest, name[:-4]) if ds == "foto_cand" else dest
        try:
            with zipfile.ZipFile(path) as z:
                broken = z.testzip()
                if broken:
                    raise zipfile.BadZipFile(f"corrupt member {broken}")
                for m in z.infolist():
                    out = os.path.abspath(os.path.join(target, m.filename))
                    if not out.startswith(target + os.sep) and out != target:
                        raise zipfile.BadZipFile(f"unsafe path {m.filename}")
                z.extractall(target)
            with open(done_path, "a") as f:
                f.write(name + "\n")
            print("OK", ds, name, flush=True)
        except Exception as e:
            bad.append(path)
            print("FAIL", ds, name, e, flush=True)
print("EXTRACT_DONE", len(bad), "failures")
sys.exit(1 if bad else 0)
