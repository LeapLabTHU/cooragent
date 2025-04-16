import logging
from typing import Annotated
from langchain_core.tools import tool
from .decorators import log_io
from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
from dashscope import ImageSynthesis
from dotenv import load_dotenv

load_dotenv()

import os
logger = logging.getLogger(__name__)


avatar_prompt = """ 
"Generate a high-quality avatar/character portrait for an AI agent based on the following description. Follow these guidelines carefully:  

1. **Style**: [Cartoon, 3D Render, Minimalist]  
2. **Key Features**:  
   - Friendly and professional
   - Strong technological elements
   - High degree of anthropomorphism  
4. **Personality Reflection**: 
    - Possesses a sense of wisdom, humor, and authority 
5. **Technical Specs**:  
   - Resolution: [Suggested resolution, e.g., 70*70]  
   - Background: [Transparent/Gradient/Tech Grid, etc.]  
   - Lighting: [Soft light/Neon effect/Duotone contrast]  

description:
{description}
"""

@tool
@log_io
def avatar_tool(
    description: Annotated[str, "Description of the AI avatar, including features, style, and personality."],
):
    """Generates an avatar/image for an AI agent. Creates a suitable AI image based on the provided description."""
    logger.info(f"Generating AI avatar, description: {description}")
    try:
        # Format the prompt
        formatted_prompt = avatar_prompt.format(description=description)
        
        # Call _call to generate the image
        _call(formatted_prompt)
        
        return "AI avatar generated successfully. Please check the image file in the current directory."
    except Exception as e:
        # Catch any exceptions
        error_message = f"Error generating AI avatar: {str(e)}"
        logger.error(error_message)
        return error_message


def _call(input_prompt):
    rsp = ImageSynthesis.call(model=os.getenv("AVATAR_MODEL"),
                              prompt=input_prompt,
                              size='768*512')
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output)
        print(rsp.usage)
        
        for result in rsp.output.results:
            file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
            with open('./%s' % file_name, 'wb+') as f:
                f.write(requests.get(result.url).content)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))


if __name__ == "__main__":
    print(avatar_tool.invoke("A professional and friendly AI assistant with a high-tech feel and blue tones")) 