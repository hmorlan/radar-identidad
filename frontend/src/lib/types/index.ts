/**
 * Type definitions for AI News Aggregator frontend
 */

export type Category = 'news' | 'research' | 'social' | 'reddit';

export interface NewsItem {
	id: string;
	title: string;
	content: string;
	content_html?: string;
	url: string;
	author: string;
	published: string;
	source: string;
	source_type: string;
	tags: string[];
	summary: string;
	summary_html?: string;
	importance_score: number;
	reasoning: string;
	themes: string[];
	freshness?: {
		status: string;
		label: string;
		reason?: string;
		primary_url?: string;
		primary_published?: string;
		age_days?: number;
		exclude_from_top?: boolean;
	};
}

export interface CategoryTheme {
	name: string;
	description: string;
	item_count: number;
	example_items: string[];
	importance: number;
}

export interface TopTopic {
	name: string;
	description: string;
	description_html: string;
	category_breakdown: Record<Category, number>;
	representative_items: string[];
	importance: number;
}

export interface CategorySummary {
	count: number;
	category_summary: string;
	category_summary_html?: string;
	themes: CategoryTheme[];
	top_items: NewsItem[];
}

export interface CollectionSource {
	name: string;
	display_name: string;
	status: 'success' | 'partial' | 'failed';
	count: number;
	error: string | null;
}

export interface CollectionStatus {
	overall: 'success' | 'partial' | 'failed';
	sources: CollectionSource[];
}

/** Radar de Identidad: una nota de la edición (fases 4.2-4.3 del pipeline). */
export interface EditionNote {
	item_id: string;
	category: string;
	title: string;
	url: string;
	source: string;
	published: string;
	que_paso: string;
	por_que_importa: string;
	pregunta_de_fondo: string | null;
	senal: 'baja' | 'media' | 'alta';
	verificacion: 'verificada' | 'corregida' | 'sin_verificar' | string;
}

export interface Edition {
	titular: string;
	notas: EditionNote[];
	/** 'domingo' = "La semana en identidad" (plantilla con grabado y sello armilar). */
	tipo?: 'diario' | 'domingo';
}

/** Imagen de la edición v3.2 (§6): variante clara y oscura derivada, punto focal y crédito. */
export interface HeroImage {
	light_url: string;
	dark_url?: string;
	/** object-position del punto focal, p. ej. "28% 45%". */
	focus?: string;
	/** "mosaico" (diario) o "grabado" (domingo o respaldo). */
	tecnica?: 'mosaico' | 'grabado';
	/** Motivo para el crédito tipo museo, p. ej. "Ulises y las sirenas". */
	motivo?: string;
	thumb_url?: string;
	/** Texto alternativo descriptivo. */
	alt?: string;
	/** Nombre visible del modelo, p. ej. "Gemini 3 Pro Image". */
	modelo?: string;
	/** Imagen de archivo (respaldo cuando ninguna candidata del día pasó). */
	archivo?: boolean;
}

export interface DaySummary {
	date: string;
	coverage_date?: string;
	coverage_start?: string;
	coverage_end?: string;
	executive_summary: string;
	executive_summary_html?: string;
	top_topics: TopTopic[];
	total_items_collected: number;
	total_items_analyzed: number;
	generated_at: string;
	categories: Record<Category, CategorySummary>;
	hero_image_url?: string;
	hero_image_prompt?: string;
	/** Usage/cost block reported by the image provider; `model` names it. */
	hero_image_usage?: { model?: string } & Record<string, unknown>;
	collection_status?: CollectionStatus;
	/** Raw model id that produced this day's analysis (absent on old reports). */
	llm_model?: string;
	/** Human-facing name of that model (e.g. "Claude Opus 5", "Ox Alpha"). */
	llm_model_display?: string;
	/** Raw hero-image model id for this day (same attribution contract). */
	image_model?: string;
	/** Human-facing name of the hero-image model. */
	image_model_display?: string;
	/** Radar de Identidad: notas de la edición (ausente en días anteriores). */
	edition?: Edition;
	/** Imagen v3.2 con variantes; si falta, se usa hero_image_url. */
	hero_image?: HeroImage;
}

export interface CategoryNotice {
	type: 'info' | 'warning';
	title: string;
	message: string;
}

export interface CategoryData {
	category: Category;
	date: string;
	category_summary: string;
	category_summary_html?: string;
	themes: CategoryTheme[];
	total_items: number;
	items: NewsItem[];
	notice?: CategoryNotice;
}

export interface DateEntry {
	date: string;
	total_items: number;
	/** Titular de la edición (v3.2: el archivo lista cada edición con su titular). */
	titular?: string;
	tipo?: 'diario' | 'domingo';
	/** Miniatura clara de la imagen de la edición. */
	hero_thumb?: string;
	categories: Record<Category, { count: number; file_size: number }>;
}

/** The LLM currently powering the pipeline, as published in index.json. */
export interface CurrentModel {
	/** Raw provider model id (e.g. stealth/ox-alpha). */
	id: string;
	/** Human-facing name shown on the site (e.g. "Ox Alpha"). */
	display_name: string;
	/** Report date (YYYY-MM-DD) this model first ran; drives the NEW badge. */
	since: string;
}

export interface DataIndex {
	version: string;
	dates: DateEntry[];
	latestDate: string | null;
	generatedAt: string;
	totalDates: number;
	current_model?: CurrentModel;
}

export interface SearchDocument {
	id: string;
	title: string;
	summary: string;
	url: string;
	date: string;
	category: Category;
	source: string;
	importance: number;
}

export interface SearchResult {
	ref: string;
	score: number;
	doc?: SearchDocument;
}

// Category display configuration
export const CATEGORY_CONFIG: Record<
	Category,
	{
		title: string;
		singularTitle: string;
		shortTitle: string;
		color: string;
		bgClass: string;
		textClass: string;
		badgeClass: string;
		accentClass: string;
	}
> = {
	news: {
		title: 'Noticias',
		singularTitle: 'Noticia',
		shortTitle: 'Noticias',
		color: '#7A5C18',
		bgClass: 'bg-category-news',
		textClass: 'text-category-news',
		badgeClass: 'badge-news',
		accentClass: 'category-accent-news'
	},
	research: {
		title: 'Investigación y estándares',
		singularTitle: 'Investigación',
		shortTitle: 'Investigación',
		color: '#7A5C18',
		bgClass: 'bg-category-research',
		textClass: 'text-category-research',
		badgeClass: 'badge-research',
		accentClass: 'category-accent-research'
	},
	social: {
		title: 'Redes',
		singularTitle: 'Redes',
		shortTitle: 'Redes',
		color: '#5A5F66',
		bgClass: 'bg-category-social',
		textClass: 'text-category-social',
		badgeClass: 'badge-social',
		accentClass: 'category-accent-social'
	},
	reddit: {
		title: 'Reddit Discussions',
		singularTitle: 'Reddit Discussion',
		shortTitle: 'Reddit',
		color: '#5A5F66',
		bgClass: 'bg-category-reddit',
		textClass: 'text-category-reddit',
		badgeClass: 'badge-reddit',
		accentClass: 'category-accent-reddit'
	}
};
