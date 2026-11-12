<script lang="ts">
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { currentDate, navigation, goToPreviousDate, goToNextDate, goToLatestDate } from '$lib/stores/dateStore';
	import { formatDate } from '$lib/services/dateUtils';

	// Optional coverage date prop from parent
	export let coverageDate: string | undefined = undefined;

	$: dateDisplay = $currentDate ? formatDate($currentDate, "EEEE d 'de' MMMM 'de' yyyy") : '';
	$: coverageDisplay = coverageDate ? formatDate(coverageDate, "EEEE d 'de' MMMM 'de' yyyy") : '';
	$: isLatest = !$navigation.hasNext;

	// Read current category from URL to preserve it during navigation
	$: currentCategory = browser ? $page.url.searchParams.get('category') : null;
</script>

<div class="flex items-center justify-between gap-4">
	<!-- Previous button -->
	<button
		on:click={() => goToPreviousDate(currentCategory || undefined)}
		disabled={!$navigation.hasPrevious}
		class="p-2 rounded-lg transition-colors
		       {$navigation.hasPrevious
			? 'text-tinta hover:text-oro'
			: 'text-filete cursor-not-allowed'}"
		aria-label="Edición anterior"
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="w-5 h-5"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
			stroke-width="2"
		>
			<path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
		</svg>
	</button>

	<!-- Date display -->
	<div class="text-center flex-1">
		<div>
			<span class="font-display text-[20px] text-tinta">
				{dateDisplay}
			</span>
			{#if isLatest}
				<span class="ml-2 t-label text-oro border border-oro px-2 py-0.5 align-middle">
					Más reciente
				</span>
			{/if}
		</div>
		{#if coverageDisplay}
			<div class="t-meta text-tinta-suave mt-1">
				Noticias hasta el {coverageDisplay}
			</div>
		{/if}
	</div>

	<!-- Next button -->
	<button
		on:click={() => goToNextDate(currentCategory || undefined)}
		disabled={!$navigation.hasNext}
		class="p-2 rounded-lg transition-colors
		       {$navigation.hasNext
			? 'text-tinta hover:text-oro'
			: 'text-filete cursor-not-allowed'}"
		aria-label="Edición siguiente"
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="w-5 h-5"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
			stroke-width="2"
		>
			<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
		</svg>
	</button>
</div>

{#if !isLatest}
	<div class="text-center mt-2">
		<button
			on:click={() => goToLatestDate(currentCategory || undefined)}
			class="text-sm text-radar-accent hover:text-radar-accent-dark transition-colors"
		>
			Ir a la más reciente &rarr;
		</button>
	</div>
{/if}
