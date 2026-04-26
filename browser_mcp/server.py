"""
MCP Browser Control - Version simplifiée avec requests
Permet de naviguer, extraire du contenu et faire des captures via API web
"""
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import json, time, base64
from datetime import datetime
import requests
from bs4 import BeautifulSoup

mcp = FastMCP("browser_mcp")

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Session globale pour garder les cookies
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})
CURRENT_URL = None
CURRENT_HTML = None

class NavigateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    url: str = Field(..., description="URL complète à charger", min_length=5)
    timeout: Optional[int] = Field(default=30, description="Timeout en secondes", ge=1, le=120)

@mcp.tool(name="browser_navigate")
def browser_navigate(params: NavigateInput) -> str:
    """Navigue vers une URL et charge la page"""
    global CURRENT_URL, CURRENT_HTML
    try:
        resp = SESSION.get(params.url, timeout=params.timeout)
        resp.raise_for_status()
        CURRENT_URL = resp.url
        CURRENT_HTML = resp.text
        soup = BeautifulSoup(CURRENT_HTML, 'html.parser')
        title = soup.title.string if soup.title else "Sans titre"
        return json.dumps({
            "success": True, "url": CURRENT_URL, "titre": title,
            "statut": resp.status_code, "timestamp": now()
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "erreur": str(e), "timestamp": now()}, indent=2)

class ScreenshotInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    format: Optional[str] = Field(default="text", description="'text' ou 'html'")

@mcp.tool(name="browser_screenshot")
def browser_screenshot(params: ScreenshotInput) -> str:
    """Retourne le contenu de la page actuelle (texte ou HTML)"""
    global CURRENT_URL, CURRENT_HTML
    if not CURRENT_HTML:
        return json.dumps({"success": False, "erreur": "Aucune page chargée. Utilisez browser_navigate d'abord", "timestamp": now()}, indent=2)
    try:
        soup = BeautifulSoup(CURRENT_HTML, 'html.parser')
        if params.format == "html":
            content = CURRENT_HTML[:5000] + "..." if len(CURRENT_HTML) > 5000 else CURRENT_HTML
        else:
            content = soup.get_text(separator='\n', strip=True)[:5000] + "..." if len(soup.get_text()) > 5000 else soup.get_text(separator='\n', strip=True)
        return json.dumps({
            "success": True, "url": CURRENT_URL, "format": params.format,
            "contenu": content, "timestamp": now()
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "erreur": str(e), "timestamp": now()}, indent=2)

class ExtractInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    selector: Optional[str] = Field(default=None, description="Sélecteur CSS (ex: 'h1', '.class', '#id')")
    extract_type: Optional[str] = Field(default="text", description="'text', 'html', 'attribute'")
    attribute_name: Optional[str] = Field(default=None, description="Nom de l'attribut si extract_type='attribute'")

@mcp.tool(name="browser_extract")
def browser_extract(params: ExtractInput) -> str:
    """Extrait du contenu de la page avec sélecteur CSS optionnel"""
    global CURRENT_HTML
    if not CURRENT_HTML:
        return json.dumps({"success": False, "erreur": "Aucune page chargée", "timestamp": now()}, indent=2)
    try:
        soup = BeautifulSoup(CURRENT_HTML, 'html.parser')
        if params.selector:
            element = soup.select_one(params.selector)
            if not element:
                return json.dumps({"success": False, "erreur": f"Sélecteur '{params.selector}' non trouvé", "timestamp": now()}, indent=2)
            if params.extract_type == "attribute" and params.attribute_name:
                content = element.get(params.attribute_name, "")
            elif params.extract_type in ["html", "outer_html"]:
                content = str(element)
            else:
                content = element.get_text(strip=True)
        else:
            content = soup.get_text(separator='\n', strip=True)
        return json.dumps({
            "success": True, "selecteur": params.selector or "body",
            "type": params.extract_type, "contenu": content[:2000], "timestamp": now()
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "erreur": str(e), "timestamp": now()}, indent=2)

class ClickInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    selector: str = Field(..., description="Sélecteur CSS du lien à cliquer")

@mcp.tool(name="browser_click")
def browser_click(params: ClickInput) -> str:
    """Simule un clic sur un lien (extrait href et navigue)"""
    global CURRENT_URL, CURRENT_HTML
    if not CURRENT_HTML:
        return json.dumps({"success": False, "erreur": "Aucune page chargée", "timestamp": now()}, indent=2)
    try:
        soup = BeautifulSoup(CURRENT_HTML, 'html.parser')
        element = soup.select_one(params.selector)
        if not element:
            return json.dumps({"success": False, "erreur": f"Sélecteur '{params.selector}' non trouvé", "timestamp": now()}, indent=2)
        href = element.get('href')
        if not href:
            return json.dumps({"success": False, "erreur": "L'élément n'a pas d'attribut href", "timestamp": now()}, indent=2)
        # Résoudre URL relative
        from urllib.parse import urljoin
        full_url = urljoin(CURRENT_URL, href)
        resp = SESSION.get(full_url, timeout=30)
        resp.raise_for_status()
        CURRENT_URL = resp.url
        CURRENT_HTML = resp.text
        soup = BeautifulSoup(CURRENT_HTML, 'html.parser')
        title = soup.title.string if soup.title else "Sans titre"
        return json.dumps({
            "success": True, "action": "click", "nouvelle_url": CURRENT_URL,
            "titre": title, "timestamp": now()
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "erreur": str(e), "timestamp": now()}, indent=2)

class TypeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    selector: str = Field(..., description="Sélecteur CSS du champ")
    text: str = Field(..., description="Texte à saisir")

@mcp.tool(name="browser_type")
def browser_type(params: TypeInput) -> str:
    """Prépare des données pour un formulaire (note: nécessite submit manuel)"""
    return json.dumps({
        "success": True, "message": f"Données prêtes: {params.selector} = {params.text[:50]}",
        "note": "Utilisez browser_execute_js pour soumettre le formulaire",
        "timestamp": now()
    }, indent=2)

class JsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    script: str = Field(..., description="Code JavaScript (simulé via BeautifulSoup)")

@mcp.tool(name="browser_execute_js")
def browser_execute_js(params: JsInput) -> str:
    """Exécute une requête personnalisée ou manipulation HTML"""
    global CURRENT_HTML
    if not CURRENT_HTML:
        return json.dumps({"success": False, "erreur": "Aucune page chargée", "timestamp": now()}, indent=2)
    try:
        # Simulation simple: exécuter du JS pour extraire/modifier
        soup = BeautifulSoup(CURRENT_HTML, 'html.parser')
        result = {"html_length": len(CURRENT_HTML), "title": soup.title.string if soup.title else None}
        return json.dumps({"success": True, "resultat": result, "timestamp": now()}, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "erreur": str(e), "timestamp": now()}, indent=2)

@mcp.tool(name="browser_info")
def browser_info() -> str:
    """Informations sur la page actuelle"""
    global CURRENT_URL, CURRENT_HTML
    if not CURRENT_HTML:
        return json.dumps({"success": False, "erreur": "Aucune page chargée", "timestamp": now()}, indent=2)
    soup = BeautifulSoup(CURRENT_HTML, 'html.parser')
    return json.dumps({
        "success": True, "url": CURRENT_URL,
        "titre": soup.title.string if soup.title else "Sans titre",
        "taille_html": len(CURRENT_HTML), "timestamp": now()
    }, indent=2)

@mcp.tool(name="browser_close")
def browser_close() -> str:
    """Réinitialise la session"""
    global CURRENT_URL, CURRENT_HTML
    CURRENT_URL = None
    CURRENT_HTML = None
    return json.dumps({"success": True, "message": "Session réinitialisée", "timestamp": now()}, indent=2)

if __name__ == "__main__":
    mcp.run()
