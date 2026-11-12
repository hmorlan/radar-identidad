<script lang="ts">
	import { isDark, toggleTheme } from '$lib/stores/themeStore';
</script>

<!-- v3.2 §3: accesos discretos en texto (RSS / Buscar / Modo), sin iconos sueltos. -->
<button
	type="button"
	on:click={toggleTheme}
	class="acceso"
	aria-label={$isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
	title={$isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
>
	Modo
</button>

<style>
	.acceso {
		font: 500 11px/1.4 'Inter', system-ui, sans-serif;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: rgb(var(--tinta-suave));
		background: none;
		border: 0;
		padding: 4px 0;
		cursor: pointer;
	}
	.acceso:hover {
		color: rgb(var(--tinta));
	}
</style>
