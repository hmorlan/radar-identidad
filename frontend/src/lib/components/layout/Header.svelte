<script lang="ts">
	import { currentDate } from '$lib/stores/dateStore';
	import { formatDate, formatDayOfWeek } from '$lib/services/dateUtils';
	import ThemeToggle from './ThemeToggle.svelte';
	import SearchBar from '$lib/components/search/SearchBar.svelte';

	$: dateDisplay = $currentDate
		? `${capitalize(formatDayOfWeek($currentDate))} ${formatDate($currentDate)}`
		: '';

	function capitalize(s: string): string {
		return s ? s[0].toUpperCase() + s.slice(1) : s;
	}

	let showSearch = false;
</script>

<!-- v3.2 §3.1: cabecera clara sobre papel, sin barra negra. Wordmark centrado,
     fecha y accesos discretos arriba. -->
<header class="bg-papel">
	<div class="max-w-[1080px] mx-auto px-4 sm:px-6 pt-3.5 flex items-center justify-between gap-4 t-ui !text-[11px] text-tinta-suave">
		<a href="/archive" class="hidden sm:inline no-underline hover:text-tinta">{dateDisplay}</a>
		<a href="/" class="sm:hidden t-wordmark font-wordmark text-[15px] !tracking-[0.26em] text-tinta no-underline" aria-label="Radar de Identidad, inicio">
			Radar de Identidad
		</a>
		<span class="flex items-center gap-5 sm:gap-6">
			<a href="/feeds" class="hidden sm:inline no-underline hover:text-tinta">RSS</a>
			<button
				type="button"
				on:click={() => (showSearch = !showSearch)}
				class="acceso"
				aria-expanded={showSearch}
			>Buscar</button>
			<ThemeToggle />
		</span>
	</div>

	<div class="hidden sm:flex flex-col items-center gap-2 px-6 pt-5 pb-4 text-center">
		<a href="/" class="t-wordmark font-wordmark text-[28px] lg:text-[34px] text-tinta no-underline" aria-label="Radar de Identidad, inicio">
			Radar de Identidad
		</a>
		<span class="font-serif italic text-[15px] text-tinta-suave">
			En quién y en qué confiar: identidad digital, IA y ciberseguridad
		</span>
	</div>

	{#if showSearch}
		<div class="max-w-[760px] mx-auto px-4 sm:px-6 pb-4">
			<SearchBar on:select={() => (showSearch = false)} />
		</div>
	{/if}
</header>

<style>
	.acceso {
		font: inherit;
		letter-spacing: inherit;
		text-transform: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: 4px 0;
		cursor: pointer;
	}
	.acceso:hover {
		color: rgb(var(--tinta));
	}
</style>
