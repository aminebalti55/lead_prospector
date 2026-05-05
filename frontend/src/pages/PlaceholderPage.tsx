interface Props {
  title: string;
  shipping: string;
}

export function PlaceholderPage({ title, shipping }: Props) {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-md">
        <h1 className="text-2xl font-semibold text-[--color-text-primary] mb-2">{title}</h1>
        <p className="text-[13px] text-[--color-text-secondary]">
          Coming next plan — {shipping}.
        </p>
      </div>
    </div>
  );
}
