<script lang="ts">
  import { app, go, level } from '../lib/state.svelte';
  import { currentLocal } from '../lib/view.svelte';

  const crumbs = $derived.by(() => {
    const lv = level();
    const out: { label: string; to: Parameters<typeof go>[0] | null }[] = [{ label: 'Brasil', to: { uf: null } }];
    if (app.uf) out.push({ label: app.uf === 'ZZ' ? 'Exterior' : app.uf, to: { uf: app.uf } });
    if (app.mun) out.push({ label: app.meta?.municipios[app.mun]?.[0] ?? app.mun, to: { mun: app.mun } });
    if (app.zona != null && lv === 'mun') out.push({ label: `Zona ${app.zona}`, to: { zona: app.zona } });
    if (app.l != null) out.push({ label: currentLocal()?.nm ?? `Local ${app.l}`, to: { l: app.l, z: app.z } });
    if (app.secao != null) out.push({ label: `Seção ${app.secao}`, to: null });
    out[out.length - 1].to = null;
    return out;
  });
</script>

<nav aria-label="Você está em">
  <ol>
    {#each crumbs as c, i}
      <li>
        {#if c.to}
          <button onclick={() => go(c.to!)}>{c.label}</button>
        {:else}
          <span aria-current="page">{c.label}</span>
        {/if}
        {#if i < crumbs.length - 1}<svg viewBox="0 0 8 12" width="7" height="10" aria-hidden="true"><path d="M2 2l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" /></svg>{/if}
      </li>
    {/each}
  </ol>
</nav>

<style>
  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px 4px;
    font-size: var(--t-sm);
    color: var(--muted);
  }
  li {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }
  button {
    border: 0;
    background: none;
    padding: 2px 3px;
    color: var(--ink-2);
    font-weight: 600;
    text-decoration: underline;
    text-decoration-color: var(--rule-strong);
    text-underline-offset: 3px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  button:hover {
    color: var(--ink);
    text-decoration-color: currentColor;
  }
  span[aria-current] {
    padding: 2px 3px;
    max-width: 240px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
