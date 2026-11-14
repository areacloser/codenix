

def _load_system_prompt():
    from codenix.config import CONFIG_DIR
    system_prompt_path = CONFIG_DIR / "prompts" / "system.md"
    if system_prompt_path.exists():
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return None
