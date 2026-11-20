<script lang="ts">
	import { isDark, toggleTheme } from '$lib/stores/themeStore';

	$: etiqueta = $isDark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro';
</script>

<!-- Tema claro/oscuro (20 nov): un icono en vez de la palabra "Modo". En claro se ve
     la luna (lleva a oscuro); en oscuro, el sol (lleva a claro). Trazo fino, mismo
     color discreto que los accesos de texto (RSS / Buscar). -->
<button type="button" on:click={toggleTheme} class="acceso" aria-label={etiqueta} title={etiqueta}>
	{#if $isDark}
		<svg viewBox="0 0 24 24" aria-hidden="true">
			<circle cx="12" cy="12" r="4.2" />
			<path
				d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"
			/>
		</svg>
	{:else}
		<svg viewBox="0 0 24 24" aria-hidden="true">
			<path d="M20.2 14.6A8.4 8.4 0 0 1 9.4 3.8a8.4 8.4 0 1 0 10.8 10.8Z" />
		</svg>
	{/if}
</button>

<style>
	.acceso {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: rgb(var(--tinta-suave));
		background: none;
		border: 0;
		padding: 4px;
		margin: -4px 0;
		cursor: pointer;
		line-height: 0;
	}
	.acceso:hover,
	.acceso:focus-visible {
		color: rgb(var(--oro));
	}
	svg {
		width: 16px;
		height: 16px;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.5;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
</style>
