<script lang="ts">
  import type { Cand } from '../lib/data';
  import { SWATCH } from '../lib/colors';

  let { c, size = 40 }: { c: Cand; size?: number } = $props();
  let broken = $state(false);
  const initials = $derived(
    (c.nome ?? '?')
      .split(' ')
      .filter((w) => w.length > 2)
      .slice(0, 2)
      .map((w) => w[0])
      .join(''),
  );
</script>

<span class="ph" style:width="{size}px" style:height="{size}px" style:--ring={SWATCH[c.cor ?? 'g']}>
  {#if c.foto && c.sq && !broken}
    <img src="/data/fotos/{c.sq}.webp" alt="" loading="lazy" onerror={() => (broken = true)} />
  {:else}
    <span class="ini" style:font-size="{size * 0.38}px">{initials}</span>
  {/if}
</span>

<style>
  .ph {
    flex: none;
    display: inline-grid;
    place-items: center;
    border-radius: 50%;
    overflow: hidden;
    background: #e3e7e2;
    box-shadow: 0 0 0 2px var(--sheet), 0 0 0 4px var(--ring);
  }
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: 50% 20%;
  }
  .ini {
    font-weight: 700;
    color: var(--ink-2);
  }
</style>
