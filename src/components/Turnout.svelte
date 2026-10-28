<script lang="ts">
  import type { Rec } from '../lib/data';
  import { validos } from '../lib/data';
  import { n, pct } from '../lib/format';

  let { rec }: { rec: Rec } = $props();

  // how the electorate split, as one bar over the eligible voters
  const parts = $derived.by(() => {
    const [ap, cp, br, nu, an] = rec.s;
    const val = validos(rec);
    return {
      ap, cp,
      segs: [
        { k: 'Válidos', v: val, c: 'var(--ink)' },
        { k: 'Brancos', v: br, c: '#8d969e' },
        { k: 'Nulos', v: nu, c: '#b4bbc1' },
        { k: 'Anulados', v: an, c: '#d1a77f' },
        { k: 'Abstenção', v: Math.max(0, ap - cp), c: 'url(#hatch)' },
      ].filter((s) => s.v > 0),
    };
  });
</script>

<section class="turnout" aria-label="Comparecimento">
  <div class="top">
    <h2>Comparecimento</h2>
    <p class="num"><strong>{pct(parts.ap ? parts.cp / parts.ap : null)}</strong> de {n(parts.ap)} eleitores</p>
  </div>
  <svg class="bar" viewBox="0 0 100 10" preserveAspectRatio="none" role="img" aria-label="Divisão dos eleitores aptos">
    <defs>
      <pattern id="hatch" width="2.2" height="2.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="2.2" height="2.2" fill="#eceee9" />
        <line x1="0" y1="0" x2="0" y2="2.2" stroke="#c4c9c3" stroke-width="1" />
      </pattern>
    </defs>
    {#each parts.segs as s, i}
      {@const x = parts.segs.slice(0, i).reduce((a, b) => a + b.v, 0) / parts.ap * 100}
      <rect x={x} y="0" width={Math.max(0, (s.v / parts.ap) * 100 - 0.3)} height="10" fill={s.c} />
    {/each}
  </svg>
  <ul>
    {#each parts.segs as s}
      <li>
        <span class="sw" style:background={s.c.startsWith('url') ? 'repeating-linear-gradient(45deg,#c4c9c3 0 1px,#eceee9 1px 3px)' : s.c}></span>
        <span>{s.k}</span>
        <span class="num v">{n(s.v)}</span>
        <span class="num p">{pct(parts.ap ? s.v / parts.ap : null)}</span>
      </li>
    {/each}
  </ul>
</section>

<style>
  .turnout {
    padding: 16px 0 4px;
  }
  .top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }
  h2 {
    margin: 0;
    font-size: var(--t-md);
    font-weight: 700;
  }
  .top p {
    margin: 0;
    color: var(--ink-2);
    font-size: var(--t-sm);
  }
  .top strong {
    color: var(--ink);
    font-size: var(--t-md);
  }
  .bar {
    display: block;
    width: 100%;
    height: 12px;
    margin: 9px 0 8px;
    border-radius: 3px;
    overflow: hidden;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 3px 18px;
    font-size: var(--t-sm);
  }
  li {
    display: grid;
    grid-template-columns: 10px 1fr auto auto;
    align-items: center;
    gap: 7px;
    color: var(--ink-2);
  }
  .sw {
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }
  .v {
    color: var(--ink);
  }
  .p {
    color: var(--muted);
    min-width: 42px;
    text-align: right;
  }
  @media (max-width: 420px) {
    ul {
      grid-template-columns: 1fr;
    }
  }
</style>
