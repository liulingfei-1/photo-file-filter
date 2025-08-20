# Photo File Filter（照片筛选与重命名）

一个小而强的照片筛选与批量重命名工具。支持“按参考表匹配重命名”和“AI 视觉理解生成文件名”。

## 它能做什么

- 按参考表在海量文件中定位需要的照片，复制到目标目录并重命名
- 保留原始扩展名与二进制数据（不会改动源文件编码格式）
- 模糊匹配（近似匹配标识），减少漏检
- AI 视觉理解生成更“像话”的文件名（通义千问多模态）
- 多格式：JPG/PNG/GIF/TIFF/WebP/BMP，专业 RAW：CR2/NEF/ARW/DNG/ORF/RW2/PEF/SRW/RAF/X3F/…
- 复制后双重校验（文件大小 + SHA-256），失败自动重试

## 安装

推荐使用 Python 3.9+。

```bash
pip install -r requirements.txt
# 可选：HEIC/HEIF 支持
pip install pillow-heif
```

## 参考表怎么写

- 传统模式（两列）：
  1) 标识符 2) 备注（最终文件名）
  示例：`example_reference.csv`

- AI 重命名模式（单列）：
  1) 标识符（用于从文件名中匹配）
  示例：`example_reference_ai.csv`

## 命令行使用

```bash
# 传统模式（按参考表匹配并重命名，保留原扩展名）
python file_filter.py \
  --source /path/to/photos \
  --target /path/to/output \
  --reference example_reference.csv

# AI 重命名模式（AI 仅生成文件名，输出仍保留原扩展名与数据）
python file_filter.py \
  --source /path/to/photos \
  --target /path/to/output \
  --reference example_reference_ai.csv \
  --ai-naming
```

参数说明：
- `--source/-s` 源目录
- `--target/-t` 输出目录（自动创建）
- `--reference/-r` 参考表（CSV/Excel）
- `--ai-naming` 打开 AI 视觉理解重命名

## 图形界面（GUI）

macOS 或 Windows：

```bash
python gui_app.py
```

在界面中选择源目录、目标目录、参考表，并可勾选“使用AI视觉理解重命名”。点击“开始处理”查看日志与进度。

## AI 重命名工作流（重要）

- AI 仅用于“生成描述性文件名”。输出文件保留原始扩展名与二进制数据。
- 为进行识别，会临时将图片压缩为 JPG（≤ 1024×768）上传给模型；生成名称后删除临时文件。
- 使用阿里云通义千问多模态端点：
  - Endpoint：`https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
  - 负载：`input.messages[].content` 同时包含 `{"image": "data:image/jpeg;base64,..."}` 与 `{"text": "..."}`（详见阿里云百炼文档）
- API Key：修改 `file_filter.py` 中的 `QWEN_API_KEY` 变量
- 建议安装：`rawpy`（RAW 解码），`pillow-heif`（HEIC/HEIF 解码）

参考文档：[阿里云百炼文档（通义千问多模态）](https://bailian.console.aliyun.com/?spm=5176.30371578.J_-b3_dpUGUU3dm_j_tEufi.1.e939154aOcE2fz&tab=doc#/doc/?type=model&url=2845871)

## 稳健性与默认阈值

以下参数在 `file_filter.py` 顶部可调：

- `AI_REQUEST_TIMEOUT_S = 40`：请求超时（秒）
- `AI_REQUEST_MAX_RETRIES = 2`：429/5xx/超时重试次数（指数回退）
- `AI_REQUEST_QPS = 1.0`：每秒请求数上限（全局节流）
- 上传前压缩：最大约 1024×768（保持宽高比）
- 文件大小过滤：源文件 > 50MB 跳过 AI 分析
- 命名清洗：移除非法字符与结尾扩展名，统一空白为下划线

已知限制：
- 极小图（最短边 ≤ 10 像素）会被模型拒绝（400）。
- 个别 RAW 读入可能失败（硬件/编解码原因），会跳过。

## 支持的格式

- 常见：JPG/JPEG、PNG、GIF、TIFF/TIF、WebP、BMP、HEIC/HEIF
- RAW：CR2、NEF、ARW、DNG、ORF、RW2、PEF、SRW、RAF、X3F

## 示例

传统模式：

```bash
python file_filter.py \
  --source ./photos \
  --target ./output \
  --reference ./example_reference.csv
```

AI 模式：

```bash
python file_filter.py \
  --source ./photos \
  --target ./output \
  --reference ./example_reference_ai.csv \
  --ai-naming
```

## 打包（可选）

已提供 `PhotoFilterGUI.spec`，可一键打包 GUI：

```bash
python -m PyInstaller --noconfirm PhotoFilterGUI.spec
# 产物位于 dist/PhotoFilterGUI 或 PhotoFilterGUI.app（macOS）
```

推 tag 可触发 GitHub Actions 自动构建并发布（macOS/Windows）：

```bash
git tag v1.1.0
git push origin v1.1.0
```

## 测试

```bash
pip install -r requirements.txt
pytest
```

## 常见问题（FAQ）

- AI 返回 400：多为图片过小（例如 8×12），建议放大最短边再试。
- HEIC 无法读取：请安装 `pillow-heif` 并重试。
- RAW 过大太慢：可自行在源码中下调最大尺寸或提高 QPS（注意配额）。

### AI 重命名工作流与参数说明

#### 工作原理
- 仅将 AI 用于“生成描述性文件名”，输出文件保留“原始编码格式与扩展名”（如 `.CR2/.NEF/.ARW/.RAF/.DNG/.HEIC/.TIFF/.JPG` 等）。
- 为进行多模态识别，程序会临时将图片压缩为 JPG（最大约 1024x768）上传至模型，生成名称后删除临时文件；最终复制到输出目录的是“原文件本体”。
- RAW 解码依赖 `rawpy`（可选），HEIC/HEIF 解码推荐安装 `pillow-heif`（可选）。

#### 接口与负载
- 多模态生成端点：
  - Endpoint: `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
  - 请求体：`input.messages[].content` 同时包含 `{"image": "data:image/jpeg;base64,..."}` 与 `{"text": "..."}`
- 参考文档：
  - [阿里云百炼文档（通义千问多模态）](https://bailian.console.aliyun.com/?spm=5176.30371578.J_-b3_dpUGUU3dm_j_tEufi.1.e939154aOcE2fz&tab=doc#/doc/?type=model&url=2845871)

#### 内置阈值（在 `file_filter.py` 顶部可修改）
- `AI_REQUEST_TIMEOUT_S = 40`：单次请求超时（秒）
- `AI_REQUEST_MAX_RETRIES = 2`：429/5xx/超时最大重试（指数回退）
- `AI_REQUEST_QPS = 1.0`：节流速率（每秒请求数上限）
- 上传前压缩：最大约 `1024x768`（保持宽高比）
- 文件大小过滤：源文件 > `50MB` 跳过 AI 分析
- 输出命名清洗：移除非法字符与结尾扩展名，空白替换为下划线，保留原始扩展名

#### 已知限制与建议
- 极小分辨率样例（最短边 ≤ 10 像素）会被模型拒绝（400），建议在上传前放大后再试。
- 个别 RAW 文件可能无法被 `rawpy` 解码（I/O/编解码异常），此类文件会被跳过。
- 若需更高吞吐，可提升 `AI_REQUEST_QPS` 并配合合理重试与超时；亦可在外层分片并发（注意 QPS）。

#### 示例命令
```bash
# 传统模式（按参考表匹配并重命名，保留原扩展名）
python file_filter.py \
  --source example_photos \
  --target output_photos \
  --reference example_reference.csv

# AI 重命名模式（用多模态生成文件名，输出仍保持原扩展名与数据）
python file_filter.py \
  --source example_photos \
  --target output_photos \
  --reference example_reference_ai.csv \
  --ai-naming
```

