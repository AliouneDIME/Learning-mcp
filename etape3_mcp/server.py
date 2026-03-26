"""
╔══════════════════════════════════════════════════════════════════╗
║   ÉTAPE 3 — 6 APIs Publiques (source : public-apis/public-apis) ║
║                                                                  ║
║  ZÉRO clé API · ZÉRO inscription · Tout fonctionne maintenant   ║
║                                                                  ║
║  APIs intégrées :                                               ║
║  1. Open-Meteo       → Météo mondiale (Weather)                 ║
║  2. ExchangeRate-API → Taux de change (Currency Exchange)       ║
║  3. JokeAPI          → Blagues (Entertainment)                  ║
║  4. Quotable         → Citations célèbres (Personality)         ║
║  5. PokeAPI          → Données Pokémon (Games & Comics)         ║
║  6. REST Countries   → Infos pays du monde (Geocoding)          ║
╚══════════════════════════════════════════════════════════════════╝
"""
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import json, sys, httpx
from datetime import datetime

OPEN_METEO_GEO_URL      = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
EXCHANGERATE_URL        = "https://api.exchangerate-api.com/v4/latest"
JOKE_API_URL            = "https://v2.jokeapi.dev/joke"
QUOTABLE_URL            = "https://api.quotable.io"
POKE_API_URL            = "https://pokeapi.co/api/v2"
REST_COUNTRIES_URL      = "https://restcountries.com/v3.1"
HTTP_TIMEOUT            = 15.0

def get_http_client():
    return httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": "AssistantMCP/3.0", "Accept": "application/json"},
        follow_redirects=True
    )

def handle_error(e, service):
    if isinstance(e, httpx.TimeoutException):
        msg, tip = f"Timeout : {service} ne repond pas", "Reessaie dans quelques secondes"
    elif isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        msg = f"Erreur HTTP {code} sur {service}"
        tip = {404: "Ressource introuvable", 429: "Trop de requetes, attends 1 min"}.get(code, "Verifie ta connexion")
    elif isinstance(e, httpx.ConnectError):
        msg, tip = f"Connexion impossible a {service}", "Verifie ta connexion internet"
    else:
        msg, tip = f"Erreur ({type(e).__name__}): {str(e)}", "Reessaie"
    return json.dumps({"success": False, "service": service, "erreur": msg, "suggestion": tip}, ensure_ascii=False, indent=2)

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

mcp = FastMCP("assistant_mcp")

# ── OUTIL 1 : MÉTÉO (Open-Meteo) ──────────────────────────────────────────────
class WeatherInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    city: str = Field(..., description="Nom de la ville (ex: 'Paris', 'Dakar', 'Tokyo')", min_length=2, max_length=100)
    units: Optional[str] = Field(default="celsius", description="'celsius' ou 'fahrenheit'")

@mcp.tool(name="get_weather", annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True})
async def get_weather(params: WeatherInput) -> str:
    """
    Meteo actuelle d'une ville via Open-Meteo (sans cle API).
    Source: public-apis -> Weather -> Open-Meteo
    Enchaine 2 appels API : geocodage ville -> coordonnees -> meteo.
    Args: city (str), units ('celsius' ou 'fahrenheit')
    Returns: JSON avec temperature, ressenti, humidite, vent, UV, previsions du jour
    """
    units = params.units if params.units in ["celsius", "fahrenheit"] else "celsius"
    symbol = "C" if units == "celsius" else "F"
    wmo = {0:"Ciel degage",1:"Principalement degage",2:"Partiellement nuageux",3:"Couvert",
           45:"Brouillard",61:"Pluie legere",63:"Pluie",65:"Pluie forte",
           71:"Neige legere",80:"Averses",95:"Orage",99:"Orage violent"}
    async with get_http_client() as client:
        try:
            geo = await client.get(OPEN_METEO_GEO_URL, params={"name": params.city, "count": 1, "language": "fr", "format": "json"})
            geo.raise_for_status()
            geo_data = geo.json()
            if not geo_data.get("results"):
                return json.dumps({"success": False, "erreur": f"Ville '{params.city}' introuvable", "suggestion": "Essaie un nom plus precis ou en anglais"}, ensure_ascii=False, indent=2)
            loc = geo_data["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]
            city_name = f"{loc['name']}, {loc.get('country', '')}"
            w = await client.get(OPEN_METEO_FORECAST_URL, params={
                "latitude": lat, "longitude": lon,
                "current": ["temperature_2m","apparent_temperature","relative_humidity_2m","precipitation","weather_code","wind_speed_10m","uv_index"],
                "daily": ["temperature_2m_max","temperature_2m_min","precipitation_sum"],
                "temperature_unit": units, "wind_speed_unit": "kmh", "timezone": "auto", "forecast_days": 1
            })
            w.raise_for_status()
            wd = w.json()
            c = wd["current"]
            d = wd["daily"]
            return json.dumps({
                "success": True, "ville": city_name,
                "actuel": {
                    "description": wmo.get(c.get("weather_code", 0), "N/A"),
                    "temperature": f"{c['temperature_2m']} {symbol}",
                    "ressenti": f"{c['apparent_temperature']} {symbol}",
                    "humidite": f"{c['relative_humidity_2m']}%",
                    "vent": f"{c['wind_speed_10m']} km/h",
                    "precipitations": f"{c['precipitation']} mm",
                    "indice_uv": c.get("uv_index", "N/A")
                },
                "previsions_jour": {"max": f"{d['temperature_2m_max'][0]} {symbol}", "min": f"{d['temperature_2m_min'][0]} {symbol}"},
                "source": "open-meteo.com (Auth: No)", "timestamp": now()
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            return handle_error(e, "Open-Meteo")

# ── OUTIL 2 : TAUX DE CHANGE (ExchangeRate-API) ───────────────────────────────
class ExchangeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    base: str = Field(..., description="Devise source ISO 4217 (ex: 'EUR', 'USD', 'XOF', 'MAD')", min_length=3, max_length=3)
    targets: Optional[list[str]] = Field(default=None, description="Devises cibles (ex: ['USD','GBP']). Vide = top 15.")
    amount: Optional[float] = Field(default=1.0, description="Montant a convertir. Defaut: 1.0", gt=0)

@mcp.tool(name="get_exchange_rate", annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True})
async def get_exchange_rate(params: ExchangeInput) -> str:
    """
    Taux de change en temps reel via ExchangeRate-API (sans cle).
    Source: public-apis -> Currency Exchange
    Supporte EUR, USD, XOF, MAD, DZD, NGN et toutes devises ISO 4217.
    Args: base (str), targets (list optionnel), amount (float)
    Returns: JSON avec taux et montants convertis
    """
    base = params.base.upper()
    async with get_http_client() as client:
        try:
            r = await client.get(f"{EXCHANGERATE_URL}/{base}")
            r.raise_for_status()
            data = r.json()
            if "rates" not in data:
                return json.dumps({"success": False, "erreur": f"Devise '{base}' non reconnue", "suggestion": "Utilise un code ISO 4217 valide"}, ensure_ascii=False, indent=2)
            all_rates = data["rates"]
            if params.targets:
                targets = [c.upper() for c in params.targets]
                rates = {c: all_rates[c] for c in targets if c in all_rates}
            else:
                defaults = ["EUR","USD","GBP","CHF","JPY","CAD","XOF","XAF","MAD","DZD","EGP","NGN","GHS","KES","TND"]
                rates = {c: all_rates[c] for c in defaults if c in all_rates}
            conversions = {
                currency: {"taux": rate, "converti": round(params.amount * rate, 4),
                           "formule": f"{params.amount} {base} = {round(params.amount * rate, 4)} {currency}"}
                for currency, rate in rates.items()
            }
            return json.dumps({"success": True, "base": base, "montant": params.amount,
                               "mise_a_jour": data.get("time_last_update_utc","N/A"),
                               "conversions": conversions, "source": "exchangerate-api.com (Auth: No)"}, ensure_ascii=False, indent=2)
        except Exception as e:
            return handle_error(e, "ExchangeRate-API")

# ── OUTIL 3 : BLAGUES (JokeAPI) ───────────────────────────────────────────────
class JokeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    category: Optional[str] = Field(default="Any", description="Categorie: 'Any','Programming','Misc','Dark','Pun','Spooky','Christmas'")
    language: Optional[str] = Field(default="fr", description="Langue: 'fr','en','de','es','pt','cs'")
    safe_mode: Optional[bool] = Field(default=True, description="Mode sans contenu adulte (True par defaut)")

@mcp.tool(name="get_joke", annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True})
async def get_joke(params: JokeInput) -> str:
    """
    Blague aleatoire via JokeAPI (sans cle).
    Source: public-apis -> Entertainment -> JokeAPI
    Supporte plusieurs categories et langues dont le francais.
    Args: category (str), language (str), safe_mode (bool)
    Returns: JSON avec la blague (question/reponse ou directe)
    """
    category = params.category or "Any"
    lang = params.language or "fr"
    query_params = {"lang": lang, "amount": 1}
    if params.safe_mode:
        query_params["safe-mode"] = "true"
    async with get_http_client() as client:
        try:
            r = await client.get(f"{JOKE_API_URL}/{category}", params=query_params)
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                return json.dumps({"success": False, "erreur": data.get("message","Erreur JokeAPI"),
                                   "suggestion": "Categories valides: Any, Programming, Misc, Dark, Pun"}, ensure_ascii=False, indent=2)
            if data["type"] == "twopart":
                blague = {"type": "question_reponse", "question": data["setup"], "reponse": data["delivery"]}
            else:
                blague = {"type": "directe", "texte": data["joke"]}
            return json.dumps({"success": True, "categorie": data.get("category", category),
                               "langue": lang, "blague": blague, "source": "jokeapi.dev (Auth: No)"}, ensure_ascii=False, indent=2)
        except Exception as e:
            return handle_error(e, "JokeAPI")

# ── OUTIL 4 : CITATIONS (Quotable) ────────────────────────────────────────────
class QuoteInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    author: Optional[str] = Field(default=None, description="Auteur (ex: 'Albert Einstein', 'Nelson Mandela'). Vide = aleatoire.")
    tag: Optional[str] = Field(default=None, description="Theme (ex: 'wisdom','success','life','love','technology','science')")
    count: Optional[int] = Field(default=1, description="Nombre de citations (1-5)", ge=1, le=5)

@mcp.tool(name="get_quote", annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True})
async def get_quote(params: QuoteInput) -> str:
    """
    Citations celebres via Quotable (sans cle).
    Source: public-apis -> Personality -> Quotable
    Milliers de citations de personnalites celebres du monde entier.
    Args: author (str optionnel), tag (str optionnel), count (int 1-5)
    Returns: JSON avec citation(s), auteur(s) et tags associes
    """
    query_params: dict = {"limit": params.count}
    if params.author:
        query_params["author"] = params.author
    if params.tag:
        query_params["tags"] = params.tag
    async with get_http_client() as client:
        try:
            r = await client.get(f"{QUOTABLE_URL}/quotes/random", params=query_params)
            r.raise_for_status()
            data = r.json()
            if not data:
                return json.dumps({"success": False, "erreur": "Aucune citation trouvee",
                                   "suggestion": "Essaie sans filtre d'auteur ou change le tag"}, ensure_ascii=False, indent=2)
            citations = [{"texte": q.get("content",""), "auteur": q.get("author","Inconnu"),
                          "tags": q.get("tags",[]), "longueur": q.get("length",0)} for q in data]
            return json.dumps({"success": True, "nombre": len(citations), "filtre_auteur": params.author,
                               "filtre_tag": params.tag, "citations": citations,
                               "source": "api.quotable.io (Auth: No)"}, ensure_ascii=False, indent=2)
        except Exception as e:
            return handle_error(e, "Quotable")

# ── OUTIL 5 : POKÉMON (PokeAPI) ───────────────────────────────────────────────
class PokeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(..., description="Nom ou numero du Pokemon en anglais (ex: 'pikachu', 'charizard', '25')", min_length=1, max_length=50)

@mcp.tool(name="get_pokemon", annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def get_pokemon(params: PokeInput) -> str:
    """
    Donnees d'un Pokemon via PokeAPI (sans cle).
    Source: public-apis -> Games & Comics -> PokeAPI
    Base de donnees complete de tous les Pokemon avec stats, types, capacites.
    Args: name (str) - nom ou numero du Pokemon en anglais
    Returns: JSON avec types, stats, taille, poids, capacites
    """
    async with get_http_client() as client:
        try:
            r = await client.get(f"{POKE_API_URL}/pokemon/{params.name.lower().strip()}")
            r.raise_for_status()
            p = r.json()
            stats = {s["stat"]["name"]: s["base_stat"] for s in p.get("stats", [])}
            moves = [m["move"]["name"] for m in p.get("moves", [])[:4]]
            return json.dumps({
                "success": True,
                "nom": p["name"].capitalize(), "numero": p["id"],
                "types": [t["type"]["name"] for t in p.get("types", [])],
                "taille": f"{p.get('height', 0) / 10} m",
                "poids": f"{p.get('weight', 0) / 10} kg",
                "stats_base": {"hp": stats.get("hp",0), "attaque": stats.get("attack",0),
                               "defense": stats.get("defense",0), "vitesse": stats.get("speed",0)},
                "capacites_exemples": moves,
                "source": "pokeapi.co (Auth: No)"
            }, ensure_ascii=False, indent=2)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return json.dumps({"success": False, "erreur": f"Pokemon '{params.name}' introuvable",
                                   "suggestion": "Utilise le nom anglais (pikachu, charizard) ou le numero (25)"}, ensure_ascii=False, indent=2)
            return handle_error(e, "PokeAPI")
        except Exception as e:
            return handle_error(e, "PokeAPI")

# ── OUTIL 6 : INFOS PAYS (REST Countries) ─────────────────────────────────────
class CountryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(..., description="Nom du pays en anglais (ex: 'France', 'Senegal', 'Japan', 'Morocco')", min_length=2, max_length=100)

@mcp.tool(name="get_country_info", annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
async def get_country_info(params: CountryInput) -> str:
    """
    Infos completes sur un pays via REST Countries (sans cle).
    Source: public-apis -> Geocoding -> REST Countries
    Donnees : capitale, population, superficie, langues, devises, drapeau...
    Args: name (str) - nom du pays en anglais
    Returns: JSON complet avec toutes les informations du pays
    """
    async with get_http_client() as client:
        try:
            r = await client.get(f"{REST_COUNTRIES_URL}/name/{params.name}")
            r.raise_for_status()
            data = r.json()
            if not data:
                return json.dumps({"success": False, "erreur": f"Pays '{params.name}' introuvable",
                                   "suggestion": "Essaie en anglais: 'Morocco','Senegal','Algeria','France'"}, ensure_ascii=False, indent=2)
            c = data[0]
            idd = c.get("idd", {})
            phone = idd.get("root","") + (idd.get("suffixes",[""])[0] if idd.get("suffixes") else "")
            return json.dumps({
                "success": True,
                "nom_officiel": c.get("name",{}).get("official","N/A"),
                "nom_commun": c.get("name",{}).get("common", params.name),
                "capitale": c.get("capital",["N/A"])[0] if c.get("capital") else "N/A",
                "region": c.get("region","N/A"), "sous_region": c.get("subregion","N/A"),
                "population": f"{c.get('population',0):,}".replace(",", " "),
                "superficie_km2": f"{c.get('area',0):,}".replace(",", " "),
                "langues": list(c.get("languages",{}).values()),
                "devises": {code: info.get("name", code) for code, info in c.get("currencies",{}).items()},
                "indicatif_tel": phone, "fuseaux_horaires": c.get("timezones",[]),
                "code_pays": c.get("cca2","N/A"), "drapeau_emoji": c.get("flag",""),
                "source": "restcountries.com (Auth: No)"
            }, ensure_ascii=False, indent=2)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return json.dumps({"success": False, "erreur": f"Pays '{params.name}' introuvable",
                                   "suggestion": "Essaie: 'Morocco','Senegal','Algeria','Japan','France'"}, ensure_ascii=False, indent=2)
            return handle_error(e, "REST Countries")
        except Exception as e:
            return handle_error(e, "REST Countries")

# ─── POINT D'ENTRÉE ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Demarrage serveur MCP - Etape 3 : 6 APIs Publiques")
    print("Source : github.com/public-apis/public-apis")
    print("Outils : meteo, taux_change, blagues, citations, pokemon, pays")
    print("Zero cle API requise !")
    print("Pour arreter : Ctrl+C")
    mcp.run()