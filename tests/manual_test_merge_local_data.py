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


import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from main import merge_ai_responses
import asyncio
import webbrowser
import re
import aiofiles



async def process_directory(tmp_dir: Path):
    """处理指定目录下的round_*.html文件"""
    # 获取所有round_*.html文件并按数字顺序排序
    round_files = sorted(
        tmp_dir.glob("round_*.html"),
        key=lambda x: int(re.search(r'round_(\d+)\.html', x.name).group(1))
    )
    
    # 读取所有文件内容
    full_content = []
    for file in round_files:
        async with aiofiles.open(file, 'r', encoding='utf-8') as f:
            content = await f.read()
            full_content.append(content)
    
    # Test
    Test = False
    if Test:
        full_content = []
        round_13 = '''        <!-- 作者信息区域 -->
        <footer class="bg-gray-50 dark:bg-gray-800 rounded-lg shadow p-6 mt-12">
            <div class="max-w-4xl mx-auto text-center">
                <h3 class="text-xl font-medium mb-4 text-gray-800 dark:text-gray-200">作者信息</h3>
                <p class="text-gray-600 dark:text-gray-400 mb-4">作者姓名：x</p>
                <div class="flex justify-center space-x-4 mb-6">
                    <a href="https://twitter.com/x" class="text-blue-500 hover:text-blue-600 dark:hover:text-blue-400" target="_blank" rel="noopener noreferrer">
                        <svg class="h-6 w-6" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9'''
        round_14 = '''<path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84"></path>
                        </svg>
                    </a>
                </div>
                <p class="text-sm text-gray-500 dark:text-gray-400"></p>
            </div>
        </footer>
    </main>

    <script>
              '''
        full_content.append(round_13)
        full_content.append(round_14)

    # 合并内容
    combined_content = merge_ai_responses(full_content)
    
    # 保存结果
    output_file = tmp_dir / "final-manual.html"
    async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
        await f.write(combined_content)
        
    return combined_content



async def process_task_dir(task_id: str):
    tmp_dir = Path("tmp") / task_id
    result = await process_directory(tmp_dir)
    print(f"处理完成，结果保存在: {tmp_dir}/final-manual.html")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test.py <task_id>")
        #sys.exit(1)
    if len(sys.argv) == 1:
        task_id = "d0ddc3fe-a014-4ed6-9347-1a8872abf3ec"
    else:
        task_id = sys.argv[1]
    asyncio.run(process_task_dir(task_id))
    
    # 打开生成的HTML文件
    html_path = Path("tmp") / task_id / "final-manual.html"
    html_path = html_path.absolute()  # 转换为绝对路径
    if html_path.exists():
        webbrowser.open(html_path.as_uri())
    else:
        print(f"无法找到HTML文件: {html_path}")
