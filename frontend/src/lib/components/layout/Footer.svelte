<script lang="ts">
	const currentYear = new Date().getFullYear();
</script>

<!-- Colofón (v3.2 §4.7): sobre papel, con filete; sin barra negra. -->
<footer class="mt-auto bg-papel border-t border-filete">
	<div class="max-w-[760px] mx-auto px-4 sm:px-6 py-10 flex flex-col gap-4">
		<div class="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-3">
			<a href="/" class="t-wordmark font-wordmark text-[15px] text-tinta no-underline">Radar de Identidad</a>
			<nav class="flex flex-wrap items-center gap-x-6 gap-y-2 t-ui !text-[11px] text-tinta-suave" aria-label="Pie de página">
				<a href="/about" class="no-underline hover:text-tinta">Acerca de</a>
				<a href="/archive" class="no-underline hover:text-tinta">Archivo</a>
				<a href="/feeds" class="no-underline hover:text-tinta">RSS</a>
				<span>&copy; {currentYear} Hiram Morlán</span>
			</nav>
		</div>
		<p class="font-serif italic text-[14px] leading-relaxed text-tinta-suave">
			Curaduría asistida por IA y revisada por Hiram Morlán, solo con fuentes públicas. Cada nota
			pasa por una segunda verificación contra su fuente y enlaza al original; aun así puede contener
			errores. <a href="/about" class="enlace">Cómo funciona</a>
		</p>
	</div>
</footer>
