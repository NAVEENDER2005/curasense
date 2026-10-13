interface BarItem {
  label: string;
  value: number;
  displayValue: string;
  color?: string;
}

/** Simple horizontal bar comparison for a handful of categories - the right
 * form for "compare magnitude across few categories" per the dataviz skill's
 * form heuristic (no need for a full chart library at this scale). */
export default function BarList({ items, emptyLabel }: { items: BarItem[]; emptyLabel: string }) {
  if (items.length === 0) {
    return <p className="py-6 text-sm text-ink-muted">{emptyLabel}</p>;
  }
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="flex flex-col gap-3">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <div className="w-32 shrink-0 truncate text-sm text-ink-secondary" title={item.label}>
            {item.label}
          </div>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-muted">
            <div
              className="h-full rounded-full"
              style={{ width: `${(item.value / max) * 100}%`, backgroundColor: item.color || "var(--color-brand)" }}
            />
          </div>
          <div className="w-24 shrink-0 text-right text-sm font-medium tabular-nums text-ink">{item.displayValue}</div>
        </div>
      ))}
    </div>
  );
}
