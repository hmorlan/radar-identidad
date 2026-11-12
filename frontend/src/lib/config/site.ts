/**
 * Datos del sitio que no salen del pipeline: perfil de LinkedIn y la franja humana
 * (foto o video de la semana). Se editan aquí a mano.
 *
 * Mientras un campo esté vacío, el sitio muestra su espacio reservado.
 */

/** URL del perfil de LinkedIn de Hiram. Vacío = el botón no se muestra. */
export const LINKEDIN_URL = 'https://www.linkedin.com/in/hiram-morlan';

export interface HumanStrip {
	/** 'placeholder' mientras no haya foto ni video. */
	kind: 'placeholder' | 'image' | 'video';
	/** Imagen (ruta en /static) o miniatura del video. */
	src?: string;
	alt?: string;
	/** Frase en Cormorant que acompaña la foto o el video. */
	frase: string;
	/** Enlace al video o a la publicación en LinkedIn. */
	enlace?: string;
}

export const HUMAN_STRIP: HumanStrip = {
	kind: 'placeholder',
	frase: 'Cada semana, Hiram explica en cámara una de las historias del radar.',
	enlace: 'https://www.linkedin.com/in/hiram-morlan'
};
