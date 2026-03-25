# 📖 Étape 1 — Guide d'installation et de test

## 🗂️ Structure du projet

```
etape1_mcp/
├── server.py          ← Ton serveur MCP (le fichier principal)
├── README.md          ← Ce fichier
└── requirements.txt   ← Dépendances Python
```

---

## ⚙️ Installation (à faire une seule fois)

### 1. Prérequis
- Python 3.10 ou plus récent  
- Vérifier : `python --version`

### 2. Créer un environnement virtuel (bonne pratique !)
```bash
# Aller dans le dossier du projet
cd etape1_mcp

# Créer l'environnement virtuel
python -m venv .venv

# L'activer (Mac/Linux)
source .venv/bin/activate

# L'activer (Windows)
.venv\Scripts\activate
```

### 3. Installer les dépendances
```bash
pip install mcp pydantic
```

### 4. Vérifier que ça fonctionne
```bash
python server.py
```
Tu devrais voir :
```
🚀 Démarrage du serveur MCP - Étape 1
📡 Transport : stdio
💡 Pour arrêter : Ctrl+C
```
→ Le serveur tourne ! (Ctrl+C pour stopper)

---

## 🖥️ Connexion à Claude Desktop

### Où est le fichier de config ?
- **Mac** : `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows** : `%APPDATA%\Claude\claude_desktop_config.json`

### Modifier le fichier de config
Ouvre ce fichier et ajoute ton serveur :

```json
{
  "mcpServers": {
    "assistant_mcp": {
      "command": "python",
      "args": ["/CHEMIN/ABSOLU/VERS/etape1_mcp/server.py"],
      "env": {}
    }
  }
}
```

⚠️ **Important** : Remplace `/CHEMIN/ABSOLU/VERS/` par le vrai chemin !

**Comment trouver le chemin absolu ?**
```bash
# Mac/Linux
pwd
# Exemple de résultat : /Users/ton_nom/projets/etape1_mcp

# Windows (dans PowerShell)
Get-Location
# Exemple : C:\Users\ton_nom\projets\etape1_mcp
```

**Exemple Mac complet :**
```json
{
  "mcpServers": {
    "assistant_mcp": {
      "command": "python",
      "args": ["/Users/alice/projets/etape1_mcp/server.py"],
      "env": {}
    }
  }
}
```

### Redémarrer Claude Desktop
Ferme et réouvre l'application. Tu verras une icône 🔌 dans l'interface.

---

## 🌐 Connexion à Claude.ai

Pour Claude.ai (navigateur), ton serveur doit être accessible via HTTP.

### Option A : Utiliser un tunnel (ngrok) — Pour le test rapide

```bash
# Installer ngrok : https://ngrok.com
# Modifier server.py pour utiliser HTTP (dernières lignes) :
# mcp.run(transport="streamable_http", port=8000)

# Lancer le tunnel
ngrok http 8000
# → Tu obtiens une URL publique : https://xxxxx.ngrok.io
```

### Option B : Tester en local avec Claude.ai
Claude.ai supporte les serveurs MCP locaux via Remote MCP.
→ Dans Claude.ai : Settings → Integrations → Add MCP Server

---

## 🧪 Tester tes outils

Une fois connecté à Claude Desktop ou Claude.ai, essaie ces prompts :

### Test 1 - say_hello
```
Utilise l'outil say_hello pour me souhaiter la bienvenue en anglais.
Mon prénom est [ton prénom].
```

### Test 2 - calculate
```
Calcule 15 multiplié par 7 avec l'outil calculate.
```
```
Quelle est la racine carrée de 144 ?
```
```
Divise 100 par 0 et dis-moi ce qu'il se passe.
```

### Test 3 - get_server_info
```
Quels outils MCP as-tu à disposition ? Utilise get_server_info.
```

---

## 🔍 Débogage avec MCP Inspector (optionnel mais très utile !)

MCP Inspector est un outil officiel pour tester ton serveur sans Claude.

```bash
# Installer Node.js d'abord (https://nodejs.org)

# Lancer l'inspecteur sur ton serveur
npx @modelcontextprotocol/inspector python server.py
```

→ Ouvre http://localhost:5173 dans ton navigateur
→ Tu verras tous tes outils et pourras les tester manuellement

---

## 🧠 Concepts clés à retenir

| Concept | Explication |
|---------|-------------|
| `FastMCP` | Framework Python qui gère le protocole MCP automatiquement |
| `@mcp.tool()` | Décorateur qui enregistre une fonction comme outil MCP |
| `Pydantic BaseModel` | Classe qui définit et valide les paramètres d'entrée |
| `Field(...)` | `...` = paramètre obligatoire, `default=X` = facultatif |
| `async def` | Fonction asynchrone (nécessaire pour MCP) |
| `stdio` | Transport local (Claude Desktop ↔ ton script Python) |
| `streamable_http` | Transport réseau (Claude.ai ↔ ton serveur sur internet) |

---

## ❓ Problèmes fréquents

**"Module 'mcp' not found"**
```bash
pip install mcp  # ou pip install "mcp[cli]"
```

**"Le serveur n'apparaît pas dans Claude Desktop"**
- Vérifie que le chemin dans le JSON de config est absolu (pas relatif)
- Vérifie que Python est dans ton PATH : `which python` ou `where python`
- Redémarre Claude Desktop complètement

**"Permission denied" sur Mac/Linux**
```bash
chmod +x server.py
```

---

## ➡️ Prochaine étape

Quand tes 3 outils fonctionnent, tu es prêt pour **l'Étape 2** :
- Outils avec persistance (lecture/écriture de fichiers JSON)
- Gestion de Notes et Tâches
- Gestion des erreurs avancée