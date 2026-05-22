import { useState } from 'react'
import { FileText, Eye, Pencil } from 'lucide-react'
import MarkdownRender from '@/components/MarkdownRender'

const demoContent = `# 小说阅读器使用指南

## 快速开始

欢迎使用 **小说阅读器**！这是一个功能强大的阅读管理平台。

### 主要功能

- 📚 **书籍管理**：批量导入、分类整理
- 🔖 **标签系统**：灵活组织书籍
- 📊 **阅读统计**：追踪阅读进度
- 🤖 **爬虫任务**：自动抓取网络小说

## 代码示例

\`\`\`python
# 批量导入书籍示例
from apps.books.models import Book

book = Book.objects.create(
    title="示例小说",
    author="作者名",
    category="玄幻"
)
\`\`\`

## 表格展示

| 功能 | 状态 | 说明 |
|------|------|------|
| 书籍导入 | ✅ | 支持TXT批量导入 |
| 阅读进度 | ✅ | 自动保存阅读位置 |
| 爬虫任务 | ✅ | 支持多站点抓取 |
| 数据统计 | ✅ | 可视化图表展示 |

## 引用

> 阅读是人类进步的阶梯。——高尔基

## 链接

[访问 GitHub 仓库](https://github.com)

---

*更多功能正在开发中...*
`

export default function MarkdownDemo() {
  const [mode, setMode] = useState<'preview' | 'edit'>('preview')
  const [content, setContent] = useState(demoContent)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-primary-500" />
          <h2 className="text-xl font-bold text-text-primary">Markdown 渲染器</h2>
        </div>
        <div className="flex items-center gap-2 bg-card-bg border border-card-border rounded-lg p-1">
          <button
            onClick={() => setMode('preview')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${mode === 'preview' ? 'bg-primary-500 text-white' : 'text-text-secondary hover:text-text-primary'}`}
          >
            <Eye className="w-4 h-4" />
            预览
          </button>
          <button
            onClick={() => setMode('edit')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${mode === 'edit' ? 'bg-primary-500 text-white' : 'text-text-secondary hover:text-text-primary'}`}
          >
            <Pencil className="w-4 h-4" />
            编辑
          </button>
        </div>
      </div>

      <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
        {mode === 'preview' ? (
          <div className="p-6">
            <MarkdownRender content={content} />
          </div>
        ) : (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-[600px] p-6 bg-content-bg text-text-primary font-mono text-sm resize-none focus:outline-none"
            placeholder="输入 Markdown 内容..."
          />
        )}
      </div>
    </div>
  )
}
