# Photo File Filter（照片筛选与重命名）

[English documentation](README_EN.md)

一个简洁而可靠的照片筛选与批量重命名工具，可按参考表匹配或调用 AI 多模态模型生成描述性文件名。

## 功能特性
- 根据参考表在大量文件中定位目标照片并复制到输出目录，同时重命名。
- 保留原始扩展名与二进制数据（不会改动源文件编码）。
- 支持模糊匹配以减少漏检。
- 可调用通义千问多模态模型，为照片生成自然语言描述的文件名。
- 支持 JPG/PNG/GIF/TIFF/WebP/BMP 以及 CR2/NEF/ARW/DNG/ORF/RW2/PEF/SRW/RAF/X3F 等专业 RAW 格式。
- 复制后使用文件大小与 SHA‑256 双重校验，失败自动重试。

## 安装
推荐 Python 3.9+。

```bash
pip install -r requirements.txt
# 可选：HEIC/HEIF 支持
pip install pillow-heif
```

## 参考表格式
- **传统模式**（两列）：1) 标识符 2) 备注（最终文件名），示例见 `example_reference.csv`。
- **AI 重命名模式**（单列）：1) 标识符，用于从文件名中匹配，示例见 `example_reference_ai.csv`。

## 命令行使用
```bash
# 传统模式：按参考表匹配并重命名，保留原扩展名
python file_filter.py \
  --source /path/to/photos \
  --target /path/to/output \
  --reference example_reference.csv

# AI 模式：AI 仅生成文件名，输出仍保留原扩展名与数据
python file_filter.py \
  --source /path/to/photos \
  --target /path/to/output \
  --reference example_reference_ai.csv \
  --ai-naming
```

参数：
- `--source/-s` 源目录
- `--target/-t` 输出目录（自动创建）
- `--reference/-r` 参考表（CSV/Excel）
- `--ai-naming` 启用 AI 视觉理解重命名

## 图形界面（GUI）
在 macOS 或 Windows 上：

```bash
python gui_app.py
```

界面中选择源目录、目标目录和参考表，可选“使用 AI 视觉理解重命名”，点击“开始处理”查看日志与进度。

## AI 重命名工作流
- AI 仅用于生成描述性文件名，输出文件保留原始扩展名与二进制数据。
- 在上传前会将图片临时压缩为 JPG（≤1024×768），生成文件名后删除临时文件。
- 使用阿里云通义千问多模态端点：
  - Endpoint: `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
  - 请求体 `input.messages[].content` 同时包含 `{ "image": "data:image/jpeg;base64,..." }` 与 `{ "text": "..." }`
- API Key：修改 `file_filter.py` 中的 `QWEN_API_KEY`。
- 建议安装：`rawpy`（RAW 解码）、`pillow-heif`（HEIC/HEIF 解码）。

### 默认阈值（可在 `file_filter.py` 顶部修改）
- `AI_REQUEST_TIMEOUT_S = 40`：请求超时（秒）
- `AI_REQUEST_MAX_RETRIES = 2`：429/5xx/超时重试次数（指数退避）
- `AI_REQUEST_QPS = 1.0`：每秒请求数上限（全局节流）
- 上传前压缩：最大约 1024×768（保持宽高比）
- 文件大小过滤：源文件 >50MB 跳过 AI 分析
- 命名清洗：移除非法字符与结尾扩展名，空白替换为下划线

已知限制：
- 最短边 ≤10 像素的图片会被模型拒绝（HTTP 400）。
- 个别 RAW 文件可能无法解码，将被跳过。

## 支持的格式
- 常见：JPG/JPEG、PNG、GIF、TIFF/TIF、WebP、BMP、HEIC/HEIF
- RAW：CR2、NEF、ARW、DNG、ORF、RW2、PEF、SRW、RAF、X3F

## 示例

```bash
# 传统模式
python file_filter.py \
  --source ./photos \
  --target ./output \
  --reference ./example_reference.csv

# AI 模式
python file_filter.py \
  --source ./photos \
  --target ./output \
  --reference ./example_reference_ai.csv \
  --ai-naming
```

## 打包
已提供 `PhotoFilterGUI.spec`，可一键打包 GUI：

```bash
python -m PyInstaller --noconfirm PhotoFilterGUI.spec
# 产物位于 dist/PhotoFilterGUI 或 PhotoFilterGUI.app（macOS）
```

推送 tag 可触发 GitHub Actions 自动构建并发布（macOS/Windows）：

```bash
git tag v1.1.0
git push origin v1.1.0
```

## 测试

```bash
pip install -r requirements.txt
pytest
```

## 常见问题 FAQ
- **AI 返回 400**：多数是图片过小（如 8×12），请放大最短边后再试。
- **无法读取 HEIC**：安装 `pillow-heif` 后重试。
- **RAW 文件处理缓慢**：可在源码中下调最大尺寸或提高 QPS（注意配额）。
