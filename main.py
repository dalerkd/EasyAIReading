#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
易读工具 - 智能网页内容提取和优化工具

Copyright 2025 dalerkd
Licensed under the Apache License, Version 2.0
"""

__author__ = "dalerkd"
__copyright__ = "Copyright 2025, 易读工具项目"
__license__ = "Apache 2.0"
__version__ = "1.0.0"
__maintainer__ = "https://github.com/dalerkd"
__status__ = "Production"

import os
from pathlib import Path
from datetime import datetime
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import openai
import uuid
import aiofiles
import asyncio
import sys
from typing import Optional, AsyncGenerator, Dict, Any
import httpx
from sse_starlette.sse import EventSourceResponse
import json  # 确保导入 json

# 首先创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 配置日志，使用 UTF-8 编码
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # 指定输出到 stdout
        logging.FileHandler(
            f'logs/app_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'  # 指定文件编码为 UTF-8
        )
    ]
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 配置OpenAI（移到函数外面）
base_url = os.getenv("OPENAI_BASE_URL")
if not base_url:
    logger.error("OPENAI_BASE_URL 未设置")
    raise ValueError("OPENAI_BASE_URL is required")

logger.info(f"初始化 OpenAI 配置，base_url: {base_url}")
openai.base_url = base_url
openai.api_key = os.getenv("OPENAI_API_KEY")

# 验证配置
logger.info(f"验证 OpenAI 配置: base_url={openai.base_url}")

app = FastAPI(title="易读工具")

# 创建必要的目录
STATIC_DIR = Path("static")
HTML_DIR = Path("static/html")
STATIC_DIR.mkdir(exist_ok=True)
HTML_DIR.mkdir(exist_ok=True)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 添加根路由
@app.get("/")
async def root():
    return FileResponse("static/index.html")

class ContentRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None

def extract_main_content(url: str) -> str:
    """提取网页主要内容"""
    try:
        # 设置请求头，模拟正常浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(
            url, 
            headers=headers,
            timeout=440,
            verify=False  # 验证 SSL 证书
        )
        response.raise_for_status()
        
        # 检测并使用正确的编码
        if response.encoding.lower() == 'iso-8859-1':
            response.encoding = response.apparent_encoding
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除不需要的元素
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'noscript']):
            element.decompose()
            
        # 获取文本
        text = soup.get_text()
        
        # 清理文本
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        logger.error(f"提取内容失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"无法访问URL: {str(e)}")

# 在文件开头添加
PROMPT_DIR = Path("prompts")
PROMPT_DIR.mkdir(exist_ok=True)

def load_prompt(filename: str) -> str:
    """从文件加载提示词"""
    try:
        prompt_path = PROMPT_DIR / filename
        if not prompt_path.exists():
            logger.warning(f"提示词文件不存在: {filename}，使用默认提示词")
            if filename == "continue_prompt.txt":
                return "请继续生成未完成的部分，从上次内容的末尾继续，不要重复之前的内容。确保HTML格式正确。"
            elif filename == "format_prompt.txt":
                return """我会给你一个文件，分析内容，并将其转化为美观漂亮的中文可视化网页作品集：
## 内容要求
- 保持原文件的核心信息，但以更易读、可视化的方式呈现
- 在页面底部添加作者信息区域，包含：    
 * 作者姓名: [作者姓名]
 * 社交媒体链接: 至少包含Twitter/X：  
- 版权信息和年份
## 设计风格
- 整体风格参考Linear App的简约现代设计
- 使用清晰的视觉层次结构，突出重要内容
- 配色方案应专业、和谐，适合长时间阅读
## 技术规范
- 使用HTML5、TailwindCSS 3.0+（通过CDN引入）和必要的JavaScript
如涉及则优先使用正确版本链接:
https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css
https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/lib/index.min.js
- 实现完整的深色/浅色模式切换功能，默认跟随系统设置
- 代码结构清晰，包含适当注释，便于理解和维护
## 响应式设计
- 页面必须在所有设备上（手机、平板、桌面）完美展示
- 针对不同屏幕尺寸优化布局和字体大小
- 确保移动端有良好的触控体验
## 媒体资源
- 使用文档中的Markdown图片链接（如果有的话）
- 使用文档中的视频嵌入代码（如果有的话）
## 图标与视觉元素
- 使用专业图标库如Font Awesome或Material Icons（通过CDN引入）
- 根据内容主题选择合适的插图或图表展示数据
- 避免使用emoji作为主要图标
## 交互体验
- 添加适当的微交互效果提升用户体验：    
 * 按钮悬停时有轻微放大和颜色变化    
 * 卡片元素悬停时有精致的阴影和边框效果    
 * 页面滚动时有平滑过渡效果    
 * 内容区块加载时有优雅的淡入动画
## 性能优化
- 确保页面加载速度快，避免不必要的大型资源
- 实现懒加载技术用于长页面内容
## 输出要求
- 提供完整可运行的单一HTML文件，包含所有必要的CSS和JavaScript
- 确保代码符合W3C标准，无错误警告
- 页面在不同浏览器中保持一致的外观和功能
请根据上传文件的内容类型（文档、数据、图片等），创建最适合展示该内容的可视化网页。"""
            else:
                raise ValueError(f"加载提示词文件失败，未知的提示词文件: {filename}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"加载提示词文件失败: {str(e)}")
        raise ValueError(f"加载提示词文件失败: {str(e)}")

# 存储任务状态和处理器
tasks: Dict[str, dict] = {}
task_processors: Dict[str, Any] = {}

async def get_task_status(task: dict) -> dict:
    """获取任务状态"""
    task_id = task.get("task_id")
    processor = task_processors.get(task_id)
    
    try:
        if not processor:
            # 创建新的处理器
            processor = process_status_generator(task.get("url"), task.get("text"))
            task_processors[task_id] = processor
        
        # 获取下一个状态
        status_data = await anext(processor)
        # 确保返回的数据包含 status 字段
        parsed_status = json.loads(status_data)
        if "data" in parsed_status:
            # 如果状态包含在 data 字段中，提取出来
            return parsed_status["data"]
        return parsed_status

    except StopAsyncIteration:
        # 处理完成，清理处理器
        if task_id in task_processors:
            del task_processors[task_id]
        return {
            "status": "completed",
            "message": "处理完成"
        }
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
        # 发生错误，清理处理器
        if task_id in task_processors:
            del task_processors[task_id]
        return {
            "status": "error",
            "error": str(e),
            "message": "处理过程中发生错误"
        }

class ProcessRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None

@app.post("/init-process")
async def init_process(request: ProcessRequest):
    """初始化处理任务"""
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "task_id": task_id,  # 添加 task_id 到任务数据中
        "url": request.url,
        "text": request.text,
        "status": "waiting"
    }
    return {"task_id": task_id}

class TaskStatusRequest(BaseModel):
    task_id: str

@app.post("/process-events")
async def process_events(request: TaskStatusRequest):
    """处理状态更新"""
    if request.task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    task = tasks[request.task_id]
    status = await get_task_status(task)
    
    # 如果任务完成或出错，清理任务数据
    if status["status"] in ["completed", "error"]:
        if request.task_id in tasks:
            del tasks[request.task_id]
    
    return status

# 在文件开头添加
TMP_DIR = Path("tmp")
TMP_DIR.mkdir(exist_ok=True)


def merge_ai_strings(first, second):
    """合并两个字符串，检查重叠部分"""
    # 可能的最大重叠长度是A的长度和B的长度中较小的那个
    max_overlap = min(len(first), len(second), 100)
    
    # 从最大可能重叠开始检查
    for overlap in range(max_overlap, 0, -1):
        # 检查A的末尾overlap个字符是否等于B的开头overlap个字符
        if first[-overlap:] == second[:overlap]:
            return first + second[overlap:]
    
    # 如果没有重叠，直接连接
    return first + second

import re

def chunk_clear(chunks):
    """清理分块,由于AI的返回内容可能会有多余的空行和换行符，导致直接合并html会出问题"""

    # Step 1: Remove chunks without valid HTML tags
    cleaned_chunks = []
    for i, chunk in enumerate(chunks):
        if not any(tag in chunk.lower() for tag in ["</style>", "</script>", "</div>", "</p>", "</section>", "</h1>", "</h2>"]):
            logger.warning(f"第 {i + 1} 块因缺少有效HTML标签被移除")
            continue
        cleaned_chunks.append(chunk)

    # Step 2: Fix specific cases in the cleaned chunks
    if len(cleaned_chunks) > 0:
        # Fix case: xxxxxxxxx\n\n<!DOCTYPE html>
        cleaned_chunks[0] = cleaned_chunks[0][cleaned_chunks[0].find('<'):]
        # Fix case: </html>\n\nxxxx这个HTML文件现在是完整的...您可以看效果
        cleaned_chunks[-1] = cleaned_chunks[-1][:cleaned_chunks[-1].rfind('</html>') + len('</html>')]

    # Step 3: Remove ```html\n from the beginning of each chunk
    final_chunks = []
    for chunk in cleaned_chunks:
        # If chunk starts with ```html\n, remove it
        cleaned_chunk = re.sub(r'^```html\s*\n?', '', chunk, count=1)
        final_chunks.append(cleaned_chunk)

    return final_chunks


def merge_ai_responses(chunks):
    combined_content = ""
    chunks = chunk_clear(chunks)
    for chunk in chunks:
        combined_content = merge_ai_strings(combined_content, chunk)
    return combined_content


def is_complete_html(content: str) -> bool:
    """检查AI回复内容是否已经完成了HTML输出"""

    ''''
    AI的回复可能存在随机性,最终结果可能并不存在</html>'
    1. 检查是否包含</html>标签
    2. ```html开头 找到最后一个```,如果后面还有内容能匹配 "精美"
    eg: ```\n\n通过这个设计精美的网页，我们......
    '''

    # 1. 检查是否包含</html>标签
    if "</html>" in content.lower():
        return True
    
    # 2. 检查不存在</html>标签的情况
    if content.startswith("```html"):
        # 找到最后一个```
        last_code_block = content.rsplit("```", 1)[-1]
        # 检查是否包含"精美"
        if "精美" in last_code_block:
            return True
    
    # 3. 检查特殊情况,本次没有任何html代码,必须结束,防止无限循环
    if not any(tag in content.lower() for tag in ["</style>", "</script>", "</div>", "</p>", "</section>", "</h1>", "</h2>"]):
        return True

    return False



async def process_status_generator(url: Optional[str] = None, text: Optional[str] = None):
    """生成处理状态事件"""
    task_id = str(uuid.uuid4())
    tmp_task_dir = TMP_DIR / task_id
    tmp_task_dir.mkdir(exist_ok=True)
    
    try:
        yield json.dumps({
            "status": "waiting",
            "message": "准备处理..."
        })
        await asyncio.sleep(0.1) #添加小延迟，确保状态被前端接收
        
        # 提取内容
        if url:
            content = extract_main_content(url)
        else:
            content = text

        content_length = len(content)
        yield json.dumps({
            "status": "extracting",
            "message": f"正在提取内容...内容长度: {content_length} 字符",
            "content_length": content_length  # 添加长度信息
        })
        await asyncio.sleep(0.1) #添加小延迟，确保状态被前端接收
        
        # 创建 httpx 客户端
        http_client = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(
                connect=120.0,
                read=240.0,
                write=240.0,
                pool=240.0
            )
        )
        
        # 创建 OpenAI 客户端
        async_client = openai.AsyncClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            http_client=http_client,
            timeout=400.0,
            max_retries=5
        )
        
        try:
            # 从文件加载系统提示词
            system_prompt = load_prompt("format_prompt.txt")
            logger.info("已加载系统提示词")
            
            # 初始化消息列表
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": content
                }
            ]
            
            full_content = []
            max_attempts = 20
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    response = await async_client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "claude 3.7"),#至少是 claude 3.7级别
                        messages=messages
                    )
                    
                    current_content = response.choices[0].message.content
                    full_content.append(current_content)
                    
                    # 保存当前轮次的返回数据
                    tmp_file = tmp_task_dir / f"round_{attempt + 1}.html"
                    async with aiofiles.open(tmp_file, 'w', encoding='utf-8') as f:
                        await f.write(current_content)
                    logger.info(f"保存第 {attempt + 1} 轮AI返回数据: {tmp_file}")
                    
                    if is_complete_html(current_content):  # 使用新的检查函数
                        break
                        
                    # 从文件加载续写提示词（如果有）
                    continue_prompt = load_prompt("continue_prompt.txt")
                    
                    # 更新消息历史，添加 AI 的回复和新的用户指令
                    messages.extend([
                        {"role": "assistant", "content": current_content},
                        {"role": "user", "content": continue_prompt}
                    ])
                    
                    attempt += 1
                    
                    yield json.dumps({
                        "status": "ai_processing",
                        "round": attempt,
                        "message": f"AI优化处理第 {attempt} 轮..."
                    })
                    await asyncio.sleep(0.1) #添加小延迟，确保状态被前端接收
                    
                except Exception as e:
                    logger.error(f"AI 请求失败: {str(e)}", exc_info=True)
                    # 保存错误信息
                    error_file = tmp_task_dir / f"error_round_{attempt + 1}.txt"
                    async with aiofiles.open(error_file, 'w', encoding='utf-8') as f:
                        await f.write(f"Error: {str(e)}")
                    continue
            
            # 修正和保存最终合并的内容
            combined_content = merge_ai_responses(full_content)

            final_file = tmp_task_dir / "final.html"
            async with aiofiles.open(final_file, 'w', encoding='utf-8') as f:
                await f.write(combined_content)
            
            # 复制到最终目标位置
            file_id = str(uuid.uuid4())
            file_path = HTML_DIR / f"{file_id}.html"
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(combined_content)
                
            yield json.dumps({
                "status": "completed",
                "file_id": file_id,
                "message": "处理完成！"
            })
            await asyncio.sleep(0.1) #添加小延迟，确保状态被前端接收
            
        finally:
            # 确保关闭 http 客户端
            await http_client.aclose()

    except Exception as e:
        logger.error(f"处理失败: {str(e)}", exc_info=True)
        # 保存整体错误信息
        error_file = tmp_task_dir / "error.txt"
        async with aiofiles.open(error_file, 'w', encoding='utf-8') as f:
            await f.write(f"Error: {str(e)}")
        yield json.dumps({
            "status": "error",
            "error": str(e),
            "message": "处理过程中发生错误"
        })
        await asyncio.sleep(0.1) #添加小延迟，确保状态被前端接收
        
    finally:
        # 可以选择在这里添加临时文件的清理逻辑
        # 或者保留临时文件以供调试
        pass

@app.get("/view/{file_id}")
async def view_html(file_id: str):
    """查看生成的HTML文件"""
    file_path = HTML_DIR / f"{file_id}.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path, media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    logger.info("启动服务器")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )