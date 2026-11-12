<script lang="ts">
	// Feeds Atom del radar (generators/feed_generator.py). Reddit no aparece porque
	// el radar no lo recolecta (API de pago).
	type Feed = { name: string; description: string; url: string };

	const principal: Feed = {
		name: 'La edición completa',
		description:
			'Lo más importante de cada categoría, igual que la portada. Recomendado para la mayoría.',
		url: '/data/feeds/main.xml'
	};

	const resumenes: Feed[] = [
		{
			name: 'Solo el resumen del día',
			description: 'El resumen de cada edición con su imagen. Una entrada por edición.',
			url: '/data/feeds/summaries-executive.xml'
		},
		{
			name: 'Todos los resúmenes',
			description: 'El resumen de la edición y los de cada categoría, sin notas sueltas.',
			url: '/data/feeds/summaries.xml'
		},
		{
			name: 'Resumen de noticias',
			description: 'Solo el resumen diario de la categoría Noticias.',
			url: '/data/feeds/summaries-news.xml'
		},
		{
			name: 'Resumen de investigación y estándares',
			description: 'Solo el resumen diario de investigación y estándares.',
			url: '/data/feeds/summaries-research.xml'
		},
		{
			name: 'Resumen de redes',
			description: 'Solo el resumen diario de lo que se dijo en redes.',
			url: '/data/feeds/summaries-social.xml'
		}
	];

	const categorias: { name: string; description: string; variants: { name: string; url: string; porDefecto?: boolean }[] }[] = [
		{
			name: 'Noticias',
			description: 'Todas las notas de prensa, reguladores y empresas observadas.',
			variants: [{ name: 'Todas', url: '/data/feeds/news.xml', porDefecto: true }]
		},
		{
			name: 'Investigación y estándares',
			description: 'Papers de arXiv, organismos de estándares y análisis de autor.',
			variants: [
				{ name: 'Las 25 principales', url: '/data/feeds/research-25.xml' },
				{ name: 'Las 50 principales', url: '/data/feeds/research-50.xml', porDefecto: true },
				{ name: 'Las 100 principales', url: '/data/feeds/research-100.xml' },
				{ name: 'Todas', url: '/data/feeds/research-full.xml' }
			]
		},
		{
			name: 'Redes',
			description: 'Publicaciones de Bluesky y Mastodon de periodistas y organizaciones independientes.',
			variants: [
				{ name: 'Las 25 principales', url: '/data/feeds/social-25.xml' },
				{ name: 'Las 50 principales', url: '/data/feeds/social-50.xml', porDefecto: true },
				{ name: 'Las 100 principales', url: '/data/feeds/social-100.xml' },
				{ name: 'Todas', url: '/data/feeds/social-full.xml' }
			]
		}
	];
</script>

<svelte:head>
	<title>RSS | Radar de Identidad</title>
</svelte:head>

<div class="max-w-[760px] mx-auto px-4 sm:px-6 py-10">
	<p class="t-kicker text-oro">Suscripción</p>
	<h1 class="t-display-hero text-tinta mt-2">RSS</h1>
	<p class="t-body text-tinta-cuerpo mt-4">
		Recibe el radar en tu lector de RSS. Todos los feeds usan formato Atom e incluyen los
		últimos 7 días.
	</p>

	<section class="mt-10 border border-oro p-5 sm:p-6">
		<p class="t-label text-oro">Recomendado</p>
		<div class="mt-2 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
			<div>
				<h2 class="font-display text-2xl text-tinta">{principal.name}</h2>
				<p class="t-body !text-[16px] text-tinta-suave mt-1">{principal.description}</p>
			</div>
			<a href={principal.url} class="shrink-0 t-ui bg-oro text-papel px-4 py-2 no-underline hover:underline">
				Suscribirse
			</a>
		</div>
	</section>

	<section class="mt-12">
		<h2 class="font-display text-2xl text-tinta">Solo resúmenes</h2>
		<p class="t-body !text-[16px] text-tinta-suave mt-1">Sin notas sueltas: para una lectura rápida.</p>
		<ul class="mt-5 border-t border-filete">
			{#each resumenes as feed}
				<li class="border-b border-filete">
					<a href={feed.url} class="flex items-baseline justify-between gap-4 py-4 no-underline group">
						<span>
							<span class="block font-serif text-[17px] text-tinta group-hover:underline">{feed.name}</span>
							<span class="block t-ui !normal-case !tracking-normal !text-[13px] text-tinta-suave mt-0.5">
								{feed.description}
							</span>
						</span>
						<span class="t-label text-oro shrink-0">RSS</span>
					</a>
				</li>
			{/each}
		</ul>
	</section>

	<section class="mt-12">
		<h2 class="font-display text-2xl text-tinta">Por categoría</h2>
		<p class="t-body !text-[16px] text-tinta-suave mt-1">Elige cuántas notas quieres recibir.</p>
		<div class="mt-5 space-y-6">
			{#each categorias as cat}
				<div class="border-t border-filete pt-4">
					<h3 class="font-serif text-[19px] text-tinta">{cat.name}</h3>
					<p class="t-ui !normal-case !tracking-normal !text-[13px] text-tinta-suave mt-0.5">{cat.description}</p>
					<div class="flex flex-wrap gap-2 mt-3">
						{#each cat.variants as v}
							<a
								href={v.url}
								class="t-ui !text-[12px] px-3 py-1.5 border no-underline hover:underline
									{v.porDefecto ? 'border-oro text-oro' : 'border-filete text-tinta-suave'}"
							>
								{v.name}{v.porDefecto ? ' · sugerido' : ''}
							</a>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</section>

	<section class="mt-12 bg-caja p-5">
		<h2 class="font-serif text-[19px] text-tinta">Cómo suscribirte</h2>
		<ol class="list-decimal list-inside t-body !text-[16px] text-tinta-cuerpo mt-2 space-y-1">
			<li>Abre el enlace del feed que quieras.</li>
			<li>Copia la dirección de la barra del navegador.</li>
			<li>Pégala en tu lector de RSS (Feedly, Inoreader, NetNewsWire u otro).</li>
		</ol>
		<p class="t-ui !normal-case !tracking-normal !text-[13px] text-tinta-suave mt-3">
			Es normal que el navegador muestre el código XML al abrir un feed: solo copia la
			dirección y agrégala a tu lector.
		</p>
	</section>
</div>
