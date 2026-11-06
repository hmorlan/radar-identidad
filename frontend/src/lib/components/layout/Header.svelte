<script lang="ts">
	import { currentDate } from '$lib/stores/dateStore';
	import { formatDate } from '$lib/services/dateUtils';
	import ThemeToggle from './ThemeToggle.svelte';
	import SearchBar from '$lib/components/search/SearchBar.svelte';

	$: dateDisplay = $currentDate ? formatDate($currentDate) : '';

	let showSearch = false;
</script>

<!-- Barra superior: se queda oscura en ambos modos (hero-ground / hero-ink). -->
<header class="bg-hero-ground text-hero-ink border-b border-white/10">
	<div class="max-w-7xl mx-auto px-4 sm:px-10 py-4">
		<div class="flex items-center justify-between gap-3">
			<a href="/" class="min-w-0 hover:opacity-90 transition-opacity" aria-label="Radar de Identidad, inicio">
				<span class="t-wordmark block truncate">Radar de Identidad</span>
				<span class="hidden sm:block t-meta text-white/60 mt-1">
					En quién y en qué confiar: identidad digital, IA y ciberseguridad
				</span>
			</a>

			<div class="flex items-center gap-2 sm:gap-3 flex-none">
				{#if dateDisplay}
					<a href="/archive" class="hidden md:block t-meta text-white/70 hover:text-white transition-colors px-2">
						{dateDisplay}
					</a>
				{/if}

				<a
					href="/feeds"
					class="icon-btn"
					aria-label="Feeds RSS"
					title="Suscríbete por RSS"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="w-[18px] h-[18px]" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
						<circle cx="6.18" cy="17.82" r="2.18"/>
						<path d="M4 4.44v2.83c7.03 0 12.73 5.7 12.73 12.73h2.83c0-8.59-6.97-15.56-15.56-15.56zm0 5.66v2.83c3.9 0 7.07 3.17 7.07 7.07h2.83c0-5.47-4.43-9.9-9.9-9.9z"/>
					</svg>
				</a>

				<button on:click={() => (showSearch = !showSearch)} class="icon-btn" aria-label="Buscar" aria-expanded={showSearch}>
					<svg xmlns="http://www.w3.org/2000/svg" class="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
						<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
					</svg>
				</button>

				<ThemeToggle />
			</div>
		</div>

		{#if showSearch}
			<div class="mt-4 pt-4 border-t border-white/10">
				<SearchBar on:select={() => (showSearch = false)} />
			</div>
		{/if}
	</div>
</header>

<style>
	.icon-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 38px;
		height: 38px;
		border-radius: 999px;
		border: 1px solid rgb(255 255 255 / 0.14);
		color: #f1f2f4;
		transition: border-color 150ms, background-color 150ms;
	}
	.icon-btn:hover {
		border-color: rgb(255 255 255 / 0.32);
		background: rgb(255 255 255 / 0.06);
	}
	.icon-btn:focus-visible {
		outline: 2px solid #4fc3ff;
		outline-offset: 2px;
	}
</style>
