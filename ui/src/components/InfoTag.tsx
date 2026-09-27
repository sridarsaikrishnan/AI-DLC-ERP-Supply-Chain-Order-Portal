/** A "?" hover/focus hint for a field or column that isn't self-explanatory. CSS-only
 * popover (no JS positioning library) — see .infotag in ui.css. */
export function InfoTag({ text }: { text: string }) {
  return (
    <span className="infotag" tabIndex={0} aria-label={text}>
      ?<span className="infotag__bubble" role="tooltip">{text}</span>
    </span>
  );
}
