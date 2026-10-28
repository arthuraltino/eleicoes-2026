<script lang="ts">
  import { app, go, level, election, heldIn } from '../lib/state.svelte';
  import { view, cands, parties, currentRec, currentLocal, ready, localKey } from '../lib/view.svelte';
  import { lead, type ColorKey, type Rec } from '../lib/data';
  import { fill, SWATCH, EMPTY } from '../lib/colors';
  import { n, nc, plural } from '../lib/format';
  import Breadcrumb from './Breadcrumb.svelte';
  import ResultMaj from './ResultMaj.svelte';
  import ResultProp from './ResultProp.svelte';
  import Turnout from './Turnout.svelte';
  import PlaceList, { type Row } from './PlaceList.svelte';
  import UrnaGrid from './UrnaGrid.svelte';
  import BuReceipt from './BuReceipt.svelte';

  const lv = $derived(level());
  const el = $derived(election());
  const presid = $derived(el?.cargo === 1);
  const held = $derived(heldIn(app.uf));
  const ok = $derived(ready());
  const rec = $derived(ok ? currentRec() : null);
  const loc = $derived(currentLocal());

  const cargoNome = $derived(el ? (el.cargo === 7 && app.uf === 'DF' ? 'Deputado distrital' : el.label) : '');

  const title = $derived.by(() => {
    if (lv === 'br') return 'Brasil';
    if (lv === 'uf') return app.uf === 'ZZ' ? 'Exterior' : app.meta?.ufs[app.uf!]?.nome ?? app.uf!;
    if (lv === 'mun') {
      const nome = app.meta?.municipios[app.mun!]?.[0] ?? '';
      return app.zona != null ? `${nome}, zona ${app.zona}` : nome;
    }
    if (lv === 'local') return loc?.nm ?? `Local ${app.l}`;
    return `Seção ${app.secao}`;
  });

  const subtitle = $derived.by(() => {
    const base = `${cargoNome} · ${el?.turno}º turno`;
    if (lv === 'mun' && view.munFile) {
      const z = view.munFile.zonas.length;
      return `${base} · ${plural(view.munFile.locais.length, 'local de votação', 'locais de votação')}${z > 1 ? ' em ' + z + ' zonas' : ''}`;
    }
    if (lv === 'local' && loc) return [loc.end, loc.bairro].filter(Boolean).join(', ') + ` · zona ${loc.z}`;
    if (lv === 'urna') return `${loc?.nm ?? ''} · zona ${app.z}`;
    return base;
  });

  // ------------------------------------------------------------------ list rows per level
  function natKey(k: ColorKey | undefined): ColorKey {
    return presid ? (k ?? 'g') : k === 'r' || k === 'b' ? k : 'g';
  }
  function rowFrom(r: Rec | null | undefined, list: { cor?: ColorKey; nome?: string; p: string }[]) {
    const w = lead(r);
    if (!w) return { color: EMPTY, who: 'Sem votos', share: null, margin: 1 };
    const x = list[w.idx];
    return { color: fill(x?.cor, w.margin), who: x?.nome ?? x?.p ?? '?', share: w.share, margin: w.margin };
  }

  const ufRows = $derived.by((): Row[] => {
    const nat = view.national;
    if (!nat || !app.meta) return [];
    const out: Row[] = [];
    for (const [sg, u] of Object.entries(app.meta.ufs)) {
      const ent = nat.ufs[sg];
      let r: Omit<Row, 'key' | 'label' | 'size' | 'to'>;
      if (!ent) r = { color: EMPTY, who: 'Sem disputa', share: null, margin: 1 };
      else if (presid) r = rowFrom(ent.total, cands());
      else if (ent.w && ent.lead) r = { color: fill(natKey(ent.lead.cor), ent.w[2] / 1000), who: ent.lead.nome ? `${ent.lead.nome} (${ent.lead.p})` : ent.lead.p, share: ent.w[1] / 1000, margin: ent.w[2] / 1000 };
      else r = { color: EMPTY, who: '—', share: null, margin: 1 };
      out.push({ key: sg, label: u.nome, size: ent?.total.s[0] ?? 0, to: { uf: sg }, hover: { source: 'ufs', id: u.ibge }, ...r });
    }
    if (presid && nat.ufs.ZZ) out.push({ key: 'ZZ', label: 'Exterior', size: nat.ufs.ZZ.total.s[0], to: { uf: 'ZZ' }, ...rowFrom(nat.ufs.ZZ.total, cands()) });
    return out;
  });

  const munRows = $derived.by((): Row[] => {
    const race = view.race;
    if (!race || !app.meta) return [];
    const list = race.parties ?? cands();
    return Object.entries(race.mun).map(([k, r]) => ({
      key: k, label: app.meta!.municipios[k]?.[0] ?? k, size: r.s[0], to: { mun: k },
      hover: { source: 'muns' as const, id: k }, ...rowFrom(r, r.p ? parties() : list),
    }));
  });

  const localRows = $derived.by((): Row[] => {
    const mf = view.munFile;
    if (!mf) return [];
    const per = mf.r[app.eid] ?? {};
    return mf.locais
      .filter((x) => app.zona == null || x.z === app.zona)
      .map((x) => {
        const r = per[localKey(x.z, x.l)];
        return {
          key: localKey(x.z, x.l), label: x.nm, sub: [x.bairro, `zona ${x.z}`].filter(Boolean).join(' · '), size: x.el,
          to: { z: x.z, l: x.l }, hover: { source: 'locais' as const, id: localKey(x.z, x.l) },
          ...rowFrom(r, r?.p ? parties() : cands()),
        };
      });
  });

  // national summary for state races: who leads in how many states
  const partyTally = $derived.by(() => {
    if (presid || lv !== 'br' || !view.national) return [];
    const m = new Map<string, { p: string; k: number; cor: ColorKey }>();
    for (const ent of Object.values(view.national.ufs)) {
      if (!ent.lead) continue;
      const e = m.get(ent.lead.p) ?? { p: ent.lead.p, k: 0, cor: natKey(ent.lead.cor) };
      e.k++;
      m.set(ent.lead.p, e);
    }
    return [...m.values()].sort((a, b) => b.k - a.k);
  });

  // ------------------------------------------------------------------ alternatives when the office wasn't voted here
  const fallback = $derived.by(() => {
    if (held || !el) return null;
    if (app.uf === 'ZZ') return { text: 'No exterior só se vota para presidente.', label: 'Ver presidente', eid: `presidente-${el.turno}` };
    if (el.cargo === 3 && el.turno === 2) return { text: `Em ${app.meta?.ufs[app.uf!]?.nome} o governador foi decidido no 1º turno.`, label: 'Ver o 1º turno', eid: 'governador-1' };
    return { text: 'Esta eleição não aconteceu aqui.', label: 'Ver presidente', eid: 'presidente-1' };
  });

  // ------------------------------------------------------------------ close / reopen
  let closeBtn: HTMLButtonElement | undefined = $state();
  let reopenBtn: HTMLButtonElement | undefined = $state();
  function close() {
    app.panel = false;
    // keep keyboard users on the control that brings the panel back
    queueMicrotask(() => reopenBtn?.focus());
  }
  function open() {
    app.panel = true;
    queueMicrotask(() => closeBtn?.focus());
  }

  // ------------------------------------------------------------------ mobile sheet
  let startY = 0, dragging = false;
  function grip(e: PointerEvent) {
    startY = e.clientY;
    dragging = true;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }
  function release(e: PointerEvent) {
    if (!dragging) return;
    dragging = false;
    const dy = e.clientY - startY;
    const order = ['peek', 'half', 'full'] as const;
    let i = order.indexOf(app.sheet);
    if (Math.abs(dy) < 6) i = (i + 1) % 3;
    else i = Math.max(0, Math.min(2, i + (dy < 0 ? 1 : -1)));
    app.sheet = order[i];
  }
</script>

{#if !app.panel}
  <button class="reopen" bind:this={reopenBtn} onclick={() => open()} aria-label="Mostrar resultados de {title}">
    <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M2 3h12M2 8h12M2 13h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /></svg>
    <span class="rlabel">Resultados</span>
    <span class="rplace">{title}</span>
  </button>
{/if}

<aside class="panel" data-sheet={app.sheet} aria-label="Resultados" hidden={!app.panel}>
  <button class="grip" onpointerdown={grip} onpointerup={release} aria-label="Expandir ou recolher o painel">
    <span></span>
  </button>
  <button class="close" bind:this={closeBtn} onclick={close} aria-label="Fechar resultados" title="Fechar resultados">
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /></svg>
  </button>
  <div class="scroll">
    <Breadcrumb />

    {#if app.preview}
      <div class="preview" role="status">
        <span>{app.preview.label}</span>
        <button onclick={() => go(app.preview!.to)}>Abrir</button>
      </div>
    {/if}

    <header>
      <h1>{title}</h1>
      <p class="sub">{subtitle}</p>
    </header>

    {#if view.error}
      <div class="msg" role="alert">
        <p>Não foi possível carregar estes resultados ({view.error}).</p>
        <button onclick={() => location.reload()}>Tentar de novo</button>
      </div>
    {:else if fallback}
      <div class="msg">
        <p>{fallback.text}</p>
        <button onclick={() => go({ eid: fallback.eid })}>{fallback.label}</button>
      </div>
    {:else if !ok}
      <div class="skeleton" aria-busy="true" aria-label="Carregando">
        <span></span><span></span><span></span>
      </div>
    {:else}
      {#if lv === 'br' && !presid}
        <section class="tally" aria-label="Resumo nacional">
          <h2>{el?.prop ? 'Partido mais votado em cada estado' : 'Mais votado em cada estado'}</h2>
          <ul>
            {#each partyTally as t}
              <li><span class="dot" style:background={SWATCH[t.cor]}></span><b>{t.p}</b> <span class="num">{t.k} {t.k === 1 ? 'estado' : 'estados'}</span></li>
            {/each}
          </ul>
          <p class="hint">Cada estado tem a sua disputa. Escolha um para ver os candidatos.</p>
        </section>
      {:else if lv === 'urna'}
        <!-- the receipt is the result at ballot-box level -->
      {:else if rec}
        {#if el?.prop}<ResultProp {rec} />{:else}<ResultMaj {rec} vagas={view.race?.vagas} />{/if}
      {/if}

      {#if rec && lv !== 'urna'}<Turnout {rec} />{/if}

      {#if lv === 'br'}
        <PlaceList title="Estados" rows={ufRows} />
      {:else if lv === 'uf'}
        <PlaceList title={app.uf === 'ZZ' ? 'Cidades' : 'Municípios'} rows={munRows} searchable />
      {:else if lv === 'mun'}
        {#if view.munFile && view.munFile.zonas.length > 1}
          <section class="zonas" aria-label="Zonas eleitorais">
            <h2>Zonas eleitorais</h2>
            <p class="hint">As áreas no mapa são aproximadas, desenhadas a partir dos locais de votação.</p>
            {#if view.munFile.zonas.length <= 12}
              <div class="chips">
                <button aria-pressed={app.zona == null} onclick={() => go({ zona: null })}>Todas</button>
                {#each view.munFile.zonas as z}
                  <button aria-pressed={app.zona === z} onclick={() => go({ zona: z })}>{z}</button>
                {/each}
              </div>
            {:else}
              <label class="zsel">
                <span class="sr-only">Zona eleitoral</span>
                <select value={app.zona ?? ''} onchange={(e) => go({ zona: e.currentTarget.value ? +e.currentTarget.value : null })}>
                  <option value="">Todas as {view.munFile.zonas.length} zonas</option>
                  {#each view.munFile.zonas as z}<option value={z}>Zona {z}</option>{/each}
                </select>
              </label>
            {/if}
          </section>
        {/if}
        <PlaceList title="Locais de votação" rows={localRows} searchable />
      {:else if lv === 'local'}
        <UrnaGrid />
      {:else}
        <BuReceipt />
        <UrnaGrid compact />
      {/if}
    {/if}

    <footer>
      Fonte: TSE, dados abertos das eleições 2026 (boletins de urna e resultados), processados em {app.meta?.gerado}.
      Mapa base © colaboradores do OpenStreetMap, via OpenFreeMap. Malhas municipais: IBGE.
    </footer>
  </div>
</aside>

<style>
  .panel {
    position: absolute;
    top: 12px;
    right: 12px;
    bottom: 12px;
    width: var(--panel-w);
    z-index: 10;
    background: var(--sheet);
    border-radius: 14px;
    box-shadow: 0 2px 6px rgb(20 33 46 / 0.1), 0 16px 40px -18px rgb(20 33 46 / 0.35), 0 0 0 1px rgb(20 33 46 / 0.06);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .panel[hidden] {
    display: none;
  }
  /* the breadcrumb wraps before reaching the close button */
  .scroll > :global(nav:first-child) {
    margin-right: 30px;
  }
  .scroll {
    overflow-y: auto;
    padding: 16px 20px 20px;
    overscroll-behavior: contain;
  }
  .grip {
    display: none;
  }
  .close {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 2;
    width: 32px;
    height: 32px;
    display: grid;
    place-items: center;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: var(--ink-2);
  }
  .close:hover {
    background: #e8ece6;
    color: var(--ink);
  }
  .reopen {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 8px;
    max-width: min(360px, calc(100% - 28px));
    padding: 9px 14px;
    border: 0;
    border-radius: 10px;
    background: var(--ink);
    color: #fff;
    font-weight: 700;
    box-shadow: 0 6px 18px -6px rgb(20 33 46 / 0.45);
  }
  .reopen:hover {
    background: #22313f;
  }
  .rplace {
    font-weight: 500;
    color: #c9cfd3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  header {
    margin: 8px 0 14px;
  }
  h1 {
    margin: 0;
    font-family: var(--cond);
    font-weight: 800;
    font-size: 40px;
    line-height: 1;
    letter-spacing: -0.005em;
    text-wrap: balance;
  }
  .sub {
    margin: 6px 0 0;
    color: var(--ink-2);
    font-size: var(--t-sm);
  }
  h2 {
    margin: 0 0 8px;
    font-size: var(--t-md);
    font-weight: 700;
  }
  .hint {
    margin: 4px 0 8px;
    color: var(--muted);
    font-size: var(--t-sm);
  }
  .msg {
    padding: 14px;
    border-radius: 10px;
    background: #f4ece4;
    border-left: 4px solid var(--corrige);
  }
  .msg p {
    margin: 0 0 10px;
  }
  .msg button,
  .preview button {
    border: 0;
    border-radius: 8px;
    padding: 8px 14px;
    background: var(--confirma);
    color: #fff;
    font-weight: 700;
  }
  .preview {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin: 10px 0 0;
    padding: 8px 8px 8px 12px;
    border-radius: 10px;
    background: #e8f1ec;
    font-weight: 600;
  }
  .skeleton {
    display: grid;
    gap: 10px;
    padding: 6px 0;
  }
  .skeleton span {
    height: 18px;
    border-radius: 6px;
    background: linear-gradient(90deg, #eceee9, #f6f7f4, #eceee9);
    background-size: 200% 100%;
    animation: shimmer 1.2s infinite linear;
  }
  .skeleton span:first-child {
    height: 56px;
  }
  @keyframes shimmer {
    to {
      background-position: -200% 0;
    }
  }
  .tally ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
  }
  .tally li {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: var(--t-sm);
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 3px;
  }
  .zonas {
    padding-top: 18px;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
  .chips button {
    border: 1px solid var(--rule-strong);
    background: #fff;
    border-radius: 7px;
    padding: 4px 9px;
    font-size: var(--t-sm);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    min-width: 36px;
  }
  .zsel select {
    width: 100%;
    border: 1px solid var(--rule-strong);
    border-radius: 8px;
    padding: 8px 10px;
    background: #fff;
    font-weight: 600;
  }
  .chips button[aria-pressed='true'] {
    background: var(--ink);
    border-color: var(--ink);
    color: #fff;
  }
  footer {
    margin-top: 26px;
    padding-top: 12px;
    border-top: 1px solid var(--rule);
    color: var(--muted);
    font-size: var(--t-xs);
  }

  @media (max-width: 899px) {
    .panel {
      top: auto;
      left: 0;
      right: 0;
      bottom: 0;
      width: auto;
      border-radius: 16px 16px 0 0;
      transition: height 0.25s ease;
      height: 48%;
    }
    .panel[data-sheet='peek'] {
      height: 168px;
    }
    .panel[data-sheet='full'] {
      height: calc(100% - 8px);
    }
    .grip {
      display: grid;
      place-items: center;
      height: 22px;
      border: 0;
      background: none;
      touch-action: none;
      flex: none;
    }
    .grip span {
      width: 42px;
      height: 5px;
      border-radius: 3px;
      background: var(--rule-strong);
    }
    .scroll {
      padding: 0 16px 24px;
    }
    h1 {
      font-size: 32px;
    }
    .close {
      top: 6px;
      right: 8px;
    }
    .reopen {
      top: auto;
      right: 50%;
      bottom: calc(40px + env(safe-area-inset-bottom));
      transform: translateX(50%);
    }
  }
</style>
