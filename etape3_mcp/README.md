# 📖 Étape 3 — 6 APIs Publiques (source : public-apis/public-apis)

## 🌐 APIs — Toutes sans clé, sans inscription

| # | Outil MCP | API | Catégorie repo | Auth |
|---|---|---|---|---|
| 1 | `get_weather` | Open-Meteo | Weather | ❌ Aucune |
| 2 | `get_exchange_rate` | ExchangeRate-API | Currency Exchange | ❌ Aucune |
| 3 | `get_joke` | JokeAPI | Entertainment | ❌ Aucune |
| 4 | `get_quote` | Quotable | Personality | ❌ Aucune |
| 5 | `get_pokemon` | PokeAPI | Games & Comics | ❌ Aucune |
| 6 | `get_country_info` | REST Countries | Geocoding | ❌ Aucune |

Source : https://github.com/public-apis/public-apis

---

## ⚙️ Installation (pas de .env nécessaire !)

```powershell
cd C:\mcp\etape3_mcp
python -m venv .venv
.venv\Scripts\activate
pip install mcp pydantic httpx
python server.py
```

---

## 🔧 Config Claude Desktop (ajouter assistant_mcp3)

```json
{
  "preferences": { "...": "..." },
  "mcpServers": {
    "assistant_mcp":  { "command": "C:\\mcp\\etape1_mcp\\.venv\\Scripts\\python.exe", "args": ["C:\\mcp\\etape1_mcp\\server.py"] },
    "assistant_mcp2": { "command": "C:\\mcp\\etape2_mcp\\.venv\\Scripts\\python.exe", "args": ["C:\\mcp\\etape2_mcp\\server.py"] },
    "assistant_mcp3": { "command": "C:\\mcp\\etape3_mcp\\.venv\\Scripts\\python.exe", "args": ["C:\\mcp\\etape3_mcp\\server.py"] }
  }
}
```

---

## 🧪 Tests rapides

```
Météo  → Quelle est la météo à Dakar ?
Change → Convertis 1000 EUR en XOF, MAD et GBP
Blague → Raconte-moi une blague de programmation en français
Citation → Une citation d'Einstein sur la science
Pokémon → Quelles sont les stats de Pikachu ?
Pays   → Donne-moi les infos sur le Sénégal
```

### 🔥 Test combiné ultime
```
Je prépare un voyage au Japon depuis la France.
1. Météo actuelle à Tokyo
2. Taux EUR/JPY pour 500 euros
3. Infos clés sur le Japon
4. Une citation de motivation pour le voyage
```

---

## 🧠 Nouveaux concepts appris

| Concept | Explication |
|---|---|
| `httpx.AsyncClient` | Client HTTP async |
| `async with client` | Ouvre/ferme la connexion automatiquement |
| `raise_for_status()` | Lève une erreur si HTTP >= 400 |
| `openWorldHint: True` | L'outil accède à internet |
| Appels en chaîne | Météo = géocodage → prévisions (2 appels) |

## ➡️ Étape 4 : Resources, Prompts et TypeScript