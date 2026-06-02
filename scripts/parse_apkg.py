#!/usr/bin/env python3
"""
Anki .apkg 文件解析脚本
解析结果用于预览，确认无误后再集成至刻印系统。

用法:
    python3 tools/parse_apkg.py <apkg文件路径>
"""
import sys
import os
import sqlite3
import json
import re
import zipfile
import tempfile
import zstandard


def extract_apkg(apkg_path, work_dir):
    """解压 .apkg 文件（zip 格式）"""
    with zipfile.ZipFile(apkg_path, 'r') as zf:
        zf.extractall(work_dir)
    return work_dir


def decompress_anki21b(anki21b_path, output_path):
    """解压 Zstandard 压缩的 collection.anki21b"""
    with open(anki21b_path, 'rb') as f:
        dctx = zstandard.ZstdDecompressor()
        with dctx.stream_reader(f) as reader:
            data = reader.read()
    with open(output_path, 'wb') as f:
        f.write(data)
    return output_path


def extract_media(apkg_path, work_dir):
    """解析 media 文件映射"""
    media_file = os.path.join(work_dir, 'media')
    if os.path.exists(media_file):
        try:
            with open(media_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (UnicodeDecodeError, json.JSONDecodeError):
            # 可能是二进制或空文件
            return {}


def parse_options(options_str):
    """将选项字符串解析为字典
    
    输入格式: A.选项内容<br>B.选项内容<br>C.选项内容<br>D.选项内容
    输出格式: {"A": "选项内容", "B": "选项内容", ...}
    """
    result = {}
    # 匹配 A.xxx B.xxx C.xxx D.xxx E.xxx 等（支持到 E/F）
    pattern = r'([A-F])\.\s*(.*?)(?=<br>|<div>|$)'
    matches = re.findall(pattern, options_str, re.DOTALL)
    for letter, content in matches:
        result[letter] = content.strip()
    
    # 如果正则没匹配到，尝试简单分割
    if not result:
        parts = re.split(r'<br>\s*', options_str)
        for part in parts:
            part = part.strip()
            m = re.match(r'^([A-F])\.\s*(.*)', part, re.DOTALL)
            if m:
                result[m.group(1)] = m.group(2).strip()
    
    return result


def clean_answer(answer_str):
    """从答案字段提取纯字母答案
    
    输入: <span style="color: rgb(39, 200, 65);">B</span> 或 B
    输出: B
    """
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', '', answer_str).strip()
    # 提取字母（支持多选如 AB）
    letters = re.findall(r'[A-F]', text)
    return ''.join(letters)


def count_questions(field0):
    """从题干开头提取题号"""
    m = re.match(r'^\s*(\d+)\.', field0)
    if m:
        return m.group(1)
    # 可能包含 HTML 标签的题号
    text = re.sub(r'<[^>]+>', '', field0).strip()
    m = re.match(r'^(\d+)\.', text)
    if m:
        return m.group(1)
    return '?'


def detect_question_type(answer):
    """根据答案判断题型"""
    if len(answer) > 1:
        return 'multiple', '多选题'
    return 'single', '单选题'


def parse_apkg(apkg_path):
    """主解析函数"""
    work_dir = tempfile.mkdtemp(prefix='apkg_parse_')
    
    # 1. 解压 apkg
    print(f"📦 解压 apkg 文件...")
    extract_apkg(apkg_path, work_dir)
    
    # 2. 找到正确的数据库文件
    db_path = None
    for name in ['collection.anki21b', 'collection.anki2']:
        p = os.path.join(work_dir, name)
        if os.path.exists(p):
            db_path = p
            break
    
    if not db_path:
        print("❌ 未找到数据库文件")
        return
    
    # 3. 如果是 .anki21b，需要解压
    if db_path.endswith('.anki21b'):
        print(f"🔓 解压 Zstandard 数据库...")
        decompressed = os.path.join(work_dir, 'collection.db')
        decompress_anki21b(db_path, decompressed)
        db_path = decompressed
    
    # 4. 解析 media
    media_map = extract_media(apkg_path, work_dir)
    
    # 5. 读取数据库
    print(f"📖 读取数据库...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 获取模板字段名（从 templates 表的 config 中提取）
    cur.execute("""
        SELECT config FROM templates 
        WHERE config LIKE '%{{Question}}%' OR config LIKE '%{{Front}}%'
        LIMIT 1
    """)
    row = cur.fetchone()
    
    # 如果找不到，尝试从 col 表的 models 字段获取
    if row and row[0]:
        try:
            # config 可能是 bytes 或 text
            config_bytes = row[0] if isinstance(row[0], bytes) else row[0].encode()
            config_str = config_bytes.decode('utf-8', errors='ignore')
            # 从模板中提取字段名
            field_placeholders = re.findall(r'\{\{(\w+)\}\}', config_str)
            print(f"  模板字段占位符: {field_placeholders}")
        except:
            pass
    
    # 6. 解析 notes
    cur.execute("""
        SELECT id, guid, tags, flds, sfld
        FROM notes 
        ORDER BY id
    """)
    
    notes = []
    for nid, guid, tags, flds, sfld in cur.fetchall():
        # Anki 使用 \x1f (Unit Separator) 分隔字段
        fields = flds.split('\x1f')
        
        if len(fields) < 4:
            print(f"⚠️  note {nid} 字段数不足 (仅 {len(fields)} 个)，跳过")
            continue
        
        field0 = fields[0]  # 题干
        field1 = fields[1]  # 选项
        field2 = fields[2]  # 答案
        field3 = fields[3]  # 解析
        
        # 解析
        question_num = count_questions(field0)
        answer = clean_answer(field2)
        options = parse_options(field1)
        qtype_code, qtype_text = detect_question_type(answer)
        
        note = {
            'id': nid,
            'num': question_num,
            'stem': field0,
            'options': options,
            'answer': answer,
            'explanation': field3,
            'qtype_code': qtype_code,
            'qtype_text': qtype_text,
            'tags': tags,
            'image_refs': re.findall(r'src="([^"]+\.(?:jpg|png|gif|svg))"', field3),
        }
        notes.append(note)
    
    conn.close()
    
    # 7. 输出解析结果
    print(f"\n{'='*60}")
    print(f"📊 解析结果总览")
    print(f"{'='*60}")
    print(f"  总题数: {len(notes)}")
    
    qtypes = {}
    for n in notes:
        qtypes[n['qtype_text']] = qtypes.get(n['qtype_text'], 0) + 1
    print(f"  题型分布: {qtypes}")
    
    has_images = [n for n in notes if n['image_refs']]
    print(f"  含图片题目: {len(has_images)} 道")
    if has_images:
        for n in has_images:
            print(f"    第 {n['num']} 题: {n['image_refs']}")
    
    if media_map:
        print(f"  媒体文件映射: {len(media_map)} 个")
        for fname, real_name in media_map.items():
            print(f"    {fname} → {real_name}")
    
    # 8. 逐题预览
    print(f"\n{'='*60}")
    print(f"📝 逐题预览")
    print(f"{'='*60}")
    
    for note in notes:
        print(f"\n{'─'*60}")
        print(f"【第 {note['num']} 题】({note['qtype_text']})")
        print(f"  题干: {note['stem'][:120]}...")
        print(f"  答案: {note['answer']}")
        print(f"  选项: {len(note['options'])} 个")
        for k, v in note['options'].items():
            print(f"    {k}. {v[:80]}")
        if note['explanation']:
            expl_clean = re.sub(r'<[^>]+>', '', note['explanation'])[:150]
            print(f"  解析: {expl_clean}...")
        if note['image_refs']:
            print(f"  图片: {note['image_refs']}")
    
    # 9. 导出 JSON（方便核对）
    output_path = os.path.join(work_dir, 'parsed_result.json')
    export_data = []
    for n in notes:
        export_data.append({
            '题号': n['num'],
            '题型': n['qtype_text'],
            '题干': n['stem'],
            '选项': n['options'],
            '答案': n['answer'],
            '解析': n['explanation'],
        })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ 解析完成！")
    print(f"  JSON 详情: {output_path}")
    print(f"  工作目录: {work_dir}")
    print(f"{'='*60}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 tools/parse_apkg.py <apkg文件路径>")
        sys.exit(1)
    
    apkg_path = sys.argv[1]
    if not os.path.exists(apkg_path):
        print(f"❌ 文件不存在: {apkg_path}")
        sys.exit(1)
    
    parse_apkg(apkg_path)
