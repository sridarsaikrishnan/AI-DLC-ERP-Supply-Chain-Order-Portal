import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "sm";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

/** design/design-system/components/Button.md — .erp-btn from bundle.css. */
export function Button({ variant = "secondary", size = "md", className, ...rest }: ButtonProps) {
  const classes = ["erp-btn", `erp-btn--${variant}`, size === "sm" ? "erp-btn--sm" : "", className]
    .filter(Boolean)
    .join(" ");
  return <button type="button" className={classes} {...rest} />;
}
