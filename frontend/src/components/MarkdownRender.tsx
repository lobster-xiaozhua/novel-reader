import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface MarkdownRenderProps {
  content: string
  className?: string
}

export default function MarkdownRender({ content, className = '' }: MarkdownRenderProps) {
  return (
    <div className={`prose prose-invert max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '')
            const language = match ? match[1] : ''
            const isInline = !match

            if (isInline) {
              return (
                <code className="px-1.5 py-0.5 rounded-md bg-white/10 text-primary-400 text-sm font-mono" {...props}>
                  {children}
                </code>
              )
            }

            return (
              <div className="rounded-xl overflow-hidden my-4 border border-card-border">
                <div className="flex items-center justify-between px-4 py-2 bg-[#1e1e1e] border-b border-white/5">
                  <span className="text-xs text-text-muted uppercase">{language}</span>
                </div>
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={language}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    padding: '1rem',
                    background: '#1e1e1e',
                    fontSize: '0.875rem',
                  }}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              </div>
            )
          },
          h1({ children }) {
            return <h1 className="text-2xl font-bold text-text-primary mt-8 mb-4 pb-2 border-b border-white/[0.06]">{children}</h1>
          },
          h2({ children }) {
            return <h2 className="text-xl font-semibold text-text-primary mt-6 mb-3">{children}</h2>
          },
          h3({ children }) {
            return <h3 className="text-lg font-medium text-text-primary mt-4 mb-2">{children}</h3>
          },
          p({ children }) {
            return <p className="text-text-secondary leading-relaxed mb-4">{children}</p>
          },
          ul({ children }) {
            return <ul className="list-disc list-inside text-text-secondary mb-4 space-y-1">{children}</ul>
          },
          ol({ children }) {
            return <ol className="list-decimal list-inside text-text-secondary mb-4 space-y-1">{children}</ol>
          },
          li({ children }) {
            return <li className="text-text-secondary">{children}</li>
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-primary-500 pl-4 py-2 my-4 bg-primary-500/5 rounded-r-lg">
                <p className="text-text-secondary italic mb-0">{children}</p>
              </blockquote>
            )
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-4">
                <table className="w-full border-collapse border border-card-border rounded-lg">
                  {children}
                </table>
              </div>
            )
          },
          thead({ children }) {
            return <thead className="bg-card-bg">{children}</thead>
          },
          th({ children }) {
            return <th className="px-4 py-3 text-left text-sm font-medium text-text-primary border-b border-card-border">{children}</th>
          },
          td({ children }) {
            return <td className="px-4 py-3 text-sm text-text-secondary border-b border-white/[0.04]">{children}</td>
          },
          hr() {
            return <hr className="border-white/[0.06] my-6" />
          },
          a({ children, href }) {
            return <a href={href} className="text-primary-500 hover:text-primary-400 underline transition-colors" target="_blank" rel="noopener noreferrer">{children}</a>
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
