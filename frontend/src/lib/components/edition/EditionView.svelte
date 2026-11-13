<!--
	Radar de Identidad — vista de una edición, dirección v3.2 "mármol, tinta y oro"
	(docs/identidad-visual.md). Una sola columna centrada, sin barra lateral.
	Orden: friso → kicker, titular y metadatos → En 60 segundos → notas →
	navegación entre ediciones → franja humana → Cada domingo → temas y todo lo
	revisado → suscripción. El colofón va en el pie global.
	Todo el texto de las notas se pinta como texto (nunca HTML).
-->
<script lang="ts">
	import type { DaySummary, Category, EditionNote, HeroImage } from '$lib/types';
	import { CATEGORY_CONFIG } from '$lib/types';
	import { formatDate, formatDayOfWeek } from '$lib/services/dateUtils';
	import { safeHtml } from '$lib/services/safeHtml';
	import { isSafeUrl } from '$lib/services/sanitize';
	import { dataUrl } from '$lib/services/dataBase';
	import DateNavigator from '$lib/components/calendar/DateNavigator.svelte';
	import HeroFriso from './HeroFriso.svelte';
	import NotaEdicion from './NotaEdicion.svelte';
	import SelloArmilar from './SelloArmilar.svelte';
	import { LINKEDIN_URL, HUMAN_STRIP } from '$lib/config/site';

	export let summary: DaySummary;
	export let heroImageUrl: string | null = null;
	export let categoryHref: (category: Category) => string;
	export let validCategories: Category[] = [];
	export let executiveSummaryHtml = '';

	/** Notas completas al inicio; el resto, colapsadas con su numeral (§3.4). */
	const EXPANDED = 2;

	$: notes = (summary.edition?.notas ?? []) as EditionNote[];
	$: domingo = summary.edition?.tipo === 'domingo';
	$: weekday = formatDayOfWeek(summary.date);
	$: dateLong = formatDate(summary.date);
	$: kicker = domingo
		? `La semana en identidad · ${capitalize(weekday)} ${dateLong}`
		: `Edición del ${weekday} · ${dateLong}`;
	$: headline = summary.edition?.titular || notes[0]?.title || 'La edición de hoy';
	$: wordCount = notes.reduce(
		(n, note) => n + `${note.que_paso} ${note.por_que_importa} ${note.pregunta_de_fondo ?? ''}`.split(/\s+/).length,
		0
	);
	$: readingMinutes = Math.max(1, Math.round(wordCount / 220));
	$: meta = [
		notes.length ? `${notes.length} notas` : '',
		notes.length ? `${readingMinutes} min` : '',
		`${summary.total_items_analyzed} notas analizadas`
	]
		.filter(Boolean)
		.join(' · ');
	// "En 60 segundos" (§3.3): una línea por cada una de las primeras notas.
	$: sesenta = notes.slice(0, 4).map((n) => n.title);
	$: topics = summary.top_topics ?? [];
	$: hero = buildHero(summary, heroImageUrl);

	function capitalize(s: string): string {
		return s ? s[0].toUpperCase() + s.slice(1) : s;
	}

	function buildHero(s: DaySummary, legacyUrl: string | null): HeroImage | null {
		const h = s.hero_image;
		if (h?.light_url) {
			return {
				...h,
				light_url: dataUrl(h.light_url),
				dark_url: h.dark_url ? dataUrl(h.dark_url) : undefined
			};
		}
		return legacyUrl ? { light_url: legacyUrl, modelo: s.image_model_display } : null;
	}
</script>

{#if hero}
	<HeroFriso {hero} dateLabel={dateLong} {domingo} />
{/if}

<section class="encabezado-edicion">
	{#if domingo}
		<SelloArmilar />
	{/if}
	<span class="t-kicker text-oro">{kicker}</span>
	<h1 class="titular">{headline}</h1>
	<span class="t-ui !text-[11.5px] text-tinta-suave">{meta}</span>
</section>

{#if notes.length}
	{#if sesenta.length >= 3}
		<section class="columna sesenta" aria-labelledby="sesenta">
			<h2 id="sesenta" class="t-kicker text-oro">En 60 segundos</h2>
			<ul>
				{#each sesenta as linea}
					<li><span class="rombo" aria-hidden="true">◆</span><span>{linea}</span></li>
				{/each}
			</ul>
		</section>
	{/if}

	<div class="notas">
		{#each notes as note, i (note.item_id)}
			<NotaEdicion {note} index={i} collapsed={i >= EXPANDED} />
		{/each}
	</div>
{:else}
	<section class="columna resumen">
		<h2 class="t-kicker text-oro mb-3">Resumen de la edición</h2>
		<div class="prose-summary t-body">
			{@html safeHtml(executiveSummaryHtml)}
		</div>
	</section>
{/if}

<div class="columna navegador">
	<DateNavigator coverageDate={summary.coverage_date} />
</div>

<!-- Franja humana (§4.9) -->
<section class="columna franja">
	<div class="franja-media">
		{#if HUMAN_STRIP.kind !== 'placeholder' && HUMAN_STRIP.src}
			<img src={HUMAN_STRIP.src} alt={HUMAN_STRIP.alt ?? ''} />
		{:else}
			<span class="play" aria-hidden="true">▶</span>
			<span class="t-label text-tinta-suave aqui">Aquí va tu foto o el video de la semana</span>
		{/if}
	</div>
	<div class="franja-texto">
		<span class="t-kicker text-oro">En cámara esta semana</span>
		<span class="frase">{HUMAN_STRIP.frase}</span>
		{#if HUMAN_STRIP.enlace && isSafeUrl(HUMAN_STRIP.enlace)}
			<a class="t-ui text-oro no-underline hover:underline" href={HUMAN_STRIP.enlace} target="_blank" rel="noopener noreferrer">Ver en LinkedIn →</a>
		{/if}
	</div>
</section>

<!-- Caja "Cada domingo" (§4.7) -->
{#if !domingo}
	<section class="columna domingo-caja">
		<SelloArmilar />
		<div class="flex flex-col gap-2">
			<span class="t-kicker text-oro">Cada domingo</span>
			<span class="frase">La semana en identidad: el análisis de fondo, firmado</span>
			<span class="t-ui text-tinta-suave">Próximamente</span>
		</div>
	</section>
{/if}

<!-- Temas y todo lo revisado (§3.7: al pie, sin barra lateral) -->
<section class="columna pie-edicion">
	{#if topics.length}
		<p>
			<span class="t-label">Temas de la edición:</span>
			{#each topics as topic, i}
				<span title={topic.description}>{topic.name}</span>{i < topics.length - 1 ? ' · ' : ''}
			{/each}
		</p>
	{/if}
	{#if validCategories.length}
		<p>
			<span class="t-label">Todo lo revisado:</span>
			{#each validCategories as category, i}
				{@const cat = summary.categories[category]}
				{#if cat}
					<a class="enlace" href={categoryHref(category)}>{CATEGORY_CONFIG[category].title} ({cat.count})</a>{i < validCategories.length - 1 ? ' · ' : ''}
				{/if}
			{/each}
		</p>
	{/if}
</section>

<!-- Suscripción (§4.10) -->
<section class="columna suscripcion">
	<span class="frase">Recibe el radar lunes, miércoles y viernes</span>
	<span class="flex gap-3">
		{#if LINKEDIN_URL && isSafeUrl(LINKEDIN_URL)}
			<a class="boton-solido" href={LINKEDIN_URL} target="_blank" rel="noopener noreferrer">Seguir en LinkedIn</a>
		{/if}
		<a class="boton-contorno" href="/feeds">RSS</a>
	</span>
</section>

<style>
	.columna {
		max-width: 760px;
		margin-left: auto;
		margin-right: auto;
		padding-left: 16px;
		padding-right: 16px;
	}
	.encabezado-edicion {
		max-width: 900px;
		margin: 0 auto;
		padding: 44px 16px 10px;
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 14px;
	}
	.titular {
		margin: 0;
		font: 500 48px/1.1 'Cormorant Garamond', Georgia, serif;
		color: rgb(var(--tinta));
		text-wrap: balance;
	}
	.sesenta {
		margin-top: 30px;
		margin-bottom: 10px;
	}
	.sesenta h2 {
		margin: 0 0 14px;
	}
	.sesenta ul {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.sesenta li {
		display: flex;
		font: 400 18px/1.55 'Newsreader', Georgia, serif;
		color: rgb(var(--tinta-cuerpo));
	}
	.rombo {
		color: rgb(var(--oro));
		margin-right: 12px;
	}
	.notas {
		margin-top: 30px;
	}
	.resumen {
		margin-top: 30px;
	}
	.navegador {
		margin-top: 10px;
		padding-top: 22px;
		padding-bottom: 22px;
		border-top: 1px solid rgb(var(--filete));
		border-bottom: 1px solid rgb(var(--filete));
	}
	.frase {
		font: 500 24px/1.2 'Cormorant Garamond', Georgia, serif;
		color: rgb(var(--tinta));
	}
	.franja {
		margin-top: 40px;
		display: grid;
		grid-template-columns: 330px 1fr;
		gap: 28px;
		align-items: center;
	}
	.franja-media {
		position: relative;
		aspect-ratio: 16 / 9;
		background: rgb(var(--piedra));
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
	}
	.franja-media img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.play {
		width: 58px;
		height: 58px;
		border-radius: 50%;
		border: 1px solid rgb(var(--oro));
		display: flex;
		align-items: center;
		justify-content: center;
		color: rgb(var(--oro));
		font-size: 20px;
		padding-left: 4px;
	}
	.aqui {
		position: absolute;
		left: 12px;
		bottom: 10px;
	}
	.franja-texto {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.domingo-caja {
		margin-top: 40px;
		display: flex;
		gap: 24px;
		align-items: center;
		border-top: 1px solid rgb(var(--tinta));
		border-bottom: 1px solid rgb(var(--tinta));
		padding-top: 24px;
		padding-bottom: 24px;
	}
	.pie-edicion {
		margin-top: 40px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		font: 400 14px/1.6 'Newsreader', Georgia, serif;
		color: rgb(var(--tinta-suave));
	}
	.pie-edicion .t-label {
		margin-right: 6px;
	}
	.suscripcion {
		margin-top: 20px;
		margin-bottom: 40px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 20px;
		border-top: 1px solid rgb(var(--filete));
		border-bottom: 1px solid rgb(var(--filete));
		padding-top: 18px;
		padding-bottom: 18px;
	}
	.suscripcion .frase {
		font-size: 22px;
	}
	.boton-solido,
	.boton-contorno {
		font: 600 11.5px/1.4 'Inter', system-ui, sans-serif;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		text-decoration: none;
		padding: 10px 16px;
	}
	.boton-solido {
		color: rgb(var(--papel));
		background: rgb(var(--oro));
	}
	.boton-solido:hover {
		background: rgb(var(--oro-hover));
	}
	.boton-contorno {
		color: rgb(var(--oro));
		border: 1px solid rgb(var(--oro));
		padding: 9px 16px;
	}
	.boton-contorno:hover {
		color: rgb(var(--oro-hover));
	}

	@media (max-width: 680px) {
		.encabezado-edicion {
			padding-top: 26px;
			text-align: left;
			align-items: flex-start;
		}
		.titular {
			font-size: 30px;
		}
		.sesenta li {
			font-size: 16.5px;
		}
		.franja {
			grid-template-columns: 1fr;
		}
		.suscripcion {
			flex-direction: column;
			align-items: flex-start;
		}
	}
</style>
