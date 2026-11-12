/** Utilidades de la vista de edición (v3.2). */

const ROMAN: [number, string][] = [
	[1000, 'M'], [900, 'CM'], [500, 'D'], [400, 'CD'], [100, 'C'], [90, 'XC'],
	[50, 'L'], [40, 'XL'], [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']
];

export function toRoman(n: number): string {
	let out = '';
	let rest = Math.max(1, Math.floor(n));
	for (const [value, numeral] of ROMAN) {
		while (rest >= value) {
			out += numeral;
			rest -= value;
		}
	}
	return out;
}

/** Puntos de señal (§3.6): 1–3; solo ALTA va en oro. */
export function signalDots(senal: string): number {
	return senal === 'alta' ? 3 : senal === 'media' ? 2 : 1;
}

export function host(url: string): string {
	try {
		return new URL(url).hostname.replace(/^www\./, '');
	} catch {
		return '';
	}
}

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** "10 nov 2026" a partir de una fecha ISO; vacío si no se puede leer. */
export function shortDate(iso: string | undefined | null): string {
	if (!iso) return '';
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return '';
	return `${d.getUTCDate()} ${MESES[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** Punto focal válido para object-position ("NN% NN%"); si no, el centro. */
export function safeFocus(focus: string | undefined | null): string {
	return focus && /^\d{1,3}(\.\d+)?% \d{1,3}(\.\d+)?%$/.test(focus.trim()) ? focus.trim() : '50% 45%';
}

/**
 * Nunca cortar a media frase (§3.5): si el texto llegó recortado con "…", se
 * muestra hasta la última frase completa.
 */
export function wholeSentences(text: string | null | undefined): string {
	const t = (text ?? '').trim();
	if (!t.endsWith('…')) return t;
	const cut = Math.max(t.lastIndexOf('. '), t.lastIndexOf('? '), t.lastIndexOf('! '));
	return cut > 0 ? t.slice(0, cut + 1) : t;
}
