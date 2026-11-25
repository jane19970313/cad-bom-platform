"use client";

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  className?: string;
}

export function StatCard({
  label,
  value,
  className = "",
}: StatCardProps) {
  return (
    <div className={`rounded-md bg-muted p-3 ${className}`}>
      <p className="text-xl font-semibold">{value}</p>

      <p className="mt-1 text-xs text-muted-foreground">
        {label}
      </p>
    </div>
  );
}