import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Markdown({ source }: { source: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{ table: ({ children }) => <div className="md-scroll"><table>{children}</table></div> }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
