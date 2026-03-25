"""
╔══════════════════════════════════════════════════════════════════╗
║         ÉTAPE 1 — Mon Premier Serveur MCP en Python             ║
║                                                                  ║
║  Concepts appris :                                               ║
║  ✅ Créer un serveur MCP avec FastMCP                            ║
║  ✅ Définir des "outils" (tools) appelables par Claude           ║
║  ✅ Valider les entrées avec Pydantic                            ║
║  ✅ Retourner des réponses formatées                             ║
╚══════════════════════════════════════════════════════════════════╝

ARCHITECTURE MCP (à comprendre avant de coder) :
─────────────────────────────────────────────────
   [Claude / LLM]  ←──────────────→  [Ton serveur MCP]
       Host                              Server
   (le "cerveau")                  (les "bras et outils")
        │                                   │
        │  1. Claude veut faire quelque chose│
        │  2. Il appelle un "tool" MCP        │
        │  3. Ton serveur exécute le code     │
        │  4. Retourne le résultat à Claude   │
        └───────────────────────────────────┘

Un "tool" MCP = une fonction Python que Claude peut déclencher.
"""

# ─── IMPORTS ──────────────────────────────────────────────────────────────────

# FastMCP = le framework Python officiel pour créer des serveurs MCP
# Il simplifie énormément le protocole bas niveau
from mcp.server.fastmcp import FastMCP

# Pydantic = bibliothèque de validation de données
# Elle vérifie que les données reçues ont le bon type avant d'exécuter le code
from pydantic import BaseModel, Field, ConfigDict

# Types Python standards
from typing import Optional
import json
import math
from datetime import datetime


# ─── INITIALISATION DU SERVEUR ────────────────────────────────────────────────

# On crée une instance FastMCP avec un nom.
# Convention de nommage : {service}_mcp (toujours en minuscules avec underscores)
mcp = FastMCP("assistant_mcp")

# C'est tout ! Le serveur est créé. Maintenant on lui ajoute des outils.


# ─── OUTIL 1 : Dire Bonjour ───────────────────────────────────────────────────

# Étape 1 : Définir le schéma d'entrée avec Pydantic
# C'est une classe qui décrit CE QUE l'outil attend comme paramètres.
class SayHelloInput(BaseModel):
    """
    Modèle de validation pour l'outil say_hello.
    Pydantic vérifie automatiquement les types et contraintes.
    """

    # model_config : paramètres de comportement du modèle Pydantic
    model_config = ConfigDict(
        str_strip_whitespace=True,  # Supprime les espaces en début/fin de chaîne
        extra='forbid'              # Interdit les paramètres non déclarés
    )

    # Field() permet de décrire un paramètre avec sa doc, ses contraintes, etc.
    # "..." signifie "obligatoire" (pas de valeur par défaut)
    name: str = Field(
        ...,
        description="Le prénom de la personne à saluer (ex: 'Alice', 'Bob')",
        min_length=1,    # Au minimum 1 caractère
        max_length=50    # Au maximum 50 caractères
    )

    # Optional[str] = le paramètre est facultatif (peut être None)
    # default=None = valeur par défaut si non fourni
    language: Optional[str] = Field(
        default="fr",
        description="Langue de la salutation : 'fr' (français), 'en' (anglais), 'es' (espagnol)"
    )


# Étape 2 : Créer l'outil avec le décorateur @mcp.tool
# Le décorateur enregistre la fonction comme outil disponible pour Claude.
@mcp.tool(
    name="say_hello",  # Nom de l'outil tel que Claude le verra
    annotations={
        # Ces annotations informent Claude sur le comportement de l'outil :
        "readOnlyHint": True,      # ✅ Cet outil ne modifie RIEN (il lit seulement)
        "destructiveHint": False,  # ✅ Pas d'opération destructive (pas de suppression)
        "idempotentHint": True,    # ✅ Appeler 2 fois donne le même résultat
        "openWorldHint": False     # ✅ N'interagit pas avec le monde extérieur (pas d'API)
    }
)
async def say_hello(params: SayHelloInput) -> str:
    """
    Génère un message de salutation personnalisé.

    Cet outil retourne un message de bienvenue dans la langue choisie.
    Utile pour tester la connexion MCP et comprendre le flux de données.

    Args:
        params (SayHelloInput): Paramètres validés contenant :
            - name (str): Prénom de la personne (obligatoire)
            - language (str): Code langue - 'fr', 'en', 'es' (défaut: 'fr')

    Returns:
        str: Message de salutation formaté en JSON avec :
            - greeting: Le message de salutation
            - name: Le prénom utilisé
            - language: La langue utilisée
            - timestamp: Heure de génération
    """
    # Dictionnaire des salutations par langue
    greetings = {
        "fr": f"Bonjour {params.name} ! Bienvenue dans le monde du MCP ! 🎉",
        "en": f"Hello {params.name}! Welcome to the world of MCP! 🎉",
        "es": f"¡Hola {params.name}! ¡Bienvenido al mundo de MCP! 🎉",
    }

    # Si la langue n'est pas supportée, on utilise le français par défaut
    greeting = greetings.get(params.language, greetings["fr"])

    # On construit la réponse sous forme de dictionnaire
    result = {
        "greeting": greeting,
        "name": params.name,
        "language": params.language,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": "Connexion MCP fonctionnelle !"
    }

    # json.dumps() convertit le dict en texte JSON proprement formaté
    # indent=2 ajoute une indentation pour la lisibilité
    return json.dumps(result, ensure_ascii=False, indent=2)


# ─── OUTIL 2 : Calculatrice ───────────────────────────────────────────────────

class CalculatorInput(BaseModel):
    """Modèle de validation pour la calculatrice."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid'
    )

    # ge = greater or equal (>=), le = less or equal (<=)
    a: float = Field(
        ...,
        description="Premier nombre (ex: 10, 3.14, -5)"
    )

    b: float = Field(
        ...,
        description="Deuxième nombre (ex: 4, 2.71, 100)"
    )

    # On utilise une liste de valeurs acceptées pour l'opération
    operation: str = Field(
        default="add",
        description="Opération : 'add' (+), 'subtract' (-), 'multiply' (*), 'divide' (/), 'power' (^), 'sqrt_a' (√a)"
    )


@mcp.tool(
    name="calculate",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def calculate(params: CalculatorInput) -> str:
    """
    Effectue des calculs mathématiques de base.

    Supporte les opérations : addition, soustraction, multiplication,
    division, puissance, et racine carrée.

    Args:
        params (CalculatorInput): Paramètres validés :
            - a (float): Premier opérande
            - b (float): Deuxième opérande
            - operation (str): Type d'opération

    Returns:
        str: Résultat en JSON avec :
            - operation: Opération effectuée
            - a, b: Les opérandes utilisés
            - result: Le résultat numérique
            - expression: L'expression mathématique lisible
    """
    result = None
    expression = ""

    # On utilise un bloc try/except pour capturer les erreurs
    # (ex: division par zéro, racine d'un nombre négatif)
    try:
        if params.operation == "add":
            result = params.a + params.b
            expression = f"{params.a} + {params.b}"

        elif params.operation == "subtract":
            result = params.a - params.b
            expression = f"{params.a} - {params.b}"

        elif params.operation == "multiply":
            result = params.a * params.b
            expression = f"{params.a} × {params.b}"

        elif params.operation == "divide":
            # Cas d'erreur classique : division par zéro
            if params.b == 0:
                return json.dumps({
                    "error": "Division par zéro impossible",
                    "suggestion": "Utilise un diviseur (b) différent de 0"
                }, ensure_ascii=False, indent=2)
            result = params.a / params.b
            expression = f"{params.a} ÷ {params.b}"

        elif params.operation == "power":
            result = params.a ** params.b
            expression = f"{params.a} ^ {params.b}"

        elif params.operation == "sqrt_a":
            if params.a < 0:
                return json.dumps({
                    "error": "Racine carrée d'un nombre négatif impossible (dans les réels)",
                    "suggestion": "Utilise un nombre positif pour a"
                }, ensure_ascii=False, indent=2)
            result = math.sqrt(params.a)
            expression = f"√{params.a}"

        else:
            return json.dumps({
                "error": f"Opération '{params.operation}' non reconnue",
                "suggestion": "Opérations disponibles : add, subtract, multiply, divide, power, sqrt_a"
            }, ensure_ascii=False, indent=2)

        return json.dumps({
            "expression": expression,
            "result": result,
            "operation": params.operation,
            "a": params.a,
            "b": params.b
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Erreur de calcul : {str(e)}"
        }, ensure_ascii=False, indent=2)


# ─── OUTIL 3 : Info Système (Bonus) ───────────────────────────────────────────

@mcp.tool(
    name="get_server_info",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,  # False car retourne l'heure actuelle (change)
        "openWorldHint": False
    }
)
async def get_server_info() -> str:
    """
    Retourne les informations sur ce serveur MCP.

    Cet outil est utile pour vérifier que le serveur est bien connecté
    et voir quels outils sont disponibles.

    Returns:
        str: JSON avec les informations du serveur :
            - name: Nom du serveur
            - version: Version
            - tools: Liste des outils disponibles
            - current_time: Heure actuelle
            - status: État du serveur
    """
    return json.dumps({
        "name": "assistant_mcp",
        "version": "1.0.0",
        "etape": "Étape 1 - Fondamentaux MCP",
        "status": "✅ Opérationnel",
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tools_disponibles": [
            {
                "name": "say_hello",
                "description": "Génère un message de salutation personnalisé",
                "params": ["name (obligatoire)", "language (optionnel, défaut: fr)"]
            },
            {
                "name": "calculate",
                "description": "Effectue des calculs mathématiques",
                "params": ["a", "b", "operation (add/subtract/multiply/divide/power/sqrt_a)"]
            },
            {
                "name": "get_server_info",
                "description": "Affiche les infos de ce serveur MCP",
                "params": []
            }
        ]
    }, ensure_ascii=False, indent=2)


# ─── POINT D'ENTRÉE ───────────────────────────────────────────────────────────

# Ce bloc s'exécute UNIQUEMENT quand on lance ce fichier directement :
#   python server.py
# (et PAS quand il est importé par un autre module)
if __name__ == "__main__":
    print(" Démarrage du serveur MCP - Étape 1")
    print(" Transport : stdio (communication locale avec Claude Desktop)")
    print(" Pour arrêter : Ctrl+C")
    print()

    # mcp.run() démarre le serveur en mode stdio
    # stdio = le serveur communique via l'entrée/sortie standard (stdin/stdout)
    # C'est le mode utilisé par Claude Desktop pour parler à ton serveur
    mcp.run()