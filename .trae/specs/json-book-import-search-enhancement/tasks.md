# Tasks: JSON格式书籍导入与搜索增强

## 任务列表

- [x] Task 1: 创建文件哈希工具模块 `utils/file_hash.py`
  - [x] 实现 `compute_file_hash(filepath)` 函数，使用SHA256计算文件内容哈希
  - [x] 实现 `compute_dir_hash(dirpath)` 函数，计算目录下所有txt文件哈希的聚合值
  - [x] 实现 `hash_storage` 上下文管理器，支持JSON格式的哈希值持久化存储
  - [x] **TDD**: 先写 `tests/test_file_hash.py`，验证哈希计算正确性和稳定性
  - ✅ 8个测试全部通过

- [x] Task 2: 创建智能章节分割器 `utils/chapter_splitter.py`
  - [x] 实现 `split_text_to_chapters(text)` 函数，支持正则匹配章节标题分割
  - [x] 支持中文"第X章"、英文"Chapter X"、数字序号等多种章节格式
  - [x] 当无章节标题时，按段落数量均分（每50段一个章节）
  - [x] 实现 `auto_split_book_dir(book_dir)` 函数，扫描目录中单文件并自动分割
  - [x] **TDD**: 先写 `tests/test_chapter_splitter.py`
  - ✅ 7个测试全部通过

- [x] Task 3: 创建JSON书籍导入器 `utils/json_book_importer.py`
  - [x] 实现 `detect_json_files(book_dir)` 检测目录中的JSON文件
  - [x] 实现 `parse_book_json(json_path)` 解析JSON，提取title/author/description/chapters
  - [x] 实现 `import_json_book(json_path)` 完整导入流程：解析→验证→创建metadata.json→清理
  - [x] 处理异常情况：缺失字段、编码错误、章节文件不存在、JSON格式错误
  - [x] 转化成功后删除原始JSON文件
  - [x] **TDD**: 先写 `tests/test_json_book_importer.py`
  - ✅ 14个测试全部通过

- [x] Task 4: 增强电子狗文件监控 `utils/watchfile.py`
  - [x] 在 `_scan_books()` 中加入JSON文件检测逻辑
  - [x] 在 `_diff_and_import()` 中使用哈希值替代mtime判断变更
  - [x] 检测到JSON文件时自动触发导入流程
  - [x] 记录哈希值缓存，减少文件重复读取

- [x] Task 5: 增强搜索引擎训练资源 `apps/recommender/search.py`
  - [x] 扩展拼音映射表至800+常用汉字（实际1465个唯一字符）
  - [x] 扩展同义词库（增加热门小说类别相关词，11个分类扩展至12个同义词）
  - [x] 添加搜索结果缓存哈希键，基于内容哈希判断缓存有效性

- [x] Task 6: 更新启动初始化命令 `apps/recommender/management/commands/init_engines.py`
  - [x] 在自动扫描步骤前增加JSON文件检测和转化
  - [x] 扫描完成后使用哈希值判断是否需要重建索引

- [x] Task 7: 更新书籍API路由 `apps/api/routes_books.py`
  - [x] 在 `scan_book_dir` 函数中增加JSON文件检测和转化
  - [x] 导入后清理JSON文件

- [x] Task 8: 优化前端搜索结果显示 `frontend/app/(reader)/search/page.tsx`
  - [x] 使用高级搜索API (`/search/advanced/`) 替代基本搜索API
  - [x] 显示匹配原因标签（Badge组件）
  - [x] 显示匹配章节预览片段
  - [x] 优化书籍卡片布局（封面渐变色、作者、分类、标签）
  - [x] 添加搜索结果骨架屏加载状态

- [x] Task 9: 运行所有测试验证
  - [x] 运行 `tests/test_file_hash.py` - 8 passed
  - [x] 运行 `tests/test_chapter_splitter.py` - 7 passed
  - [x] 运行 `tests/test_json_book_importer.py` - 14 passed
  - [x] 运行 Django check --deploy - 无错误（仅安全警告）
  - [x] 验证拼音映射覆盖1465个唯一汉字
  - ✅ 29个测试全部通过

- [ ] Task 10: 提交到GitHub远程仓库
  - [ ] 检查所有变更文件
  - [ ] 生成规范的commit message
  - [ ] 提交并推送到GitHub远程仓库

## 任务依赖关系

- Task 2 依赖 Task 1（章节分割器可能需要文件哈希）
- Task 3 依赖 Task 1、Task 2（JSON导入器需要哈希和分割功能）
- Task 4 依赖 Task 1、Task 3（电子狗需要哈希和JSON导入）
- Task 5 可并行执行
- Task 6 依赖 Task 3（初始化需要JSON导入）
- Task 7 依赖 Task 3（API路由需要JSON导入）
- Task 8 可并行执行
- Task 9 依赖 Task 1-8
- Task 10 依赖 Task 9