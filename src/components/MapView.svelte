<script lang="ts">
  import { onMount } from 'svelte';
  import { Map as MLMap, NavigationControl, AttributionControl, setWorkerUrl, type GeoJSONSource, type MapLayerMouseEvent } from 'maplibre-gl';
  import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
  import 'maplibre-gl/dist/maplibre-gl.css';
  import { app, go, level, heldIn, election, primeiroTurno } from '../lib/state.svelte';
  import { view, cands, parties, localKey, swing, viradaOn } from '../lib/view.svelte';
  import { lead, loadNational, type ColorKey, type MunSummary, type Rec } from '../lib/data';
  import { fill, swingFill, EMPTY } from '../lib/colors';
  import { ufShapes, brMunShapes, ufMunShapes, bbox, BRASIL, type BBox } from '../lib/geo';
  import { pct, pp, n } from '../lib/format';

  setWorkerUrl(workerUrl);

  let el: HTMLDivElement;
  let map: MLMap | null = $state(null);
  let ready = $state(false);
  let tip = $state<{ x: number; y: number; title: string; lines: string[] } | null>(null);

  // shapes currently loaded into the sources
  let ufFC: GeoJSON.FeatureCollection | null = $state(null);
  let munFC: GeoJSON.FeatureCollection | null = $state(null);
  let munFCKey = '';
  let aptosBR: Record<string, Rec | MunSummary> | null = $state(null);

  const sgByCode = $derived(
    Object.fromEntries(Object.entries(app.meta?.ufs ?? {}).map(([sg, u]) => [u.ibge, sg])) as Record<number, string>,
  );
  const touch = typeof matchMedia !== 'undefined' && matchMedia('(hover: none)').matches;

  const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

  onMount(() => {
    const m = new MLMap({
      container: el,
      style: 'https://tiles.openfreemap.org/styles/positron',
      bounds: BRASIL,
      fitBoundsOptions: { padding: padding() },
      attributionControl: false,
      maxPitch: 0,
      dragRotate: false,
      minZoom: 2.5,
    });
    m.touchZoomRotate.disableRotation();
    m.addControl(new NavigationControl({ showCompass: false }), 'bottom-right');
    m.addControl(new AttributionControl({ compact: true }), 'bottom-left');
    m.on('load', () => {
      setupLayers(m);
      map = m;
      ready = true;
    });
    return () => m.remove();
  });

  function padding() {
    const w = innerWidth, h = innerHeight;
    // a closed results panel gives its room back to the map
    if (w >= 900) return { top: 88, bottom: 40, left: 40, right: app.panel ? Math.min(460, w * 0.4) + 32 : 40 };
    // the map controls take up to two rows at the top on phones
    return { top: 112, bottom: app.panel ? Math.round(h * 0.48) + 16 : 76, left: 16, right: 16 };
  }

  function setupLayers(m: MLMap) {
    const style = m.getStyle();
    // quiet the basemap: our data is the color on the page
    for (const ly of style.layers) {
      if (ly.type === 'background') m.setPaintProperty(ly.id, 'background-color', '#eef1ed');
      if (ly.type === 'fill' && /water/.test(ly.id)) m.setPaintProperty(ly.id, 'fill-color', '#dfe7ea');
    }
    const firstSymbol = style.layers.find((l) => l.type === 'symbol')?.id;
    const add = (layer: Parameters<MLMap['addLayer']>[0], top = false) => m.addLayer(layer, top ? undefined : firstSymbol);

    for (const id of ['ufs', 'muns', 'bolhas', 'zonas', 'locais', 'uflabels'])
      m.addSource(id, { type: 'geojson', data: EMPTY_FC, promoteId: 'k' });

    add({ id: 'ufs-fill', type: 'fill', source: 'ufs', paint: { 'fill-color': ['get', 'c'], 'fill-opacity': ['get', 'o'] } });
    add({ id: 'muns-fill', type: 'fill', source: 'muns', paint: { 'fill-color': ['get', 'c'], 'fill-opacity': ['get', 'o'] } });
    add({
      id: 'muns-line', type: 'line', source: 'muns',
      // zoomed out, thousands of borders would wash the fills out: keep them faint and hairline
      paint: {
        'line-color': '#ffffff',
        'line-opacity': ['interpolate', ['linear'], ['zoom'], 3, 0.12, 6, 0.3, 9, 0.65],
        'line-width': ['interpolate', ['linear'], ['zoom'], 3, 0.1, 6, 0.3, 9, 0.8, 12, 1.4],
      },
    });
    add({
      id: 'ufs-line', type: 'line', source: 'ufs',
      paint: { 'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 3, 0.8, 7, 2] },
    });
    add({
      id: 'zonas-line', type: 'line', source: 'zonas',
      paint: { 'line-color': '#14212E', 'line-opacity': ['case', ['get', 'sel'], 0.9, 0.45], 'line-width': ['case', ['get', 'sel'], 2.2, 1.1], 'line-dasharray': [3, 2] },
    });
    add({ id: 'zonas-fill', type: 'fill', source: 'zonas', paint: { 'fill-color': '#14212E', 'fill-opacity': ['case', ['get', 'sel'], 0.06, 0] } });
    add({
      id: 'hover-muns', type: 'line', source: 'muns',
      paint: { 'line-color': '#14212E', 'line-width': ['case', ['boolean', ['feature-state', 'hover'], false], 2, 0] },
    });
    add({
      id: 'hover-ufs', type: 'line', source: 'ufs',
      paint: { 'line-color': '#14212E', 'line-width': ['case', ['boolean', ['feature-state', 'hover'], false], 2.2, 0] },
    });
    add({
      id: 'sel-muns', type: 'line', source: 'muns', filter: ['==', ['get', 'sel'], true],
      paint: { 'line-color': '#14212E', 'line-width': 2.4 },
    });
    add({
      id: 'bolhas', type: 'circle', source: 'bolhas',
      paint: {
        'circle-color': ['get', 'c'],
        'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 3, ['max', 0.6, ['*', 0.0055, ['get', 'r']]], 9, ['*', 0.35, ['get', 'r']]],
        'circle-stroke-color': '#ffffff', 'circle-stroke-width': 0.6, 'circle-opacity': 0.92,
      },
    });
    add({
      id: 'locais', type: 'circle', source: 'locais',
      paint: {
        'circle-color': ['get', 'c'],
        'circle-opacity': ['case', ['get', 'dim'], 0.25, 1],
        'circle-radius': ['interpolate', ['exponential', 1.6], ['zoom'], 8, ['max', 2, ['*', 0.05, ['sqrt', ['get', 'el']]]], 16, ['*', 0.42, ['sqrt', ['get', 'el']]]],
        'circle-stroke-color': ['case', ['get', 'sel'], '#14212E', ['boolean', ['feature-state', 'hover'], false], '#14212E', '#ffffff'],
        'circle-stroke-width': ['case', ['get', 'sel'], 3, ['boolean', ['feature-state', 'hover'], false], 2, 1],
      },
    }, true);
    // winning party written on each state: hue alone can't name the gray "other parties"
    add({
      id: 'ufs-label', type: 'symbol', source: 'uflabels',
      layout: { 'text-field': ['get', 't'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-allow-overlap': false, 'text-padding': 1 },
      paint: { 'text-color': '#14212E', 'text-halo-color': 'rgba(255,255,255,0.85)', 'text-halo-width': 1.4 },
    }, true);

    // ------------------------------------------------------------------ interaction
    let hovered: { source: string; id: string | number } | null = null;
    const setHover = (h: typeof hovered) => {
      if (hovered) m.setFeatureState(hovered, { hover: false });
      hovered = h;
      if (h) m.setFeatureState(h, { hover: true });
    };
    const layers = ['locais', 'bolhas', 'muns-fill', 'ufs-fill'];
    m.on('mousemove', (e) => {
      const f = m.queryRenderedFeatures(e.point, { layers: layers.filter((l) => m.getLayer(l)) })[0];
      if (!f || f.properties.o === 0 && f.layer.id !== 'locais') {
        setHover(null);
        tip = null;
        m.getCanvas().style.cursor = '';
        return;
      }
      const source = f.layer.id === 'bolhas' ? 'muns' : (f.source as string);
      if (f.id != null) setHover({ source, id: f.id });
      m.getCanvas().style.cursor = f.properties.go ? 'pointer' : '';
      tip = { x: e.point.x, y: e.point.y, title: f.properties.nome, lines: JSON.parse(f.properties.tt ?? '[]') };
    });
    m.on('mouseout', () => { setHover(null); tip = null; });
    m.on('click', (e: MapLayerMouseEvent | any) => {
      const f = m.queryRenderedFeatures(e.point, { layers: [...layers, 'zonas-fill'].filter((l) => m.getLayer(l)) })[0];
      if (!f || !f.properties.go) return;
      const target = JSON.parse(f.properties.go);
      const key = f.properties.k + ':' + f.layer.id;
      if (touch && app.preview?.key !== key) {
        app.preview = { key, label: f.properties.nome, to: target.to };
        tip = { x: e.point.x, y: e.point.y, title: f.properties.nome, lines: [...JSON.parse(f.properties.tt ?? '[]'), 'Toque de novo para abrir'] };
        return;
      }
      tip = null;
      go(target.to);
    });
  }

  // list rows in the panel highlight their place on the map
  let listHover: { source: string; id: string | number } | null = null;
  $effect(() => {
    if (!map) return;
    const h = app.hover;
    if (listHover) map.setFeatureState(listHover, { hover: false });
    listHover = h ? { source: h.source, id: h.id } : null;
    if (listHover) map.setFeatureState(listHover, { hover: true });
  });

  // ------------------------------------------------------------------ data helpers
  function natColor(key: ColorKey | undefined, presid: boolean): ColorKey {
    // across states, ochre/aqua mean different parties: only PT and PL keep a hue
    if (presid) return key ?? 'g';
    return key === 'r' || key === 'b' ? key : 'g';
  }

  function recText(r: Rec | null | undefined, list: { nome?: string; p: string; cor?: ColorKey }[]): { c: string; tt: string[] } {
    const w = lead(r);
    if (!r || !w) return { c: EMPTY, tt: ['Sem votos neste cargo'] };
    const who = list[w.idx];
    const nome = who?.nome ? `${who.nome} (${who.p})` : who?.p ?? '?';
    return { c: fill(who?.cor, w.margin), tt: [`${nome} ${pct(w.share)}`, `Vantagem de ${pp(w.margin)}`] };
  }

  /** result color, or the swing since the 1º turno when the "virada" map is on */
  function paintRec(r: Rec | null | undefined, r1: Rec | null | undefined, list: { nome?: string; p: string; cor?: ColorKey }[]) {
    if (!viradaOn()) return recText(r, list);
    const sw = swing(r, r1);
    if (!sw) return { c: EMPTY, tt: ['Sem dados para comparar os turnos'] };
    const who = cands()[sw.idx];
    return { c: swingFill(who?.cor, sw.s), tt: [`Andou ${pp(sw.s)} para ${who?.nome}`, 'desde o 1º turno'] };
  }

  // ------------------------------------------------------------------ geometry for the current place
  $effect(() => {
    if (!ready) return;
    ufShapes().then((fc) => (ufFC = fc));
  });

  $effect(() => {
    if (!ready) return;
    const lv = level();
    const uf = app.uf;
    let key = '';
    if (lv === 'br' && app.prefs.nacional === 'mun') key = 'BR';
    else if (uf && uf !== 'ZZ' && lv !== 'br') key = uf;
    if (key === munFCKey) return;
    munFCKey = key;
    if (!key) { munFC = null; return; }
    (key === 'BR' ? brMunShapes() : ufMunShapes(key)).then((fc) => { if (munFCKey === key) munFC = fc; });
  });

  // electorate for bubble sizes: same for every office, take it from presidente
  $effect(() => {
    if (!ready || app.prefs.tamanho !== 'bolhas') return;
    loadNational('presidente-1').then((nf) => (aptosBR = nf.mun));
  });

  // ------------------------------------------------------------------ paint
  $effect(() => {
    if (!map || !ufFC) return;
    const lv = level();
    const nat = view.national;
    const presid = app.eid.startsWith('presidente');
    const curUf = app.uf;
    const cs = cands();
    const labels: GeoJSON.Feature[] = [];
    const feats = ufFC.features.map((f) => {
      const sg = sgByCode[f.id as number];
      const ent = nat?.ufs[sg];
      let c = EMPTY, tt: string[] = ['Não houve esta eleição aqui'];
      if (ent) {
        if (presid) ({ c, tt } = paintRec(ent.total, view.prevNational?.ufs[sg]?.total, cs));
        else if (ent.w && ent.lead) {
          c = fill(natColor(ent.lead.cor, false), ent.w[2] / 1000);
          tt = [`${ent.lead.nome ? ent.lead.nome + ' (' + ent.lead.p + ')' : ent.lead.p} ${pct(ent.w[1] / 1000)}`];
          const b = bbox([f.geometry]);
          if (b && lv === 'br' && app.prefs.nacional === 'uf')
            labels.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2] }, properties: { k: sg, t: ent.lead.p } });
        }
      }
      const isCur = sg === curUf;
      const o = lv === 'br' ? (app.prefs.nacional === 'mun' ? 0 : 1) : isCur ? 0 : 0.4;
      const to = lv === 'br' || !isCur ? { uf: sg } : null;
      return {
        type: 'Feature' as const, geometry: f.geometry,
        properties: { k: f.id, nome: app.meta?.ufs[sg]?.nome ?? sg, c, o, tt: JSON.stringify(tt), go: to ? JSON.stringify({ kind: 'uf', to }) : null },
      };
    });
    (map.getSource('ufs') as GeoJSONSource).setData({ type: 'FeatureCollection', features: feats });
    (map.getSource('uflabels') as GeoJSONSource).setData({ type: 'FeatureCollection', features: labels });
  });

  $effect(() => {
    if (!map) return;
    const lv = level();
    const fc = munFC;
    const src = map.getSource('muns') as GeoJSONSource;
    const bsrc = map.getSource('bolhas') as GeoJSONSource;
    if (!fc) { src.setData(EMPTY_FC); bsrc.setData(EMPTY_FC); return; }
    const presid = app.eid.startsWith('presidente');
    const nat = view.national;
    const race = view.race;
    const cs = cands();
    const ps = parties();
    const held = heldIn(app.uf);
    const bubbles = app.prefs.tamanho === 'bolhas' && (lv === 'br' || lv === 'uf');
    const names = app.meta?.municipios ?? {};
    const centros = app.meta?.centros ?? {};
    const feats: GeoJSON.Feature[] = [];
    const dots: GeoJSON.Feature[] = [];
    for (const f of fc.features) {
      const k = String(f.id);
      const [nome, uf] = names[k] ?? ['?', ''];
      let c = EMPTY, tt: string[] = ['Não houve esta eleição aqui'];
      if (lv === 'br') {
        const r = nat?.mun[k];
        if (Array.isArray(r)) {
          c = fill(natColor(r[0], false), r[2] / 1000);
          tt = [`Mais votado: ${r[3]} ${pct(r[1] / 1000)}`];
        } else if (r) ({ c, tt } = paintRec(r, view.prevNational?.mun[k] as Rec | undefined, cs));
      } else if (held && race) {
        const r = race.mun[k];
        ({ c, tt } = paintRec(r, view.prevRace?.mun[k], r?.p ? ps : cs));
      }
      const isCur = k === app.mun;
      let o = 1;
      if (lv === 'mun' || lv === 'local' || lv === 'urna') o = isCur ? 0.06 : 0.2;
      const go_ = lv === 'br' ? { uf, mun: k } : isCur ? null : { mun: k };
      const label = `${nome}${lv === 'br' ? ' (' + uf + ')' : ''}`;
      feats.push({
        type: 'Feature', geometry: f.geometry,
        properties: { k, nome: label, c: bubbles ? '#e3e6e1' : c, o, sel: isCur, tt: JSON.stringify(tt), go: go_ ? JSON.stringify({ kind: 'mun', to: go_ }) : null },
      });
      if (bubbles) {
        const ap = aptosBR?.[k];
        const r = ap && !Array.isArray(ap) ? Math.sqrt(ap.s[0]) : 0;
        if (r && centros[k]) dots.push({
          type: 'Feature', geometry: { type: 'Point', coordinates: centros[k] },
          properties: { k, nome: label, c, r, tt: JSON.stringify(tt), go: JSON.stringify({ kind: 'mun', to: go_ ?? { mun: k } }) },
        });
      }
    }
    // biggest bubbles first so small ones stay clickable on top
    dots.sort((a, b) => (b.properties!.r as number) - (a.properties!.r as number));
    src.setData({ type: 'FeatureCollection', features: feats });
    bsrc.setData({ type: 'FeatureCollection', features: dots });
  });

  // voting places and zone areas inside a municipality
  $effect(() => {
    if (!map) return;
    const lv = level();
    const mf = view.munFile;
    const lsrc = map.getSource('locais') as GeoJSONSource;
    const zsrc = map.getSource('zonas') as GeoJSONSource;
    if (lv === 'br' || lv === 'uf' || !mf || String(mf.mun) !== app.mun) { lsrc.setData(EMPTY_FC); zsrc.setData(EMPTY_FC); return; }
    const per = mf.r[app.eid] ?? {};
    const first = primeiroTurno();
    const per1 = first ? mf.r[first] ?? {} : {};
    void view.prevNational; void view.prevRace;
    const cs = cands();
    const ps = parties();
    const feats: GeoJSON.Feature[] = [];
    for (const x of mf.locais) {
      if (x.lat == null || x.lon == null) continue;
      const r = per[localKey(x.z, x.l)];
      const { c, tt } = paintRec(r, per1[localKey(x.z, x.l)], r?.p ? ps : cs);
      const sel = x.z === app.z && x.l === app.l;
      feats.push({
        type: 'Feature', geometry: { type: 'Point', coordinates: [x.lon, x.lat] },
        properties: {
          k: localKey(x.z, x.l), nome: x.nm, c, el: x.el, sel, dim: app.zona != null && x.z !== app.zona,
          tt: JSON.stringify([...tt, `${n(x.el)} eleitores · zona ${x.z}${x.aprox ? ' · posição aproximada' : ''}`]),
          go: JSON.stringify({ kind: 'local', to: { z: x.z, l: x.l } }),
        },
      });
    }
    // selected on top
    feats.sort((a, b) => Number(a.properties!.sel) - Number(b.properties!.sel));
    lsrc.setData({ type: 'FeatureCollection', features: feats });
    const zg = mf.zg;
    zsrc.setData(zg ? {
      type: 'FeatureCollection',
      features: zg.features.map((f) => ({ ...f, properties: { ...f.properties, k: f.properties!.z, sel: f.properties!.z === app.zona } })),
    } : EMPTY_FC);
  });

  // ------------------------------------------------------------------ camera
  let lastCam = '';
  $effect(() => {
    if (!map) return;
    const lv = level();
    // opening/closing the results panel changes the free area, so it re-frames too
    const key = `${lv}|${app.uf}|${app.mun}|${app.z}-${app.l}|${app.zona}|${app.panel}`;
    let box: BBox | null = null;
    if (lv === 'br') box = BRASIL;
    else if (lv === 'uf' && ufFC && app.uf !== 'ZZ') {
      const code = app.meta?.ufs[app.uf!]?.ibge;
      box = bbox(ufFC.features.filter((f) => f.id === code).map((f) => f.geometry));
    } else if (lv === 'mun' && munFC) {
      const mf = view.munFile;
      if (app.zona != null && mf) {
        box = bbox(mf.locais.filter((x) => x.z === app.zona && x.lat != null && !x.aprox).map((x) => ({ type: 'Point', coordinates: [x.lon!, x.lat!] }) as GeoJSON.Point));
      } else {
        box = bbox(munFC.features.filter((f) => String(f.id) === app.mun).map((f) => f.geometry));
      }
    } else if ((lv === 'local' || lv === 'urna') && view.munFile) {
      const x = view.munFile.locais.find((p) => p.z === app.z && p.l === app.l);
      if (x?.lat != null && x.lon != null) {
        if (key !== lastCam) map.easeTo({ center: [x.lon, x.lat], zoom: Math.max(map.getZoom(), 15), padding: padding(), duration: 700 });
        lastCam = key;
      }
      return;
    }
    if (!box || key === lastCam) return;
    lastCam = key;
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    map.fitBounds(box, { padding: padding(), duration: reduce ? 0 : 800, maxZoom: lv === 'mun' ? 14 : 9 });
  });

  // basemap labels compete with the choropleth at national scale
  $effect(() => {
    if (!map) return;
    const show = level() !== 'br';
    for (const ly of map.getStyle().layers) {
      if (ly.type === 'symbol' && ly.id !== 'ufs-label') map.setLayoutProperty(ly.id, 'visibility', show ? 'visible' : 'none');
    }
  });

  // bubbles replace fills
  $effect(() => {
    if (!map) return;
    const lv = level();
    const on = app.prefs.tamanho === 'bolhas' && (lv === 'br' || lv === 'uf');
    map.setLayoutProperty('bolhas', 'visibility', on ? 'visible' : 'none');
  });

  // keep `election` referenced so a cargo change repaints even if files are cached
  $effect(() => { void election(); });
</script>

<div class="map" bind:this={el} role="application" aria-label="Mapa de resultados"></div>
{#if tip}
  <div class="tip" style:left="{tip.x}px" style:top="{tip.y}px" role="tooltip">
    <strong>{tip.title}</strong>
    {#each tip.lines as line}<span>{line}</span>{/each}
  </div>
{/if}

<style>
  .map {
    position: absolute;
    inset: 0;
    background: var(--paper);
  }
  .tip {
    position: absolute;
    z-index: 5;
    pointer-events: none;
    transform: translate(14px, 14px);
    max-width: 280px;
    padding: 8px 10px;
    border-radius: 6px;
    background: var(--grafite);
    color: #f2f4f1;
    font-size: 13px;
    line-height: 1.35;
    display: grid;
    gap: 1px;
    box-shadow: 0 6px 18px rgb(20 33 46 / 0.25);
  }
  .tip strong {
    font-weight: 600;
  }
  .tip span {
    color: #c9cfd3;
  }
  :global(.maplibregl-ctrl-group) {
    border-radius: 8px !important;
    box-shadow: 0 1px 4px rgb(20 33 46 / 0.18) !important;
  }
</style>
