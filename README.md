# 视频裁剪Web工具 (video-crop-web)

Web端视频裁剪与水印工具（8010端口）。

## 功能
- 在线视频裁剪（指定时间段）
- 视频水印添加与去除
- 格式转换与压缩
- AI自动命名（基于GLM-4V）

## 快速启动
`ash
# 1. 安装依赖
pip install flask requests

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 GLM_API_KEY

# 3. 启动服务
python -m server.app
# 访问 http://127.0.0.1:8010
`

## 项目结构
`
├── server/            # 后端服务
│   ├── app.py         # 主应用
│   ├── crop_engine.py # 裁剪引擎
│   ├── watermark.py   # 水印处理
│   ├── ai_naming.py   # AI自动命名
│   └── config.json     # 配置
├── web/               # 前端页面
├── docs/design/       # 设计文档
├── tests/             # 测试脚本
└── tools/             # 补丁与工具脚本
`

## 技术栈
- 后端: Python Flask
- 视频处理: FFmpeg
- AI识别: 智谱 GLM-4V 视觉大模型
