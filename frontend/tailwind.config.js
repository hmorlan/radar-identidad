/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	darkMode: 'class',
	theme: {
		extend: {
			colors: {
				// Paleta PROVISIONAL de Radar de Identidad (azul profundo + bronce).
				// Se reemplaza cuando cerremos el mockup visual.
				'radar-accent': '#2F5F9E',
				'radar-accent-dark': '#1F4373',
				'radar-bronze': '#B8925A',
				'radar-dark': '#0F1A2A',
				'radar-gray': {
					50: '#f8fafc',
					100: '#f1f4f8',
					200: '#e2e7ee',
					300: '#cbd3de',
					400: '#94a0b2',
					500: '#64718a',
					600: '#475468',
					700: '#334155',
					800: '#1e293b',
					900: '#111827'
				},
				// Category accent colors
				'category-news': '#667eea',
				'category-research': '#10b981',
				'category-social': '#f59e0b',
				'category-reddit': '#ef4444'
			},
			fontFamily: {
				sans: [
					'-apple-system',
					'BlinkMacSystemFont',
					'Segoe UI',
					'Roboto',
					'Oxygen',
					'Ubuntu',
					'Cantarell',
					'sans-serif'
				]
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
