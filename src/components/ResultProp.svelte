<script lang="ts">
  import type { Rec } from '../lib/data';
  import { pairs, validos } from '../lib/data';
  import { cands, parties, view } from '../lib/view.svelte';
  import { level } from '../lib/state.svelte';
  import { SWATCH } from '../lib/colors';
  import { n, pct } from '../lib/format';
  import Photo from './Photo.svelte';

  let { rec }: { rec: Rec } = $props();

  let allParties = $state(false);
  const total = $derived(validos(rec));
  const ps = $derived(
    parties()
      .map((p, i) => ({ p, q: rec.p?.[i] ?? 0 }))
      .filter((r) => r.q > 0)
      .sort((a, b) => b.q - a.q),
  );
  const shownParties = $derived(allParties ? ps : ps.slice(0, 8));
  const top = $derived(pairs(rec.t).slice(0, 10).map(([i, q]) => ({ c: cands()[i], q })).filter((r) => r.c));
  const isEleito = (s: string | null | undefined) => !!s && s.startsWith('Eleito');

  // seats per party for the whole state (only meaningful at UF level)
  const seats = $derived.by(() => {
    if (level() !== 'uf') return [];
    const m = new Map<string, { p: string; cor: string; k: number }>();
    for (const c of cands()) {
      if (!isEleito(c.sit)) continue;
      const party = parties().find((p) => p.n === c.pn);
      const e = m.get(c.p) ?? { p: c.p, cor: SWATCH[party?.cor ?? 'g'], k: 0 };
      e.k++;
      m.set(c.p, e);
    }
    return [...m.values()].sort((a, b) => b.k - a.k);
  });
  const vagas = $derived(view.race?.vagas ?? 0);
</script>

{#if total === 0}
  <p class="empty">Nenhum voto válido para este cargo aqui.</p>
{:else}
  {#if seats.length}
    <section class="seats" aria-label="Cadeiras conquistadas">
      <h2>{vagas} cadeiras</h2>
      <div class="waffle" role="img" aria-label={seats.map((s) => `${s.p} ${s.k}`).join(', ')}>
        {#each seats as s}{#each Array(s.k) as _}<span style:background={s.cor} title={s.p}></span>{/each}{/each}
      </div>
      <ul class="chips">
        {#each seats as s}<li><span class="dot" style:background={s.cor}></span>{s.p} <b class="num">{s.k}</b></li>{/each}
      </ul>
    </section>
  {/if}

  <section aria-label="Votos por partido">
    <h2>Votos por partido</h2>
    <ol class="parties">
      {#each shownParties as r}
        <li>
          <span class="pname">{r.p.p}{#if r.p.fed}<span class="fed" title="Federação {r.p.fed}">fed.</span>{/if}</span>
          <span class="track"><span style:width="{(r.q / (ps[0].q || 1)) * 100}%" style:background={SWATCH[r.p.cor]}></span></span>
          <span class="num pct">{pct(r.q / total)}</span>
        </li>
      {/each}
    </ol>
    {#if ps.length > 8}
      <button class="more" onclick={() => (allParties = !allParties)}>{allParties ? 'Mostrar menos' : `Mostrar os ${ps.length} partidos`}</button>
    {/if}
    {#if rec.s[5]}<p class="note">Inclui {n(rec.s[5])} votos só na legenda.</p>{/if}
  </section>

  <section aria-label="Mais votados aqui">
    <h2>Mais votados aqui</h2>
    <ol class="cands">
      {#each top as r, i}
        <li>
          <span class="rank num">{i + 1}</span>
          {#if r.c.foto}<Photo c={{ ...r.c, cor: parties().find((p) => p.n === r.c.pn)?.cor }} size={30} />{:else}<span class="ph-gap"></span>{/if}
          <span class="who">
            <span class="name">{r.c.nome}{#if isEleito(r.c.sit)}<b class="badge">Eleito</b>{/if}</span>
            <span class="party">{r.c.n} · {r.c.p}</span>
          </span>
          <span class="nums"><span class="num">{n(r.q)}</span><span class="num muted">{pct(r.q / total)}</span></span>
        </li>
      {/each}
    </ol>
  </section>
{/if}

<style>
  section + section {
    margin-top: 16px;
  }
  h2 {
    margin: 0 0 8px;
    font-size: var(--t-md);
    font-weight: 700;
  }
  .empty,
  .note {
    color: var(--ink-2);
    font-size: var(--t-xs);
    margin: 8px 0 0;
  }
  .waffle {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
  }
  .waffle span {
    width: 9px;
    height: 9px;
    border-radius: 2px;
  }
  .chips {
    list-style: none;
    padding: 0;
    margin: 8px 0 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    font-size: var(--t-sm);
    color: var(--ink-2);
  }
  .chips li {
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .dot {
    width: 9px;
    height: 9px;
    border-radius: 2px;
  }
  .parties {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 6px;
  }
  .parties li {
    display: grid;
    grid-template-columns: 92px 1fr 52px;
    align-items: center;
    gap: 10px;
    font-size: var(--t-sm);
  }
  .pname {
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .fed {
    margin-left: 4px;
    font-weight: 400;
    color: var(--muted);
    font-size: 11px;
  }
  .track {
    height: 8px;
    background: #e6e9e4;
    border-radius: 3px;
    overflow: hidden;
  }
  .track span {
    display: block;
    height: 100%;
    border-radius: 3px;
  }
  .pct {
    text-align: right;
    font-weight: 600;
  }
  .more {
    margin-top: 8px;
    border: 0;
    background: none;
    padding: 2px 0;
    font-weight: 600;
    color: var(--ink-2);
    text-decoration: underline;
    text-underline-offset: 3px;
    font-size: var(--t-sm);
  }
  .cands {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 7px;
  }
  .cands li {
    display: grid;
    grid-template-columns: 18px 30px 1fr auto;
    align-items: center;
    gap: 10px;
  }
  .rank {
    color: var(--muted);
    font-size: var(--t-xs);
    text-align: right;
  }
  .ph-gap {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: #e3e7e2;
  }
  .who {
    display: grid;
    min-width: 0;
  }
  .name {
    font-weight: 600;
    line-height: 1.2;
  }
  .party {
    color: var(--muted);
    font-size: var(--t-xs);
  }
  .badge {
    margin-left: 6px;
    padding: 0 5px;
    border-radius: 4px;
    background: var(--confirma);
    color: #fff;
    font-size: 10.5px;
    font-weight: 700;
    line-height: 16px;
    display: inline-block;
    vertical-align: 1px;
  }
  .nums {
    display: grid;
    justify-items: end;
    font-size: var(--t-sm);
    font-weight: 600;
  }
  .muted {
    color: var(--muted);
    font-weight: 400;
    font-size: var(--t-xs);
  }
</style>
