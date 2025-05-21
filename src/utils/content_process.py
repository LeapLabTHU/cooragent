import re


def remove_think_tags(content: any) -> str:
    """
        remove <think>**</think> tags
    """

    if isinstance(content, str):
        return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    return content  