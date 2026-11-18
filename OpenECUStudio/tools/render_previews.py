# -*- coding: utf-8 -*-
"""Génère des aperçus PNG de l'interface OpenECU Studio (rendu fidèle au thème).

Le sandbox d'exécution est Linux headless sans libGL : Qt ne peut pas y être
rendu. Ce script reproduit pixel-faithful la disposition et les couleurs
définies dans ui/theme.py et produit chaque onglet en **thème sombre ET clair,
côte à côte**. Les couleurs proviennent des palettes de ui/theme.py.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ui.theme import DARK, LIGHT

S = 2  # facteur de sur-échantillonnage (haute résolution pour zoom confortable)


class ScaledDraw:
    """Proxy ImageDraw qui multiplie toutes les coordonnées par S.

    Les tailles de police sont multipliées par S ; ``textlength`` ramène la
    valeur en unités logiques pour que les calculs de mise en page restent
    inchangés.
    """

    def __init__(self, draw: ImageDraw.ImageDraw, scale: int) -> None:
        self._d = draw
        self.scale = scale

    def _s(self, pts):
        return [v * self.scale for v in pts]

    def rectangle(self, box, **kw):
        kw["width"] = kw.get("width", 1) * self.scale
        self._d.rectangle(self._s(box), **kw)

    def rounded_rectangle(self, box, radius=0, **kw):
        kw["width"] = kw.get("width", 1) * self.scale
        self._d.rounded_rectangle(self._s(box), radius=radius * self.scale, **kw)

    def ellipse(self, box, **kw):
        kw["width"] = kw.get("width", 1) * self.scale
        self._d.ellipse(self._s(box), **kw)

    def line(self, pts, **kw):
        kw["width"] = kw.get("width", 1) * self.scale
        self._d.line(self._s(pts), **kw)

    def text(self, xy, txt, font=None, fill=None, anchor=None, **kw):
        self._d.text(self._s(xy), txt, font=font, fill=fill, anchor=anchor, **kw)

    def textlength(self, txt, font=None):
        return self._d.textlength(txt, font=font) / self.scale


def palette_dict(theme) -> dict:
    return {
        "BG": theme.bg,
        "PANEL": theme.panel,
        "BORDER": theme.border,
        "TEXT": theme.text,
        "DIM": theme.text_dim,
        "ACCENT": theme.accent,
        "ACCENT_TEXT": theme.accent_text,
        "OK": theme.ok,
        "ERR": theme.error,
        "CONSOLE": theme.console_bg,
        "INPUT": theme.input_bg,
        "BTN": theme.button_bg,
        "ALT_ROW": theme.alt_row,
        "HEADER_BG": theme.header_bg,
        "THEME_LABEL": "Thème sombre" if theme.name == "dark" else "Thème clair",
    }


DARK_PALETTE = palette_dict(DARK)
LIGHT_PALETTE = palette_dict(LIGHT)

BG = PANEL = BORDER = TEXT = DIM = ACCENT = ACCENT_TEXT = ""
OK = ERR = CONSOLE = INPUT = BTN = ALT_ROW = HEADER_BG = THEME_LABEL = ""


def use_theme(palette: dict) -> None:
    globals().update(palette)


use_theme(DARK_PALETTE)


W, H = 1280, 860
TITLE_H = 28
TAB_H = 34

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size * S)
    except OSError:
        return ImageFont.load_default()


def base_window(active_tab):
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ScaledDraw(ImageDraw.Draw(img), S)
    d.rectangle([0, 0, W, TITLE_H], fill=PANEL)
    d.text((10, 6), "OpenECU Studio v1.2.0 — J2534 / UDS / ECU Patcher", font=font(FONT, 13), fill=TEXT)
    d.text((W - 190, 7), "Affichage ▾", font=font(FONT, 11), fill=TEXT)
    badge = font(FONT, 10)
    tw = d.textlength(THEME_LABEL, font=badge)
    d.rounded_rectangle([W - 138, 6, W - 108, 22], radius=4, outline=BORDER, fill=INPUT)
    d.text((W - 132 + (26 - tw) / 2 if tw < 22 else W - 134, 8), "◑", font=font(FONT, 11), fill=ACCENT)
    d.text((W - 96, 8), THEME_LABEL, font=badge, fill=DIM)
    d.line([0, TITLE_H, W, TITLE_H + TAB_H], fill=BORDER)
    d.rectangle([0, TITLE_H, W, H], fill=BG)
    d.rectangle([0, TITLE_H, W, TITLE_H + 1], fill=PANEL)
    d.line([0, TITLE_H, W, TITLE_H], fill=BORDER)
    tabs = ["Diagnostic & SM2 Pro (J2534)", "Éditeur ECU & Patcher (Offline)", "Comparateur Hexadécimal", "Gestionnaire de Définitions"]
    x = 4
    for i, label in enumerate(tabs):
        f = font(FONT_B if i == active_tab else FONT, 12)
        tw = d.textlength(label, font=f)
        pad = 16
        box = [x, TITLE_H + 4, x + tw + 2 * pad, TITLE_H + TAB_H]
        if i == active_tab:
            d.rectangle(box, fill=PANEL, outline=BORDER)
            d.line([box[0] + 1, box[3] - 1, box[2], box[3] - 1], fill=ACCENT, width=2)
            d.text((x + pad, TITLE_H + 12), label, font=f, fill=ACCENT)
        else:
            d.text((x + pad, TITLE_H + 12), label, font=f, fill=DIM)
        x += tw + 2 * pad + 4
    d.rectangle([0, TITLE_H + TAB_H, W, H], fill=PANEL, outline=BORDER)
    return img, d


def groupbox(d, x, y, w, h, title):
    d.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=PANEL, outline=BORDER, width=1)
    f = font(FONT_B, 11)
    tw = d.textlength(title, font=f)
    d.rectangle([x + 8, y - 9, x + 18 + tw, y + 9], fill=PANEL)
    d.text((x + 16, y - 8), title, font=f, fill=ACCENT)


def button(d, x, y, w, h, label, primary=False, danger=False, enabled=True):
    if primary and enabled:
        fill, fg = ACCENT, ACCENT_TEXT
    elif danger and enabled:
        fill, fg = ERR, "#ffffff"
    else:
        fill, fg = (BG, DIM) if not enabled else (BTN, TEXT)
    outline = None if (primary or danger) and enabled else BORDER
    d.rounded_rectangle([x, y, x + w, y + h], radius=6, fill=fill, outline=outline)
    f = font(FONT_B if (primary or danger) else FONT, 11)
    tw = d.textlength(label, font=f)
    d.text((x + (w - tw) / 2, y + (h - 14) / 2 - 1), label, font=f, fill=fg)


def input_box(d, x, y, w, h, text, mono=False, color=None):
    color = color or TEXT
    d.rounded_rectangle([x, y, x + w, y + h], radius=6, fill=INPUT, outline=BORDER)
    d.text((x + 8, y + (h - 12) / 2), text, font=font(MONO if mono else FONT, 11), fill=color)


def checkbox(d, x, y, label, checked=True):
    d.rounded_rectangle([x, y, x + 15, y + 15], radius=4, fill=ACCENT if checked else INPUT, outline=ACCENT if checked else BORDER)
    if checked:
        d.line([x + 3, y + 8, x + 6, y + 11], fill=ACCENT_TEXT, width=2)
        d.line([x + 6, y + 11, x + 12, y + 4], fill=ACCENT_TEXT, width=2)
    d.text((x + 22, y - 1), label, font=font(FONT, 11), fill=TEXT)


# ==========================================================================
# Onglet 1 : Diagnostic & SM2 Pro
# ==========================================================================
def render_tab1(path):
    img, d = base_window(0)
    top = TITLE_H + TAB_H + 12

    # --- Interface J2534 ---
    groupbox(d, 10, top, W - 20, 62, "Interface J2534 (SAE PassThru 04.04)")
    y = top + 16
    d.text((24, y + 8), "Interface :", font=font(FONT, 11), fill=TEXT)
    input_box(d, 96, y, 400, 28, "SM2 USB  [C:\\Program Files (x86)\\Scanmatik\\smj2534.dll]")
    button(d, 506, y, 90, 28, "Rafraîchir")
    button(d, 606, y, 110, 28, "Se connecter", primary=True)
    button(d, 726, y, 110, 28, "Déconnecter", enabled=False)

    # --- Configuration CAN (v1.2.0) ---
    cy_ = top + 72
    groupbox(d, 10, cy_, W - 20, 92, "Configuration CAN (ISO 15765)")
    r1 = cy_ + 16
    d.text((24, r1 + 8), "Vitesse (bauds) :", font=font(FONT, 11), fill=TEXT)
    input_box(d, 148, r1, 110, 28, "500 000")
    d.text((272, r1 + 8), "ID requête (TX) :", font=font(FONT, 11), fill=TEXT)
    input_box(d, 392, r1, 70, 28, "7E0", mono=True)
    d.text((478, r1 + 8), "ID réponse (RX) :", font=font(FONT, 11), fill=TEXT)
    input_box(d, 596, r1, 70, 28, "7E8", mono=True)
    checkbox(d, 24, r1 + 40, "Tester Present automatique (2 s) — maintient la session de diagnostic active", True)

    # --- VBatt + UDS ---
    mid = cy_ + 102
    gb_h = 280
    groupbox(d, 10, mid, 380, gb_h, "Tension batterie (VBatt — pin 16)")
    d.text((200, mid + 60), "12.47 V", font=font(MONO_B, 34), fill=OK, anchor="mm")
    d.text((200, mid + 110), "Lecture temps réel (1 Hz)", font=font(FONT, 10), fill=DIM, anchor="mm")

    groupbox(d, 400, mid, W - 420, gb_h, "Diagnostic UDS (ISO 14229)")
    ux, uy = 414, mid + 14
    button(d, ux, uy, 190, 26, "Identifier ECU (UDS)", primary=True)
    button(d, ux + 200, uy, 190, 26, "Session étendue (10 03)")
    button(d, ux, uy + 32, 190, 26, "Lire les DTC (19 02 FF)")
    button(d, ux + 200, uy + 32, 260, 26, "Effacer les DTC de la mémoire ECU", danger=True)
    tx, ty = ux, uy + 66
    d.rounded_rectangle([tx, ty, ux + 700, mid + gb_h - 14], radius=6, fill=CONSOLE, outline=BORDER)
    lines = [
        "--- Identification ECU ---",
        "VIN (F190) : VF3MOCKEDCU000000",
        "N° Hardware (F191) : 0281020304",
        "N° Software (F195) : 1037501234",
        "",
        "--- Lecture DTC ---",
        "4 DTC(s) en mémoire :",
        "  • P0401  (brut 0x0401) — statut 0x2F",
        "  • P2002  (brut 0x2002) — statut 0x2F",
        "  • P2463  (brut 0x2463) — statut 0x2F",
        "  • P2263  (brut 0x2263) — statut 0x08",
    ]
    for i, line in enumerate(lines):
        d.text((tx + 8, ty + 6 + i * 15), line, font=font(MONO, 10), fill=TEXT)

    # --- Console ---
    con = mid + gb_h + 12
    groupbox(d, 10, con, W - 20, H - con - 40, "Console trames CAN / UDS brutes")
    frames = [
        "[19:21:26] TX ID=0x7E0 [03] 02 10 03",
        "[19:21:26] RX ID=0x7E8 [06] 06 50 03 00 32 01 F4",
        "[19:21:26] TX ID=0x7E0 [04] 03 22 F1 90",
        "[19:21:26] RX ID=0x7E8 [04] 05 62 F1 90",
        "[19:21:26] TX ID=0x7E0 [04] 03 19 02 FF",
        "[19:21:26] RX ID=0x7E8 [08] 10 0F 59 02 FF 04 01 2F",
        "[19:21:26] RX ID=0x7E8 [08] 21 20 02 2F 24 63 2F 22",
        "[19:21:26] RX ID=0x7E8 [03] 22 63 08",
        "[19:21:26] TX ID=0x7E0 [05] 04 14 FF FF FF",
        "[19:21:26] RX ID=0x7E8 [02] 01 54",
    ]
    for i, line in enumerate(frames):
        d.text((24, con + 16 + i * 17), line, font=font(MONO, 11), fill=TEXT)

    d.text((10, H - 24), "Connecté : SM2 USB — ISO 15765 @ 500 000 bauds — TX=0x7E0, RX=0x7E8", font=font(FONT, 10), fill=DIM)
    img.save(path)
    print("OK", path)


# ==========================================================================
# Onglet 2 : Éditeur ECU & Patcher
# ==========================================================================
def render_tab2(path):
    img, d = base_window(1)
    top = TITLE_H + TAB_H + 10

    # --- Fichier ECU ---
    groupbox(d, 10, top, W - 20, 150, "Fichier ECU (.bin / .ori)")
    button(d, 24, top + 16, 240, 28, "Charger un fichier ECU (.bin / .ori)", primary=True)
    button(d, 272, top + 16, 230, 28, "Sauvegarder le calculateur (copie)")
    button(d, 510, top + 16, 190, 28, "Restaurer une sauvegarde .bak")
    button(d, 708, top + 16, 210, 28, "Annuler les modifications (session)")
    rows = [
        ("Famille détectée :", "EDC17C10 (Élevée)"),
        ("Constructeur ECU :", "Bosch"),
        ("Taille :", "2097152 octets (0x200000)"),
        ("Entropie :", "7.894 bits/octet"),
        ("N° de pièce :", "0281020304"),
        ("SAUVEGARDE :", "C:\\Dumps\\edc17c10_origine_20250101_120000.bak"),
    ]
    for i, (k, v) in enumerate(rows):
        ry = top + 52 + i * 15
        d.text((30, ry), k, font=font(FONT, 10), fill=DIM)
        d.rounded_rectangle([150, ry - 2, 780, ry + 13], radius=2, fill=INPUT, outline=BORDER)
        d.text((158, ry), v, font=font(MONO, 10), fill=TEXT)

    # --- VIN ---
    vy = top + 152
    groupbox(d, 10, vy, W - 20, 56, "Réemploi d'un calculateur d'occasion — VIN")
    d.text((24, vy + 20), "2 occurrence(s) : VF3MABBB1BB123456   @ 0x004001, 0x050001", font=font(MONO, 10), fill=TEXT)
    input_box(d, 640, vy + 14, 340, 26, "VF3MZZZZ6ZZ654321", mono=True)
    button(d, 988, vy + 14, 264, 26, "Remplacer le VIN dans le dump", primary=True)

    # --- Définition ---
    dy = vy + 58
    groupbox(d, 10, dy, W - 20, 50, "Définition de calculateur (JSON)")
    d.text((24, dy + 16), "Définition :", font=font(FONT, 11), fill=TEXT)
    input_box(d, 110, dy + 12, 480, 26, "Bosch EDC17 — DTC Remover générique (modèle)")
    button(d, 600, dy + 12, 90, 26, "Recharger")
    d.text((700, dy + 18), "✔ Compatible avec le dump chargé", font=font(FONT, 10), fill=OK)

    # --- Solutions + DTC ---
    sy = dy + 52
    gb_h = H - sy - 90
    groupbox(d, 10, sy, 400, gb_h, "Solutions disponibles")
    sols = [
        ("EGR Off  (antipollution)", True),
        ("DPF / FAP Off  (antipollution)", True),
        ("AdBlue / SCR Off  (antipollution)", False),
        ("Swirl Flaps Off  (admission)", False),
    ]
    for i, (label, checked) in enumerate(sols):
        cy2 = sy + 20 + i * 24
        checkbox(d, 24, cy2, label, checked)
    button(d, 24, sy + gb_h - 40, 230, 28, "Appliquer les solutions cochées", primary=True)

    groupbox(d, 420, sy, W - 440, gb_h, "DTC détectés dans le dump (DTC Remover)")
    input_box(d, 434, sy + 14, 500, 26, "P0401")
    button(d, 944, sy + 14, 80, 26, "Scanner")
    cols = [434, 560, 660, 940, 1030]
    headers = ["Offset", "Code", "Table", "État", "Switch"]
    for cx, hd in zip(cols, headers):
        d.text((cx + 6, sy + 48), hd, font=font(FONT_B, 10), fill=TEXT)
    d.line([434, sy + 66, W - 34, sy + 66], fill=BORDER)
    dtc_rows = [
        ("0x100000", "P0401", "Table DTC principale (P-codes + switch)", "ACTIF", "0x2F @ 0x100003"),
        ("0x100004", "P2002", "Table DTC principale (P-codes + switch)", "ACTIF", "0x2F @ 0x100007"),
        ("0x100008", "P2463", "Table DTC principale (P-codes + switch)", "ACTIF", "0x2F @ 0x10000B"),
        ("0x10000C", "P2263", "Table DTC principale (P-codes + switch)", "ACTIF", "0x08 @ 0x10000F"),
        ("0x100010", "P0100", "Table DTC principale (P-codes + switch)", "désactivé", "0x00 @ 0x100013"),
    ]
    for i, row in enumerate(dtc_rows):
        ry = sy + 74 + i * 18
        if i % 2 == 1:
            d.rectangle([430, ry - 2, W - 30, ry + 15], fill=ALT_ROW)
        for cx, val in zip(cols, row):
            d.text((cx + 6, ry), val, font=font(MONO, 10),
                   fill=OK if val == "ACTIF" else (DIM if val == "désactivé" else TEXT))
    button(d, 434, sy + gb_h - 36, 240, 28, "Désactiver les DTC sélectionnés", danger=True)
    d.text((690, sy + gb_h - 28), "16 DTC", font=font(FONT, 10), fill=DIM)

    # --- Export ---
    ey = H - 78
    button(d, 10, ey, 210, 30, "Exporter le .bin patché", primary=True)
    d.text((232, ey + 8), "⚠ [CHECKSUM] crc32 … valeur stockée inconnue : vérifiez/corrigez le checksum avant flash !",
           font=font(FONT, 10), fill=ERR)
    img.save(path)
    print("OK", path)


# ==========================================================================
# Onglet 3 : Comparateur Hexadécimal
# ==========================================================================
def render_tab3(path):
    img, d = base_window(2)
    top = TITLE_H + TAB_H + 12
    gb_h = H - top - 80
    groupbox(d, 10, top, W - 20, gb_h, "Octets modifiés (Offset | D'origine | Modifié)")
    d.text((24, top + 20), "Filtre :", font=font(FONT, 11), fill=TEXT)
    input_box(d, 80, top + 14, 400, 26, "")
    d.text((500, top + 20), "12 modification(s) affichée(s) / 12 total", font=font(FONT, 10), fill=DIM)
    cols = [30, 400, 700]
    for cx, hd in zip(cols, ["Offset", "D'origine", "Modifié"]):
        d.text((cx + 6, top + 52), hd, font=font(FONT_B, 11), fill=TEXT)
    d.line([20, top + 74, W - 20, top + 74], fill=BORDER)
    rows = [
        ("0x003000", "0x31", "0x56"), ("0x003001", "0x46", "0x46"), ("0x003008", "0x41", "0x5A"),
        ("0x003009", "0x42", "0x5A"), ("0x00300A", "0x42", "0x5A"), ("0x00300F", "0x31", "0x36"),
        ("0x040000", "0x31", "0x56"), ("0x040008", "0x41", "0x5A"), ("0x040009", "0x42", "0x5A"),
        ("0x04000A", "0x42", "0x5A"), ("0x100003", "0x2F", "0x00"), ("0x100007", "0x2F", "0x00"),
    ]
    for i, (off, orig, mod) in enumerate(rows):
        ry = top + 82 + i * 20
        if i % 2 == 1:
            d.rectangle([20, ry - 3, W - 20, ry + 16], fill=ALT_ROW)
        d.text((cols[0] + 6, ry), off, font=font(MONO, 11), fill=TEXT)
        d.text((cols[1] + 6, ry), orig, font=font(MONO, 11), fill=TEXT)
        d.text((cols[2] + 6, ry), mod, font=font(MONO, 11), fill=ACCENT)
    ey = H - 66
    button(d, 10, ey, 210, 30, "Exporter le .bin patché", primary=True)
    d.text((232, ey + 8), "Vérifiez le checksum avant export.", font=font(FONT, 10), fill=ERR)
    img.save(path)
    print("OK", path)


# ==========================================================================
# Onglet 4 : Gestionnaire de Définitions
# ==========================================================================
def render_tab4(path):
    img, d = base_window(3)
    top = TITLE_H + TAB_H + 12
    gb_h = H - top - 60

    groupbox(d, 10, top, 340, gb_h, "Définitions installées")
    files = ["bosch_edc17_generic_dtc.json", "psa_sid807_egr_dpf.json"]
    for i, name in enumerate(files):
        ly = top + 20 + i * 26
        sel = i == 0
        if sel:
            d.rounded_rectangle([20, ly - 3, 330, ly + 19], radius=4, fill=ALT_ROW, outline=ACCENT)
        d.text((30, ly), name, font=font(MONO, 11), fill=ACCENT if sel else TEXT)
    by = top + gb_h - 100
    button(d, 24, by, 90, 26, "Recharger")
    button(d, 122, by, 120, 26, "Nouveau (modèle)")
    button(d, 24, by + 34, 130, 26, "Importer un .json")

    rx = 360
    groupbox(d, rx, top, W - rx - 10, gb_h, "Éditeur JSON (validé à l'enregistrement)")
    ex, ey2 = rx + 14, top + 16
    d.rounded_rectangle([ex, ey2, W - 24, top + gb_h - 90], radius=6, fill=CONSOLE, outline=BORDER)
    json_lines = [
      '{',
      '  "schema_version": 1,',
      '  "definition_id": "bosch_edc17_generic_dtc",',
      '  "name": "Bosch EDC17 — DTC Remover générique (modèle)",',
      '  "manufacturer": "Bosch",',
      '  "ecu_families": ["EDC17C10", "EDC17C60", "EDC17CP44"],',
      '  "match": {',
      '    "id_patterns": ["EDC17"],',
      '    "min_size": 1048576,',
      '    "max_size": 8388608',
      '  },',
      '  "solutions": [',
      '    {',
      '      "id": "egr_off",',
      '      "label": "EGR Off",',
      '      "patches": [',
      '        {',
      '          "name": "EGR — contrôle d\'activation",',
      '          "find":    "48 8B ?? ?? 00 00 66 85 ?? 74 ??",',
      '          "replace": "48 8B ?? ?? 00 00 66 85 ?? EB ??"',
      '        }',
      '      ]',
      '    }',
      '  ],',
      '  "dtc_tables": [ ... ]',
      '}',
    ]
    for i, line in enumerate(json_lines):
        d.text((ex + 10, ey2 + 8 + i * 17), line, font=font(MONO, 10), fill=TEXT)
    vy2 = top + gb_h - 78
    d.text((ex, vy2), "✔ Valide : Bosch EDC17 — DTC Remover générique (modèle) — 4 solution(s), 2 table(s) DTC.",
           font=font(FONT, 10), fill=OK)
    button(d, ex, vy2 + 18, 150, 28, "Valider la syntaxe")
    button(d, ex + 160, vy2 + 18, 130, 28, "Enregistrer", primary=True)
    d.text((10, H - 40), "Astuce : les définitions sont des fichiers JSON dans le dossier 'definitions/' à côté de l'exécutable — ajoutez-en sans recompiler.",
           font=font(FONT, 10), fill=DIM)
    img.save(path)
    print("OK", path)


# ==========================================================================
# Assemblage sombre + clair côte à côte
# ==========================================================================
def render_side_by_side(render_fn, path, dark_path, light_path):
    render_fn(dark_path)
    use_theme(LIGHT_PALETTE)
    render_fn(light_path)
    use_theme(DARK_PALETTE)
    dark_img = Image.open(dark_path)
    light_img = Image.open(light_path)
    gutter = 8 * S
    combined = Image.new(
        "RGB", (dark_img.width + gutter + light_img.width, dark_img.height), "#7a8699"
    )
    combined.paste(dark_img, (0, 0))
    combined.paste(light_img, (dark_img.width + gutter, 0))
    combined.save(path)
    print("OK (sombre | clair)", path)


def crop(src, box_logical, dst):
    img = Image.open(src)
    x0, y0, x1, y1 = [v * S for v in box_logical]
    img.crop((x0, y0, x1, y1)).save(dst)
    print("OK", dst)


if __name__ == "__main__":
    use_theme(DARK_PALETTE)
    out = "/workspace/OpenECUStudio/docs/"
    tmp = "/tmp/"
    render_side_by_side(render_tab1, out + "preview_onglet1_diagnostic.png", tmp + "t1_dark.png", tmp + "t1_light.png")
    render_side_by_side(render_tab2, out + "preview_onglet2_patcher.png", tmp + "t2_dark.png", tmp + "t2_light.png")
    render_side_by_side(render_tab3, out + "preview_onglet3_comparateur.png", tmp + "t3_dark.png", tmp + "t3_light.png")
    render_side_by_side(render_tab4, out + "preview_onglet4_definitions.png", tmp + "t4_dark.png", tmp + "t4_light.png")

    crop(tmp + "t1_dark.png", (400, 212, 1260, 530), out + "zoom_uds_resultats.png")
    crop(tmp + "t1_dark.png", (10, 536, 1270, 850), out + "zoom_console_trames.png")
    crop(tmp + "t2_dark.png", (10, 74, 1270, 236), out + "zoom_identite_vin.png")
    crop(tmp + "t2_dark.png", (420, 380, 1270, 810), out + "zoom_table_dtc.png")
