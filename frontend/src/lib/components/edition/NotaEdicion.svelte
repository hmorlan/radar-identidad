<!--
	Una nota de la edición (v3.2 §3.4–3.6, §4.2).
	Numeral romano en oro en su columna lateral, también en las notas colapsadas.
	Las colapsadas muestran señal, titular más chico y "Leer nota →", que la abre en
	el mismo lugar. Todo el texto se pinta como texto (nunca HTML).
-->
<script lang="ts">
	import type { EditionNote } from '$lib/types';
	import { isSafeUrl } from '$lib/services/sanitize';
	import { toRoman, signalDots, host, shortDate, wholeSentences } from './editionUtils';

	export let note: EditionNote;
	export let index: number;
	export let collapsed = false;

	const SIGNAL_LABEL: Record<string, string> = { alta: 'Señal alta', media: 'Señal media', baja: 'Señal baja' };
	const VERIFICACION: Record<string, string> = {
		verificada: 'verificada contra la fuente',
		corregida: 'corregida tras verificar la fuente',
		sin_verificar: 'sin verificación automática'
	};

	let open = !collapsed;
	$: dots = signalDots(note.senal);
	$: alta = note.senal === 'alta';
	$: fuenteTexto = [note.source || host(note.url), shortDate(note.published)].filter(Boolean).join(', ');
	$: id = `nota-${note.item_id}`;
</script>

<article {id} class="nota" class:colapsada={!open}>
	<span class="numeral" aria-hidden="true">{toRoman(index + 1)}</span>
	<div class="cuerpo">
		<span class="senal" class:alta>
			{#each [1, 2, 3] as i}
				<span class="punto" class:lleno={i <= dots}></span>
			{/each}
			<span class="senal-texto">{SIGNAL_LABEL[note.senal] ?? note.senal}</span>
		</span>

		{#if open}
			<h3 class="titulo">{note.title}</h3>

			<div class="encabezado">Qué pasó</div>
			<p class="texto">{wholeSentences(note.que_paso)}</p>

			<div class="encabezado">Por qué importa</div>
			<p class="texto">{wholeSentences(note.por_que_importa)}</p>

			{#if note.pregunta_de_fondo}
				<figure class="pregunta">
					<figcaption class="pk">La pregunta de fondo</figcaption>
					<blockquote>{note.pregunta_de_fondo}</blockquote>
				</figure>
			{/if}

			<p class="fuente">
				Fuente:
				{#if isSafeUrl(note.url)}
					<a class="enlace" href={note.url} target="_blank" rel="noopener noreferrer">{fuenteTexto}</a>
				{:else}
					{fuenteTexto}
				{/if}
				<span class:corregida={note.verificacion === 'corregida'}>
					· {VERIFICACION[note.verificacion] ?? VERIFICACION.sin_verificar}
				</span>
			</p>
		{:else}
			<h3 class="titulo titulo-chico">{note.title}</h3>
			<button type="button" class="leer" aria-controls={id} aria-expanded="false" on:click={() => (open = true)}>
				Leer nota →
			</button>
		{/if}
	</div>
</article>

<style>
	.nota {
		display: grid;
		grid-template-columns: 80px minmax(0, 680px);
		justify-content: center;
		padding: 40px 16px;
		border-top: 1px solid rgb(var(--filete));
	}
	.nota.colapsada {
		padding: 26px 16px;
	}
	.numeral {
		font: 500 34px/1.1 'Cormorant Garamond', Georgia, serif;
		color: rgb(var(--oro));
	}
	.colapsada .numeral {
		font-size: 28px;
	}
	.senal {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font: 400 10.5px/1.4 'Inter', system-ui, sans-serif;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: rgb(var(--tinta-suave));
	}
	.punto {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		border: 1px solid rgb(var(--tinta));
	}
	.punto.lleno {
		background: rgb(var(--tinta));
	}
	.senal.alta {
		color: rgb(var(--oro));
	}
	.senal.alta .punto {
		border-color: rgb(var(--oro));
		background: rgb(var(--oro));
	}
	.senal-texto {
		margin-left: 6px;
	}
	.titulo {
		margin: 10px 0 0;
		font: 500 36px/1.12 'Cormorant Garamond', Georgia, serif;
		color: rgb(var(--tinta));
	}
	.titulo-chico {
		margin-top: 8px;
		font-size: 26px;
		line-height: 1.2;
	}
	.encabezado {
		font: 600 10.5px/1.4 'Inter', system-ui, sans-serif;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: rgb(var(--tinta-suave));
		margin: 18px 0 6px;
	}
	.texto {
		margin: 0;
		font: 400 18.5px/1.65 'Newsreader', Georgia, serif;
		color: rgb(var(--tinta-cuerpo));
		max-width: 68ch;
	}
	/* La pregunta de fondo (§4.2): filete de 1px en oro, sin barra ni fondo. */
	.pregunta {
		border: 1px solid rgb(var(--oro));
		padding: 20px 24px 22px;
		margin: 26px 0 14px;
	}
	.pk {
		font: 600 10.5px/1.4 'Inter', system-ui, sans-serif;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: rgb(var(--oro));
		margin-bottom: 8px;
	}
	.pregunta blockquote {
		margin: 0;
		font: italic 500 24px/1.3 'Cormorant Garamond', Georgia, serif;
		color: rgb(var(--tinta));
	}
	.fuente {
		margin: 14px 0 0;
		font: italic 14px/1.5 'Newsreader', Georgia, serif;
		color: rgb(var(--tinta-suave));
	}
	.corregida {
		color: rgb(var(--terracota));
	}
	.leer {
		align-self: flex-start;
		margin-top: 8px;
		padding: 0;
		background: none;
		border: 0;
		cursor: pointer;
		font: 400 12px/1.4 'Inter', system-ui, sans-serif;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: rgb(var(--oro));
	}
	.leer:hover {
		color: rgb(var(--oro-hover));
		text-decoration: underline;
	}

	/* Móvil (§3.9): numeral encima de la nota, titular 26–30px. */
	@media (max-width: 680px) {
		.nota {
			grid-template-columns: minmax(0, 1fr);
			padding: 26px 16px;
		}
		.numeral {
			font-size: 26px;
		}
		.titulo {
			font-size: 28px;
		}
		.titulo-chico {
			font-size: 23px;
		}
		.texto {
			font-size: 17px;
			line-height: 1.6;
		}
		.pregunta blockquote {
			font-size: 22px;
		}
	}
</style>
