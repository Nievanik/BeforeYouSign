// The agent's markdown report, rendered as React elements (never raw HTML: the text comes from an LLM).
// shortcut: handles headings, bullet/numbered lists, tables, **bold** and paragraphs; add a markdown lib if reports need more.

function inline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  )
}

const cells = (row: string) => row.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim())

export default function AgentReport({ markdown }: { markdown: string }) {
  const lines = markdown.split('\n')
  const out: React.ReactNode[] = []
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue
    const h = line.match(/^(#{1,4})\s+(.*)/)
    if (h) {
      out.push(<h4 key={i} className={`agent-report-h${h[1].length}`}>{inline(h[2])}</h4>)
    } else if (line.startsWith('|')) {
      const rows: string[] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(lines[i++].trim())
      i--
      const body = rows.filter((r) => !/^\|[\s:|-]+\|$/.test(r)) // drop the |---|---| divider
      out.push(
        <table key={i} className="agent-report-table">
          <thead><tr>{cells(body[0]).map((c, j) => <th key={j}>{inline(c)}</th>)}</tr></thead>
          <tbody>
            {body.slice(1).map((r, k) => <tr key={k}>{cells(r).map((c, j) => <td key={j}>{inline(c)}</td>)}</tr>)}
          </tbody>
        </table>,
      )
    } else if (/^([-*]|\d+\.)\s+/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) items.push(lines[i++].trim().replace(/^([-*]|\d+\.)\s+/, ''))
      i--
      out.push(<ul key={i}>{items.map((t, k) => <li key={k}>{inline(t)}</li>)}</ul>)
    } else {
      out.push(<p key={i}>{inline(line.replace(/^_(.*)_$/, '$1'))}</p>)
    }
  }
  return <div className="agent-report">{out}</div>
}
