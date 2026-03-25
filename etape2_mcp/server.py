"""
╔══════════════════════════════════════════════════════════════════╗
║       ÉTAPE 2 — Notes & Tâches avec Persistance JSON            ║
║                                                                  ║
║  Nouveaux concepts appris :                                      ║
║  ✅ Lire/écrire des fichiers JSON (persistance des données)      ║
║  ✅ Organiser le code en modules séparés                         ║
║  ✅ Gérer un état qui survit au redémarrage du serveur           ║
║  ✅ Gestion avancée des erreurs                                  ║
║  ✅ Annotations destructiveHint pour les outils dangereux        ║
╚══════════════════════════════════════════════════════════════════╝

NOUVEAUTÉ ÉTAPE 2 — La persistance :
─────────────────────────────────────
  Étape 1 : Les données vivaient en mémoire RAM
            → Perdues à chaque redémarrage du serveur

  Étape 2 : Les données sont sauvegardées dans des fichiers JSON
            → Survivent aux redémarrages, accessibles toujours

  Fichiers créés automatiquement :
    data/notes.json   ← toutes tes notes
    data/tasks.json   ← toutes tes tâches
"""

# ─── IMPORTS ──────────────────────────────────────────────────────────────────
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import json
import os
import sys
from datetime import datetime
from uuid import uuid4   # Pour générer des IDs uniques


# ─── CONFIGURATION ────────────────────────────────────────────────────────────

# Dossier où seront stockés les fichiers JSON
# os.path.dirname(__file__) = dossier du script actuel
# os.path.join() = construit un chemin compatible Windows/Mac/Linux
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Chemins complets des fichiers de données
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")


# ─── UTILITAIRES JSON ─────────────────────────────────────────────────────────
# Ces fonctions sont PARTAGÉES par tous les outils (pas de duplication !)

def ensure_data_dir():
    """Crée le dossier 'data' s'il n'existe pas encore."""
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(filepath: str, default: list) -> list:
    """
    Charge un fichier JSON depuis le disque.
    Si le fichier n'existe pas encore, retourne la valeur par défaut.

    C'est le cœur de la persistance : on lit les données sauvegardées.
    """
    ensure_data_dir()
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Fichier corrompu ou illisible → on repart de zéro
        return default


def save_json(filepath: str, data: list) -> None:
    """
    Sauvegarde des données dans un fichier JSON sur le disque.

    C'est l'autre moitié de la persistance : on écrit les données.
    indent=2 rend le fichier lisible si tu l'ouvres avec un éditeur.
    ensure_ascii=False conserve les accents (é, à, ù...)
    """
    ensure_data_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now() -> str:
    """Retourne la date et heure actuelle formatée."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── INITIALISATION DU SERVEUR ────────────────────────────────────────────────
mcp = FastMCP("assistant_mcp")


# ══════════════════════════════════════════════════════════════════════════════
#  MODULE 1 — NOTES
# ══════════════════════════════════════════════════════════════════════════════

class CreateNoteInput(BaseModel):
    """Paramètres pour créer une note."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    title: str = Field(
        ...,
        description="Titre de la note (ex: 'Idées projet', 'Réunion lundi')",
        min_length=1,
        max_length=100
    )
    content: str = Field(
        ...,
        description="Contenu de la note",
        min_length=1,
        max_length=5000
    )
    tags: Optional[list[str]] = Field(
        default_factory=list,
        description="Tags pour organiser les notes (ex: ['travail', 'urgent'])"
    )


@mcp.tool(
    name="create_note",
    annotations={
        "readOnlyHint": False,      # ❌ Modifie les données (crée un fichier)
        "destructiveHint": False,   # ✅ Pas destructif (crée, ne supprime pas)
        "idempotentHint": False,    # ❌ Chaque appel crée une nouvelle note
        "openWorldHint": False      # ✅ Reste local (pas d'API externe)
    }
)
async def create_note(params: CreateNoteInput) -> str:
    """
    Crée une nouvelle note et la sauvegarde sur le disque.

    La note est assignée un ID unique et horodatée automatiquement.
    Elle persiste entre les redémarrages du serveur.

    Args:
        params (CreateNoteInput):
            - title (str): Titre de la note
            - content (str): Contenu de la note
            - tags (list[str]): Tags optionnels

    Returns:
        str: JSON confirmant la création avec l'ID de la note
    """
    # 1. Charger les notes existantes depuis le fichier
    notes = load_json(NOTES_FILE, [])

    # 2. Créer la nouvelle note
    note = {
        "id": str(uuid4())[:8],      # ID court : ex "a3f2b1c9"
        "title": params.title,
        "content": params.content,
        "tags": params.tags or [],
        "created_at": now(),
        "updated_at": now()
    }

    # 3. Ajouter la note à la liste
    notes.append(note)

    # 4. Sauvegarder TOUTE la liste sur le disque
    save_json(NOTES_FILE, notes)

    return json.dumps({
        "success": True,
        "message": f"Note '{params.title}' creee avec succes",
        "note_id": note["id"],
        "total_notes": len(notes)
    }, ensure_ascii=False, indent=2)


class ListNotesInput(BaseModel):
    """Paramètres pour lister les notes."""
    model_config = ConfigDict(extra='forbid')

    tag: Optional[str] = Field(
        default=None,
        description="Filtrer par tag (ex: 'travail'). Laisser vide pour tout voir."
    )
    limit: Optional[int] = Field(
        default=20,
        description="Nombre maximum de notes à retourner",
        ge=1,
        le=100
    )


@mcp.tool(
    name="list_notes",
    annotations={
        "readOnlyHint": True,       # ✅ Lecture seule
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_notes(params: ListNotesInput) -> str:
    """
    Liste toutes les notes sauvegardées, avec filtrage optionnel par tag.

    Args:
        params (ListNotesInput):
            - tag (str): Filtre optionnel par tag
            - limit (int): Nombre max de résultats (défaut: 20)

    Returns:
        str: JSON avec la liste des notes et métadonnées de pagination
    """
    notes = load_json(NOTES_FILE, [])

    # Filtrer par tag si demandé
    if params.tag:
        notes = [n for n in notes if params.tag in n.get("tags", [])]

    total = len(notes)

    # Appliquer la limite (pagination simple)
    # On prend les notes les plus récentes en premier (ordre inversé)
    notes_page = notes[-params.limit:][::-1]

    return json.dumps({
        "total": total,
        "count": len(notes_page),
        "filter_tag": params.tag,
        "notes": notes_page,
        "has_more": total > params.limit
    }, ensure_ascii=False, indent=2)


class DeleteNoteInput(BaseModel):
    """Paramètres pour supprimer une note."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    note_id: str = Field(
        ...,
        description="ID de la note à supprimer (obtenu via list_notes)",
        min_length=1
    )


@mcp.tool(
    name="delete_note",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,    # ⚠️ DESTRUCTIF : supprime définitivement
        "idempotentHint": True,     # ✅ Supprimer 2 fois = même résultat
        "openWorldHint": False
    }
)
async def delete_note(params: DeleteNoteInput) -> str:
    """
    Supprime définitivement une note par son ID.

    ATTENTION : Cette opération est irréversible.

    Args:
        params (DeleteNoteInput):
            - note_id (str): ID de la note à supprimer

    Returns:
        str: JSON confirmant la suppression ou signalant que l'ID est introuvable
    """
    notes = load_json(NOTES_FILE, [])

    # Chercher la note à supprimer
    note_to_delete = next((n for n in notes if n["id"] == params.note_id), None)

    if not note_to_delete:
        return json.dumps({
            "success": False,
            "error": f"Note avec l'ID '{params.note_id}' introuvable",
            "suggestion": "Utilise list_notes pour voir les IDs disponibles"
        }, ensure_ascii=False, indent=2)

    # Reconstruire la liste SANS la note supprimée
    notes = [n for n in notes if n["id"] != params.note_id]
    save_json(NOTES_FILE, notes)

    return json.dumps({
        "success": True,
        "message": f"Note '{note_to_delete['title']}' supprimee",
        "remaining_notes": len(notes)
    }, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
#  MODULE 2 — TÂCHES
# ══════════════════════════════════════════════════════════════════════════════

class AddTaskInput(BaseModel):
    """Paramètres pour ajouter une tâche."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    title: str = Field(
        ...,
        description="Titre de la tâche (ex: 'Appeler le client', 'Finir rapport')",
        min_length=1,
        max_length=200
    )
    priority: Optional[str] = Field(
        default="medium",
        description="Priorité : 'low' (faible), 'medium' (moyenne), 'high' (haute)"
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Date d'échéance optionnelle (ex: '2026-04-01')"
    )


@mcp.tool(
    name="add_task",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def add_task(params: AddTaskInput) -> str:
    """
    Ajoute une nouvelle tâche à la liste et la sauvegarde sur le disque.

    Args:
        params (AddTaskInput):
            - title (str): Titre de la tâche
            - priority (str): 'low', 'medium', ou 'high' (défaut: 'medium')
            - due_date (str): Date d'échéance optionnelle (YYYY-MM-DD)

    Returns:
        str: JSON confirmant l'ajout avec l'ID de la tâche
    """
    # Valider la priorité
    valid_priorities = ["low", "medium", "high"]
    if params.priority not in valid_priorities:
        return json.dumps({
            "success": False,
            "error": f"Priorite '{params.priority}' invalide",
            "suggestion": f"Utilise l'une de ces valeurs : {valid_priorities}"
        }, ensure_ascii=False, indent=2)

    tasks = load_json(TASKS_FILE, [])

    task = {
        "id": str(uuid4())[:8],
        "title": params.title,
        "priority": params.priority,
        "status": "pending",         # pending → completed
        "due_date": params.due_date,
        "created_at": now(),
        "completed_at": None
    }

    tasks.append(task)
    save_json(TASKS_FILE, tasks)

    return json.dumps({
        "success": True,
        "message": f"Tache '{params.title}' ajoutee",
        "task_id": task["id"],
        "priority": params.priority,
        "total_tasks": len(tasks)
    }, ensure_ascii=False, indent=2)


class ListTasksInput(BaseModel):
    """Paramètres pour lister les tâches."""
    model_config = ConfigDict(extra='forbid')

    status: Optional[str] = Field(
        default=None,
        description="Filtrer par statut : 'pending' (en cours) ou 'completed' (terminées). Vide = tout."
    )
    priority: Optional[str] = Field(
        default=None,
        description="Filtrer par priorité : 'low', 'medium', 'high'. Vide = toutes."
    )
    limit: Optional[int] = Field(
        default=20,
        description="Nombre maximum de tâches à retourner",
        ge=1,
        le=100
    )


@mcp.tool(
    name="list_tasks",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_tasks(params: ListTasksInput) -> str:
    """
    Liste les tâches avec filtrage par statut et/ou priorité.

    Args:
        params (ListTasksInput):
            - status (str): 'pending' ou 'completed' (optionnel)
            - priority (str): 'low', 'medium', 'high' (optionnel)
            - limit (int): Nombre max de résultats

    Returns:
        str: JSON avec les tâches filtrées et un résumé des compteurs
    """
    tasks = load_json(TASKS_FILE, [])

    # Appliquer les filtres
    filtered = tasks
    if params.status:
        filtered = [t for t in filtered if t["status"] == params.status]
    if params.priority:
        filtered = [t for t in filtered if t["priority"] == params.priority]

    # Trier par priorité (high → medium → low)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    filtered.sort(key=lambda t: priority_order.get(t["priority"], 99))

    # Statistiques globales (toujours calculées sur TOUTES les tâches)
    total_pending = sum(1 for t in tasks if t["status"] == "pending")
    total_completed = sum(1 for t in tasks if t["status"] == "completed")

    return json.dumps({
        "summary": {
            "total": len(tasks),
            "pending": total_pending,
            "completed": total_completed
        },
        "filters_applied": {
            "status": params.status,
            "priority": params.priority
        },
        "count": len(filtered[:params.limit]),
        "tasks": filtered[:params.limit],
        "has_more": len(filtered) > params.limit
    }, ensure_ascii=False, indent=2)


class CompleteTaskInput(BaseModel):
    """Paramètres pour marquer une tâche comme terminée."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    task_id: str = Field(
        ...,
        description="ID de la tâche à marquer comme terminée (obtenu via list_tasks)",
        min_length=1
    )


@mcp.tool(
    name="complete_task",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,   # ✅ Pas destructif (juste un changement de statut)
        "idempotentHint": True,     # ✅ Compléter une tâche déjà complétée = même résultat
        "openWorldHint": False
    }
)
async def complete_task(params: CompleteTaskInput) -> str:
    """
    Marque une tâche comme terminée et enregistre l'heure de complétion.

    Args:
        params (CompleteTaskInput):
            - task_id (str): ID de la tâche à terminer

    Returns:
        str: JSON confirmant la complétion ou signalant l'erreur
    """
    tasks = load_json(TASKS_FILE, [])

    # Trouver la tâche par son ID
    task = next((t for t in tasks if t["id"] == params.task_id), None)

    if not task:
        return json.dumps({
            "success": False,
            "error": f"Tache avec l'ID '{params.task_id}' introuvable",
            "suggestion": "Utilise list_tasks pour voir les IDs disponibles"
        }, ensure_ascii=False, indent=2)

    if task["status"] == "completed":
        return json.dumps({
            "success": True,
            "message": f"La tache '{task['title']}' etait deja terminee",
            "completed_at": task["completed_at"]
        }, ensure_ascii=False, indent=2)

    # Mettre à jour le statut
    task["status"] = "completed"
    task["completed_at"] = now()

    save_json(TASKS_FILE, tasks)

    return json.dumps({
        "success": True,
        "message": f"Tache '{task['title']}' marquee comme terminee !",
        "task_id": params.task_id,
        "completed_at": task["completed_at"]
    }, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
#  MODULE 3 — TABLEAU DE BORD
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    name="get_dashboard",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def get_dashboard() -> str:
    """
    Affiche un tableau de bord avec le résumé de toutes les notes et tâches.

    Utile pour avoir une vue d'ensemble rapide de tout ce qui est sauvegardé.

    Returns:
        str: JSON avec statistiques complètes et éléments urgents
    """
    notes = load_json(NOTES_FILE, [])
    tasks = load_json(TASKS_FILE, [])

    # Calculer les stats des tâches
    pending_tasks = [t for t in tasks if t["status"] == "pending"]
    high_priority = [t for t in pending_tasks if t["priority"] == "high"]

    return json.dumps({
        "dashboard": {
            "notes": {
                "total": len(notes),
                "derniere_note": notes[-1]["title"] if notes else None
            },
            "taches": {
                "total": len(tasks),
                "en_cours": len(pending_tasks),
                "terminees": len(tasks) - len(pending_tasks),
                "urgentes_high": len(high_priority)
            }
        },
        "taches_urgentes": high_priority[:3],   # Les 3 plus urgentes
        "dernières_notes": [
            {"id": n["id"], "title": n["title"], "created_at": n["created_at"]}
            for n in notes[-3:][::-1]            # Les 3 dernières notes
        ],
        "generated_at": now()
    }, ensure_ascii=False, indent=2)


# ─── POINT D'ENTRÉE ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Demarrage du serveur MCP - Etape 2 : Notes et Taches")
    print("Donnees sauvegardees dans :", DATA_DIR)
    print("Pour arreter : Ctrl+C")
    mcp.run()