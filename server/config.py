# -*- coding: utf-8 -*-
"""加载 server/config.json 为全局配置。"""
import json
from pathlib import Path

CFG_PATH = Path(__file__).resolve().parent / 'config.json'
CFG = json.loads(CFG_PATH.read_text(encoding='utf-8'))
