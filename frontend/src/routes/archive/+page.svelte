<script lang="ts">
	import { goto } from '$app/navigation';
	import { availableDates } from '$lib/stores/dateStore';
	import { loadIndex } from '$lib/services/dataLoader';
	import { dataUrl } from '$lib/services/dataBase';
	import type { DataIndex, DateEntry } from '$lib/types';
	import Calendar from '$lib/components/calendar/Calendar.svelte';
	import LoadingSpinner from '$lib/components/common/LoadingSpinner.svelte';

	let index: DataIndex | null = null;
	let loading = true;

	loadIndex()
		.then((data) => {
			index = data;
			loading = false;
		})
		.catch(() => {
			loading = false;
		});

	function handleDateSelect(event: CustomEvent<{ date: string }>) {
		goto(`/?date=${event.detail.date}`);
	}

	const DIAS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
	const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
	const MESES_LARGOS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

	function parse(date: string): Date {
		const [y, m, d] = date.split('-').map(Number);
		return new Date(Date.UTC(y, m - 1, d));
	}

	/** Lunes de la semana (las semanas del radar van de lunes a domingo). */
	function weekStart(date: string): string {
		const d = parse(date);
		const offset = (d.getUTCDay() + 6) % 7;
		d.setUTCDate(d.getUTCDate() - offset);
		return d.toISOString().slice(0, 10);
	}

	function shortLabel(date: string): string {
		const d = parse(date);
		return `${DIAS[d.getUTCDay()]} ${d.getUTCDate()} ${MESES[d.getUTCMonth()]}`;
	}

	function weekLabel(start: string): string {
		const d = parse(start);
		return `Semana del ${d.getUTCDate()} de ${MESES_LARGOS[d.getUTCMonth()]} de ${d.getUTCFullYear()}`;
	}

	function longLabel(date: string): string {
		const d = parse(date);
		const dias = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
		return `${dias[d.getUTCDay()]} ${d.getUTCDate()} de ${MESES_LARGOS[d.getUTCMonth()]}`;
	}

	let calendarioAbierto = false;

	function isSunday(entry: DateEntry): boolean {
		return entry.tipo === 'domingo';
	}

	$: weeks = groupByWeek(index?.dates ?? []);

	function groupByWeek(dates: DateEntry[]): { start: string; entries: DateEntry[] }[] {
		const map = new Map<string, DateEntry[]>();
		for (const entry of dates) {
			const key = weekStart(entry.date);
			if (!map.has(key)) map.set(key, []);
			map.get(key)!.push(entry);
		}
		return [...map.entries()]
			.sort((a, b) => b[0].localeCompare(a[0]))
			.map(([start, entries]) => ({ start, entries: entries.sort((a, b) => a.date.localeCompare(b.date)) }));
	}
</script>

<svelte:head>
	<title>Archivo | Radar de Identidad</title>
</svelte:head>

<div class="max-w-[1080px] mx-auto px-4 sm:px-6 py-10">
	<div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
		<div>
			<h1 class="font-display font-medium text-[40px] sm:text-[48px] leading-tight text-tinta">Archivo</h1>
			<p class="font-serif italic text-[17px] text-tinta-suave mt-2" id="semana">
				Mosaico entre semana, grabado los domingos. Las columnas de «La semana en identidad»
				llevan su distintivo dorado.
			</p>
		</div>
		<button
			type="button"
			class="t-ui !text-[11px] text-tinta-suave hover:text-tinta self-start sm:self-auto"
			aria-expanded={calendarioAbierto}
			on:click={() => (calendarioAbierto = !calendarioAbierto)}
		>
			{calendarioAbierto ? 'Ocultar calendario' : 'Buscar por fecha'}
		</button>
	</div>

	{#if calendarioAbierto}
		<div class="mt-6 max-w-[320px]">
			<Calendar on:select={handleDateSelect} />
		</div>
	{/if}

	{#if loading}
		<div class="py-20">
			<LoadingSpinner size="lg" />
		</div>
	{:else if !weeks.length}
		<p class="font-serif text-tinta-suave mt-10">Todavía no hay ediciones publicadas.</p>
	{:else}
		<p class="t-kicker text-oro mt-10">Ediciones ({$availableDates.length})</p>
		{#each weeks as week (week.start)}
			<section class="border-t border-filete mt-4 pt-5 pb-8">
				<h2 class="t-label text-tinta-suave mb-5">{weekLabel(week.start)}</h2>
				<ul class="grid gap-x-6 gap-y-9 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
					{#each week.entries as entry (entry.date)}
						<li>
							<a href="/?date={entry.date}" class="group block no-underline">
								<figure class="m-0">
									<div
										class="relative aspect-[21/9] overflow-hidden bg-caja border
											{isSunday(entry) ? 'border-oro' : 'border-filete'}"
									>
										{#if entry.hero_thumb}
											<img
												src={dataUrl(entry.hero_thumb)}
												alt={entry.hero_alt || ''}
												loading="lazy"
												class="w-full h-full object-cover transition-transform duration-500 ease-out
													group-hover:scale-[1.03] motion-reduce:transition-none motion-reduce:group-hover:scale-100"
											/>
										{:else}
											<div class="w-full h-full flex items-center justify-center">
												<span class="t-wordmark font-wordmark text-[13px] text-tinta-suave">Radar de Identidad</span>
											</div>
										{/if}
										{#if isSunday(entry)}
											<span class="absolute top-2 left-2 t-label bg-papel text-oro border border-oro px-1.5 py-0.5">
												La semana
											</span>
										{/if}
									</div>
									<figcaption class="mt-3">
										<span class="block t-ui !text-[10.5px] text-tinta-suave">
											{longLabel(entry.date)}{entry.hero_motivo ? ` · ${entry.hero_motivo}` : ''}
										</span>
										<span
											class="block mt-1 font-display font-medium text-[21px] leading-snug text-tinta
												group-hover:underline decoration-oro decoration-1 underline-offset-4"
										>
											{entry.titular || `Edición del ${shortLabel(entry.date).toLowerCase()}`}
										</span>
									</figcaption>
								</figure>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	{/if}
</div>
