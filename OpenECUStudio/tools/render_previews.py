# -*- coding: utf-8 -*-
"""Génère des aperçus PNG de l'interface OpenECU Studio (rendu fidèle au thème).

Le sandbox d'exécution est Linux headless sans libGL : Qt ne peut pas y être
rendu. Ce script reproduit pixel-faithful la disposition et les couleurs
définies dans ui/theme.py pour donner un aperçu visuel de l'application.
"""
from PIL import Image, ImageDraw, ImageFont

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

BG = "#121417"
PANEL = "#1b1f24"
BORDER = "#2c333c"
TEXT = "#d8dee7"
DIM = "#8b95a3"
ACCENT = "#e8a33d"
OK = "#5cbf60"
ERR = "#e05555"
CONSOLE = "#0d0f12"
BTN = "#262c34"
BTN_HOVER = "#323a45"

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
    d.text((10, 6), "OpenECU Studio v1.0.0 — J2534 / UDS / ECU Patcher", font=font(FONT, 13), fill=TEXT)
    d.ellipse([W - 46, 8, W - 34, 20], outline=DIM, width=1)
    d.ellipse([W - 26, 8, W - 14, 20], outline=DIM, width=1)
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
            d.line([box[0], box[1], box[2], box[1]], fill=ACCENT, width=2)
            d.text((x + pad, TITLE_H + 12), label, font=f, fill=ACCENT)
        else:
            d.rectangle(box, fill=BG, outline=BORDER)
            d.text((x + pad, TITLE_H + 12), label, font=f, fill=DIM)
        x += tw + 2 * pad + 4
    d.rectangle([0, TITLE_H + TAB_H, W, H], fill=PANEL, outline=BORDER)
    return img, d


def groupbox(d, x, y, w, h, title):
    d.rounded_rectangle([x, y, x + w, y + h], radius=6, fill="#1b1f24", outline=BORDER, width=1)
    f = font(FONT_B, 11)
    tw = d.textlength(title, font=f)
    d.rectangle([x + 8, y - 8, x + 16 + tw, y + 8], fill=PANEL)
    d.text((x + 16, y - 7), title, font=f, fill=ACCENT)


def button(d, x, y, w, h, label, primary=False, danger=False, enabled=True):
    if primary and enabled:
        fill, fg = ACCENT, "#14161a"
    elif danger and enabled:
        fill, fg = ERR, "#ffffff"
    else:
        fill, fg = ("#1a1e23", "#5a626d") if not enabled else (BTN, TEXT)
    d.rounded_rectangle([x, y, x + w, y + h], radius=4, fill=fill, outline=None if (primary or danger) and enabled else BORDER)
    f = font(FONT_B if (primary or danger) else FONT, 11)
    tw = d.textlength(label, font=f)
    d.text((x + (w - tw) / 2, y + (h - 14) / 2 - 1), label, font=f, fill=fg)


def input_box(d, x, y, w, h, text, mono=False, color=TEXT):
    d.rounded_rectangle([x, y, x + w, y + h], radius=4, fill=CONSOLE, outline=BORDER)
    d.text((x + 8, y + (h - 12) / 2), text, font=font(MONO if mono else FONT, 11), fill=color)


# ==========================================================================
# Onglet 1 : Diagnostic & SM2 Pro
# ==========================================================================
def render_tab1(path):
    img, d = base_window(0)
    top = TITLE_H + TAB_H + 12

    # --- Interface J2534 ---
    groupbox(d, 10, top, W - 20, 64, "Interface J2534 (SAE PassThru 04.04)")
    y = top + 18
    d.text((24, y + 10), "Interface :", font=font(FONT, 11), fill=TEXT)
    input_box(d, 100, y, 420, 28, "SM2 USB  [C:\\Program Files (x86)\\Scanmatik\\smj2534.dll]")
    button(d, 530, y, 90, 28, "Rafraîchir")
    button(d, 630, y, 110, 28, "Se connecter", primary=True)
    button(d, 750, y, 110, 28, "Déconnecter", enabled=False)

    # --- VBatt + UDS ---
    mid = top + 76
    gb_h = 300
    groupbox(d, 10, mid, 380, gb_h, "Tension batterie (VBatt — pin 16)")
    d.text((200, mid + 60), "12.47 V", font=font(MONO_B, 34), fill=OK, anchor="mm")
    d.text((200, mid + 110), "Lecture temps réel (1 Hz)", font=font(FONT, 10), fill=DIM, anchor="mm")

    groupbox(d, 400, mid, W - 420, gb_h, "Diagnostic UDS (ISO 14229 — CAN 500 kbps, 0x7E0/0x7E8)")
    ux, uy = 414, mid + 16
    button(d, ux, uy, 190, 28, "Identifier ECU (UDS)", primary=True)
    button(d, ux + 200, uy, 190, 28, "Session étendue (10 03)")
    button(d, ux, uy + 36, 190, 28, "Lire les DTC (19 02 FF)")
    button(d, ux, uy + 72, 190, 28, "Effacer les DTC (14 FF FF FF)", danger=True)
    tx, ty = ux + 200, uy + 36
    d.rounded_rectangle([tx, ty, ux + 390, mid + gb_h - 14], radius=4, fill=CONSOLE, outline=BORDER)
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
        d.text((tx + 8, ty + 8 + i * 16), line, font=font(MONO, 10), fill=TEXT)

    # --- Console ---
    cy = mid + gb_h + 12
    groupbox(d, 10, cy, W - 20, H - cy - 40, "Console trames CAN / UDS brutes")
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
        color = "#9fd49f" if " TX " in line else "#7fbf7f"
        d.text((24, cy + 16 + i * 17), line, font=font(MONO, 11), fill=color)

    d.text((10, H - 24), "Connecté : SM2 USB — ISO 15765 @ 500 kbps", font=font(FONT, 10), fill=DIM)
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
    button(d, 24, top + 16, 180, 28, "Charger un fichier ECU", primary=True)
    button(d, 212, top + 16, 190, 28, "Restaurer une sauvegarde .bak")
    button(d, 410, top + 16, 210, 28, "Annuler les modifications (session)")
    d.text((630, top + 24), "C:\\Dumps\\edc17c10_origine.bin", font=font(FONT, 10), fill=DIM)
    rows = [
        ("Famille détectée :", "EDC17C10 (Élevée)"),
        ("Constructeur ECU :", "Bosch"),
        ("Taille :", "2097152 octets (0x200000)"),
        ("Entropie :", "7.894 bits/octet"),
        ("N° de pièce :", "0281020304"),
        ("SAUVEGARDE :", "edc17c10_origine_20250101_120000.bak"),
    ]
    for i, (k, v) in enumerate(rows):
        ry = top + 52 + i * 15
        d.text((30, ry), k, font=font(FONT, 10), fill=DIM)
        d.rounded_rectangle([150, ry - 2, 560, ry + 13], radius=2, fill=CONSOLE, outline=BORDER)
        d.text((158, ry), v, font=font(MONO, 10), fill=TEXT)

    # --- VIN ---
    vy = top + 152
    groupbox(d, 10, vy, W - 20, 56, "Réemploi d'un calculateur d'occasion — VIN")
    d.text((24, vy + 20), "2 occurrence(s) : VF3MABBB1BB123456   @ 0x003000, 0x040000", font=font(MONO, 10), fill=TEXT)
    input_box(d, 700, vy + 14, 340, 26, "VF3MZZZZ6ZZ654321", mono=True)
    button(d, 1050, vy + 14, 200, 26, "Remplacer le VIN dans le dump", primary=True)

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
        cy_ = sy + 20 + i * 24
        d.rectangle([24, cy_, 38, cy_ + 14], fill=ACCENT if checked else CONSOLE, outline=BORDER)
        if checked:
            d.line([27, cy_ + 7, 32, cy_ + 12], fill="#14161a", width=2)
            d.line([32, cy_ + 12, 36, cy_ + 3], fill="#14161a", width=2)
        d.text((48, cy_), label, font=font(FONT, 11), fill=TEXT)
    button(d, 24, sy + gb_h - 40, 230, 28, "Appliquer les solutions cochées", primary=True)

    groupbox(d, 420, sy, W - 440, gb_h, "DTC détectés dans le dump (DTC Remover)")
    input_box(d, 434, sy + 14, 500, 26, "P0401")
    button(d, 944, sy + 14, 80, 26, "Scanner")
    cols = [434, 560, 660, 940, 1030]
    headers = ["Offset", "Code", "Table", "État", "Switch"]
    for cx, hd in zip(cols, headers):
        d.text((cx + 6, sy + 48), hd, font=font(FONT_B, 10), fill=ACCENT)
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
            d.rectangle([430, ry - 2, W - 30, ry + 15], fill="#14181d")
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
    groupbox(d, 10, top, W - 20, gb_h, "Octets modifiés (Offset | Original | Modifié)")
    d.text((24, top + 20), "Filtre :", font=font(FONT, 11), fill=TEXT)
    input_box(d, 80, top + 14, 400, 26, "")
    d.text((500, top + 20), "12 modification(s) affichée(s) / 12 total", font=font(FONT, 10), fill=DIM)
    cols = [30, 400, 700]
    for cx, hd in zip(cols, ["Offset", "Original", "Modifié"]):
        d.text((cx + 6, top + 52), hd, font=font(FONT_B, 11), fill=ACCENT)
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
            d.rectangle([20, ry - 3, W - 20, ry + 16], fill="#14181d")
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
            d.rounded_rectangle([20, ly - 3, 330, ly + 19], radius=3, fill="#2a3140")
        d.text((30, ly), name, font=font(MONO, 11), fill=ACCENT if sel else TEXT)
    by = top + gb_h - 100
    button(d, 24, by, 90, 26, "Recharger")
    button(d, 122, by, 120, 26, "Nouveau (modèle)")
    button(d, 24, by + 34, 130, 26, "Importer un .json")

    rx = 360
    groupbox(d, rx, top, W - rx - 10, gb_h, "Éditeur JSON (validé à l'enregistrement)")
    ex, ey_ = rx + 14, top + 16
    d.rounded_rectangle([ex, ey_, W - 24, top + gb_h - 90], radius=4, fill=CONSOLE, outline=BORDER)
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
        d.text((ex + 10, ey_ + 8 + i * 17), line, font=font(MONO, 10), fill="#9fd49f")
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
# Gros plans (crops haute résolution depuis les rendus 2x)
# ==========================================================================
def crop(src, box_logical, dst):
    img = Image.open(src)
    x0, y0, x1, y1 = [v * S for v in box_logical]
    img.crop((x0, y0, x1, y1)).save(dst)
    print("OK", dst)


OUT = "/workspace/OpenECUStudio/docs/"
render_tab1(OUT + "preview_onglet1_diagnostic.png")
render_tab2(OUT + "preview_onglet2_patcher.png")
render_tab3(OUT + "preview_onglet3_comparateur.png")
render_tab4(OUT + "preview_onglet4_definitions.png")

crop(OUT + "preview_onglet1_diagnostic.png", (400, 150, 1260, 460), OUT + "zoom_uds_resultats.png")
crop(OUT + "preview_onglet1_diagnostic.png", (10, 462, 1270, 830), OUT + "zoom_console_trames.png")
crop(OUT + "preview_onglet2_patcher.png", (10, 74, 1270, 230), OUT + "zoom_identite_vin.png")
crop(OUT + "preview_onglet2_patcher.png", (420, 336, 1270, 780), OUT + "zoom_table_dtc.png")
