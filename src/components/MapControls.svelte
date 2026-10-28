<script lang="ts">
  import { app, level, savePrefs, primeiroTurno, election } from '../lib/state.svelte';

  const lv = $derived(level());
  // comparing rounds needs per-place results of both: presidente everywhere, governador inside a state
  const showVirada = $derived(!!primeiroTurno() && (election()?.cargo === 1 || lv !== 'br') && app.uf !== 'ZZ');
  const showDivision = $derived(lv === 'br');
  // bubbles only make sense where municipalities are drawn
  const showSize = $derived((lv === 'br' && app.prefs.nacional === 'mun') || lv === 'uf');

  function set<K extends keyof typeof app.prefs>(k: K, v: (typeof app.prefs)[K]) {
    app.prefs[k] = v;
    savePrefs();
  }
</script>

{#if showDivision || showSize || showVirada}
  <div class="controls">
    {#if showVirada}
      <div class="seg" role="group" aria-label="O que o mapa mostra">
        <button aria-pressed={!app.virada} onclick={() => (app.virada = false)}>Resultado</button>
        <button aria-pressed={app.virada} onclick={() => (app.virada = true)} title="Quanto a vantagem entre os finalistas mudou do 1º para o 2º turno">Virada desde o 1º turno</button>
      </div>
    {/if}
    {#if showDivision}
      <div class="seg" role="group" aria-label="Divisão do mapa">
        <button aria-pressed={app.prefs.nacional === 'uf'} onclick={() => set('nacional', 'uf')}>Estados</button>
        <button aria-pressed={app.prefs.nacional === 'mun'} onclick={() => set('nacional', 'mun')}>Municípios</button>
      </div>
    {/if}
    {#if showSize}
      <div class="seg" role="group" aria-label="Forma dos municípios">
        <button aria-pressed={app.prefs.tamanho === 'area'} onclick={() => set('tamanho', 'area')} title="Cada município pintado pela sua área">Área</button>
        <button aria-pressed={app.prefs.tamanho === 'bolhas'} onclick={() => set('tamanho', 'bolhas')} title="Cada município como um círculo do tamanho do seu eleitorado">Bolhas por eleitorado</button>
      </div>
    {/if}
  </div>
{/if}

<style>
  .controls {
    position: absolute;
    top: 14px;
    left: 14px;
    z-index: 4;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .seg {
    display: flex;
    background: var(--sheet);
    border-radius: 9px;
    padding: 3px;
    box-shadow: 0 1px 4px rgb(20 33 46 / 0.16), 0 0 0 1px rgb(20 33 46 / 0.06);
  }
  .seg button {
    border: 0;
    background: transparent;
    padding: 6px 11px;
    border-radius: 7px;
    font-size: var(--t-sm);
    font-weight: 600;
    color: var(--ink-2);
  }
  .seg button[aria-pressed='true'] {
    background: var(--ink);
    color: var(--sheet);
  }
  .seg button:hover:not([aria-pressed='true']) {
    color: var(--ink);
  }
  @media (max-width: 640px) {
    .controls {
      top: 10px;
      left: 10px;
      right: 10px;
    }
    .seg button {
      padding: 6px 9px;
    }
  }
</style>
