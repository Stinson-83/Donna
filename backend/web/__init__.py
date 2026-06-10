"""External web search + research for Donna's web tools.

`search.py` — single-shot search (`search_web`) and read-and-synthesize
(`agentic_search`). `pipeline.py` — deeper multi-source research
(`run_web_research`). All degrade to status=degraded when no provider key is
configured so the BRAIN loop never crashes on a missing dependency.
"""
