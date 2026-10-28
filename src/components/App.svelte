<script lang="ts">
  import { onMount } from 'svelte';
  import { app, fromPath, toPath, up } from '../lib/state.svelte';
  import { loadMeta } from '../lib/data';
  import { sync, view } from '../lib/view.svelte';
  import TopBar from './TopBar.svelte';
  import MapView from './MapView.svelte';
  import MapControls from './MapControls.svelte';
  import Legend from './Legend.svelte';
  import Panel from './Panel.svelte';
  import Search from './Search.svelte';

  let failed = $state<string | null>(null);

  onMount(() => {
    loadMeta()
      .then((m) => {
        app.meta = m;
        fromPath(location.pathname, location.search);
        history.replaceState(null, '', toPath());
      })
      .catch((e) => (failed = e.message));
    const onPop = () => fromPath(location.pathname, location.search);
    addEventListener('popstate', onPop);
    return () => removeEventListener('popstate', onPop);
  });

  // load the files for wherever the URL points
  $effect(() => {
    if (!app.meta) return;
    void [app.eid, app.uf, app.mun, app.z, app.virada];
    sync();
  });

  function onKey(e: KeyboardEvent) {
    const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement;
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) {
      e.preventDefault();
      app.searchOpen = true;
    } else if (e.key === 'Escape' && !app.searchOpen && !typing) {
      if (app.preview) app.preview = null;
      else up();
    }
  }
</script>

<svelte:window onkeydown={onKey} />

{#if failed}
  <div class="fatal" role="alert">
    <h1>Os dados não carregaram</h1>
    <p>{failed}. Verifique a conexão e recarregue a página.</p>
    <button onclick={() => location.reload()}>Recarregar</button>
  </div>
{:else}
  <div class="shell">
    <TopBar />
    <main>
      <MapView />
      {#if app.meta}
        <MapControls />
        <Legend />
        <Panel />
      {/if}
      {#if view.loading}<div class="loading" aria-hidden="true"></div>{/if}
    </main>
    {#if app.searchOpen}<Search />{/if}
  </div>
{/if}

<style>
  .shell {
    height: 100%;
    display: grid;
    grid-template-rows: var(--bar-h) 1fr;
  }
  main {
    position: relative;
    overflow: hidden;
  }
  .loading {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    z-index: 20;
    background: linear-gradient(90deg, transparent, var(--confirma), transparent);
    background-size: 40% 100%;
    background-repeat: no-repeat;
    animation: slide 1.1s linear infinite;
  }
  @keyframes slide {
    from { background-position: -40% 0; }
    to { background-position: 140% 0; }
  }
  .fatal {
    max-width: 520px;
    margin: 18vh auto;
    padding: 0 16px;
  }
  .fatal h1 {
    font-size: var(--t-xl);
  }
  .fatal button {
    padding: 10px 16px;
    border-radius: 8px;
    border: 0;
    background: var(--confirma);
    color: white;
    font-weight: 600;
  }
</style>
