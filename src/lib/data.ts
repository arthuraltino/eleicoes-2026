// Types and loaders for the files produced by scripts/build_data.py.

/** s = [aptos, comparecimento, brancos, nulos, anulados, legenda]
 *  majoritarian: v = votes per candidate (race order)
 *  proportional: p = votes per party (race order), t = [candIdx, votes, candIdx, votes, ...] */
export type Rec = { s: number[]; v?: number[]; p?: number[]; t?: number[] };

export type ColorKey = 'r' | 'b' | 'o' | 'a' | 'g';

export type Cand = {
  n: number; q: number; nome: string; civil?: string; p: string; pn: number; cor?: ColorKey;
  sq?: number; foto?: 1; sit?: string | null; anulado?: 1; fed?: string | null; col?: string | null;
  gen?: string; ocup?: string; esc?: string; nasc?: string; ue?: string;
};
export type Party = { n: number; q: number; p: string; nome: string; fed?: string | null; cor: ColorKey };

export type Election = { id: string; cargo: number; turno: number; label: string; prop: boolean; ufs: string[] | null };

export type Meta = {
  bu: string[];
  elections: Election[];
  ufs: Record<string, { nome: string; ibge: number; regiao: string }>;
  municipios: Record<string, [string, string, number]>; // key -> [nome, uf, código TSE]
  centros: Record<string, [number, number]>;
  gerado: string;
};

/** summary used by the national municipal map of state races: [color, share‰, margin‰, sigla] */
export type MunSummary = [ColorKey, number, number, string];

export type UfEntry = {
  total: Rec;
  w: [number, number, number] | null;
  lead?: { n: number; nome?: string; p: string; cor: ColorKey; sq?: number; fed?: string | null };
  eleitos?: { n: number; nome: string; p: string; cor: ColorKey; sq?: number; sit: string }[];
};

export type NationalFile = {
  e: string; c?: Cand[]; total: Rec;
  ufs: Record<string, UfEntry>;
  mun: Record<string, Rec | MunSummary>;
};

export type RaceFile = {
  e: string; race: string; uf: string; c: Cand[] | null; parties: Party[] | null; vagas: number | null;
  total: Rec; mun: Record<string, Rec>;
};

export type Local = {
  z: number; l: number; nm: string; end?: string | null; bairro?: string | null; cep?: string | null;
  lat: number | null; lon: number | null; el: number; acc: number; aprox?: 1;
};

export type MunFile = {
  mun: number | string; uf: string; zonas: number[]; locais: Local[];
  r: Record<string, Record<string, Rec>>;
  zg?: GeoJSON.FeatureCollection | null;
};

export type Urna = { s: number; l: number; bu: Record<string, (string | number | number[] | null)[]>; e: Record<string, Rec> };
export type UrnaFile = { mun: number | string; z: number; urnas: Urna[] };

export type SearchEntry = [number | string, number, number, string, string | null]; // mun, zona, local, nome, bairro

const cache = new Map<string, Promise<unknown>>();

export function load<T>(path: string): Promise<T> {
  let p = cache.get(path) as Promise<T> | undefined;
  if (!p) {
    p = fetch(`/data/${path}`).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ao carregar ${path}`);
      return r.json() as Promise<T>;
    });
    // a failed request must be retryable
    p.catch(() => cache.delete(path));
    cache.set(path, p);
  }
  return p;
}

export const loadMeta = () => load<Meta>('meta.json');
export const loadNational = (eid: string) => load<NationalFile>(`r/${eid}/BR.json`);
export const loadRace = (eid: string, uf: string) => load<RaceFile>(`r/${eid}/${uf}.json`);
export const loadMun = (mun: string | number) => load<MunFile>(`m/${mun}.json`);
export const loadUrnas = (mun: string | number, z: number) => load<UrnaFile>(`u/${mun}/${z}.json`);
export const loadSearch = (uf: string) => load<SearchEntry[]>(`s/${uf}.json`);

// ------------------------------------------------------------------ record helpers

export const aptos = (r: Rec) => r.s[0];
export const comparecimento = (r: Rec) => r.s[1];
export const abstencao = (r: Rec) => r.s[0] - r.s[1];
export const brancos = (r: Rec) => r.s[2];
export const nulos = (r: Rec) => r.s[3];
export const anulados = (r: Rec) => r.s[4];

/** valid votes: candidates (majoritarian) or parties incl. legenda (proportional) */
export function validos(r: Rec): number {
  const vec = r.v ?? r.p;
  // national files of state races carry only the totals
  if (!vec) return Math.max(0, r.s[1] - r.s[2] - r.s[3] - r.s[4]);
  let t = 0;
  for (const x of vec) t += x;
  return t;
}

export type Lead = { idx: number; share: number; margin: number };

/** winner index, share of valid votes and margin over the runner-up (0..1) */
export function lead(r: Rec | undefined | null): Lead | null {
  const vec = r?.v ?? r?.p;
  if (!vec || !vec.length) return null;
  let total = 0, a = -1, b = -1;
  for (let i = 0; i < vec.length; i++) {
    total += vec[i];
    if (a < 0 || vec[i] > vec[a]) { b = a; a = i; } else if (b < 0 || vec[i] > vec[b]) b = i;
  }
  if (!total || vec[a] === 0) return null;
  return { idx: a, share: vec[a] / total, margin: (vec[a] - (b >= 0 ? vec[b] : 0)) / total };
}

/** proportional records keep candidates as a flat [idx, votes, ...] list */
export function pairs(t: number[] | undefined): [number, number][] {
  const out: [number, number][] = [];
  if (!t) return out;
  for (let i = 0; i + 1 < t.length; i += 2) out.push([t[i], t[i + 1]]);
  return out;
}

export function sumRecs(recs: Rec[]): Rec {
  const s = [0, 0, 0, 0, 0, 0];
  let v: number[] | undefined, p: number[] | undefined;
  const cand = new Map<number, number>();
  for (const r of recs) {
    for (let i = 0; i < 6; i++) s[i] += r.s[i] ?? 0;
    if (r.v) { v ??= []; r.v.forEach((x, i) => (v![i] = (v![i] ?? 0) + x)); }
    if (r.p) { p ??= []; r.p.forEach((x, i) => (p![i] = (p![i] ?? 0) + x)); }
    for (const [i, q] of pairs(r.t)) cand.set(i, (cand.get(i) ?? 0) + q);
  }
  const out: Rec = { s };
  if (v) out.v = Array.from(v, (x) => x ?? 0);
  if (p) out.p = Array.from(p, (x) => x ?? 0);
  if (cand.size) out.t = [...cand].sort((x, y) => y[1] - x[1]).flat();
  return out;
}
