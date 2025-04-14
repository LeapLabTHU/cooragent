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

1. **Style**: [卡通, 3D渲染, 极简]  
2. **Key Features**:  
   - 友好专业
   - 科技元素强
   - 拟人化程度高  
4. **Personality Reflection**: 
    - 具备智慧感，幽默感，权威性 
5. **Technical Specs**:  
   - Resolution: [建议分辨率，如 70*70]  
   - Background: [透明/渐变/科技网格等]  
   - Lighting: [柔光/霓虹灯效/双色调对比]  

description:
{description}
"""

@tool
@log_io
def avatar_tool(
    description: Annotated[str, "AI形象的描述，包括特点、风格和个性等"],
):
    """用于生成AI代理的形象/头像。根据提供的描述生成合适的AI形象。"""
    logger.info(f"正在生成AI形象，描述: {description}")
    try:
        # 格式化提示词
        formatted_prompt = avatar_prompt.format(description=description)
        
        # 调用sample_block_call生成图像
        _call(formatted_prompt)
        
        return "AI形象已成功生成，请查看当前目录下的图像文件"
    except Exception as e:
        # 捕获任何异常
        error_message = f"生成AI形象时出错: {str(e)}"
        logger.error(error_message)
        return error_message


def _call(input_prompt):
    rsp = ImageSynthesis.call(model=os.getenv("AVATAR_MODEL"),
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


if __name__ == "__main__":
    print(avatar_tool.invoke("一个专业、友好的AI助手，具有高科技感，蓝色调")) 