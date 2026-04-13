/** TypeBadge — displays document type name in table cells or em-dash for untyped. */

interface TypeBadgeProps {
  typeName: string | null | undefined;
}

export function TypeBadge({ typeName }: TypeBadgeProps) {
  if (typeName) {
    return <span className="text-sm">{typeName}</span>;
  }
  return (
    <span className="text-sm text-muted-foreground">{"\u2014"}</span>
  );
}
