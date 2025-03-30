# 手动处理指定目录
"""
此脚本是一个用于处理指定目录数据的手动工具。
它使用 `tests.test_merge_responses` 模块中的 `TestMergeResponses` 类来处理与给定任务 ID 对应的目录。
脚本执行以下操作：
1. 接收命令行参数 `task_id`。
2. 使用 `TestMergeResponses` 处理位于 `tmp/<task_id>` 的目录。
3. 将处理结果保存为名为 `final-manual.html` 的 HTML 文件，存储在同一目录中。
4. 如果生成的 HTML 文件存在，则自动在默认浏览器中打开。
用法：
    python manual_test_merge_local_data.py <task_id>
参数：
    task_id (str): 要处理的任务目录的标识符。
依赖：
    - asyncio: 用于异步处理。
    - pathlib.Path: 用于处理文件路径。
    - sys: 用于命令行参数处理。
    - webbrowser: 用于在浏览器中打开生成的 HTML 文件。
    - TestMergeResponses: 负责处理目录的类。
注意：
    在运行脚本之前，请确保 `tmp` 文件夹下存在对应的 `task_id` 目录。
"""


from tests.test_merge_responses import TestMergeResponses
import asyncio
from pathlib import Path
import sys
import webbrowser

async def process_task_dir(task_id: str):
    processor = TestMergeResponses()
    tmp_dir = Path("tmp") / task_id
    result = await processor.process_directory(tmp_dir)
    print(f"处理完成，结果保存在: {tmp_dir}/final-manual.html")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test.py <task_id>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    asyncio.run(process_task_dir(task_id))
    
    # 打开生成的HTML文件
    html_path = Path("tmp") / task_id / "final-manual.html"
    if html_path.exists():
        webbrowser.open(html_path.as_uri())
    else:
        print(f"无法找到HTML文件: {html_path}")
