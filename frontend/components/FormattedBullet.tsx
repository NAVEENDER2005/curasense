/** Renders a tiny markdown subset (**bold**, *italic*) as React nodes -
 * no HTML injection, so this stays safe even if a bullet's text ever
 * incorporates LLM-generated content in the future. */
export default function FormattedBullet({ text, className }: { text: string; className?: string }) {
  const parts = text.split(/(\*\*.+?\*\*|\*.+?\*)/g).filter(Boolean);
  return (
    <p className={className}>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith("*") && part.endsWith("*")) {
          return <em key={i}>{part.slice(1, -1)}</em>;
        }
        return <span key={i}>{part}</span>;
      })}
    </p>
  );
}
