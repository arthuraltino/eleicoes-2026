<script lang="ts">
  import { onMount } from 'svelte';
  import { app, go } from '../lib/state.svelte';
  import { loadSearch, loadMun, loadUrnas, type SearchEntry } from '../lib/data';
  import { fold } from '../lib/format';

  type Hit = { key: string; label: string; sub: string; to: Parameters<typeof go>[0] };

  let mode = $state<'buscar' | 'secao'>('buscar');
  let q = $state('');
  let active = $state(0);
  let input: HTMLInputElement | undefined = $state();
  let locais = $state<SearchEntry[] | null>(null);

  // "Minha seção"
  let munQ = $state('');
  let munKey = $state<string | null>(null);
  let zona = $state('');
  let secao = $state('');
  let erro = $state<string | null>(null);
  let buscando = $state(false);

  const muns = $derived(Object.entries(app.meta?.municipios ?? {}).map(([k, [nome, uf]]) => ({ k, nome, uf, f: fold(nome) })));

  onMount(() => {
    input?.focus();
  });

  $effect(() => {
    if (app.uf && app.uf !== 'ZZ') loadSearch(app.uf).then((x) => (locais = x)).catch(() => {});
  });

  function findMuns(text: string, max = 8) {
    const f = fold(text.trim());
    if (f.length < 2) return [];
    const starts = muns.filter((m) => m.f.startsWith(f));
    const has = muns.filter((m) => !m.f.startsWith(f) && m.f.includes(f));
    // the current state first, then the biggest names alphabetically
    const cur = (m: { uf: string }) => (m.uf === app.uf ? 0 : 1);
    return [...starts.sort((a, b) => cur(a) - cur(b) || a.nome.localeCompare(b.nome)), ...has].slice(0, max);
  }

  const hits = $derived.by((): Hit[] => {
    const f = fold(q.trim());
    if (f.length < 2) return [];
    const out: Hit[] = findMuns(q, 6).map((m) => ({
      key: 'm' + m.k, label: m.nome, sub: m.uf === 'ZZ' ? 'Cidade no exterior' : `Município · ${m.uf}`, to: { uf: m.uf, mun: m.k },
    }));
    if (locais) {
      let n = 0;
      for (const [mk, z, l, nome, bairro] of locais) {
        if (fold(nome).includes(f) || (bairro && fold(bairro).includes(f))) {
          const munNome = app.meta?.municipios[String(mk)]?.[0] ?? '';
          out.push({ key: `l${mk}-${z}-${l}`, label: nome, sub: `Local de votação · ${[bairro, munNome].filter(Boolean).join(', ')}`, to: { uf: app.uf, mun: String(mk), z, l } });
          if (++n >= 8) break;
        }
      }
    }
    return out;
  });
  $effect(() => {
    void hits;
    active = 0;
  });

  function pick(h: Hit) {
    close();
    go(h.to);
  }
  function close() {
    app.searchOpen = false;
  }
  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
    else if (mode === 'buscar' && e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(hits.length - 1, active + 1); }
    else if (mode === 'buscar' && e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(0, active - 1); }
    else if (mode === 'buscar' && e.key === 'Enter' && hits[active]) pick(hits[active]);
  }

  const munSugestoes = $derived(munKey ? [] : findMuns(munQ, 6));

  async function abrirSecao(e: SubmitEvent) {
    e.preventDefault();
    erro = null;
    if (!munKey) { erro = 'Escolha o município na lista.'; return; }
    const z = parseInt(zona, 10), s = parseInt(secao, 10);
    if (!z || !s) { erro = 'Preencha a zona e a seção, como aparecem no título de eleitor.'; return; }
    buscando = true;
    try {
      const mf = await loadMun(munKey);
      const nome = app.meta?.municipios[munKey]?.[0];
      if (!mf.zonas.includes(z)) { erro = `${nome} não tem a zona ${z}. Zonas deste município: ${mf.zonas.join(', ')}.`; return; }
      const uf = await loadUrnas(munKey, z);
      const u = uf.urnas.find((x) => x.s === s);
      if (!u) { erro = `A seção ${s} não existe na zona ${z} de ${nome}. Confira o número no título ou no e-Título.`; return; }
      close();
      go({ uf: app.meta!.municipios[munKey][1], mun: munKey, z, l: u.l, secao: s });
    } catch {
      erro = 'Não foi possível consultar esta seção agora. Tente de novo.';
    } finally {
      buscando = false;
    }
  }
</script>

<div class="backdrop" onclick={close} role="presentation"></div>
<div class="dialog" role="dialog" aria-modal="true" aria-label="Buscar" tabindex="-1" onkeydown={onKey}>
  <div class="tabs" role="tablist">
    <button role="tab" aria-selected={mode === 'buscar'} onclick={() => (mode = 'buscar')}>Município ou local</button>
    <button role="tab" aria-selected={mode === 'secao'} onclick={() => (mode = 'secao')}>Minha seção</button>
    <button class="x" onclick={close} aria-label="Fechar">Esc</button>
  </div>

  {#if mode === 'buscar'}
    <input
      bind:this={input}
      bind:value={q}
      type="search"
      placeholder={app.uf && app.uf !== 'ZZ' ? `Município, escola ou bairro em ${app.uf}` : 'Nome do município'}
      aria-label="Buscar"
      aria-controls="hits"
      autocomplete="off" />
    <ul id="hits" role="listbox">
      {#each hits as h, i (h.key)}
        <li role="option" aria-selected={i === active}>
          <button class:on={i === active} onclick={() => pick(h)} onmouseenter={() => (active = i)}>
            <span class="label">{h.label}</span>
            <span class="sub">{h.sub}</span>
          </button>
        </li>
      {/each}
    </ul>
    {#if q.trim().length >= 2 && !hits.length}
      <p class="empty">Nada encontrado. {app.uf ? '' : 'Para buscar escolas e bairros, abra primeiro um estado.'}</p>
    {:else if q.trim().length < 2}
      <p class="empty">Digite pelo menos duas letras.{app.uf && app.uf !== 'ZZ' ? ` Locais de votação são buscados em ${app.meta?.ufs[app.uf]?.nome}.` : ''}</p>
    {/if}
  {:else}
    <form onsubmit={abrirSecao}>
      <p class="lead">Veja o boletim da urna onde você vota. Zona e seção estão no título de eleitor e no e-Título.</p>
      <label>
        <span>Município</span>
        <input
          bind:value={munQ}
          oninput={() => (munKey = null)}
          placeholder="Comece a digitar"
          autocomplete="off" />
      </label>
      {#if munSugestoes.length}
        <ul class="sug">
          {#each munSugestoes as m (m.k)}
            <li><button type="button" onclick={() => { munKey = m.k; munQ = `${m.nome} (${m.uf})`; }}>{m.nome} <span>{m.uf}</span></button></li>
          {/each}
        </ul>
      {/if}
      <div class="pair">
        <label><span>Zona</span><input bind:value={zona} inputmode="numeric" pattern="[0-9]*" placeholder="Ex.: 1" /></label>
        <label><span>Seção</span><input bind:value={secao} inputmode="numeric" pattern="[0-9]*" placeholder="Ex.: 67" /></label>
      </div>
      {#if erro}<p class="erro" role="alert">{erro}</p>{/if}
      <button class="go" type="submit" disabled={buscando}>{buscando ? 'Procurando…' : 'Ver minha urna'}</button>
    </form>
  {/if}
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 50;
    background: rgb(20 33 46 / 0.35);
  }
  .dialog {
    position: fixed;
    z-index: 51;
    top: 10vh;
    left: 50%;
    transform: translateX(-50%);
    width: min(560px, calc(100vw - 24px));
    max-height: 78vh;
    overflow: auto;
    background: var(--sheet);
    border-radius: 14px;
    box-shadow: 0 24px 60px -20px rgb(20 33 46 / 0.5);
    padding: 12px;
  }
  .tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 10px;
  }
  .tabs button {
    border: 0;
    background: none;
    padding: 7px 11px;
    border-radius: 8px;
    font-weight: 600;
    color: var(--ink-2);
    font-size: var(--t-sm);
  }
  .tabs button[aria-selected='true'] {
    background: var(--ink);
    color: #fff;
  }
  .tabs .x {
    margin-left: auto;
    color: var(--muted);
    font-weight: 500;
    font-size: var(--t-xs);
  }
  input {
    width: 100%;
    border: 1px solid var(--rule-strong);
    border-radius: 9px;
    padding: 11px 12px;
    font-size: var(--t-md);
    background: #fff;
  }
  ul {
    list-style: none;
    margin: 8px 0 0;
    padding: 0;
  }
  li button {
    width: 100%;
    text-align: left;
    border: 0;
    background: none;
    border-radius: 8px;
    padding: 8px 10px;
    display: grid;
  }
  li button.on,
  li button:hover {
    background: #e8ece6;
  }
  .label {
    font-weight: 600;
  }
  .sub {
    color: var(--muted);
    font-size: var(--t-xs);
  }
  .empty {
    color: var(--muted);
    font-size: var(--t-sm);
    margin: 12px 4px 4px;
  }
  form {
    display: grid;
    gap: 10px;
  }
  .lead {
    margin: 0;
    color: var(--ink-2);
    font-size: var(--t-sm);
  }
  label {
    display: grid;
    gap: 4px;
    font-size: var(--t-sm);
    font-weight: 600;
  }
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .sug {
    margin: -4px 0 0;
    border: 1px solid var(--rule);
    border-radius: 9px;
  }
  .sug button span {
    color: var(--muted);
    font-weight: 400;
  }
  .sug button {
    display: block;
  }
  .erro {
    margin: 0;
    color: #8a3d0d;
    background: #f7ece2;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: var(--t-sm);
  }
  .go {
    border: 0;
    border-radius: 9px;
    padding: 11px;
    background: var(--confirma);
    color: #fff;
    font-weight: 700;
    font-size: var(--t-md);
  }
  .go:disabled {
    opacity: 0.7;
  }
</style>
