import { Construction } from "lucide-react";
import { Card } from "../design/primitives";

interface Props {
  title: string;
  shipping: string;
}

export function PlaceholderPage({ title, shipping }: Props) {
  return (
    <div className="h-full flex items-center justify-center p-8">
      <Card className="max-w-md w-full p-8 flex flex-col items-center text-center gap-4">
        <div className="w-10 h-10 rounded-[var(--radius-md)] bg-[var(--color-accent-soft)] flex items-center justify-center">
          <Construction className="w-5 h-5 text-[var(--color-accent)]" strokeWidth={1.75} />
        </div>
        <div className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-[var(--color-text-primary)]">{title}</h1>
          <p className="text-[12px] text-[var(--color-text-tertiary)]">
            Coming next plan — {shipping}.
          </p>
        </div>
      </Card>
    </div>
  );
}
