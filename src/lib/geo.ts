import { feature } from 'topojson-client';
import type { Topology, GeometryCollection } from 'topojson-specification';

type FC = GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon>;

const cache = new Map<string, Promise<FC>>();

function topo(path: string): Promise<FC> {
  let p = cache.get(path);
  if (!p) {
    p = fetch(`/data/geo/${path}`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ao carregar ${path}`);
        return r.json() as Promise<Topology>;
      })
      .then((t) => {
        const name = Object.keys(t.objects)[0];
        const fc = feature(t, t.objects[name] as GeometryCollection) as unknown as FC;
        for (const f of fc.features) f.id = Number(f.id);
        return fc;
      });
    p.catch(() => cache.delete(path));
    cache.set(path, p);
  }
  return p;
}

/** states, id = IBGE UF code */
export const ufShapes = () => topo('ufs.json');
/** every municipality, light (national view), id = IBGE code */
export const brMunShapes = () => topo('municipios.json');
/** municipalities of one state, more detail */
export const ufMunShapes = (uf: string) => topo(`uf/${uf}.json`);

export type BBox = [[number, number], [number, number]];

export function bbox(geoms: (GeoJSON.Geometry | null | undefined)[]): BBox | null {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const visit = (c: unknown) => {
    if (typeof (c as number[])[0] === 'number') {
      const [x, y] = c as number[];
      if (x < x0) x0 = x; if (x > x1) x1 = x;
      if (y < y0) y0 = y; if (y > y1) y1 = y;
    } else for (const k of c as unknown[]) visit(k);
  };
  for (const g of geoms) if (g && 'coordinates' in g) visit(g.coordinates);
  return isFinite(x0) ? [[x0, y0], [x1, y1]] : null;
}

export const BRASIL: BBox = [[-74.2, -33.9], [-34.6, 5.4]];
