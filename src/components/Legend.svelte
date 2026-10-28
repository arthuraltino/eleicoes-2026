<script lang="ts">
  import { app, level, election } from '../lib/state.svelte';
  import { view, cands, parties, viradaOn } from '../lib/view.svelte';
  import { RAMPS, MARGIN_LABELS, SWING_LABELS, SWATCH } from '../lib/colors';
  import type { ColorKey } from '../lib/data';

  let open = $state(true);

  const lv = $derived(level());
  const presid = $derived(app.eid.startsWith('presidente'));
  const prop = $derived(!!election()?.prop);

  // one row per hue actually on the map, named by who wears it
  const virada = $derived(viradaOn());
  const rows = $derived.by(() => {
    const out: { key: ColorKey; label: string }[] = [];
    if (virada) {
      for (const c of cands().slice(0, 2)) out.push({ key: (c.cor ?? 'g') as ColorKey, label: `Andou para ${c.nome}` });
      return out;
    }
    if (lv === 'br' && !presid) {
      out.push({ key: 'r', label: prop ? 'PT mais votado' : 'Venceu: PT' });
      out.push({ key: 'b', label: prop ? 'PL mais votado' : 'Venceu: PL' });
      out.push({ key: 'g', label: prop ? 'Outro partido' : 'Venceu: outro partido' });
      return out;
    }
    const list: { cor?: ColorKey; nome?: string; p: string }[] = prop ? parties() : cands();
    const seen = new Set<ColorKey>();
    for (const x of list) {
      const k = (x.cor ?? 'g') as ColorKey;
      if (seen.has(k) || k === 'g') continue;
      seen.add(k);
      out.push({ key: k, label: prop ? x.p : `${x.nome} (${x.p})` });
    }
    if (list.some((x) => x.cor === 'g')) out.push({ key: 'g', label: prop ? 'Outros partidos' : 'Outros candidatos' });
    return out;
  });
  const hasData = $derived(!!view.national);
</script>

{#if hasData}
  <section class="legend" aria-label="Legenda do mapa">
    <button class="head" aria-expanded={open} onclick={() => (open = !open)}>
      <span>{virada ? 'Virada desde o 1º turno' : prop ? 'Partido mais votado' : 'Quem venceu'}</span>
      <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" style:rotate={open ? '0deg' : '180deg'}><path d="M2 8l4-4 4 4" fill="none" stroke="currentColor" stroke-width="1.8" /></svg>
    </button>
    {#if open}
      <ul>
        {#each rows as r}
          <li><span class="dot" style:background={SWATCH[r.key]}></span>{r.label}</li>
        {/each}
      </ul>
      <div class="ramp">
        <p>{virada ? 'Cor mais forte, mudança maior na vantagem entre os finalistas' : 'Cor mais forte, vitória mais folgada'}</p>
        {#each rows.slice(0, 2) as r}
          <div class="steps" aria-hidden="true">
            {#each RAMPS[r.key] as c}<span style:background={c}></span>{/each}
          </div>
        {/each}
        <div class="scale" aria-hidden="true"><span>{(virada ? SWING_LABELS : MARGIN_LABELS)[0]}</span><span>{(virada ? SWING_LABELS : MARGIN_LABELS)[4]}</span></div>
      </div>
    {/if}
  </section>
{/if}

<style>
  .legend {
    position: absolute;
    left: 14px;
    bottom: 30px;
    z-index: 4;
    width: 236px;
    background: var(--sheet);
    border-radius: 10px;
    box-shadow: 0 1px 4px rgb(20 33 46 / 0.16), 0 0 0 1px rgb(20 33 46 / 0.06);
    font-size: var(--t-sm);
  }
  .head {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 0;
    background: none;
    padding: 9px 12px;
    font-weight: 700;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0 12px 6px;
    display: grid;
    gap: 4px;
  }
  li {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--ink-2);
    line-height: 1.25;
  }
  .dot {
    flex: none;
    width: 11px;
    height: 11px;
    border-radius: 3px;
  }
  .ramp {
    padding: 6px 12px 11px;
    border-top: 1px solid var(--rule);
  }
  .ramp p {
    margin: 0 0 6px;
    color: var(--muted);
    font-size: var(--t-xs);
  }
  .steps {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 2px;
    margin-bottom: 2px;
  }
  .steps span {
    height: 8px;
  }
  .steps span:first-child {
    border-radius: 3px 0 0 3px;
  }
  .steps span:last-child {
    border-radius: 0 3px 3px 0;
  }
  .scale {
    display: flex;
    justify-content: space-between;
    color: var(--muted);
    font-size: 11px;
    margin-top: 3px;
  }
  @media (max-width: 899px) {
    .legend {
      display: none;
    }
  }
</style>
