# 照片文件筛选与重命名工具

本项目提供一套简洁而强大的脚本，可对大批量照片依据文件名中的文字或数字片段进行筛选，并将符合条件的图片复制到指定位置。与此同时，脚本会按照预先准备的参考表格为文件赋予更具语义的名称，以实现更高效的整理与归档。

## 核心功能

- **智能检索**：解析文件名中的标识符（可为文字或数字），并与参考表中的记录进行匹配。
- **批量归档**：将匹配到的图片复制至目标目录，自动保留原文件扩展名。
- **自定义命名**：依据参考表中的备注字段重命名文件，使输出结果更具可读性。
- **多格式支持**：兼容 CSV 及 Excel（.xlsx/.xls）格式的参考表格。
- **模糊匹配**：若未找到完全匹配的标识符，脚本会尝试寻找最接近的项，以减少遗漏。
- **AI 智能匹配**：利用 TF-IDF 与余弦相似度，进一步提升模糊匹配的准确性。
- **复制后校验**：复制完成后进行文件大小与 SHA-256 双重校验，失败自动重试并跳过问题文件，最大限度避免拷贝错误。
- **AI视觉理解重命名**：使用阿里云通义千问视觉模型分析图片内容，自动生成描述性文件名。
- **RAW格式支持**：支持专业相机RAW格式（CR2、NEF、ARW、DNG等）的读取和处理。
- **智能压缩**：AI分析时自动压缩图片以优化API上传速度和成本。

## 安装依赖

运行前请确保环境中已安装以下 Python 库：

```bash
pip install pandas openpyxl scikit-learn PySide6 requests Pillow rawpy
```

### 可选依赖
- `rawpy`：用于处理RAW格式图片，如果未安装将跳过RAW文件处理

## 参考表格式要求

### 传统模式（两列）
参考表需包含两列：
1. **标识符**：用于与文件名中的片段匹配，支持文字或数字。
2. **备注信息**：匹配成功后将作为新文件名使用。

### AI重命名模式（单列）
参考表只需包含一列：
1. **标识符**：用于与文件名中的片段匹配，支持文字或数字。

示例参考表格可在仓库中的 `example_reference.csv` 中找到。

## 使用指南

### 命令行模式

```bash
python file_filter.py --source <源文件夹路径> --target <目标文件夹路径> --reference <参考表路径>
```

#### 命令行参数

- `--source` 或 `-s`：包含待筛选照片的源目录。
- `--target` 或 `-t`：输出目录，不存在时会自动创建。
- `--reference` 或 `-r`：参考表格的文件路径。
- `--ai-naming`：启用AI视觉理解重命名功能。

#### 示例

```bash
# 传统模式
python file_filter.py --source /path/to/photos --target /path/to/output --reference example_reference.csv

# AI重命名模式
python file_filter.py --source /path/to/photos --target /path/to/output --reference example_reference.csv --ai-naming
```

## 图形界面 (macOS)

若希望在 macOS 上以图形界面使用本工具，可运行：

```bash
python gui_app.py
```

界面中依次选择：
- 源文件夹：包含待筛选照片
- 目标文件夹：输出目录
- 参考表：CSV 或 Excel 文件
- AI重命名：勾选启用通义千问视觉理解

点击"开始处理"即可，处理日志会在下方实时显示。

### 打包为独立 App（可选）

可以使用 `pyinstaller` 将 GUI 打包为独立应用：

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name PhotoFilterGUI gui_app.py
```

打包后在 `dist/PhotoFilterGUI.app` 下即可直接双击运行。

## 图形界面 (Windows)

在 Windows 上可直接运行：

```bat
run_windows.bat
```

或在命令行中执行：

```bat
python gui_app.py
```

### 打包为独立 EXE（可选）

使用 `pyinstaller` 打包：

```bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name PhotoFilterGUI gui_app.py
```

生成的可执行文件位于 `dist/PhotoFilterGUI` 目录。

## AI视觉理解重命名功能

### 功能说明
启用AI重命名后，系统将：
1. 自动将图片转换为JPG格式（支持RAW格式解码）
2. 智能压缩图片以优化API上传速度
3. 调用阿里云通义千问视觉模型分析图片内容
4. 生成描述性文件名（如：`蓝天白云下的城市建筑.jpg`）

### 支持的图片格式
- **普通格式**：JPG/JPEG、PNG、BMP、GIF、TIFF、WebP
- **RAW格式**：CR2（佳能）、NEF（尼康）、ARW（索尼）、DNG（Adobe）、ORF（奥林巴斯）、RW2（松下）、PEF（宾得）、SRW（三星）、RAF（富士）、X3F（适马）

### 图片压缩优化
- **尺寸限制**：最大1024x768像素
- **质量设置**：80% JPEG质量
- **自动调整**：保持宽高比的同时压缩
- **RAW处理**：专业RAW解码，保持色彩准确性

### API配置
当前使用阿里云通义千问API，如需更换API密钥，请修改 `file_filter.py` 中的 `QWEN_API_KEY` 变量。

## 自动发布到 GitHub Releases

当你打 tag（如 `v1.0.0`）推送到 GitHub 后，Actions 会自动在 macOS 与 Windows 上构建，并把以下产物上传到 Releases：
- `PhotoFilterGUI-macOS.zip`（内含 `.app`）
- `PhotoFilterGUI-Windows.zip`（内含 `.exe` 及所需文件）

手动触发流程：
```bash
git tag v1.0.0
git push origin v1.0.0
```

## 重要说明

1. 脚本仅对文件名中包含参考表格标识符的图片生效，其他文件将被忽略。
2. 当目标目录已存在同名文件时，脚本会在新文件名后追加数字后缀以避免覆盖。
3. 脚本仅复制并重命名文件，不会修改原始图片。
4. AI重命名功能需要网络连接，处理速度取决于API响应时间。
5. 使用AI重命名时，所有图片将统一转换为JPG格式。
6. RAW格式处理需要安装rawpy库，未安装时将跳过RAW文件。
7. 图片压缩可显著减少API上传时间和成本。

## 运行效果示例

### 传统模式
给定如下文件：
- 源目录：`/photos/IMG_1234.jpg`、`/photos/holiday.png`
- 参考表：
  ```
  标识符,备注
  1234,北京风景照
  holiday,假日照片
  ```

执行脚本后，目标目录将生成：
- `/output/北京风景照.jpg`
- `/output/假日照片.png`

### AI重命名模式
给定如下文件：
- 源目录：`/photos/IMG_001.CR2`（RAW格式城市建筑照片）
- 参考表：
  ```
  标识符
  001
  ```

执行脚本后，目标目录将生成：
- `/output/现代城市建筑群_高楼大厦_蓝天白云.jpg`

## 项目结构

仓库中的主要文件与目录说明如下：

- `file_filter.py`：命令行脚本，负责根据参考表筛选、复制并重命名照片。
- `gui_app.py`：基于 PySide6 的图形界面，封装了核心筛选逻辑。
- `example_photos/`：示例源照片，可用于快速体验脚本功能。
- `output_photos/`：示例输出照片，展示处理后的结果格式。
- `example_reference.csv`：示例参考表格，提供标识符到备注的映射。
- `example_reference_ai.csv`：AI重命名模式示例参考表格。
- `tests/`：包含 `pytest` 单元测试，确保核心功能正常工作。
- `requirements.txt`：项目依赖清单。
- `run_windows.bat`：在 Windows 环境下启动 GUI 的批处理脚本。
- `PhotoFilterGUI.spec` 与 `pyinstaller.spec`：用于使用 PyInstaller 打包为可执行文件的配置。

## 开发与测试

1. 安装开发依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 运行单元测试：
   ```bash
   pytest
   ```

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

