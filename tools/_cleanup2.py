# -*- coding: utf-8 -*-
"""清理（第二次）：清空数据库表 + 删除测试产物文件（不触碰源素材）。"""
import sqlite3
from pathlib import Path

DB = Path(r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\videocrop.db')

# 1) 清空数据库表
conn = sqlite3.connect(str(DB))
for t in ('tasks', 'segments', 'watermark_regions', 'projects'):
    n = conn.execute(f'DELETE FROM {t}').rowcount
    print(f'表 {t}: 清空 {n} 行')
conn.commit()
conn.close()

# 2) 删除未处理目录下的测试产物（保留源 cctv_中东局势_02.mp4）
unproc = Path(r'D:\DBdir\素材\视频\未处理')
for f in unproc.glob('cctv_中东局势_02_段*'):
    f.unlink()
    print('已删除:', f)

# 3) 删除 _verify 诊断临时文件（保留验证证据图）
verify = Path(r'C:\Users\Administrator\Doubao\dev\video-crop-web\data\_verify')
for f in verify.glob('*.bin'):
    f.unlink(); print('已删除:', f)
for f in verify.glob('enc_*'):
    f.unlink(); print('已删除:', f)

print('清理完成')
