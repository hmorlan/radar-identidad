/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			// Radar de Identidad — design system "Radar de Identidad" (tokens.json).
			// Los colores semánticos son variables CSS (src/app.css) con valor
			// distinto en claro y oscuro. Los radar-* son alias para los componentes
			// heredados, de modo que adoptan la misma paleta.
			colors: {
				ground: 'rgb(var(--ground) / <alpha-value>)',
				surface: 'rgb(var(--surface) / <alpha-value>)',
				line: 'rgb(var(--line) / <alpha-value>)',
				ink: 'rgb(var(--ink) / <alpha-value>)',
				'ink-body': 'rgb(var(--ink-body) / <alpha-value>)',
				'ink-muted': 'rgb(var(--ink-muted) / <alpha-value>)',
				electric: 'rgb(var(--electric-blue) / <alpha-value>)',
				sapphire: 'rgb(var(--sapphire) / <alpha-value>)',
				gold: 'rgb(var(--signal-gold) / <alpha-value>)',
				glow: 'rgb(var(--core-glow) / <alpha-value>)',
				'hero-ground': '#050608',
				'hero-ink': '#F1F2F4',
				'radar-accent': 'rgb(var(--electric-blue) / <alpha-value>)',
				'radar-accent-dark': 'rgb(var(--sapphire) / <alpha-value>)',
				'radar-bronze': 'rgb(var(--signal-gold) / <alpha-value>)',
				'radar-dark': '#050608',
				'radar-gray': {
					50: '#F4F5F7',
					100: '#F4F5F7',
					200: '#DCE0E6',
					300: '#C3C9D1',
					400: '#8D96A3',
					500: '#5B6472',
					600: '#3A4250',
					700: '#1D232C',
					800: '#0C0E12',
					900: '#050608'
				},
				// Categorías: sin verdes ni naranjas (reglas del design system).
				'category-news': '#1E5BFF',
				'category-research': '#0B63CE',
				'category-social': '#5B6472',
				'category-reddit': '#5B6472'
			},
			fontFamily: {
				sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
				display: ['"Marcellus SC"', 'Georgia', 'serif']
			},
			borderRadius: {
				sm: '6px',
				md: '10px',
				lg: '14px'
			},
			boxShadow: {
				'card': '0 2px 8px rgba(0, 0, 0, 0.08)',
				'card-hover': '0 4px 12px rgba(0, 0, 0, 0.12)'
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
