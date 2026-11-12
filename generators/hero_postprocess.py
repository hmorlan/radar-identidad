"""Postproceso y control automático de la imagen de la edición (v3.2).

Todo es local y sin costo (docs/identidad-visual.md):
- §6.3 variante oscura: inversión de luminancia en HLS protegiendo el oro.
- §6.4 control: porcentaje de oro y colores ajenos.
- §6.7 tono del mosaico emparejado al marfil de referencia; papel del grabado
  blanqueado; grabado oscuro como tinta marfil sobre obsidiana.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from PIL import Image, ImageFilter

IVORY_REF = np.array([228, 219, 202], dtype=np.float32) / 255.0  # §6.7
GAIN_MIN, GAIN_MAX = 0.85, 1.18
OBSIDIAN = np.array([14, 15, 18], dtype=np.float32) / 255.0      # --papel oscuro
IVORY_INK = np.array([236, 230, 216], dtype=np.float32) / 255.0  # --tinta oscura

# Oro: tono entre ~25° y ~65° (ámbar a amarillo) y croma por encima del fondo.
# Calibrado el 11 nov con las 16 imágenes de las pruebas v3.2 y de consistencia
# más las 2 referencias: el fondo de arena tiene croma de 0.13 a 0.22 según la
# imagen, así que un umbral absoluto de 0.3 (el de la especificación) contaba el
# fondo cálido como oro en unas y no veía el oro fino en otras. Con un umbral
# relativo (mediana de la imagen + 0.10) las 16 aprobadas miden de 1.6% a 13.8%
# y las referencias 0.15% (Troya, oro en línea fina) y 1.3% (Cerbero).
GOLD_CHROMA_OVER_MEDIAN = 0.10
GOLD_CHROMA = 0.30                # solo para colores ajenos (saturación fuerte)
GOLD_HUE = (25.0 / 360.0, 65.0 / 360.0)
GOLD_RANGE = (0.001, 0.15)        # 0.1% (hay oro) a 15% (no es un mosaico dorado)
FOREIGN_MAX = 0.003               # tolerancia a ruido JPEG: 0.3% de píxeles
# Máscara de la variante oscura: rampa sobre la croma relativa al fondo.
DARK_MASK_START, DARK_MASK_WIDTH = 0.12, 0.12

SERVE_WIDTH = 2400                # §6.6: ~2400 px para el paneo
THUMB_WIDTH = 640


def load_rgb(data: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.float32) / 255.0


def to_image(a: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


# --- HLS vectorizado (§6.3) -------------------------------------------------

def rgb_to_hls(a: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    mx, mn = a.max(-1), a.min(-1)
    l = (mx + mn) / 2
    d = mx - mn
    s = np.where(d == 0, 0, np.where(l < .5, d / np.maximum(mx + mn, 1e-9), d / np.maximum(2 - mx - mn, 1e-9)))
    sf = np.maximum(d, 1e-9)
    h = np.where(mx == a[..., 0], (mx - a[..., 2]) / sf - (mx - a[..., 1]) / sf,
        np.where(mx == a[..., 1], 2 + (mx - a[..., 0]) / sf - (mx - a[..., 2]) / sf,
                 4 + (mx - a[..., 1]) / sf - (mx - a[..., 0]) / sf))
    return np.where(d == 0, 0, (h / 6) % 1), l, s


def hls_to_rgb(h: np.ndarray, l: np.ndarray, s: np.ndarray) -> np.ndarray:
    m2 = np.where(l <= .5, l * (1 + s), l + s - l * s)
    m1 = 2 * l - m2

    def v(hh):
        hh = hh % 1
        return np.where(hh < 1 / 6, m1 + (m2 - m1) * hh * 6,
               np.where(hh < .5, m2, np.where(hh < 2 / 3, m1 + (m2 - m1) * (2 / 3 - hh) * 6, m1)))

    return np.stack([v(h + 1 / 3), v(h), v(h - 1 / 3)], -1)


def _hue(a: np.ndarray) -> np.ndarray:
    return rgb_to_hls(a)[0]


# --- Control automático (§6.4) ---------------------------------------------

@dataclass
class ColorCheck:
    gold_fraction: float
    foreign_fraction: float

    @property
    def gold_ok(self) -> bool:
        return GOLD_RANGE[0] <= self.gold_fraction <= GOLD_RANGE[1]

    @property
    def foreign_ok(self) -> bool:
        return self.foreign_fraction <= FOREIGN_MAX

    @property
    def ok(self) -> bool:
        return self.gold_ok and self.foreign_ok

    def reason(self) -> str:
        parts = []
        if not self.gold_ok:
            parts.append(f"oro {self.gold_fraction:.1%} fuera de {GOLD_RANGE[0]:.1%}–{GOLD_RANGE[1]:.0%}")
        if not self.foreign_ok:
            parts.append(f"colores ajenos en {self.foreign_fraction:.2%} de la imagen")
        return "; ".join(parts) or "ok"


def configure(control: dict | None) -> None:
    """Toma los umbrales de config/hero_prompt.yaml (bloque control)."""
    global GOLD_CHROMA, GOLD_CHROMA_OVER_MEDIAN, GOLD_RANGE, FOREIGN_MAX
    if not control:
        return
    GOLD_CHROMA = float(control.get("croma_ajenos", GOLD_CHROMA))
    GOLD_CHROMA_OVER_MEDIAN = float(control.get("croma_oro_sobre_fondo", GOLD_CHROMA_OVER_MEDIAN))
    GOLD_RANGE = (float(control.get("oro_min", GOLD_RANGE[0])), float(control.get("oro_max", GOLD_RANGE[1])))
    FOREIGN_MAX = float(control.get("ajenos_max", FOREIGN_MAX))


def color_check(a: np.ndarray) -> ColorCheck:
    """Mide el oro y los píxeles saturados de otro tono (verde, azul…)."""
    small = a
    if a.shape[1] > 1200:  # medir en una versión reducida basta y es más rápido
        img = to_image(a)
        img.thumbnail((1200, 1200))
        small = np.asarray(img, dtype=np.float32) / 255.0
    croma = small.max(-1) - small.min(-1)
    saturated = croma > GOLD_CHROMA
    hue = _hue(small)
    above_background = croma > float(np.median(croma)) + GOLD_CHROMA_OVER_MEDIAN
    gold = above_background & (hue >= GOLD_HUE[0]) & (hue <= GOLD_HUE[1])
    # Ajeno: saturado y fuera de un margen amplio alrededor del oro (rojizos a
    # verdosos tolerados como sombra del oro), es decir verdes, cianes, azules, morados.
    foreign = saturated & ((hue < 10 / 360) | (hue > 75 / 360))
    n = croma.size
    return ColorCheck(float(gold.sum()) / n, float(foreign.sum()) / n)


# --- Postproceso (§6.7) -----------------------------------------------------

def match_mosaic_tone(a: np.ndarray) -> np.ndarray:
    """Ganancia por canal para que las teselas claras de fondo queden en marfil."""
    croma = a.max(-1) - a.min(-1)
    lum = a.mean(-1)
    neutral = croma < 0.12
    if neutral.sum() < 1000:
        return a
    threshold = np.quantile(lum[neutral], 0.6)
    background = neutral & (lum >= threshold)
    median = np.median(a[background], axis=0)
    gain = np.clip(IVORY_REF / np.maximum(median, 1e-3), GAIN_MIN, GAIN_MAX)
    return np.clip(a * gain, 0, 1)


def whiten_paper(a: np.ndarray) -> np.ndarray:
    """Divide el grabado entre una estimación de su papel: el fondo queda blanco
    y, con mix-blend-mode:multiply, el grabado se imprime directo sobre --papel."""
    img = to_image(a)
    bg = img.filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(40))
    b = np.asarray(bg, dtype=np.float32) / 255.0
    return np.clip(a / np.maximum(b, 1e-3), 0, 1)


def dark_mosaic(a: np.ndarray) -> np.ndarray:
    """§6.3: invierte la luminancia en HLS y conserva el oro con su luz."""
    h, l, s = rgb_to_hls(a)
    dark = np.clip(hls_to_rgb(h, 1 - l, s), 0, 1)
    croma = a.max(-1) - a.min(-1)
    # Relativa al fondo: en mosaicos cálidos la arena ya tiene croma ~0.2 y una
    # rampa absoluta (0.22) la protegería como si fuera oro.
    start = float(np.median(croma)) + DARK_MASK_START
    m = np.clip((croma - start) / DARK_MASK_WIDTH, 0, 1)
    mask = to_image(np.repeat(m[..., None], 3, -1)).convert("L")
    mask = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    m = (np.asarray(mask, dtype=np.float32) / 255.0)[..., None]
    return dark * (1 - m) + a * m


def dark_engraving(a: np.ndarray) -> np.ndarray:
    """§6.7: grises invertidos mapeados de obsidiana a marfil."""
    gray = a.mean(-1, keepdims=True)
    ink = 1 - gray
    return OBSIDIAN + ink * (IVORY_INK - OBSIDIAN)


def resize_width(img: Image.Image, width: int) -> Image.Image:
    if img.width <= width:
        return img
    h = round(img.height * width / img.width)
    return img.resize((width, h), Image.LANCZOS)


def jpeg_bytes(img: Image.Image, quality: int = 88) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def build_variants(data: bytes, tecnica: str) -> Tuple[bytes, bytes, bytes]:
    """Devuelve (claro, oscuro, miniatura) en JPEG listos para publicar."""
    a = load_rgb(data)
    if tecnica == "grabado":
        light = whiten_paper(a)
        dark = dark_engraving(light)
    else:
        light = match_mosaic_tone(a)
        dark = dark_mosaic(light)
    light_img = resize_width(to_image(light), SERVE_WIDTH)
    dark_img = resize_width(to_image(dark), SERVE_WIDTH)
    thumb = resize_width(light_img, THUMB_WIDTH)
    return jpeg_bytes(light_img), jpeg_bytes(dark_img), jpeg_bytes(thumb, 82)
