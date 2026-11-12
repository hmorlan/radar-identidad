<script lang="ts">
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import type { Category } from '$lib/types';

	// Guard searchParams access for prerendering compatibility
	$: pathname = $page.url.pathname;
	$: dateParam = browser ? $page.url.searchParams.get('date') : null;
	$: categoryParam = browser ? $page.url.searchParams.get('category') : null;

	function categoryHref(category: Category): string {
		return dateParam ? `/?date=${dateParam}&category=${category}` : `/?category=${category}`;
	}

	// v3.2 §3: menú centrado bajo un filete. Redes y Reddit siguen accesibles desde
	// "Todo lo revisado" al pie de cada edición.
	$: items = [
		{ label: 'Inicio', short: 'Inicio', href: '/', active: pathname === '/' && !categoryParam },
		{ label: 'Noticias', short: 'Noticias', href: categoryHref('news'), active: categoryParam === 'news' },
		{
			label: 'Investigación y estándares',
			short: 'Investigación',
			href: categoryHref('research'),
			active: categoryParam === 'research'
		},
		{ label: 'Archivo', short: 'Archivo', href: '/archive', active: pathname === '/archive' },
		{ label: 'La semana en identidad', short: 'La semana', href: '/archive#semana', active: false },
		{ label: 'Acerca de', short: 'Acerca de', href: '/about', active: pathname === '/about' }
	];
</script>

<!-- Sticky y siempre opaca (§3.1): nunca translúcida ni con blur. -->
<nav aria-label="Secciones" class="menu">
	<ul class="max-w-[1080px] mx-auto">
		{#each items as item}
			<li>
				<a
					href={item.href}
					class="nav-link whitespace-nowrap {item.active ? 'nav-link-active' : ''}"
					aria-current={item.active ? 'page' : undefined}
				>
					<span class="lg:hidden">{item.short}</span>
					<span class="hidden lg:inline">{item.label}</span>
				</a>
			</li>
		{/each}
	</ul>
</nav>

<style>
	.menu {
		position: sticky;
		top: 0;
		z-index: 50;
		background: rgb(var(--papel));
		border-top: 1px solid rgb(var(--filete));
		border-bottom: 1px solid rgb(var(--filete));
	}
	ul {
		display: flex;
		justify-content: center;
		gap: 30px;
		list-style: none;
		margin: 0 auto;
		padding: 12px 24px;
	}
	/* Móvil (§3.9): scroll horizontal sin barra visible y desvanecido al borde. */
	@media (max-width: 680px) {
		ul {
			justify-content: flex-start;
			gap: 20px;
			padding: 10px 16px;
			overflow-x: auto;
			scrollbar-width: none;
			-webkit-mask-image: linear-gradient(90deg, #000 80%, transparent);
			mask-image: linear-gradient(90deg, #000 80%, transparent);
		}
		ul::-webkit-scrollbar {
			display: none;
		}
		li:last-child {
			padding-right: 40px;
		}
	}
</style>
