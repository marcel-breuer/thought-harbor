export function humanize(value: string): string {
  return value.replaceAll('_', ' ');
}

export function provenanceLabel(sourceType: string, location: Record<string, unknown>): string {
  const page = location.page;
  if (typeof page === 'number') return `${sourceType} · page ${page}`;
  const section = location.section;
  if (typeof section === 'string' && section) return `${sourceType} · ${section}`;
  return sourceType;
}
