<!--
	Radar de Identidad — vista "Editorial" de una edición.
	Hero a pantalla completa (se queda oscuro en ambos modos), notas numeradas en
	una columna y barra lateral con el resumen, los temas y el análisis semanal.
	Todo el texto de las notas se pinta como texto (nunca HTML).
-->
<script lang="ts">
	import type { DaySummary, Category, EditionNote } from '$lib/types';
	import { CATEGORY_CONFIG } from '$lib/types';
	import { formatDate, formatDayOfWeek } from '$lib/services/dateUtils';
	import { safeHtml } from '$lib/services/safeHtml';
	import { isSafeUrl } from '$lib/services/sanitize';
	import DateNavigator from '$lib/components/calendar/DateNavigator.svelte';

	export let summary: DaySummary;
	export let heroImageUrl: string | null = null;
	export let categoryHref: (category: Category) => string;
	export let validCategories: Category[] = [];
	export let executiveSummaryHtml = '';

	const SIGNAL_LABEL: Record<string, string> = { alta: 'Señal alta', media: 'Señal media', baja: 'Señal baja' };
	const VERIFICATION_LABEL: Record<string, string> = {
		verificada: 'Verificada contra la fuente',
		corregida: 'Corregida tras verificar la fuente',
		sin_verificar: 'Sin verificación automática'
	};

	$: notes = (summary.edition?.notas ?? []) as EditionNote[];
	$: weekday = formatDayOfWeek(summary.date);
	$: kicker = `Edición del ${weekday} · ${formatDate(summary.date)}`;
	$: headline = summary.edition?.titular || notes[0]?.title || 'La edición de hoy';
	$: wordCount = notes.reduce(
		(n, note) => n + `${note.que_paso} ${note.por_que_importa} ${note.pregunta_de_fondo ?? ''}`.split(/\s+/).length,
		0
	);
	$: readingMinutes = Math.max(1, Math.round(wordCount / 220));
	$: topics = summary.top_topics ?? [];

	function pad(n: number): string {
		return String(n).padStart(2, '0');
	}

	function host(url: string): string {
		try {
			return new URL(url).hostname.replace(/^www\./, '');
		} catch {
			return '';
		}
	}
</script>

<!-- HERO -->
<section class="hero" aria-label="Portada de la edición">
	{#if heroImageUrl}
		<img class="hero-img" src={heroImageUrl} alt="" />
	{/if}
	<div class="hero-shade"></div>
	<div class="hero-content max-w-7xl mx-auto px-4 sm:px-10">
		<p class="t-kicker hero-kicker">{kicker}</p>
		<h1 class="t-display-hero hero-title">{headline}</h1>
		<p class="t-meta hero-meta">
			{notes.length ? `${notes.length} notas · ${readingMinutes} min de lectura · ` : ''}{summary.total_items_analyzed} fuentes revisadas
		</p>
	</div>
</section>

<div class="max-w-7xl mx-auto px-4 sm:px-10">
	<div class="py-5 border-b border-line">
		<DateNavigator coverageDate={summary.coverage_date} />
	</div>

	<div class="grid lg:grid-cols-[minmax(0,1fr)_340px] gap-x-14 gap-y-10 py-10">
		<!-- NOTAS -->
		<div>
			{#if notes.length}
				<p class="t-label text-electric mb-2">Las notas</p>
				<ol class="list-none p-0 m-0">
					{#each notes as note, i (note.item_id)}
						<li id="nota-{note.item_id}" class="note">
							<div class="t-numeral note-num" class:note-num-high={note.senal === 'alta'}>{pad(i + 1)}</div>
							<div class="min-w-0">
								<div class="flex flex-wrap items-center gap-2 mb-2">
									<span class="chip chip-{note.senal}">{SIGNAL_LABEL[note.senal] ?? note.senal}</span>
									<span class="t-meta text-ink-muted">{note.source}</span>
								</div>
								<h2 class="t-display-note text-ink">{note.title}</h2>

								<p class="t-label text-ink-muted mt-4 mb-1">Qué pasó</p>
								<p class="t-body text-ink-body">
									{note.que_paso}
									{#if isSafeUrl(note.url)}
										<a class="source-link" href={note.url} target="_blank" rel="noopener noreferrer"
											>Fuente: {host(note.url) || note.source}</a
										>
									{/if}
								</p>

								<p class="t-label text-ink-muted mt-4 mb-1">Por qué importa</p>
								<p class="t-body text-ink-body">{note.por_que_importa}</p>

								{#if note.pregunta_de_fondo}
									<div class="question">
										<p class="t-label text-ink-muted mb-1">La pregunta de fondo</p>
										<p class="t-question text-glow">{note.pregunta_de_fondo}</p>
									</div>
								{/if}

								<p class="t-meta text-ink-muted mt-4">
									{VERIFICATION_LABEL[note.verificacion] ?? 'Sin verificación automática'}
								</p>
							</div>
						</li>
					{/each}
				</ol>
			{:else}
				<p class="t-label text-electric mb-3">Resumen de la edición</p>
				<div class="prose-summary max-w-none t-body">
					{@html safeHtml(executiveSummaryHtml)}
				</div>
			{/if}
		</div>

		<!-- BARRA LATERAL -->
		<aside class="space-y-6">
			<section class="box">
				<p class="t-label text-electric mb-3">La semana en identidad</p>
				<p class="t-body text-ink-body">
					Cada domingo, el análisis de fondo de la semana y el guion del video. Próximamente.
				</p>
			</section>

			{#if notes.length && executiveSummaryHtml}
				<section class="box">
					<p class="t-label text-electric mb-3">Resumen de la edición</p>
					<div class="prose-summary sidebar-prose max-w-none">
						{@html safeHtml(executiveSummaryHtml)}
					</div>
				</section>
			{/if}

			{#if topics.length}
				<section class="box">
					<p class="t-label text-electric mb-3">Temas</p>
					<ul class="flex flex-wrap gap-2 list-none p-0 m-0">
						{#each topics as topic}
							<li class="tag" title={topic.description}>{topic.name}</li>
						{/each}
					</ul>
				</section>
			{/if}

			{#if validCategories.length}
				<section class="box">
					<p class="t-label text-electric mb-3">Todo lo revisado</p>
					<ul class="list-none p-0 m-0 divide-y divide-line">
						{#each validCategories as category}
							{@const cat = summary.categories[category]}
							{#if cat}
								<li>
									<a class="flex justify-between py-2 t-body text-ink hover:text-electric transition-colors" href={categoryHref(category)}>
										<span>{CATEGORY_CONFIG[category].title}</span>
										<span class="t-meta text-ink-muted">{cat.count}</span>
									</a>
								</li>
							{/if}
						{/each}
					</ul>
				</section>
			{/if}
		</aside>
	</div>
</div>

<style>
	.hero {
		position: relative;
		min-height: clamp(420px, 68vh, 760px);
		background: #050608;
		display: flex;
		align-items: flex-end;
		overflow: hidden;
	}
	.hero-img {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.hero-shade {
		position: absolute;
		inset: 0;
		background: linear-gradient(
			to top,
			rgb(5 6 8 / 0.96) 0%,
			rgb(5 6 8 / 0.7) 32%,
			rgb(5 6 8 / 0.15) 65%,
			rgb(5 6 8 / 0) 100%
		);
	}
	.hero-content {
		position: relative;
		width: 100%;
		padding-top: 6rem;
		padding-bottom: 3rem;
	}
	.hero-kicker {
		color: #ffd23f; /* signal-gold (oscuro): el hero se queda oscuro en ambos modos */
		margin-bottom: 0.9rem;
	}
	.hero-title {
		color: #f1f2f4;
		max-width: 18ch;
		text-wrap: balance;
	}
	.hero-meta {
		color: #c3c9d1;
		margin-top: 1rem;
	}

	.note {
		display: grid;
		grid-template-columns: 64px minmax(0, 1fr);
		gap: 0 1.25rem;
		padding: 2.25rem 0;
		border-top: 1px solid rgb(var(--line));
	}
	.note:first-child {
		border-top: 0;
		padding-top: 1rem;
	}
	.note-num {
		color: rgb(var(--sapphire));
		padding-top: 0.15rem;
	}
	.note-num-high {
		color: rgb(var(--signal-gold));
	}
	@media (max-width: 640px) {
		.note {
			grid-template-columns: 1fr;
		}
		.note-num {
			font-size: 28px;
			margin-bottom: 0.5rem;
		}
	}

	.chip {
		display: inline-block;
		padding: 0.2rem 0.6rem;
		border-radius: 999px;
		font-size: 11px;
		line-height: 1.4;
		font-weight: 600;
		letter-spacing: 2px;
		text-transform: uppercase;
		border: 1px solid rgb(var(--line));
		color: rgb(var(--ink-muted));
	}
	.chip-alta {
		color: rgb(var(--signal-gold));
		border-color: rgb(var(--signal-gold) / 0.55);
	}
	.chip-media {
		color: rgb(var(--electric-blue));
		border-color: rgb(var(--electric-blue) / 0.5);
	}

	.source-link {
		color: rgb(var(--electric-blue));
		text-decoration: underline;
		text-decoration-color: rgb(var(--electric-blue) / 0.4);
		text-underline-offset: 3px;
		white-space: nowrap;
	}
	.source-link:hover {
		text-decoration-color: rgb(var(--electric-blue));
	}

	.question {
		margin-top: 1.25rem;
		padding: 0.25rem 0 0.25rem 1rem;
		border-left: 2px solid rgb(var(--sapphire));
	}

	.box {
		background: rgb(var(--surface));
		border: 1px solid rgb(var(--line));
		border-radius: 14px;
		padding: 24px;
	}
	.tag {
		padding: 0.25rem 0.6rem;
		border-radius: 6px;
		border: 1px solid rgb(var(--line));
		font-size: 13px;
		color: rgb(var(--ink-body));
	}
	.sidebar-prose :global(p),
	.sidebar-prose :global(li) {
		font-size: 14px;
	}
</style>
