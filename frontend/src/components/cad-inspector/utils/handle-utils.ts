export function normalizeHandle(value: unknown): string {
  return String(value ?? "")
    .replace(/^0x/i, "")
    .trim()
    .toUpperCase();
}

export function getNodeHandle(node: any): string {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }

  return String(
    node?.source_handle ??
      node?.handle ??
      node?.element_id ??
      node?.id ??
      ""
  );
}

export function getElementHandle(element: any): string {
  return String(element?.source_handle ?? element?.handle ?? "");
}