import { useState } from "react";
import { X } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useCreateTemplate, useUpdateTemplate } from "../../api/templates";
import type { EmailTemplate } from "../../types/template";

interface Props {
  initial?: EmailTemplate;
  onClose: () => void;
}

const inputClass =
  "h-8 px-2.5 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] w-full";

export function TemplateEditor({ initial, onClose }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [subject, setSubject] = useState(initial?.subject ?? "");
  const [body, setBody] = useState(initial?.body ?? "");

  const create = useCreateTemplate();
  const update = useUpdateTemplate();
  const isPending = create.isPending || update.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !subject.trim() || !body.trim()) return;
    if (initial) {
      await update.mutateAsync({ id: initial.id, body: { name, subject, body } });
    } else {
      await create.mutateAsync({ name, subject, body });
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <Card
        className="w-[640px] max-h-[85vh] overflow-auto p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-[var(--color-text-primary)]">
            {initial ? "Edit template" : "New template"}
          </h2>
          <button type="button" onClick={onClose} className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Name</label>
            <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Subject</label>
            <input className={inputClass} value={subject} onChange={(e) => setSubject(e.target.value)} required
              placeholder="Quick idea for {company}" />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Body</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              rows={14}
              className="px-2.5 py-2 bg-[var(--color-surface-raised)] border border-[var(--color-border)] rounded-[var(--radius-sm)] text-[13px] text-[var(--color-text-primary)] font-mono resize-y"
              placeholder={"Hi {first_name},\n\n..."}
            />
            <p className="text-[10px] text-[var(--color-text-tertiary)]">
              Variables: <code>{"{name}"}</code> · <code>{"{first_name}"}</code> · <code>{"{company}"}</code> · <code>{"{title}"}</code> · <code>{"{value}"}</code> · <code>{"{source}"}</code> · <code>{"{location}"}</code> · <code>{"{sender_name}"}</code>
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={isPending}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={isPending}>
              {isPending ? "Saving…" : initial ? "Save changes" : "Create"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
