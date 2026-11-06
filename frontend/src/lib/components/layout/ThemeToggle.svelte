<script lang="ts">
	import { isDark, toggleTheme } from '$lib/stores/themeStore';
</script>

<button
	on:click={toggleTheme}
	class="toggle"
	aria-label={$isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
	title={$isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
>
	{#if $isDark}
		<!-- Sun icon -->
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="w-[18px] h-[18px]"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
			stroke-width="2"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
			/>
		</svg>
	{:else}
		<!-- Moon icon -->
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="w-[18px] h-[18px]"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
			stroke-width="2"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
			/>
		</svg>
	{/if}
</button>

<style>
	.toggle {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 38px;
		height: 38px;
		border-radius: 999px;
		border: 1px solid rgb(255 255 255 / 0.14);
		color: #f1f2f4;
		transition: border-color 150ms, background-color 150ms;
	}
	.toggle:hover {
		border-color: rgb(255 255 255 / 0.32);
		background: rgb(255 255 255 / 0.06);
	}
	.toggle:focus-visible {
		outline: 2px solid #4fc3ff;
		outline-offset: 2px;
	}
</style>
