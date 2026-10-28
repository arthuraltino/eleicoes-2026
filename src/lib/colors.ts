import type { ColorKey } from './data';

// Five steps per hue, same OKLCH lightness across hues (validated for CVD with the
// dataviz validator: red/blue/ochre pass all-pairs; aqua needs labels, which the
// panel list always provides). Lighter = narrower margin of victory.
export const RAMPS: Record<ColorKey, string[]> = {
  r: ['#f9c0ba', '#ea9a93', '#d9736d', '#b53a39', '#830112'],
  b: ['#b7d3f6', '#86b6ef', '#5598e7', '#256abf', '#104281'],
  o: ['#e6cca8', '#d1ab76', '#bc8b41', '#8f6004', '#5d3c00'],
  a: ['#b4dbc7', '#88c1a4', '#5aa884', '#0d7e57', '#005136'],
  g: ['#d0d0cd', '#b2b2b0', '#969693', '#6b6b69', '#444441'],
};

/** solid swatch for legends, bars and chips: the strong end of each ramp */
export const SWATCH: Record<ColorKey, string> = {
  r: '#b53a39', b: '#256abf', o: '#8f6004', a: '#0d7e57', g: '#6b6b69',
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
