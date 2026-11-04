<script lang="ts">
	import { currentDate } from '$lib/stores/dateStore';
	import { formatDate } from '$lib/services/dateUtils';
	import ThemeToggle from './ThemeToggle.svelte';
	import SearchBar from '$lib/components/search/SearchBar.svelte';

	$: dateDisplay = $currentDate ? formatDate($currentDate) : '';

	let showSearch = false;
</script>

<header class="bg-gradient-to-r from-radar-accent to-radar-accent-dark text-white shadow-lg">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
		<!--
			Mobile geometry, the short version: four 36px icon buttons plus their gaps
			claim ~190px of a 393px viewport. Whatever the brand block is given, it must
			fit in the rest — so it needs `min-w-0` (a flex item defaults to
			`min-width:auto` and refuses to shrink below its content) and a title small
			enough that its longest word fits. At `text-2xl`, "Aggregator" alone is 121px
			against ~109px of space, which is exactly how the title came to sit under the
			search icon.
		-->
		<div class="flex items-center justify-between gap-2 sm:gap-4">
			<div class="flex items-center min-w-0">
				<a href="/" class="flex items-center gap-2 sm:gap-3 min-w-0 hover:opacity-90 transition-opacity">
					<img
						src="/assets/logo.svg"
						alt=""
						class="w-10 h-10 sm:w-12 sm:h-12 flex-none rounded-full"
					/>
					<div class="min-w-0">
						<h1 class="text-lg sm:text-2xl font-bold tracking-tight leading-tight">
							Radar de Identidad
						</h1>
						<p class="text-xs sm:text-sm text-white/80 leading-snug">
							En quién y en qué confiar: identidad digital, IA y ciberseguridad
						</p>
					</div>
				</a>
			</div>

			<div class="flex items-center gap-1.5 sm:gap-4 flex-none">
				{#if dateDisplay}
					<a
						href="/archive"
						class="hidden sm:block text-sm text-white/90 bg-white/10 px-3 py-1.5 rounded-lg hover:bg-white/20 transition-colors"
					>
						{dateDisplay}
					</a>
				{/if}


				<!-- RSS Feed link -->
				<a
					href="/feeds"
					class="p-1.5 sm:p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors flex-none"
					aria-label="Feeds RSS"
					title="Suscríbete por RSS"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-5 h-5"
						fill="currentColor"
						viewBox="0 0 24 24"
					>
						<circle cx="6.18" cy="17.82" r="2.18"/>
						<path d="M4 4.44v2.83c7.03 0 12.73 5.7 12.73 12.73h2.83c0-8.59-6.97-15.56-15.56-15.56zm0 5.66v2.83c3.9 0 7.07 3.17 7.07 7.07h2.83c0-5.47-4.43-9.9-9.9-9.9z"/>
					</svg>
				</a>

				<!-- Search toggle button -->
				<button
					on:click={() => showSearch = !showSearch}
					class="p-1.5 sm:p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors flex-none"
					aria-label="Buscar"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-5 h-5"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="2"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
						/>
					</svg>
				</button>

				<ThemeToggle />
			</div>
		</div>

		<!-- Expandable search bar -->
		{#if showSearch}
			<div class="mt-4 pt-4 border-t border-white/20">
				<SearchBar on:select={() => showSearch = false} />
			</div>
		{/if}
	</div>
</header>

