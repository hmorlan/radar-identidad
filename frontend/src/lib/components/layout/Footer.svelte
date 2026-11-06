<script lang="ts">
	const currentYear = new Date().getFullYear();
</script>

<footer class="bg-hero-ground text-hero-ink border-t border-white/10 mt-auto">
	<div class="max-w-7xl mx-auto px-4 sm:px-10 py-10">
		<div class="flex flex-col md:flex-row md:items-end justify-between gap-6">
			<div>
				<p class="t-wordmark">Radar de Identidad</p>
				<p class="t-meta text-white/60 mt-2">
					Identidad digital, IA y ciberseguridad, en español
				</p>
			</div>

			<nav class="flex items-center gap-6 t-meta text-white/70" aria-label="Pie de página">
				<a href="/about" class="hover:text-white transition-colors">Acerca de</a>
				<a href="/archive" class="hover:text-white transition-colors">Archivo</a>
				<a href="/feeds" class="hover:text-white transition-colors">RSS</a>
				<span>&copy; {currentYear} Hiram Morlan</span>
			</nav>
		</div>

		<p class="t-meta text-white/50 mt-8 pt-6 border-t border-white/10">
			Contenido curado y redactado con apoyo de IA a partir de fuentes públicas, con una segunda
			pasada de verificación contra la fuente. Puede contener errores: cada nota enlaza a su fuente
			original. <a href="/about" class="underline hover:text-white/80">Cómo funciona</a>
		</p>
	</div>
</footer>
