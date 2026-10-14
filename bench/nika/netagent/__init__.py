"""AIOps One-style network agent for NIKA. Each module does one job and can be swapped on its own:
evidence (read-only probes + parsers) · skills (rules, catalog mapping) · agent (NIKA/MCP glue only).
evidence and skills import nothing from NIKA, so they are tested without a lab."""
