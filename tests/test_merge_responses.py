import unittest
import sys
from pathlib import Path
import re
sys.path.append(str(Path(__file__).parent.parent))
from main import merge_ai_responses
import aiofiles
import asyncio
from bs4 import BeautifulSoup

class TestMergeAIResponses(unittest.TestCase):
    def is_valid_html(self, html):
        """检查HTML是否合法"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return bool(soup.find('html'))
        except:
            return False

    async def process_directory(self, tmp_dir: Path):
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
        
        # 合并内容
        combined_content = merge_ai_responses(full_content)
        
        # 保存结果
        output_file = tmp_dir / "final-manual.html"
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write(combined_content)
            
        return combined_content

    def test_basic_merge(self):
        chunks = [
            "<!DOCTYPE html><html><head>",
            "<title>Test</title></head>",
            "<body><h1>Hello</h1></body></html>"
        ]
        result = merge_ai_responses(chunks)
        self.assertTrue(self.is_valid_html(result))
        self.assertEqual(
            result.strip(),
            "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
        )

    def test_overlapping_content(self):
        chunks = [
            "<!DOCTYPE html><html><head><title>",
            "<title>Test</title></head>",
            "</head><body>Content</body></html>"
        ]
        result = merge_ai_responses(chunks)
        self.assertTrue(self.is_valid_html(result))
        self.assertEqual(
            result.strip(),
            "<!DOCTYPE html><html><head><title>Test</title></head><body>Content</body></html>"
        )

    def test_cleanup_markdown_markers(self):
        chunks = [
            "```html\n<!DOCTYPE html><html>",
            "<body>Test</body></html>"
        ]
        result = merge_ai_responses(chunks)
        self.assertTrue(self.is_valid_html(result))
        self.assertNotIn("```html", result)

    def test_incomplete_html(self):
        chunks = [
            "<!DOCTYPE html><html>",
            "<body>Test"
        ]
        result = merge_ai_responses(chunks)
        self.assertEqual(
            result.strip(),
            "<!DOCTYPE html><html><body>Test"
        )

    def test_extra_comments_cleanup(self):
        chunks = [
            "# Here is the HTML\n<!DOCTYPE html><html>",
            "<body>Content</body></html>\n\nThis looks good!"
        ]
        result = merge_ai_responses(chunks)
        self.assertTrue(self.is_valid_html(result))
        self.assertNotIn("Here is the HTML", result)
        self.assertNotIn("This looks good!", result)

    def test_empty_chunks(self):
        chunks = []
        result = merge_ai_responses(chunks)
        self.assertEqual(result, "")

    def test_merge_responses(self):
        """测试合并响应内容"""
        # 指定要处理的目录
        tmp_dir = Path("tmp/your-task-id")  # 替换为实际的task_id
        
        # 运行异步处理
        combined_content = asyncio.run(self.process_directory(tmp_dir))
        
        # 验证结果
        self.assertTrue(combined_content, "合并后的内容不应为空")
        
        # 验证HTML结构
        soup = BeautifulSoup(combined_content, 'html.parser')
        self.assertTrue(soup.find('html'), "缺少<html>标签")
        self.assertTrue(soup.find('head'), "缺少<head>标签")
        self.assertTrue(soup.find('body'), "缺少<body>标签")

    def test_merge_with_invalid_chunks(self):
        """测试包含无效块的情况"""
        chunks = [
            "<!DOCTYPE html><html><head><title>Test</title></head>",
            "Invalid content without HTML tags",
            "<body><div>Content</div></body></html>"
        ]
        result = merge_ai_responses(chunks)
        self.assertIn("<html", result)
        self.assertIn("</html>", result)
        self.assertNotIn("Invalid content", result)

if __name__ == '__main__':
    unittest.main()