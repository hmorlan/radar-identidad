<!--
	Página de error en español. Sin ella, SvelteKit mostraba su "404 Not Found"
	en inglés (el sitio usa index.html como fallback, así que toda ruta
	desconocida termina aquí).
-->
<script lang="ts">
	import { page } from '$app/stores';

	$: noEncontrada = $page.status === 404;
</script>

<svelte:head>
	<title>{noEncontrada ? 'Página no encontrada' : 'Error'} | Radar de Identidad</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<section class="max-w-[760px] mx-auto px-4 py-16 text-center">
	<p class="t-kicker text-oro">{noEncontrada ? 'Error 404' : `Error ${$page.status}`}</p>
	<h1 class="t-display-hero text-tinta mt-3">
		{noEncontrada ? 'Esta página no existe' : 'Algo salió mal'}
	</h1>
	<p class="text-tinta-suave mt-3">
		{noEncontrada
			? 'Puede que el enlace esté mal escrito o que la página se haya movido.'
			: 'No pudimos mostrar esta página. Inténtalo de nuevo en un momento.'}
	</p>
	<p class="mt-6 flex flex-wrap justify-center gap-x-6 gap-y-2 t-ui">
		<a class="text-oro hover:underline" href="/">Edición más reciente</a>
		<a class="text-oro hover:underline" href="/archive">Archivo</a>
	</p>
</section>
