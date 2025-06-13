from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
from dashscope import ImageSynthesis
from dotenv import load_dotenv
import os

load_dotenv()

model = "flux-merged"

avatar_prompt = """ 
"Generate a high-quality avatar/character portrait for an AI agent based on the following description. Follow these guidelines carefully:  

1. **Style**: [Cartoon, 3D Rendering, Minimalist]  
2. **Key Features**:  
   - Friendly and Professional
   - Strong Technological Elements
   - High Degree of Anthropomorphism  
4. **Personality Reflection**: 
    - Possess Wisdom, Humor, and Authority 
5. **Technical Specs**:  
   - Resolution: [Recommended resolution, e.g. 70*70]  
   - Background: [Transparent/Gradient/Tech Grid]  
   - Lighting: [Soft Light/Neon Effect/Dual-tone Contrast]  

description:
{description}
"""

agent_description = "You are a researcher tasked with solving a given problem by utilizing the provided tools."

prompt = avatar_prompt.format(description=agent_description)

def sample_block_call(input_prompt):
    rsp = ImageSynthesis.call(model=model,
                              prompt=input_prompt,
                              size='768*512')
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output)
        print(rsp.usage)
        # save file to current directory
        for result in rsp.output.results:
            file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
            with open('./%s' % file_name, 'wb+') as f:
                f.write(requests.get(result.url).content)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))


def sample_async_call(input_prompt):
    rsp = ImageSynthesis.async_call(model=model,
                                    prompt=input_prompt,
                                    size='1024*1024')
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output)
        print(rsp.usage)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))
    status = ImageSynthesis.fetch(rsp)
    if status.status_code == HTTPStatus.OK:
        print(status.output.task_status)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (status.status_code, status.code, status.message))

    rsp = ImageSynthesis.wait(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    sample_block_call(prompt)
