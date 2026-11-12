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
	<h1 class="font-display font-medium text-[40px] sm:text-[48px] leading-tight text-tinta">Archivo</h1>
	<p class="font-serif italic text-[17px] text-tinta-suave mt-2 mb-8" id="semana">
		Mosaico entre semana, grabado los domingos. Las columnas de «La semana en identidad»
		llevan su distintivo dorado.
	</p>

	{#if loading}
		<div class="py-20">
			<LoadingSpinner size="lg" />
		</div>
	{:else}
		<div class="grid gap-10 lg:grid-cols-[minmax(0,1fr)_300px]">
			<div>
				<h2 class="t-kicker text-oro mb-4">Reportes disponibles ({$availableDates.length})</h2>

				{#if !weeks.length}
					<p class="font-serif text-tinta-suave">Todavía no hay ediciones publicadas.</p>
				{:else}
					{#each weeks as week (week.start)}
						<section class="border-t border-filete pt-5 pb-6">
							<h3 class="t-label text-tinta-suave mb-3">{weekLabel(week.start)}</h3>
							<ul class="flex flex-col gap-3">
								{#each week.entries as entry (entry.date)}
									<li>
										<a href="/?date={entry.date}" class="group flex items-baseline gap-4 no-underline">
											<span class="t-ui !text-[10.5px] text-tinta-suave w-[86px] flex-none">{shortLabel(entry.date)}</span>
											<span class="font-display font-medium text-[21px] leading-snug text-tinta group-hover:underline decoration-oro decoration-1 underline-offset-4">
												{entry.titular || `Edición del ${shortLabel(entry.date).toLowerCase()}`}
											</span>
											{#if isSunday(entry)}
												<span class="t-label text-oro border border-oro px-1.5 py-0.5 flex-none">La semana</span>
											{/if}
										</a>
									</li>
								{/each}
							</ul>
						</section>
					{/each}
				{/if}
			</div>

			<aside class="lg:pt-9">
				<Calendar on:select={handleDateSelect} />
			</aside>
		</div>
	{/if}
</div>
