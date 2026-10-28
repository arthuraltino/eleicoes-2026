<script lang="ts">
  import { app, go } from '../lib/state.svelte';
  import { view, cands, parties } from '../lib/view.svelte';
  import { lead, type Urna } from '../lib/data';
  import { fill, step, EMPTY } from '../lib/colors';
  import { pct } from '../lib/format';

  let { compact = false }: { compact?: boolean } = $props();

  const urnas = $derived((view.urnas?.urnas ?? []).filter((u) => u.l === app.l));

  function tile(u: Urna) {
    const r = u.e[app.eid];
    const w = lead(r);
    const list: { cor?: string; p: string; nome?: string }[] = r?.p ? parties() : cands();
    const who = w ? list[w.idx] : null;
    const bg = w ? fill((who?.cor ?? 'g') as never, w.margin) : EMPTY;
    return { bg, dark: !!w && step(w.margin) >= 3, share: w?.share ?? null, who: who ? (who.nome ?? who.p) : 'sem votos' };
  }
</script>

<section class="grid-wrap" aria-label="Urnas deste local">
  {#if !compact}
    <h2>{urnas.length} {urnas.length === 1 ? 'urna' : 'urnas'} neste local</h2>
    <p class="hint">Cada quadrado é uma seção eleitoral. Abra uma para ver o boletim da urna.</p>
  {:else}
    <h2 class="small">Outras urnas deste local</h2>
  {/if}
  <ul class="grid" class:compact>
    {#each urnas as u (u.s)}
      {@const t = tile(u)}
      <li>
        <button
          class:sel={u.s === app.secao}
          class:dark={t.dark}
          style:background={t.bg}
          onclick={() => go({ secao: u.s })}
          aria-label="Seção {u.s}: {t.who} {pct(t.share)}"
          aria-current={u.s === app.secao ? 'true' : undefined}>
          <span class="s num">{u.s}</span>
          {#if !compact}<span class="p num">{pct(t.share)}</span>{/if}
        </button>
      </li>
    {/each}
  </ul>
</section>

<style>
  .grid-wrap {
    padding-top: 18px;
  }
  h2 {
    margin: 0;
    font-size: var(--t-md);
    font-weight: 700;
  }
  h2.small {
    font-size: var(--t-sm);
    margin-bottom: 8px;
  }
  .hint {
    margin: 2px 0 10px;
    color: var(--muted);
    font-size: var(--t-sm);
  }
  .grid {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
    gap: 4px;
  }
  .grid.compact {
    grid-template-columns: repeat(auto-fill, minmax(42px, 1fr));
    gap: 3px;
  }
  button {
    width: 100%;
    aspect-ratio: 1;
    border: 0;
    border-radius: 6px;
    display: grid;
    align-content: space-between;
    justify-items: start;
    padding: 6px 7px;
    color: var(--ink);
    text-align: left;
  }
  .compact button {
    padding: 3px 4px;
    border-radius: 4px;
  }
  button.dark {
    color: #fff;
  }
  button:hover {
    box-shadow: inset 0 0 0 2px var(--ink);
  }
  button.sel {
    box-shadow: inset 0 0 0 3px var(--ink), 0 0 0 2px var(--sheet), 0 0 0 4px var(--ink);
  }
  .s {
    font-size: var(--t-xs);
    font-weight: 600;
    opacity: 0.85;
  }
  .p {
    font-family: var(--cond);
    font-weight: 800;
    font-size: 21px;
    line-height: 1;
  }
</style>
