"""Validation réelle du site statique (site/index.html).

Un code HTTP 200 sur la page d'accueil n'est pas une preuve suffisante : ce module
analyse le HTML généré, extrait tous les liens (href) et ressources (src), et vérifie
que chaque fichier référencé existe réellement sur le disque, à l'emplacement relatif
attendu, avec un contenu non vide. Les liens externes (http/https vers des domaines
autres que le site lui-même, ex. GitHub, Streamlit Cloud) sont recensés séparément
et signalés explicitement comme non vérifiables automatiquement (nécessitent une
connexion réseau), plutôt que d'être ignorés silencieusement.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parent.parent / "site"
INDEX_HTML = SITE_DIR / "index.html"


class _LinkExtractor(HTMLParser):
    """Extrait tous les attributs href/src du HTML, ainsi que le texte des balises."""

    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []  # (tag, url)
        self._current_tag = None
        self._current_attrs = None
        self.tags_seen: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags_seen.append(tag)
        attrs_dict = dict(attrs)
        if "href" in attrs_dict:
            self.links.append((tag, attrs_dict["href"]))
        if "src" in attrs_dict:
            self.links.append((tag, attrs_dict["src"]))


def _parse_site_html() -> _LinkExtractor:
    assert INDEX_HTML.exists(), f"site/index.html introuvable : {INDEX_HTML}"
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert content.strip(), "site/index.html est vide."
    parser = _LinkExtractor()
    parser.feed(content)
    return parser


def _is_external(url: str) -> bool:
    return bool(re.match(r"^(https?:)?//", url)) or url.startswith("http://") or url.startswith("https://")


def test_site_index_exists_and_not_empty():
    """La page d'accueil existe et contient du contenu HTML réel."""
    assert INDEX_HTML.exists()
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert len(content) > 500, "index.html semble anormalement court."
    assert "<html" in content.lower()


def test_site_index_has_title_and_headings():
    """La page contient un titre principal et des sections (h2)."""
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert "<h1>" in content, "Aucun titre principal (h1) trouvé."
    assert content.count("<h2>") >= 3, "Moins de 3 sections (h2) trouvées : structure incomplète."


def test_site_no_absolute_local_paths():
    """Aucun chemin absolu local (C:\\, /home/, Desktop) ne doit apparaître dans le HTML généré."""
    content = INDEX_HTML.read_text(encoding="utf-8")
    forbidden_patterns = [r"[A-Za-z]:\\", r"/home/[^/]+/", r"[Dd]esktop", r"[Dd]ocuments\\"]
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, content)
        assert not matches, f"Chemin local suspect trouvé ({pattern}) : {matches}"


def test_site_all_local_links_resolve_to_existing_files():
    """Chaque lien/ressource local (relatif) référencé dans le HTML pointe vers un fichier
    réellement présent sur le disque, non vide."""
    parser = _parse_site_html()
    local_links = [(tag, url) for tag, url in parser.links if not _is_external(url) and not url.startswith("#")]
    assert local_links, "Aucun lien local trouvé dans la page : structure suspecte."

    broken = []
    empty = []
    for tag, url in local_links:
        clean_url = url.split("#")[0].split("?")[0]
        if not clean_url:
            continue
        target = (SITE_DIR / clean_url).resolve()
        if not target.exists():
            broken.append((tag, url))
        elif target.is_file() and target.stat().st_size == 0:
            empty.append((tag, url))

    assert not broken, f"Lien(s) cassé(s) trouvé(s) (fichier introuvable) : {broken}"
    assert not empty, f"Ressource(s) vide(s) trouvée(s) : {empty}"


def test_site_figures_directory_matches_links():
    """Toutes les images référencées dans le HTML existent physiquement dans site/figures/."""
    parser = _parse_site_html()
    img_links = [url for tag, url in parser.links if tag == "img"]
    assert img_links, "Aucune image référencée dans le site."
    for url in img_links:
        target = (SITE_DIR / url).resolve()
        assert target.exists(), f"Image référencée mais introuvable : {url}"
        assert target.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".webp"}, f"Extension inattendue : {url}"


def test_site_tables_links_point_to_csv_files():
    """Les liens vers les tableaux pointent vers des fichiers .csv existants et non vides."""
    parser = _parse_site_html()
    csv_links = [url for tag, url in parser.links if tag == "a" and url.endswith(".csv")]
    assert csv_links, "Aucun lien vers un tableau CSV trouvé."
    for url in csv_links:
        target = (SITE_DIR / url).resolve()
        assert target.exists(), f"Tableau référencé mais introuvable : {url}"
        assert target.stat().st_size > 0, f"Tableau vide : {url}"


def test_site_report_link_points_to_existing_markdown():
    """Le lien vers le rapport final pointe vers un fichier Markdown existant et non vide."""
    parser = _parse_site_html()
    report_links = [url for tag, url in parser.links if tag == "a" and url.endswith(".md")]
    assert report_links, "Aucun lien vers le rapport final (.md) trouvé."
    for url in report_links:
        target = (SITE_DIR / url).resolve()
        assert target.exists(), f"Rapport référencé mais introuvable : {url}"
        assert target.stat().st_size > 0, f"Rapport vide : {url}"


def test_site_external_links_are_well_formed_and_flagged():
    """Les liens externes (GitHub, dashboard public) sont syntaxiquement valides ; ils sont
    listés explicitement car leur disponibilité réseau n'est pas vérifiable en local."""
    parser = _parse_site_html()
    external_links = [(tag, url) for tag, url in parser.links if _is_external(url)]
    assert external_links, "Aucun lien externe trouvé (GitHub / dashboard attendus)."
    for _tag, url in external_links:
        assert url.startswith("http://") or url.startswith("https://"), f"URL externe mal formée : {url}"

    # Les URLs placeholders doivent être clairement identifiables comme telles pour ne pas
    # être confondues avec de vraies ressources publiées.
    placeholder_markers = ("votre-organisation", "votre-espace-streamlit")
    flagged_placeholders = [url for _tag, url in external_links if any(m in url for m in placeholder_markers)]
    if flagged_placeholders:
        pytest.skip(
            "Liens externes non vérifiables automatiquement (placeholders à remplacer manuellement) : "
            f"{flagged_placeholders}"
        )


def test_site_relative_paths_only_for_local_resources():
    """Toutes les ressources locales (figures, tableaux, rapports) utilisent des chemins
    relatifs, jamais de chemin absolu ni de protocole file://."""
    parser = _parse_site_html()
    local_links = [(tag, url) for tag, url in parser.links if not _is_external(url)]
    for _tag, url in local_links:
        assert not url.startswith("/"), f"Chemin absolu (depuis la racine) détecté : {url}"
        assert not url.startswith("file://"), f"Chemin file:// détecté : {url}"


def test_site_directories_are_non_empty():
    """Les dossiers figures/, tables/, reports/ du site publié contiennent bien des fichiers."""
    for sub in ("figures", "tables", "reports"):
        directory = SITE_DIR / sub
        assert directory.exists(), f"Dossier manquant : {directory}"
        files = [f for f in directory.iterdir() if f.is_file() and f.name != ".gitkeep"]
        assert files, f"Dossier vide (hors .gitkeep) : {directory}"
        for f in files:
            assert f.stat().st_size > 0, f"Fichier vide trouvé : {f}"
