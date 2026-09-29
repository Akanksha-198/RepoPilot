export default function Diff({ text }) {
  if (!text) return null;
  return (
    <pre className="diff" tabIndex={0}>
      {text.split('\n').map((line, i) => {
        const c = line.startsWith('+++') || line.startsWith('---') ? 'meta'
          : line.startsWith('+') ? 'add' : line.startsWith('-') ? 'del' : line.startsWith('@@') ? 'hunk' : '';
        return <div key={i} className={c}>{line || ' '}</div>;
      })}
    </pre>
  );
}
