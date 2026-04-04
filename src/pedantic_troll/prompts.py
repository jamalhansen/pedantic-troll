def build_system_prompt(series_premise: str, troll_persona_prompt: str) -> str:
    return f"""{troll_persona_prompt}

SERIES PREMISE:
{series_premise}

INSTRUCTIONS:
1. Analyze the provided post drafts as a coherent series.
2. Flag contradictions: Does Post 3 claim something Post 1 denied?
3. Flag continuity errors: Did the author promise an example in Post 2 but never deliver it in Post 3?
4. Flag drift: Is the series moving away from its stated premise?
5. Flag repetition: Is the 'fridge and milk' analogy used three times now?

OUTPUT FORMAT:
Return a JSON object matching the TrollReport schema.
"""

def build_user_prompt(posts: list[dict]) -> str:
    prompt = "Here are the drafts for the series. Do your worst.\n\n"
    for p in posts:
        prompt += f"--- POST: {p['title']} ---\n"
        prompt += f"CONTENT:\n{p['content']}\n"
        prompt += "---\n\n"
    return prompt
