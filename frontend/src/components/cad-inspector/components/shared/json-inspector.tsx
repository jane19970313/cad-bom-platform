"use client";

interface JsonInspectorProps {
  data: unknown;
  emptyMessage?: string;
}

export function JsonInspector({
  data,
  emptyMessage = "No data available for this stage.",
}: JsonInspectorProps) {
  if (
    data === null ||
    data === undefined ||
    (Array.isArray(data) && data.length === 0)
  ) {
    return (
      <div className="p-6 text-center text-sm text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return (
    <pre className="overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted p-3 text-xs leading-relaxed">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}