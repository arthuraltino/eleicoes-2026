// Loads the files the current place needs and exposes what the map and panel show.
import {
  loadMun, loadNational, loadRace, loadUrnas, lead, sumRecs,
  type Cand, type ColorKey, type Local, type MunFile, type NationalFile, type Party, type RaceFile, type Rec, type UrnaFile,
} from './data';
import { app, election, heldIn, level, primeiroTurno } from './state.svelte';
import { validos } from './data';

export const view = $state({
  national: null as NationalFile | null,
  race: null as RaceFile | null,
  munFile: null as MunFile | null,
  urnas: null as UrnaFile | null,
  /** 1º turno files, for the "virada" map */
  prevNational: null as NationalFile | null,
  prevRace: null as RaceFile | null,
  loading: false,
  error: null as string | null,
});

let ticket = 0;

/** (re)load whatever the current URL needs; stale responses are dropped */
export async function sync() {
  const my = ++ticket;
  const eid = app.eid;
  const uf = app.uf;
  const mun = app.mun;
  const z = app.z;
  view.loading = true;
  view.error = null;
  try {
    const national = await loadNational(eid);
    if (my !== ticket) return;
    view.national = national;
    let race: RaceFile | null = null;
    if (uf && heldIn(uf)) race = await loadRace(eid, uf).catch(() => null);
    if (my !== ticket) return;
    view.race = race;
    const munFile = mun ? await loadMun(mun) : null;
    if (my !== ticket) return;
    view.munFile = munFile;
    const urnas = mun && z != null ? await loadUrnas(mun, z) : null;
    if (my !== ticket) return;
    view.urnas = urnas;
    const first = app.virada ? primeiroTurno() : null;
    view.prevNational = first ? await loadNational(first) : null;
    view.prevRace = first && uf && race ? await loadRace(first, uf).catch(() => null) : null;
  } catch (e) {
    if (my === ticket) view.error = (e as Error).message;
  } finally {
    if (my === ticket) view.loading = false;
  }
}

// ------------------------------------------------------------------ derived helpers

/** candidate list of the current race (presidente: national list) */
export function cands(): Cand[] {
  return view.national?.c ?? view.race?.c ?? [];
}
export function parties(): Party[] {
  return view.race?.parties ?? [];
}
export function isProp(): boolean {
  return !!election()?.prop;
}

/** color of a record's winner, null when there is no data */
export function winnerColor(r: Rec | null | undefined, list?: { cor?: ColorKey }[]): { key: ColorKey; margin: number } | null {
  const w = lead(r);
  if (!w) return null;
  const src = list ?? (r?.p ? parties() : cands());
  return { key: (src[w.idx]?.cor ?? 'g') as ColorKey, margin: w.margin };
}

export function localKey(z: number, l: number) {
  return `${z}-${l}`;
}

export function localRec(z: number, l: number): Rec | null {
  return view.munFile?.r[app.eid]?.[localKey(z, l)] ?? null;
}

export function currentLocal(): Local | null {
  if (!view.munFile || app.l == null) return null;
  return view.munFile.locais.find((x) => x.z === app.z && x.l === app.l) ?? null;
}

export function currentUrna() {
  if (!view.urnas || app.secao == null) return null;
  return view.urnas.urnas.find((u) => u.s === app.secao) ?? null;
}

/** the record the panel summarizes for the current place */
export function currentRec(): Rec | null {
  const lv = level();
  if (lv === 'br') return view.national?.total ?? null;
  if (lv === 'uf') return view.race?.total ?? (app.eid.startsWith('presidente') ? view.national?.ufs[app.uf!]?.total ?? null : null);
  if (lv === 'mun') {
    if (app.zona != null && view.munFile) {
      const per = view.munFile.r[app.eid] ?? {};
      return sumRecs(view.munFile.locais.filter((x) => x.z === app.zona).map((x) => per[localKey(x.z, x.l)]).filter(Boolean));
    }
    return view.race?.mun[app.mun!] ?? (app.uf === 'ZZ' ? (view.national?.mun[app.mun!] as Rec) ?? null : null);
  }
  if (lv === 'local') return localRec(app.z!, app.l!);
  return currentUrna()?.e[app.eid] ?? null;
}

/** list of the 1º turno race (to find the finalists' numbers) */
export function prevCands(): Cand[] {
  return view.prevNational?.c ?? view.prevRace?.c ?? [];
}

/** how the margin between the two finalists moved from the 1º to the 2º turno.
 *  idx: finalist (2º turno order) the place moved toward; s: size of the move (fraction of valid votes) */
export function swing(rec2: Rec | null | undefined, rec1: Rec | null | undefined): { idx: number; s: number } | null {
  const c2 = cands(), c1 = prevCands();
  if (!rec2?.v || !rec1?.v || c2.length < 2 || !c1.length) return null;
  const ia = c1.findIndex((c) => c.n === c2[0].n), ib = c1.findIndex((c) => c.n === c2[1].n);
  const v2 = validos(rec2), v1 = validos(rec1);
  if (!v2 || !v1 || ia < 0 || ib < 0) return null;
  const m2 = ((rec2.v[0] ?? 0) - (rec2.v[1] ?? 0)) / v2;
  const m1 = ((rec1.v[ia] ?? 0) - (rec1.v[ib] ?? 0)) / v1;
  const d = m2 - m1;
  return { idx: d >= 0 ? 0 : 1, s: Math.abs(d) };
}

export function viradaOn(): boolean {
  return app.virada && !!primeiroTurno() && (election()?.cargo === 1 || level() !== 'br');
}

/** the files a level needs have arrived (avoids flashing stale numbers) */
export function ready(): boolean {
  const lv = level();
  if (!view.national || view.national.e !== app.eid) return false;
  if (lv !== 'br' && heldIn(app.uf) && app.uf !== 'ZZ' && (!view.race || view.race.uf !== app.uf || view.race.e !== app.eid)) return false;
  if ((lv === 'mun' || lv === 'local' || lv === 'urna') && String(view.munFile?.mun) !== app.mun) return false;
  if ((lv === 'local' || lv === 'urna') && (!view.urnas || view.urnas.z !== app.z || String(view.urnas.mun) !== app.mun)) return false;
  return true;
}
