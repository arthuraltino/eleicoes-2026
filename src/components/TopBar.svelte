<script lang="ts">
  import { app, go } from '../lib/state.svelte';

  // cargos in ballot order; each knows which rounds it had
  const CARGOS = [
    { cargo: 1, label: 'Presidente', short: 'Presidente' },
    { cargo: 3, label: 'Governador', short: 'Governador' },
    { cargo: 5, label: 'Senador', short: 'Senador' },
    { cargo: 6, label: 'Deputado federal', short: 'Dep. federal' },
    { cargo: 7, label: 'Deputado estadual', short: 'Dep. estadual' },
  ];

  const els = $derived(app.meta?.elections ?? []);
  const cur = $derived(els.find((e) => e.id === app.eid));
  const turnos = $derived(els.filter((e) => e.cargo === cur?.cargo).map((e) => e.turno));

  function pickCargo(cargo: number) {
    // keep the round when the office had it, else fall back to the 1º turno
    const same = els.find((e) => e.cargo === cargo && e.turno === cur?.turno);
    const any = els.find((e) => e.cargo === cargo);
    const target = same ?? any;
    if (target) go({ eid: target.id });
  }
  function pickTurno(t: number) {
    const target = els.find((e) => e.cargo === cur?.cargo && e.turno === t);
    if (target) go({ eid: target.id });
  }
  const estadual = $derived(app.uf === 'DF' ? 'Dep. distrital' : 'Dep. estadual');
</script>

<header>
  <a class="brand" href="/" onclick={(e) => { e.preventDefault(); go({ uf: null }); }} aria-label="Eleições 2026, voltar ao Brasil">
    <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">
      <rect x="3" y="4" width="26" height="12" rx="2" fill="#F2F4F1" />
      <rect x="3" y="19" width="7.5" height="4" rx="1.2" fill="#F2F4F1" />
      <rect x="12.25" y="19" width="7.5" height="4" rx="1.2" fill="#E07A2E" />
      <rect x="21.5" y="19" width="7.5" height="4" rx="1.2" fill="#2E8B57" />
      <rect x="3" y="25" width="26" height="3" rx="1.2" fill="#6b7178" />
    </svg>
    <span>Eleições <b>2026</b></span>
  </a>

  <nav class="cargos" aria-label="Cargo">
    {#each CARGOS as c}
      <button class:on={cur?.cargo === c.cargo} aria-pressed={cur?.cargo === c.cargo} onclick={() => pickCargo(c.cargo)}>
        {c.cargo === 7 ? estadual : c.short}
      </button>
    {/each}
  </nav>
  <label class="cargo-select">
    <span class="sr-only">Cargo</span>
    <select value={cur?.cargo} onchange={(e) => pickCargo(+e.currentTarget.value)}>
      {#each CARGOS as c}<option value={c.cargo}>{c.cargo === 7 && app.uf === 'DF' ? 'Deputado distrital' : c.label}</option>{/each}
    </select>
  </label>

  <div class="turno" role="group" aria-label="Turno">
    {#each [1, 2] as t}
      <button
        class:on={cur?.turno === t}
        aria-pressed={cur?.turno === t}
        disabled={!turnos.includes(t)}
        title={!turnos.includes(t) ? 'Este cargo não tem 2º turno' : undefined}
        onclick={() => pickTurno(t)}>{t}º turno</button>
    {/each}
  </div>

  <button class="search" onclick={() => (app.searchOpen = true)} aria-label="Buscar município, local de votação ou seção">
    <svg viewBox="0 0 20 20" width="17" height="17" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2" /><path d="M13 13l4.5 4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" /></svg>
    <span class="label">Buscar</span>
    <kbd>/</kbd>
  </button>
</header>

<style>
  header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 16px;
    background: var(--grafite);
    color: #eef1ed;
    position: relative;
    z-index: 30;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 9px;
    color: inherit;
    text-decoration: none;
    font-family: var(--cond);
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 0.01em;
    white-space: nowrap;
    margin-right: 6px;
  }
  .brand b {
    font-weight: 800;
    color: #ffffff;
  }
  .cargos {
    display: flex;
    gap: 2px;
    background: var(--grafite-2);
    padding: 3px;
    border-radius: 9px;
  }
  .cargos button,
  .turno button {
    border: 0;
    background: transparent;
    color: #c9cfd3;
    padding: 6px 12px;
    border-radius: 7px;
    font-size: var(--t-sm);
    font-weight: 600;
    white-space: nowrap;
  }
  .cargos button:hover,
  .turno button:hover:not(:disabled) {
    color: #fff;
  }
  .cargos button.on {
    background: var(--paper);
    color: var(--ink);
  }
  .turno {
    display: flex;
    gap: 2px;
    border: 1px solid #4b5157;
    padding: 2px;
    border-radius: 9px;
  }
  .turno button.on {
    background: var(--confirma);
    color: #fff;
  }
  .turno button:disabled {
    color: #6b7178;
    cursor: not-allowed;
  }
  .search {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;
    border: 1px solid #4b5157;
    background: transparent;
    color: #dfe3e6;
    border-radius: 9px;
    padding: 6px 8px 6px 11px;
    font-size: var(--t-sm);
  }
  .search:hover {
    border-color: #8a9096;
    color: #fff;
  }
  kbd {
    font-family: var(--sans);
    font-size: 11px;
    border: 1px solid #5d6369;
    border-radius: 4px;
    padding: 0 5px;
    color: #aab1b6;
  }
  .cargo-select {
    display: none;
  }
  .cargo-select select {
    background: var(--grafite-2);
    color: #fff;
    border: 0;
    border-radius: 8px;
    padding: 7px 8px;
    font-weight: 600;
    font-size: var(--t-sm);
  }
  @media (max-width: 1120px) {
    .cargos {
      display: none;
    }
    .cargo-select {
      display: block;
    }
  }
  @media (max-width: 640px) {
    header {
      gap: 8px;
      padding: 0 10px;
    }
    .brand span {
      display: none;
    }
    .turno button {
      padding: 6px 8px;
    }
    .search .label,
    .search kbd {
      display: none;
    }
  }
</style>
