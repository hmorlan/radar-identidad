<script lang="ts">
	const currentYear = new Date().getFullYear();
</script>

<footer class="bg-radar-dark text-white mt-auto">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<div class="flex flex-col md:flex-row items-center justify-between gap-4">
			<div class="flex items-center gap-3">
				<img src="/assets/logo.svg" alt="" class="w-8 h-8 rounded-full" />
				<div>
					<p class="font-medium">Radar de Identidad</p>
					<p class="text-sm text-radar-gray-400">
						Identidad digital, IA y ciberseguridad, en español
					</p>
				</div>
			</div>

			<div class="flex items-center gap-6 text-sm text-radar-gray-400">
				<span>&copy; {currentYear} Hiram Morlan</span>
				<a href="/about" class="hover:text-white transition-colors">Acerca de</a>
				<a href="/feeds" class="hover:text-white transition-colors">RSS</a>
			</div>
		</div>

		<div class="border-t border-radar-gray-700 mt-4 pt-4">
			<p class="text-xs text-radar-gray-500 text-center">
				Contenido curado y redactado con apoyo de IA a partir de fuentes públicas, con revisión editorial.
				Puede contener errores: cada nota enlaza a su fuente original.
				<a href="/about" class="hover:text-radar-gray-400 underline">Cómo funciona</a>
			</p>
		</div>
	</div>
</footer>
