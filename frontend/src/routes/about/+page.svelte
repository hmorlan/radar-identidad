<svelte:head>
	<title>Acerca de | Radar de Identidad</title>
</svelte:head>

<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
	<h1 class="t-display-hero text-ink mb-10">
		Acerca de Radar de Identidad
	</h1>

	<section class="card mb-6">
		<h2 class="t-label text-electric mb-3">Qué es</h2>
		<div class="prose-summary t-body max-w-none">
			<p>
				Un radar de inteligencia en español sobre identidad digital y sobre las noticias de IA y
				ciberseguridad que cambian cómo decidimos en quién o en qué confiar.
			</p>
			<p>
				Casi toda la cobertura seria de identidad está en inglés. Aquí la promesa no es “más
				noticias”, sino criterio: qué pasó, por qué importa y cuál es la pregunta de fondo.
			</p>
		</div>
	</section>

	<section class="card mb-6">
		<h2 class="t-label text-electric mb-3">Qué entra y qué no</h2>
		<div class="prose-summary t-body max-w-none">
			<p>La regla es una sola: <strong>¿la noticia cambia cómo decidimos en quién o en qué confiar?</strong></p>
			<ul>
				<li>Sí: passkeys, OAuth y OpenID; account takeover y fatiga de MFA; deepfakes que pasan la verificación de identidad; agentes de IA que actúan con nuestros accesos; regulación de identidad.</li>
				<li>No: malware genérico, vulnerabilidades sin ángulo de identidad o noticias de IA que no tocan la confianza.</li>
			</ul>
		</div>
	</section>

	<section class="card mb-6">
		<h2 class="t-label text-electric mb-3">Cómo se hace</h2>
		<div class="prose-summary t-body max-w-none">
			<p>
				Cada día se recolectan fuentes públicas: organismos de estándares, prensa especializada,
				blogs técnicos, medios de Latinoamérica e investigación académica. Un pipeline con modelos
				de IA filtra lo relevante, redacta las notas y hace una segunda pasada que contrasta cada
				nota con el texto de su fuente.
			</p>
			<p>
				<strong>La IA puede equivocarse.</strong> Por eso cada nota enlaza a su fuente original:
				verifícala antes de actuar o compartir.
			</p>
		</div>
	</section>

	<section class="card">
		<h2 class="t-label text-electric mb-3">Créditos</h2>
		<div class="prose-summary t-body max-w-none">
			<p>
				Proyecto personal de Hiram Morlán, con fuentes exclusivamente públicas. El código parte del
				proyecto de código abierto
				<a href="https://github.com/flyryan/ai-news-aggregator" target="_blank" rel="noopener noreferrer">ai-news-aggregator</a>
				(licencia Apache 2.0), adaptado para este fin.
			</p>
			<p>
				<strong>Declaración de interés:</strong> el autor trabaja en la industria de identidad digital.
				Este es un proyecto personal; las opiniones son propias. El radar es agnóstico: no usa
				blogs ni comunicados de empresas del sector como fuente, y las empresas solo aparecen
				cuando las cubre una fuente independiente.
			</p>
		</div>
	</section>
</div>
