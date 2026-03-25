# Concepts à maîtriser :

1. Qu'est-ce que MCP ? (protocole client ↔ serveur entre un LLM et des outils)
2. Les 3 primitives : Tools (actions), Resources (données), Prompts (templates)
3. Les transports : stdio (local) vs HTTP (distant)
4. L'architecture : Host (Claude) → Client → Server → API externe


🧠 Concepts clés à retenir
ConceptExplicationFastMCPFramework Python qui gère le protocole MCP automatiquement@mcp.tool()Décorateur qui enregistre une fonction comme outil MCPPydantic BaseModelClasse qui définit et valide les paramètres d'entréeField(...)... = paramètre obligatoire, default=X = facultatifasync defFonction asynchrone (nécessaire pour MCP)stdioTransport local (Claude Desktop ↔ ton script Python)streamable_httpTransport réseau (Claude.ai ↔ ton serveur sur internet)