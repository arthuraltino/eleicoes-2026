import { slug } from './format';
import type { Meta } from './data';

export type Level = 'br' | 'uf' | 'mun' | 'local' | 'urna';
export type Place = { uf: string | null; mun: string | null; z: number | null; l: number | null; secao: number | null };

type Prefs = { nacional: 'uf' | 'mun'; tamanho: 'area' | 'bolhas' };

const PREFS_KEY = 'eleicoes2026:prefs';

function readPrefs(): Prefs {
  const def: Prefs = { nacional: 'uf', tamanho: 'area' };
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return def;
    const p = JSON.parse(raw);
    return {
      nacional: p.nacional === 'mun' ? 'mun' : 'uf',
      tamanho: p.tamanho === 'bolhas' ? 'bolhas' : 'area',
    };
  } catch {
    return def;
  }
}

export const DEFAULT_EID = 'presidente-2';

export const app = $state({
  meta: null as Meta | null,
  eid: DEFAULT_EID,
  uf: null as string | null,
  mun: null as string | null,
  z: null as number | null,
  l: null as number | null,
  secao: null as number | null,
  /** zone filter inside a municipality */
  zona: null as number | null,
  prefs: readPrefs(),
  searchOpen: false,
  /** touch devices: first tap previews, second tap opens */
  preview: null as { key: string; label: string; to: Partial<Place> } | null,
  /** list row under the pointer, highlighted on the map */
  hover: null as { source: 'ufs' | 'muns' | 'locais'; id: string | number } | null,
  sheet: 'half' as 'peek' | 'half' | 'full',
  /** 2º turno only: color by how the finalists' margin moved since the 1º turno */
  virada: false,
  /** results panel shown; closing it leaves the whole map */
  panel: true,
});

/** the 1º turno of the current 2º turno election, if any */
export function primeiroTurno(): string | null {
  const e = election();
  if (!e || e.turno !== 2) return null;
  return app.meta?.elections.find((x) => x.cargo === e.cargo && x.turno === 1)?.id ?? null;
}

export function savePrefs() {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(app.prefs));
  } catch {
    // private mode or blocked storage: the choice just lasts for this visit
  }
}

export function level(): Level {
  if (app.secao != null) return 'urna';
  if (app.l != null) return 'local';
  if (app.mun) return 'mun';
  if (app.uf) return 'uf';
  return 'br';
}

export function election() {
  return app.meta?.elections.find((e) => e.id === app.eid) ?? null;
}

/** is the current election held in this UF? (governador 2º turno only in a few) */
export function heldIn(uf: string | null): boolean {
  const e = election();
  if (!e || !uf) return true;
  if (e.cargo === 1) return true;
  if (uf === 'ZZ') return false;
  return !e.ufs || e.ufs.includes(uf);
}

// ------------------------------------------------------------------ URL <-> state

export function toPath(): string {
  const parts = [app.eid];
  if (app.uf) parts.push(app.uf.toLowerCase());
  if (app.mun) {
    const nome = app.meta?.municipios[app.mun]?.[0];
    parts.push(nome ? `${app.mun}-${slug(nome)}` : app.mun);
  }
  if (app.mun && app.l != null && app.z != null) parts.push(`local-${app.z}-${app.l}`);
  if (app.l != null && app.secao != null) parts.push(`secao-${app.secao}`);
  let path = '/' + parts.join('/');
  if (app.zona != null && app.l == null) path += `?zona=${app.zona}`;
  return path;
}

export function fromPath(pathname: string, search: string) {
  const seg = pathname.split('/').filter(Boolean);
  const ids = app.meta?.elections.map((e) => e.id) ?? [];
  app.eid = seg[0] && ids.includes(seg[0]) ? seg[0] : DEFAULT_EID;
  const uf = seg[1]?.toUpperCase() ?? null;
  app.uf = uf && (app.meta?.ufs[uf] || uf === 'ZZ') ? uf : null;
  const munKey = seg[2]?.match(/^(zz\d+|\d+)/)?.[1] ?? null;
  app.mun = app.uf && munKey && app.meta?.municipios[munKey] ? munKey : null;
  const loc = seg[3]?.match(/^local-(\d+)-(\d+)$/);
  app.z = app.mun && loc ? +loc[1] : null;
  app.l = app.mun && loc ? +loc[2] : null;
  const sec = seg[4]?.match(/^secao-(\d+)$/);
  app.secao = app.l != null && sec ? +sec[1] : null;
  const zona = new URLSearchParams(search).get('zona');
  app.zona = app.mun && app.l == null && zona ? +zona : null;
  app.preview = null;
}

/** move to a place (and/or election) and record it in the browser history */
export function go(p: Partial<Place> & { eid?: string; zona?: number | null }, replace = false) {
  if (p.eid !== undefined) app.eid = p.eid;
  if (p.uf !== undefined) {
    app.uf = p.uf;
    if (p.mun === undefined) p.mun = null;
  }
  if (p.mun !== undefined) {
    app.mun = p.mun;
    if (p.l === undefined) { p.l = null; p.z = null; }
    if (p.zona === undefined) p.zona = null;
  }
  if (p.l !== undefined) {
    app.l = p.l;
    app.z = p.z ?? null;
    if (p.secao === undefined) p.secao = null;
  }
  if (p.secao !== undefined) app.secao = p.secao;
  if (p.zona !== undefined) app.zona = p.zona;
  app.preview = null;
  const path = toPath();
  if (path !== location.pathname + location.search) {
    (replace ? history.replaceState : history.pushState).call(history, null, '', path);
  }
}

/** one level up (Esc, breadcrumb) */
export function up() {
  const lv = level();
  if (lv === 'urna') go({ secao: null });
  else if (lv === 'local') go({ l: null, z: null });
  else if (lv === 'mun' && app.zona != null) go({ zona: null });
  else if (lv === 'mun') go({ mun: null });
  else if (lv === 'uf') go({ uf: null });
}
