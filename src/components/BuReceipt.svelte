<script lang="ts">
  import { app } from '../lib/state.svelte';
  import { currentUrna, currentLocal } from '../lib/view.svelte';
  import { loadNational, loadRace, pairs, type Cand, type Party, type Rec } from '../lib/data';
  import { n, dataHora, hhmm } from '../lib/format';

  const urna = $derived(currentUrna());
  const local = $derived(currentLocal());
  const turno = $derived(+app.eid.split('-').pop()!);
  const meta = $derived.by(() => {
    const raw = urna?.bu[String(turno)] ?? [];
    const names = app.meta?.bu ?? [];
    return Object.fromEntries(names.map((k, i) => [k, raw[i] ?? null])) as Record<string, any>;
  });
  const munNome = $derived(app.meta?.municipios[app.mun!]?.[0] ?? '');

  // every office voted in this round, in ballot order
  const offices = $derived(
    (app.meta?.elections ?? []).filter((e) => e.turno === turno && urna?.e[e.id]).map((e) => ({ e, rec: urna!.e[e.id] as Rec })),
  );

  // names for each office's numbers (presidente: national list; others: the state race)
  let lists = $state<Record<string, { c: Cand[]; p: Party[] }>>({});
  $effect(() => {
    const uf = app.uf!;
    for (const { e } of offices) {
      if (lists[e.id]) continue;
      const p = e.cargo === 1 ? loadNational(e.id).then((f) => ({ c: f.c ?? [], p: [] })) : loadRace(e.id, uf).then((f) => ({ c: f.c ?? [], p: f.parties ?? [] }));
      p.then((x) => (lists[e.id] = x)).catch(() => {});
    }
  });

  let expanded = $state<Record<string, boolean>>({});

  function lines(id: string, rec: Rec) {
    const L = lists[id];
    if (!L) return [];
    if (rec.v) {
      return rec.v
        .map((q, i) => ({ nr: L.c[i]?.n, nome: L.c[i]?.nome ?? '?', q }))
        .filter((x) => x.q > 0)
        .sort((a, b) => a.nr - b.nr);
    }
    return pairs(rec.t).map(([i, q]) => ({ nr: L.c[i]?.n, nome: L.c[i]?.nome ?? '?', q }));
  }

  function duration(a: unknown, b: unknown) {
    if (typeof a !== 'string' || typeof b !== 'string') return null;
    const ms = new Date(b.replace(' ', 'T')).getTime() - new Date(a.replace(' ', 'T')).getTime();
    if (!isFinite(ms) || ms <= 0) return null;
    const h = Math.floor(ms / 3.6e6), m = Math.floor((ms % 3.6e6) / 6e4);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }
  const label = (cargo: number, nome: string) => (cargo === 7 && app.uf === 'DF' ? 'Deputado distrital' : nome);
</script>

{#if urna}
  <article class="receipt" aria-label="Boletim de urna da seção {urna.s}">
    <div class="shade"><div class="paper">
      <header>
        <p class="t1">Boletim de urna</p>
        <p class="row"><span>Eleições gerais 2026</span><span>{turno}º turno</span></p>
        <p class="row"><span>{munNome} ({app.uf})</span></p>
        <p class="row"><span>Zona {app.z}</span><span>Seção {urna.s}</span></p>
        {#if local}<p class="row"><span>Local {local.l}</span><span class="clip">{local.nm}</span></p>{/if}
      </header>

      {#each offices as { e, rec }, oi}
        {@const all = lines(e.id, rec)}
        {@const open = expanded[e.id]}
        {@const lim = e.prop ? 8 : 20}
        <section class:first={oi === 0}>
          <p class="t2">{label(e.cargo, e.label)}</p>
          {#if !lists[e.id]}
            <p class="row muted"><span>Carregando nomes…</span></p>
          {/if}
          {#each open ? all : all.slice(0, lim) as x}
            <p class="row"><span class="clip"><span class="nr">{x.nr}</span> {x.nome}</span><span class="num">{n(x.q)}</span></p>
          {/each}
          {#if all.length > lim}
            <button class="exp" onclick={() => (expanded[e.id] = !open)}>{open ? 'Recolher' : `Mostrar mais ${all.length - lim} candidatos`}</button>
          {/if}
          {#if rec.s[5]}<p class="row"><span>Votos de legenda</span><span class="num">{n(rec.s[5])}</span></p>{/if}
          <p class="row"><span>Brancos</span><span class="num">{n(rec.s[2])}</span></p>
          <p class="row"><span>Nulos</span><span class="num">{n(rec.s[3] + rec.s[4])}</span></p>
          <p class="row strong"><span>Total apurado</span><span class="num">{n(rec.s[1])}</span></p>
        </section>
      {/each}

      <section>
        <p class="row"><span>Eleitores aptos</span><span class="num">{n(offices[0]?.rec.s[0])}</span></p>
        <p class="row"><span>Compareceram</span><span class="num">{n(offices[0]?.rec.s[1])}</span></p>
        <p class="row"><span>Faltaram</span><span class="num">{n((offices[0]?.rec.s[0] ?? 0) - (offices[0]?.rec.s[1] ?? 0))}</span></p>
        {#if meta.biosem != null}<p class="row"><span>Liberados sem biometria</span><span class="num">{n(meta.biosem)}</span></p>{/if}
      </section>

      <section>
        <p class="row"><span>Urna</span><span class="num">{meta.urna ?? '—'}</span></p>
        <p class="row"><span>Código de carga</span><span class="num clip">{meta.carga1 ?? '—'}</span></p>
        <p class="row"><span>Carregada em</span><span class="num">{dataHora(meta.dtcarga)}</span></p>
        <p class="row"><span>Abertura</span><span class="num">{dataHora(meta.abertura)}</span></p>
        <p class="row"><span>Encerramento</span><span class="num">{dataHora(meta.encerramento)}</span></p>
        {#if duration(meta.abertura, meta.encerramento)}
          <p class="row"><span>Votação durou</span><span class="num">{duration(meta.abertura, meta.encerramento)}</span></p>
        {/if}
        <p class="row"><span>BU emitido</span><span class="num">{hhmm(meta.emissao)}</span></p>
        <p class="row"><span>Recebido pelo TSE</span><span class="num">{dataHora(meta.recebido)}</span></p>
        {#if meta.agregadas?.length}<p class="row"><span>Seções agregadas</span><span class="num">{meta.agregadas.join(', ')}</span></p>{/if}
        {#if meta.junta}<p class="row warn"><span>Apurada pela junta eleitoral</span><span class="num">{meta.junta}{meta.turma ? '/' + meta.turma : ''}</span></p>{/if}
      </section>
    </div></div>
    <p class="caption">Dados do boletim desta urna publicados pelo TSE, reorganizados para leitura. Nulos incluem votos anulados.</p>
  </article>
{/if}

<style>
  .receipt {
    padding-top: 16px;
  }
  .shade {
    filter: drop-shadow(0 1px 1px rgb(20 33 46 / 0.14)) drop-shadow(0 6px 10px rgb(20 33 46 / 0.1));
  }
  .paper {
    position: relative;
    margin: 8px 0;
    background: #fdfdfb;
    color: #1d2329;
    font-family: var(--mono);
    font-variation-settings: 'wdth' 75;
    font-size: 12px;
    line-height: 1.55;
    padding: 12px 16px 14px;
    text-transform: uppercase;
    letter-spacing: 0.01em;
  }
  /* torn thermal-paper edges (the drop-shadow on .receipt follows them) */
  .paper::before,
  .paper::after {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    height: 8px;
    background:
      linear-gradient(135deg, #fdfdfb 33.33%, transparent 33.33%) 0 0 / 12px 16px repeat-x,
      linear-gradient(225deg, #fdfdfb 33.33%, transparent 33.33%) 0 0 / 12px 16px repeat-x;
  }
  .paper::before {
    top: -8px;
    transform: scaleY(-1);
  }
  .paper::after {
    bottom: -8px;
  }
  p {
    margin: 0;
  }
  .t1 {
    text-align: center;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
  }
  .t2 {
    font-weight: 600;
    margin-bottom: 2px;
  }
  .row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }
  .row .num {
    text-align: right;
    white-space: nowrap;
  }
  .clip {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }
  .nr {
    display: inline-block;
    min-width: 5ch;
    color: #5b636b;
  }
  .strong {
    font-weight: 600;
  }
  .muted {
    color: #8a9096;
  }
  .warn {
    color: #a24e12;
  }
  header,
  section {
    padding: 8px 0;
  }
  section {
    border-top: 1px dashed #b9bfc4;
  }
  .exp {
    border: 0;
    background: none;
    padding: 2px 0;
    font: inherit;
    text-transform: none;
    text-decoration: underline;
    color: #3d4650;
  }
  .caption {
    margin-top: 10px;
    color: var(--muted);
    font-size: var(--t-xs);
  }
</style>
