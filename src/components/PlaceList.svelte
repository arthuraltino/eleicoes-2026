<script lang="ts" module>
  export type Row = {
    key: string;
    label: string;
    sub?: string | null;
    color: string;
    who: string;
    share: number | null;
    margin: number;
    size: number;
    to: Record<string, unknown>;
    hover?: { source: 'ufs' | 'muns' | 'locais'; id: string | number };
  };
</script>

<script lang="ts">
  import { app, go } from '../lib/state.svelte';
  import { fold, nc, pct } from '../lib/format';

  let { title, rows, unit = 'eleitores', searchable = false }: { title: string; rows: Row[]; unit?: string; searchable?: boolean } = $props();

  let q = $state('');
  let sort = $state<'nome' | 'tamanho' | 'margem'>('tamanho');
  let limit = $state(80);

  const shown = $derived.by(() => {
    const f = fold(q.trim());
    let out = f ? rows.filter((r) => fold(r.label).includes(f) || (r.sub && fold(r.sub).includes(f))) : rows.slice();
    if (sort === 'nome') out.sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'));
    else if (sort === 'tamanho') out.sort((a, b) => b.size - a.size);
    else out.sort((a, b) => a.margin - b.margin);
    return out;
  });
  $effect(() => {
    void [q, sort, rows];
    limit = 80;
  });
</script>

<section class="places" aria-label={title}>
  <div class="head">
    <h2>{title} <span class="count num">{rows.length}</span></h2>
    <label class="sort">
      <span class="sr-only">Ordenar</span>
      <select bind:value={sort}>
        <option value="tamanho">Maior eleitorado</option>
        <option value="nome">Nome</option>
        <option value="margem">Disputa mais apertada</option>
      </select>
    </label>
  </div>
  {#if searchable && rows.length > 12}
    <input class="filter" type="search" placeholder="Filtrar por nome" bind:value={q} aria-label="Filtrar {title.toLowerCase()}" />
  {/if}
  <ul>
    {#each shown.slice(0, limit) as r (r.key)}
      <li>
        <button
          onclick={() => go(r.to)}
          onmouseenter={() => (app.hover = r.hover ?? null)}
          onmouseleave={() => (app.hover = null)}
          onfocus={() => (app.hover = r.hover ?? null)}
          onblur={() => (app.hover = null)}>
          <span class="sw" style:background={r.color}></span>
          <span class="txt">
            <span class="label">{r.label}</span>
            {#if r.sub}<span class="sub">{r.sub}</span>{/if}
          </span>
          <span class="res">
            <span class="who">{r.who}</span>
            <span class="num share">{pct(r.share)}</span>
          </span>
          <span class="num size" title="{unit}">{nc(r.size)}</span>
        </button>
      </li>
    {:else}
      <li class="none">Nada encontrado com “{q}”.</li>
    {/each}
  </ul>
  {#if shown.length > limit}
    <button class="more" onclick={() => (limit += 200)}>Mostrar mais {Math.min(200, shown.length - limit)} de {shown.length - limit}</button>
  {/if}
</section>

<style>
  .places {
    padding-top: 18px;
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  h2 {
    margin: 0;
    font-size: var(--t-md);
    font-weight: 700;
  }
  .count {
    color: var(--muted);
    font-weight: 500;
    margin-left: 4px;
  }
  .sort select {
    border: 1px solid var(--rule-strong);
    background: var(--sheet);
    border-radius: 7px;
    padding: 4px 6px;
    font-size: var(--t-xs);
    color: var(--ink-2);
  }
  .filter {
    width: 100%;
    border: 1px solid var(--rule-strong);
    border-radius: 8px;
    padding: 8px 10px;
    background: #fff;
    margin-bottom: 8px;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  li + li {
    border-top: 1px solid var(--rule);
  }
  li button {
    width: 100%;
    display: grid;
    grid-template-columns: 10px 1fr auto 46px;
    align-items: center;
    gap: 10px;
    padding: 8px 4px;
    border: 0;
    background: none;
    text-align: left;
    border-radius: 6px;
  }
  li button:hover {
    background: #eaede8;
  }
  .sw {
    width: 10px;
    height: 26px;
    border-radius: 3px;
  }
  .txt {
    display: grid;
    min-width: 0;
  }
  .label {
    font-weight: 600;
    line-height: 1.25;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sub {
    color: var(--muted);
    font-size: var(--t-xs);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .res {
    display: grid;
    justify-items: end;
    font-size: var(--t-sm);
    line-height: 1.25;
  }
  .who {
    color: var(--ink-2);
    max-width: 130px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .share {
    font-weight: 700;
  }
  .size {
    color: var(--muted);
    font-size: var(--t-xs);
    text-align: right;
  }
  .none {
    color: var(--muted);
    padding: 10px 4px;
    font-size: var(--t-sm);
  }
  .more {
    margin-top: 8px;
    width: 100%;
    border: 1px solid var(--rule-strong);
    background: var(--sheet);
    border-radius: 8px;
    padding: 8px;
    font-weight: 600;
    color: var(--ink-2);
  }
</style>
