import type { ColorKey } from './data';

// Five steps per hue, same OKLCH lightness across hues (L .735 → .385), checked with
// the dataviz validator: every ramp passes the ordinal checks (monotone, ΔL ≥ .06,
// lightest step ≥ 2:1 on the map surface) and red/blue/ochre pass all-pairs CVD;
// aqua needs labels, which the panel list always provides.
// The light end stays clearly tinted so narrow wins don't read as washed out.
// Lighter = narrower margin of victory.
export const RAMPS: Record<ColorKey, string[]> = {
  r: ['#f6827b', '#e0655f', '#c94643', '#ae1c25', '#830312'],
  b: ['#71acf8', '#5392e3', '#3479cf', '#055cb6', '#004287'],
  o: ['#d59e49', '#bf831a', '#a26d00', '#805501', '#5d3c00'],
  a: ['#5fb88d', '#42a67b', '#0c8f62', '#00714c', '#015136'],
  g: ['#aaaaa4', '#91918c', '#797974', '#5f5f5a', '#44443f'],
};

/** solid swatch for legends, bars and chips: the strong end of each ramp */
export const SWATCH: Record<ColorKey, string> = {
  r: '#ae1c25', b: '#055cb6', o: '#805501', a: '#00714c', g: '#5f5f5a',
};

/** margin of victory (fraction of valid votes) -> ramp step */
export const MARGIN_BINS = [0.05, 0.15, 0.3, 0.5];
export const MARGIN_LABELS = ['até 5 pontos', '5 a 15', '15 a 30', '30 a 50', 'mais de 50'];

export function step(margin: number): number {
  let i = 0;
  while (i < MARGIN_BINS.length && margin >= MARGIN_BINS[i]) i++;
  return i;
}

export function fill(key: ColorKey | undefined, margin: number): string {
  return RAMPS[key ?? 'g'][step(margin)];
}

/** change of margin between rounds (fraction of valid votes) -> ramp step */
export const SWING_BINS = [0.02, 0.05, 0.1, 0.2];
export const SWING_LABELS = ['até 2 pontos', '2 a 5', '5 a 10', '10 a 20', 'mais de 20'];

export function swingFill(key: ColorKey | undefined, swing: number): string {
  let i = 0;
  while (i < SWING_BINS.length && Math.abs(swing) >= SWING_BINS[i]) i++;
  return RAMPS[key ?? 'g'][i];
}

/** no data (e.g. a state without a runoff) */
export const EMPTY = '#e4e7e2';
