const int = new Intl.NumberFormat('pt-BR');
const pct1 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pct2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const compact = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 });

export const n = (x: number | null | undefined) => (x == null ? '—' : int.format(x));
export const nc = (x: number) => (x < 10000 ? int.format(x) : compact.format(x));

/** 0.5183 -> "51,8%"; tiny shares keep two decimals so they don't read as zero */
export function pct(x: number | null | undefined): string {
  if (x == null || !isFinite(x)) return '—';
  const v = x * 100;
  return (v > 0 && v < 1 ? pct2 : pct1).format(v) + '%';
}

/** margin in percentage points: 0.0359 -> "3,6 pontos" */
export const pp = (x: number) => `${pct1.format(x * 100)} ${Math.abs(x) >= 0.0195 ? 'pontos' : 'ponto'}`;

export function slug(s: string): string {
  return s
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export function fold(s: string): string {
  return s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

/** "2026-10-04 08:00:01" -> "08:00" */
export const hhmm = (s: unknown) => (typeof s === 'string' && s.length >= 16 ? s.slice(11, 16) : '—');
/** "2026-10-04 08:00:01" -> "04/10/2026 08:00:01" */
export function dataHora(s: unknown): string {
  if (typeof s !== 'string' || s.length < 10) return '—';
  const [d, t] = s.split(' ');
  const [y, m, dd] = d.split('-');
  return `${dd}/${m}/${y}${t ? ' ' + t : ''}`;
}

export function plural(x: number, one: string, many: string) {
  return `${n(x)} ${x === 1 ? one : many}`;
}
