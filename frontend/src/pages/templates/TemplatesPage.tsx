import { useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button, Card } from "../../design/primitives";
import { useTemplates, useDeleteTemplate } from "../../api/templates";
import { TemplateEditor } from "./TemplateEditor";
import type { EmailTemplate } from "../../types/template";

export function TemplatesPage() {
  const { data, isLoading } = useTemplates();
  const templates = data?.templates ?? [];
  const deleteMut = useDeleteTemplate();

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<EmailTemplate | null>(null);

  return (
    <div className="p-6 flex flex-col gap-4 w-full">
      <Card className="p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] font-medium">Templates</div>
            <div className="text-[11px] text-[var(--color-text-tertiary)]">
              {templates.length} {templates.length === 1 ? "template" : "templates"}
            </div>
          </div>
          <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
            <Plus className="w-3 h-3" /> New template
          </Button>
        </div>

        {isLoading && (
          <div className="text-[12px] text-[var(--color-text-tertiary)] py-4">Loading…</div>
        )}

        <div className="flex flex-col">
          {templates.map((t) => (
            <div key={t.id} className="flex items-start gap-3 py-3 border-b border-[var(--color-border)] last:border-0">
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium text-[var(--color-text-primary)]">{t.name}</div>
                <div className="text-[12px] text-[var(--color-text-secondary)] truncate mt-0.5">{t.subject}</div>
                <div className="text-[11px] text-[var(--color-text-tertiary)] mt-1 whitespace-pre-line line-clamp-2">{t.body}</div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setEditing(t)}>
                <Pencil className="w-3 h-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (confirm(`Delete template "${t.name}"?`)) deleteMut.mutate(t.id);
                }}
                disabled={deleteMut.isPending}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          ))}
        </div>
      </Card>

      {creating && <TemplateEditor onClose={() => setCreating(false)} />}
      {editing && <TemplateEditor initial={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}
