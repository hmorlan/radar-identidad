/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			// Radar de Identidad — dirección v3.2 "mármol, tinta y oro"
			// (docs/identidad-visual.md). Los colores son variables CSS (src/app.css)
			// con valor distinto en claro y oscuro. Los nombres anteriores (ground,
			// ink, electric, sapphire…) quedan como alias para que los componentes
			// heredados adopten la paleta nueva sin azul ni cian.
			colors: {
				papel: 'rgb(var(--papel) / <alpha-value>)',
				piedra: 'rgb(var(--piedra) / <alpha-value>)',
				filete: 'rgb(var(--filete) / <alpha-value>)',
				caja: 'rgb(var(--caja) / <alpha-value>)',
				tinta: 'rgb(var(--tinta) / <alpha-value>)',
				'tinta-cuerpo': 'rgb(var(--tinta-cuerpo) / <alpha-value>)',
				'tinta-suave': 'rgb(var(--tinta-suave) / <alpha-value>)',
				oro: 'rgb(var(--oro) / <alpha-value>)',
				'oro-hover': 'rgb(var(--oro-hover) / <alpha-value>)',
				foco: 'rgb(var(--foco) / <alpha-value>)',
				terracota: 'rgb(var(--terracota) / <alpha-value>)',
				// Alias heredados
				ground: 'rgb(var(--papel) / <alpha-value>)',
				surface: 'rgb(var(--caja) / <alpha-value>)',
				line: 'rgb(var(--filete) / <alpha-value>)',
				ink: 'rgb(var(--tinta) / <alpha-value>)',
				'ink-body': 'rgb(var(--tinta-cuerpo) / <alpha-value>)',
				'ink-muted': 'rgb(var(--tinta-suave) / <alpha-value>)',
				electric: 'rgb(var(--oro) / <alpha-value>)',
				sapphire: 'rgb(var(--oro) / <alpha-value>)',
				gold: 'rgb(var(--oro) / <alpha-value>)',
				glow: 'rgb(var(--tinta) / <alpha-value>)',
				'radar-accent': 'rgb(var(--oro) / <alpha-value>)',
				'radar-accent-dark': 'rgb(var(--oro) / <alpha-value>)',
				'radar-bronze': 'rgb(var(--oro) / <alpha-value>)',
				'radar-dark': 'rgb(var(--tinta) / <alpha-value>)',
				// Escala fija (no por variable): los componentes heredados ya alternan
				// tonos con dark:, así que la escala va de papel (50) a obsidiana (900).
				'radar-gray': {
					50: '#F5F1E8',
					100: '#EFE9DB',
					200: '#DCD4BF',
					300: '#C9C1AD',
					400: '#A39D8F',
					500: '#5A5F66',
					600: '#3A3D44',
					700: '#2A2B2F',
					800: '#17181D',
					900: '#0E0F12'
				},
				// Categorías: sin azul ni cian; oro y tinta suave.
				'category-news': 'rgb(var(--oro) / <alpha-value>)',
				'category-research': 'rgb(var(--oro) / <alpha-value>)',
				'category-social': 'rgb(var(--tinta-suave) / <alpha-value>)',
				'category-reddit': 'rgb(var(--tinta-suave) / <alpha-value>)'
			},
			fontFamily: {
				sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
				serif: ['Newsreader', 'Georgia', 'serif'],
				display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
				wordmark: ['"Marcellus SC"', 'Georgia', 'serif']
			},
			borderRadius: {
				sm: '0px',
				md: '0px',
				lg: '0px'
			},
			boxShadow: {
				// Sin sombras (§8): filetes de 1px en vez de cajas.
				'card': 'none',
				'card-hover': 'none'
			},
			typography: {
				DEFAULT: {
					css: {
						// The plugin draws literal backticks around inline code with
						// ::before/::after and sets font-weight 600, so a <code> span
						// renders as **`like this`** — bold, with the markers we just
						// converted away put back. Style it as a chip instead.
						'code::before': { content: 'none' },
						'code::after': { content: 'none' },
						code: {
							fontWeight: '400',
							backgroundColor: 'rgb(0 0 0 / 0.06)',
							padding: '0.1em 0.35em',
							borderRadius: '0.25rem',
							fontSize: '0.9em'
						}
					}
				},
				invert: {
					css: {
						code: {
							backgroundColor: 'rgb(255 255 255 / 0.1)',
							color: 'inherit'
						}
					}
				}
			}
		}
	},
	plugins: [
		require('@tailwindcss/typography')
	]
};
