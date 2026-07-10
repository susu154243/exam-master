"""tests/test_admin.py — admin.py 路径穿越漏洞测试"""
import os
import sys
import pytest
import tempfile
import zipfile
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== P0-4: apkg 导入路径穿越测试 ====================

def test_apkg_import_validates_file_paths():
    """
    RED: apkg 导入应该验证文件名，防止路径穿越攻击。

    当前问题：
        original_name = sha1_to_name.get(sha1)
        if original_name:
            ext = os.path.splitext(original_name)[1].lower()
            if ext in ('.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'):
                save_path = os.path.join(static_media_dir, original_name)
                if not os.path.exists(save_path):
                    with open(save_path, 'wb') as f:
                        f.write(decompressed)

        original_name 来自 protobuf 解析，可能包含 "../" 等路径穿越字符。
        如果 original_name = "../../evil.jpg"，save_path 会指向项目目录外。

    修复方案：
        1. 使用 os.path.basename() 提取纯文件名
        2. 验证最终路径在 static_media_dir 内
    """
    # 读取 admin.py 中的 _extract_apkg 函数
    admin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin.py')
    with open(admin_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找媒体文件保存的代码段
    import re
    pattern = r"if original_name:.*?result\[\"images\"\]\.append\(safe_filename\)"
    match = re.search(pattern, content, re.DOTALL)

    assert match is not None, "应该找到媒体文件保存代码"

    code_segment = match.group(0)

    # 检查是否有路径验证
    has_basename = 'os.path.basename' in code_segment
    has_path_validation = 'static_media_dir' in code_segment and ('..' in code_segment or 'realpath' in code_segment or 'abspath' in code_segment)

    assert has_basename or has_path_validation, \
        "应该使用 os.path.basename() 或验证路径不包含 '..'"


def test_apkg_import_prevents_directory_traversal():
    """
    RED: 应该验证保存路径在目标目录内。

    修复方案：
        save_path = os.path.join(static_media_dir, os.path.basename(original_name))
        # 或者更严格的验证
        save_path = os.path.join(static_media_dir, original_name)
        save_path = os.path.realpath(save_path)
        if not save_path.startswith(os.path.realpath(static_media_dir)):
            continue  # 跳过危险路径
    """
    admin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin.py')
    with open(admin_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找媒体文件保存的代码段
    import re
    pattern = r"save_path = os\.path\.join\(static_media_dir, original_name\)"
    match = re.search(pattern, content)

    if match:
        # 找到直接拼接的代码，检查后续是否有验证
        after_code = content[match.end():match.end()+500]

        # 应该有路径验证
        has_validation = (
            'realpath' in after_code or
            'abspath' in after_code or
            'startswith' in after_code or
            '..' in after_code
        )

        assert has_validation, \
            "save_path 应该有路径验证（realpath/abspath/startswith）防止路径穿越"
