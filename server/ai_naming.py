# -*- coding: utf-8 -*-
"""AI 命名：智谱 GLM-4V 识别 3 帧 → 结合源文件名关键词综合选词 → 规范组装。
复用 video-manager 的 vision_api 配置（endpoint/key/模型回退链/参数）。
"""
import base64
import json
import re
import time
import urllib.request
from pathlib import Path

from . import media
from .config import CFG

VISION = CFG['vision_api']
NAMING = CFG['naming']


def _b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


def _call_glm4v(images_b64, prompt):
    """调用智谱 GLM-4V；失败自动回退下一个模型。返回关键词文本。"""
    content = [{'type': 'text', 'text': prompt}]
    for b64 in images_b64:
        content.append({
            'type': 'image_url',
            'image_url': {'url': 'data:image/jpeg;base64,' + b64},
        })
    body = {
        'model': VISION['models'][0],
        'messages': [{'role': 'user', 'content': content}],
        'max_tokens': VISION.get('max_tokens', 512),
        'temperature': VISION.get('temperature', 0.1),
    }
    last_err = None
    for model in VISION['models']:
        body['model'] = model
        req = urllib.request.Request(
            VISION['endpoint'],
            data=json.dumps(body).encode('utf-8'),
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer ' + VISION['api_key']})
        try:
            with urllib.request.urlopen(req, timeout=VISION.get('timeout', 120)) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.0)
    raise RuntimeError('智谱识别失败: ' + str(last_err))


PROMPT_TMPL = (
    '你是一个视频素材打标助手。下面提供一段由「{src_name}」裁剪出的视频片段（源文件关键词：{src_words}）'
    '以及它的 3 帧画面。请结合【源文件名关键词】与【画面内容】综合判断，'
    '输出 3~6 个最能代表这段视频内容的中文关键词，用中文逗号分隔成一行。'
    '要求：相近词合并为一个；不要输出时间、日期、纯数字、模板词'
    '（通用、XX、横屏、竖屏、段、裁剪、去水印、增强）和文件名中的任务标记词。'
)


def recognize(frame_paths, src_name, src_words, direction):
    """识别 3 帧 → 综合源文件名关键词 → 返回去重关键词列表。
    frame_paths: 1~3 个帧图片路径
    src_name: 源文件名（含扩展名）
    src_words: 源文件名解析出的关键词列表
    direction: 'vertical' | 'horizontal'（方向不进入关键词）
    """
    prompt = PROMPT_TMPL.format(
        src_name=src_name,
        src_words='、'.join(src_words) if src_words else '（无）',
    )
    images = [_b64(p) for p in frame_paths]
    # 请求间隔 1s（规避限流）
    time.sleep(VISION.get('request_interval', 1.0))
    text = _call_glm4v(images, prompt)
    # 解析关键词
    words = [w.strip() for w in re.split(r'[，,、；;]', text) if w.strip()]
    out, seen = [], set()
    noise = set(NAMING.get('noise_words', []))
    for w in words:
        if w in seen or w in noise:
            continue
        if re.fullmatch(r'\d{2,}[\d:：.]*', w):  # 时间/纯数字
            continue
        if len(w) > 12:
            continue
        seen.add(w)
        out.append(w)
    return out[:8]


def pick_country(words, path=None, project_name=None):
    """首词优先级：路径国家文件夹名 > AI 词中的国家 > 通用。"""
    countries = set(NAMING.get('country_names', []))
    # 1) 路径
    if path:
        for part in Path(path).parts:
            if part in countries:
                return part
    # 2) AI 词
    for w in words:
        if w in countries:
            return w
    # 3) 通用
    return NAMING.get('default_prefix', '通用')


def _clean_src_words(src_path):
    """源文件名关键词二次清洗：去噪声/方向/段序号/纯数字/重复。"""
    noise = set(NAMING.get('noise_words', []))
    out, seen = [], set()
    for w in media.parse_video_name(src_path):
        if not w or w in seen or w in noise:
            continue
        if re.match(r'^段\d*$', w):
            continue
        if w.isdigit() or re.fullmatch(r'\d{2,}', w):
            continue
        if w.lower() in ('vertical', 'horizontal', 'both', 'mp4', 'webm', 'mov'):
            continue
        if len(w) < 2:
            continue
        seen.add(w)
        out.append(w)
    return out


def merge_name(src_path, words, direction):
    """组装规范文件名：{国家或通用}_{源文件名关键词}_{AI识别词}..._{横屏|竖屏}。
    源文件名关键词与 AI 词去重合并（AI 词中出现过的源词不重复拼）；
    80 字符截断兜底。"""
    first = pick_country(words, path=src_path)
    src_kw = [w for w in _clean_src_words(src_path) if w != first]
    ai_tail = [w for w in words if w != first and w not in src_kw]
    parts = [first] + src_kw + ai_tail
    # 去掉可能残留的模板词/占位
    parts = [w for w in parts if w not in set(NAMING.get('noise_words', []))
             and w != NAMING.get('placeholder', 'XX')
             and not re.match(r'^段\d*$', w)]
    direction_tag = '竖屏' if direction == 'vertical' else '横屏'
    name = '主题_' + '_'.join(parts + [direction_tag])
    # 80 字符截断（保留方向后缀）
    max_len = NAMING.get('max_filename_len', 80)
    suffix = '_' + direction_tag
    if len(name) > max_len:
        head = name[: max_len - len(suffix)]
        name = head.rstrip('_') + suffix
    return name
