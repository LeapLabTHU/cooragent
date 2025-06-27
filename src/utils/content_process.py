import re


def clean_response_tags(content: str) -> str:
    """
        remove think tags and json tags from the response content.
    """
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)

    if content.startswith("```json"):
        content = content.removeprefix("```json")

    if content.startswith("```ts"):
        content = content.removeprefix("```ts")

    if content.endswith("```"):
        content = content.removesuffix("```")

    return content

