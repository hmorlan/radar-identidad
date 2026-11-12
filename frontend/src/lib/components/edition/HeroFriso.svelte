<!--
	Imagen de la edición (v3.2 §3.2, §4.1, §6.3, §6.6).
	- Diario: friso a todo el ancho (300px; 210px en móvil) entre doble filete, con un
	  solo paneo al cargar que termina en el punto focal.
	- Domingo / grabado: dentro de la columna de 760px, ~330px, con multiply en claro.
	Las dos variantes (clara y oscura derivada) se intercambian con el modo.
-->
<script lang="ts">
	import type { HeroImage } from '$lib/types';
	import { safeFocus } from './editionUtils';

	export let hero: HeroImage;
	export let dateLabel = '';
	export let domingo = false;

	$: tecnica = hero.tecnica ?? (domingo ? 'grabado' : 'mosaico');
	$: focus = safeFocus(hero.focus);
	$: tecnicaTexto =
		tecnica === 'grabado' ? 'grabado al buril' : 'mosaico romano con circuitos de oro';
	$: modelo = hero.modelo || 'Gemini 3 Pro Image';
	$: credito = [
		`${hero.motivo ? hero.motivo + ': ' : ''}${tecnicaTexto}`,
		hero.archivo ? `Imagen de archivo, generada con ${modelo}` : `Imagen generada con ${modelo}`,
		dateLabel ? `Edición del ${dateLabel}` : ''
	]
		.filter(Boolean)
		.join(' · ');
	$: creditoOscuro = credito.replace(tecnicaTexto, `${tecnicaTexto}, variante oscura para modo nocturno`);
	$: enColumna = domingo || tecnica === 'grabado';
</script>

<figure class="hero {enColumna ? 'columna' : 'friso'} {tecnica}" style="--foco: {focus}">
	<div class="marco">
		<img class="img-light" src={hero.light_url} alt={hero.alt ?? ''} decoding="async" />
		{#if hero.dark_url}
			<img class="img-dark" src={hero.dark_url} alt="" aria-hidden="true" decoding="async" />
		{/if}
	</div>
	<figcaption class="credito">
		<span class="cred-light">{credito}</span>
		{#if hero.dark_url}<span class="cred-dark">{creditoOscuro}</span>{/if}
	</figcaption>
</figure>

<style>
	.hero {
		margin: 0;
	}
	img {
		display: block;
		width: 100%;
		object-fit: cover;
		object-position: var(--foco);
	}
	.img-dark,
	.cred-dark {
		display: none;
	}
	:global(html.dark) .hero:has(.img-dark) .img-light,
	:global(html.dark) .hero:has(.img-dark) .cred-light {
		display: none;
	}
	:global(html.dark) .img-dark,
	:global(html.dark) .cred-dark {
		display: block;
	}

	/* Friso del diario: doble filete de 1px en tinta con 8px de aire. */
	.friso .marco {
		border-top: 1px solid rgb(var(--tinta));
		border-bottom: 1px solid rgb(var(--tinta));
		padding: 8px 0;
	}
	.friso img {
		height: 300px;
		animation: paneo 4s ease-out 1 both;
	}
	@keyframes paneo {
		from {
			object-position: 15% 45%;
		}
		to {
			object-position: var(--foco);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.friso img {
			animation: none;
		}
	}
	@media (max-width: 680px) {
		.friso img {
			height: 210px;
		}
	}

	/* Domingo o grabado: dentro de la columna, impreso sobre el papel. */
	.columna {
		max-width: 760px;
		margin: 0 auto;
		padding: 0 16px;
	}
	.columna img {
		height: 330px;
	}
	.grabado .img-light {
		mix-blend-mode: multiply;
	}
	@media (max-width: 680px) {
		.columna img {
			height: 210px;
		}
	}

	/* Crédito tipo museo (§4.1). */
	.credito {
		max-width: 1080px;
		margin: 0 auto;
		background: rgb(var(--caja));
		padding: 10px 16px;
		font: italic 13.5px/1.5 'Newsreader', Georgia, serif;
		color: rgb(var(--tinta-suave));
	}
	.columna .credito {
		max-width: 760px;
	}
</style>
