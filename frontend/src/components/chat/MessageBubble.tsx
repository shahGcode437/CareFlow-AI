import type { ReactNode } from "react";
import { Sparkles, User } from "lucide-react";
import { formatRelativeTime } from "@/lib/formatTimestamp";
import { cn } from "@/lib/utils";

/**
 * A single chat row. Two visual variants:
 *
 *   - `user`: subtle background, right-side avatar
 *   - `assistant`: primary-soft bubble, left-side avatar, optional
 *     `attachment` slot (used to render an IntentCard beneath the
 *     text) and an optional footer (staff-review banner, request-id).
 */
export function MessageBubble({
  role,
  text,
  timestamp,
  attachment,
  footer,
}: {
  role: "user" | "assistant";
  text: string;
  timestamp: number;
  attachment?: ReactNode;
  footer?: ReactNode;
}) {
  const isUser = role === "user";
  return (
    <div
      className={cn(
        "flex w-full gap-3 animate-fade-in-up",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {!isUser && (
        <Avatar
          role="assistant"
          className="mt-0.5 bg-primary text-primary-foreground"
        />
      )}
      <div
        className={cn(
          "flex min-w-0 max-w-[calc(100%-3rem)] flex-col sm:max-w-[80%]",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "rounded-tr-md bg-primary text-primary-foreground"
              : "rounded-tl-md bg-primary-soft text-primary-soft-foreground",
          )}
        >
          {text.split("\n").map((line, i) => (
            <p key={i} className={i === 0 ? "" : "mt-2"}>
              {line}
            </p>
          ))}
        </div>
        {attachment && <div className="mt-3 w-full">{attachment}</div>}
        {footer && <div className="mt-1.5 w-full">{footer}</div>}
        <div className="mt-1 text-[11px] text-muted-foreground">
          {formatRelativeTime(timestamp)}
        </div>
      </div>
      {isUser && (
        <Avatar
          role="user"
          className="mt-0.5 bg-muted text-muted-foreground"
        />
      )}
    </div>
  );
}

function Avatar({
  role,
  className,
}: {
  role: "user" | "assistant";
  className?: string;
}) {
  const Icon = role === "user" ? User : Sparkles;
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex size-8 flex-shrink-0 items-center justify-center rounded-full",
        className,
      )}
    >
      <Icon className="size-4" strokeWidth={1.75} />
    </span>
  );
}
