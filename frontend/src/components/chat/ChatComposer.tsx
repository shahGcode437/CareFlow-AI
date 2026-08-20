import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { SendHorizonal } from "lucide-react";
import { cn } from "@/lib/utils";

const MAX_HEIGHT_PX = 180;

export interface ChatComposerHandle {
  /** Fill the textarea, focus it, and place the cursor at the end. */
  setValueAndFocus: (value: string) => void;
  focus: () => void;
}

interface ChatComposerProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * Autosizing chat textarea + send button.
 *
 *   - Enter sends. Shift+Enter or IME composition inserts a newline.
 *   - `enterKeyHint="send"` gives iOS/Android keyboards the right glyph.
 *   - Disabled while a reply is in flight; the send button also
 *     disables when the trimmed value is empty.
 *   - The button and textarea both meet a 44 px minimum touch target.
 */
export const ChatComposer = forwardRef<ChatComposerHandle, ChatComposerProps>(
  function ChatComposer({ onSend, disabled, placeholder, className }, ref) {
    const [value, setValue] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);

    useImperativeHandle(
      ref,
      () => ({
        setValueAndFocus(next: string) {
          setValue(next);
          // Focus + move caret to end on the next tick so React has
          // applied the value.
          queueMicrotask(() => {
            const el = textareaRef.current;
            if (!el) return;
            el.focus();
            const len = el.value.length;
            el.setSelectionRange(len, len);
          });
        },
        focus() {
          textareaRef.current?.focus();
        },
      }),
      [],
    );

    useEffect(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
    }, [value]);

    const trimmed = value.trim();
    const canSend = trimmed.length > 0 && !disabled;

    function handleKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
      if (event.key !== "Enter") return;
      if (event.shiftKey) return; // newline
      if (event.nativeEvent.isComposing) return; // IME
      event.preventDefault();
      if (!canSend) return;
      onSend(trimmed);
      setValue("");
    }

    function handleSendClick() {
      if (!canSend) return;
      onSend(trimmed);
      setValue("");
    }

    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendClick();
        }}
        className={cn(
          "flex items-end gap-2 rounded-2xl border border-border bg-card p-2",
          "focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-ring/50",
          className,
        )}
      >
        <label htmlFor="chat-composer-textarea" className="sr-only">
          Message CareFlow AI
        </label>
        <textarea
          id="chat-composer-textarea"
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
          placeholder={
            placeholder ?? "Ask about availability, book, reschedule, or cancel…"
          }
          enterKeyHint="send"
          spellCheck
          autoComplete="off"
          className={cn(
            "block max-h-[180px] min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2.5 text-sm text-foreground",
            "placeholder:text-muted-foreground focus:outline-none",
            "disabled:cursor-not-allowed disabled:opacity-60",
          )}
        />
        <button
          type="submit"
          disabled={!canSend}
          aria-label="Send message"
          className={cn(
            "inline-flex size-11 flex-shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground",
            "transition-colors hover:bg-primary/90",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          <SendHorizonal className="size-4.5" strokeWidth={1.75} />
        </button>
      </form>
    );
  },
);
