<script lang="ts">
  import type { Rec } from '../lib/data';
  import { validos } from '../lib/data';
  import { cands } from '../lib/view.svelte';
  import { level } from '../lib/state.svelte';
  import { SWATCH } from '../lib/colors';
  import { n, pct, pp } from '../lib/format';
  import Photo from './Photo.svelte';

  let { rec, vagas = 1 }: { rec: Rec; vagas?: number | null } = $props();

  let all = $state(false);
  const total = $derived(validos(rec));
  const rows = $derived(
    cands()
      .map((c, i) => ({ c, q: rec.v?.[i] ?? 0 }))
      .filter((r) => !r.c.anulado)
      .sort((a, b) => b.q - a.q),
  );
  const duel = $derived(rows.length === 2);
  // in a duel each candidate keeps a side everywhere (race order), so the eye never has to re-find them
  const sides = $derived(
    cands()
      .map((c, i) => ({ c, q: rec.v?.[i] ?? 0 }))
      .filter((r) => !r.c.anulado),
  );
  const shown = $derived(all ? rows : rows.slice(0, 6));
  // official outcome only means something for the whole race
  const raceLevel = $derived(level() === 'br' || (level() === 'uf' && cands()[0]?.ue !== 'BR'));
  const badge = (sit: string | null | undefined) =>
    !sit ? null : sit.startsWith('Eleito') ? 'Eleito' : sit.startsWith('2º') ? '2º turno' : null;
</script>

{#if total === 0}
  <p class="empty">Nenhum voto válido para este cargo aqui.</p>
{:else if duel}
  {@const [a, b] = sides}
  <section class="duel" aria-label="Resultado">
    <div class="sides">
      {#each [a, b] as r, i}
        <div class="side" class:right={i === 1} class:win={r.q > (i ? a.q : b.q)}>
          <Photo c={r.c} size={52} />
          <div class="who">
            <span class="name">{r.c.nome}</span>
            <span class="party">{r.c.p}{#if raceLevel && badge(r.c.sit)}<b class="badge">{badge(r.c.sit)}</b>{/if}</span>
          </div>
          <span class="big num" style:color={SWATCH[r.c.cor ?? 'g']}>{pct(r.q / total)}</span>
          <span class="votes num">{n(r.q)} votos</span>
        </div>
      {/each}
    </div>
    <div class="split" role="img" aria-label="{a.c.nome} {pct(a.q / total)}, {b.c.nome} {pct(b.q / total)}">
      <span style:flex-grow={a.q} style:background={SWATCH[a.c.cor ?? 'g']}></span>
      <span style:flex-grow={b.q} style:background={SWATCH[b.c.cor ?? 'g']}></span>
      <i class="mid" aria-hidden="true"></i>
    </div>
    <p class="margin">
      {#if a.q === b.q}Empate{:else}{(a.q > b.q ? a : b).c.nome} à frente por <b>{n(Math.abs(a.q - b.q))}</b> votos ({pp(Math.abs(a.q - b.q) / total)}){/if}
    </p>
  </section>
{:else}
  <section aria-label="Resultado">
    {#if vagas && vagas > 1 && raceLevel}<p class="note">{vagas} vagas em disputa: os {vagas} mais votados se elegem.</p>{/if}
    <ol class="list">
      {#each shown as r, i}
        <li>
          <Photo c={r.c} size={i < 3 ? 40 : 30} />
          <div class="who">
            <span class="name">{r.c.nome}{#if raceLevel && badge(r.c.sit)}<b class="badge">{badge(r.c.sit)}</b>{/if}</span>
            <span class="party">{r.c.n} · {r.c.p}</span>
            <span class="track"><span style:width="{(r.q / (rows[0].q || 1)) * 100}%" style:background={SWATCH[r.c.cor ?? 'g']}></span></span>
          </div>
          <span class="nums">
            <span class="pct num">{pct(r.q / total)}</span>
            <span class="votes num">{n(r.q)}</span>
          </span>
        </li>
      {/each}
    </ol>
    {#if rows.length > 6}
      <button class="more" onclick={() => (all = !all)}>{all ? 'Mostrar só os 6 primeiros' : `Mostrar todos os ${rows.length} candidatos`}</button>
    {/if}
  </section>
{/if}
{#if rec.s[4] > 0}
  <p class="anulados">
    {n(rec.s[4])} votos anulados: foram para candidatos com registro indeferido e não contam como válidos.
  </p>
{/if}

<style>
  .empty,
  .note {
    color: var(--ink-2);
    font-size: var(--t-sm);
    margin: 6px 0 10px;
  }
  .duel {
    padding: 4px 0 2px;
  }
  .sides {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .side {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-areas: 'ph who' 'big big' 'votes votes';
    align-items: center;
    column-gap: 10px;
  }
  .side.right {
    grid-template-columns: 1fr auto;
    grid-template-areas: 'who ph' 'big big' 'votes votes';
    text-align: right;
  }
  .side :global(.ph) {
    grid-area: ph;
  }
  .side .who {
    grid-area: who;
  }
  .big {
    grid-area: big;
    font-family: var(--cond);
    font-weight: 800;
    font-size: var(--t-hero);
    line-height: 0.95;
    margin-top: 10px;
    letter-spacing: -0.01em;
  }
  .side:not(.win) .big {
    opacity: 0.68;
  }
  .votes {
    grid-area: votes;
    color: var(--muted);
    font-size: var(--t-sm);
  }
  .who {
    display: grid;
    min-width: 0;
  }
  .name {
    font-weight: 700;
    line-height: 1.2;
  }
  .party {
    color: var(--muted);
    font-size: var(--t-sm);
  }
  .badge {
    display: inline-block;
    margin-left: 6px;
    padding: 0 6px;
    border-radius: 4px;
    background: var(--confirma);
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    line-height: 17px;
    vertical-align: 1px;
  }
  .split {
    position: relative;
    display: flex;
    gap: 2px;
    height: 14px;
    margin: 12px 0 6px;
  }
  .split span:first-child {
    border-radius: 4px 0 0 4px;
  }
  .split span:nth-child(2) {
    border-radius: 0 4px 4px 0;
  }
  .mid {
    position: absolute;
    left: 50%;
    top: -4px;
    bottom: -4px;
    width: 2px;
    margin-left: -1px;
    background: var(--ink);
  }
  .margin {
    margin: 6px 0 0;
    font-size: var(--t-sm);
    color: var(--ink-2);
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 10px;
  }
  .list li {
    display: grid;
    grid-template-columns: 40px 1fr auto;
    align-items: center;
    gap: 12px;
  }
  .list li :global(.ph) {
    justify-self: center;
  }
  .track {
    display: block;
    height: 6px;
    margin-top: 5px;
    background: #e6e9e4;
    border-radius: 3px;
    overflow: hidden;
  }
  .track span {
    display: block;
    height: 100%;
    border-radius: 3px;
  }
  .nums {
    display: grid;
    justify-items: end;
  }
  .pct {
    font-weight: 700;
    font-size: var(--t-lg);
    line-height: 1.1;
  }
  .nums .votes {
    font-size: var(--t-xs);
  }
  .more {
    margin-top: 10px;
    border: 0;
    background: none;
    padding: 4px 0;
    font-weight: 600;
    color: var(--ink-2);
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .anulados {
    margin: 10px 0 0;
    font-size: var(--t-xs);
    color: var(--muted);
  }
  @media (max-width: 420px) {
    .big {
      font-size: 48px;
    }
  }
</style>
