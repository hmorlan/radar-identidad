<!--
	Sello armilar del domingo (v3.2 §4.8): esfera pequeña en SVG, líneas de oro y
	tinta. Un anillo gira muy lento (40 s por vuelta) y se detiene con
	prefers-reduced-motion. Decorativo: aria-hidden.
-->
<svg aria-hidden="true" viewBox="0 0 60 60" class="sello" width="40" height="40">
	<circle cx="30" cy="30" r="27" fill="none" stroke="rgb(var(--oro))" stroke-width="1" />
	<g class="gira">
		<ellipse cx="30" cy="30" rx="24" ry="9" fill="none" stroke="rgb(var(--oro))" stroke-width="1.2" transform="rotate(-22 30 30)" />
		<circle cx="54" cy="30" r="2" fill="rgb(var(--oro))" transform="rotate(-22 30 30)" />
	</g>
	<ellipse cx="30" cy="30" rx="9" ry="24" fill="none" stroke="rgb(var(--tinta))" stroke-width="1" transform="rotate(18 30 30)" />
	<circle cx="30" cy="30" r="2.5" fill="rgb(var(--tinta))" />
</svg>

<style>
	.sello {
		display: block;
	}
	.gira {
		transform-origin: 30px 30px;
		animation: gira 40s linear infinite;
	}
	@keyframes gira {
		to {
			transform: rotate(360deg);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.gira {
			animation: none;
		}
	}
</style>
