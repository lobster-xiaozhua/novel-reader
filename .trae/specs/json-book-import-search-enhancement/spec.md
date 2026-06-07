# JSON格式书籍导入与搜索增强 Spec

## Why
当前系统仅支持标准txt格式的书籍目录扫描，但用户提供的书籍数据可能以JSON格式存在（包含id、title、author、description、cover、chapters数组等字段）。需要支持JSON格式的自动识别、转化和清理，同时增强搜索引擎的训练资源和变化检测能力，优化前端搜索结果展示。

## What Changes
- **JSON书籍自动转化**：扫描到书籍目录中的JSON文件时，自动解析并转化为标准书籍格式（txt章节 + metadata.json）
- **删除旧文件**：转化完成后清理原始JSON文件，避免重复处理
- **异常文件处理**：兼容各种异常格式的JSON（缺失字段、编码错误、章节文件不存在等）
- **书籍自动分割整理**：通过文本内容规律（如章节标题模式）智能分割单文件为多章节
- **前端搜索结果显示优化**：优雅美观的搜索结果展示，符合大众审美
- **模糊搜索训练资源增强**：扩展拼音映射表、同义词库，提升搜索质量
- **哈希值变化检测**：通过文件哈希判断内容是否变更，减少不必要的重复处理和索引重建
- **TDD测试驱动**：所有新功能先写测试，后写实现

## Impact
- Affected specs: 书籍导入、搜索引擎、文件监控、前端搜索页面
- Affected code:
  - 新增：`utils/json_book_importer.py`（JSON书籍导入器）
  - 新增：`utils/file_hash.py`（文件哈希工具）
  - 新增：`utils/chapter_splitter.py`（智能章节分割器）
  - 修改：`utils/watchfile.py`（电子狗增加JSON检测和哈希变化检测）
  - 修改：`apps/recommender/search.py`（扩展拼音映射和同义词库）
  - 修改：`apps/recommender/management/commands/init_engines.py`（启动时支持JSON导入）
  - 修改：`apps/api/routes_books.py`（扫描API支持JSON导入）
  - 修改：`frontend/app/(reader)/search/page.tsx`（优化搜索结果展示）
  - 新增：`tests/test_json_book_importer.py`（TDD测试）
  - 新增：`tests/test_file_hash.py`（TDD测试）
  - 新增：`tests/test_chapter_splitter.py`（TDD测试）

## ADDED Requirements

### Requirement: JSON书籍自动转化
系统 SHALL 在扫描书籍目录时自动检测JSON格式的书籍描述文件，并解析转化为标准格式。

#### Scenario: 标准JSON格式书籍导入
- **WHEN** 书籍目录下存在包含 `chapters` 数组的JSON文件（如 `book.json`）
- **THEN** 系统解析JSON中的 title、author、description、chapters 字段，创建 metadata.json 并保留已有章节文件

#### Scenario: JSON中章节文件不存在
- **WHEN** JSON中引用的章节文件路径不存在
- **THEN** 系统记录警告日志，跳过该章节，继续处理其他章节

#### Scenario: JSON格式错误
- **WHEN** JSON文件内容格式错误无法解析
- **THEN** 系统记录错误日志，跳过该JSON文件，不中断其他书籍处理

### Requirement: 删除旧JSON文件
系统 SHALL 在成功转化JSON书籍后删除原始JSON文件，避免重复处理和磁盘占用。

#### Scenario: 转化成功后清理
- **WHEN** JSON书籍成功转化为标准格式
- **THEN** 原始JSON文件被删除，目录中仅保留txt章节和metadata.json

#### Scenario: 转化失败时保留
- **WHEN** JSON书籍转化过程中发生错误
- **THEN** 原始JSON文件保留，不删除

### Requirement: 异常文件处理
系统 SHALL 提供高效的异常兼容性，处理各种异常格式的JSON和txt文件。

#### Scenario: 编码自动检测
- **WHEN** 章节文件编码非UTF-8（如GBK、GB2312）
- **THEN** 系统自动尝试多种编码读取，成功读取后以UTF-8重新保存

#### Scenario: 缺失必填字段
- **WHEN** JSON中缺少 title 字段
- **THEN** 系统使用目录名作为书名，使用JSON中其他可用字段

#### Scenario: 空章节文件
- **WHEN** 章节文件存在但内容为空
- **THEN** 系统记录警告，创建空章节记录

### Requirement: 书籍自动分割整理
系统 SHALL 通过文本内容规律智能检测章节边界，支持单文件自动分割为多章节。

#### Scenario: 标准章节标题分割
- **WHEN** 单文件内容包含"第X章"、"Chapter X"等标准章节标题
- **THEN** 系统按章节标题分割为独立章节文件

#### Scenario: 无章节标题的文本
- **WHEN** 单文件内容无明确章节标题
- **THEN** 系统按段落数量均分，每50段为一个章节

### Requirement: 前端搜索结果显示优化
前端 SHALL 在搜索结果页面显示优雅美观的书籍卡片，包含封面渐变色、匹配原因标签、匹配章节预览。

#### Scenario: 搜索结果含匹配原因
- **WHEN** 用户搜索关键词后返回结果
- **THEN** 每本书显示匹配原因标签（如"书名匹配"、"拼音匹配"、"作者匹配"）

#### Scenario: 搜索结果含章节预览
- **WHEN** 搜索结果中包含章节级别匹配
- **THEN** 显示匹配章节的标题和内容预览片段

### Requirement: 模糊搜索训练资源增强
搜索引擎 SHALL 拥有足够的中文模糊搜索训练资源，包括扩展的拼音映射表和同义词库。

#### Scenario: 拼音搜索覆盖常用汉字
- **WHEN** 用户输入拼音关键词搜索
- **THEN** 拼音映射表覆盖至少800个常用汉字

#### Scenario: 同义词扩展
- **WHEN** 用户搜索"科幻"
- **THEN** 搜索结果自动扩展包含"三体"、"刘慈欣"、"未来"等关联词

### Requirement: 哈希值变化检测
系统 SHALL 通过文件内容哈希值判断内容是否变更，减少不必要的重复处理。

#### Scenario: 文件内容未变化
- **WHEN** 电子狗检测到文件mtime变化但内容哈希值未变
- **THEN** 系统跳过该文件的重新导入和索引重建

#### Scenario: 文件内容变化
- **WHEN** 电子狗检测到文件内容哈希值变化
- **THEN** 系统重新导入该文件并更新索引

## MODIFIED Requirements

### Requirement: 电子狗扫描逻辑增强
现有的 `BookWatcher._scan_books()` 方法 SHALL 扩展以支持JSON文件检测和哈希值比较。

#### Scenario: 扫描检测JSON文件
- **WHEN** 书籍目录下存在JSON文件
- **THEN** 电子狗识别为待转化书籍，触发JSON导入流程

#### Scenario: 哈希值变化比对
- **WHEN** 电子狗对比新旧书籍状态
- **THEN** 使用内容哈希值而非仅mtime判断是否变更

## REMOVED Requirements
无