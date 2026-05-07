import { ChipMultiSelect, type Suggestion } from "./ChipMultiSelect";

interface Props {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}

/** Curated software-keyword suggestions for the Direct-leads search box.
 * Free-text is also allowed — the suggestions are just a quick-add
 * shortcut so users don't have to type every variant. */
const SUGGESTIONS: Suggestion[] = [
  // English roles
  { value: "react developer", label: "react developer" },
  { value: "next.js developer", label: "next.js developer" },
  { value: "fullstack developer", label: "fullstack developer" },
  { value: "frontend developer", label: "frontend developer" },
  { value: "backend developer", label: "backend developer" },
  { value: "software engineer", label: "software engineer" },
  { value: "node.js developer", label: "node.js developer" },
  { value: "typescript developer", label: "typescript developer" },
  { value: "python developer", label: "python developer" },
  { value: "fastapi developer", label: "fastapi developer" },
  { value: "django developer", label: "django developer" },
  { value: "devops engineer", label: "devops engineer" },
  { value: "data engineer", label: "data engineer" },
  { value: "ai engineer", label: "ai engineer" },
  { value: "machine learning engineer", label: "machine learning engineer" },
  // French / Tunisian
  { value: "ingénieur logiciel", label: "ingénieur logiciel" },
  { value: "développeur fullstack", label: "développeur fullstack" },
  { value: "développeur web", label: "développeur web" },
  { value: "développeur react", label: "développeur react" },
  { value: "développeur python", label: "développeur python" },
  // Contract-flavored
  { value: "freelance react", label: "freelance react" },
  { value: "contract react developer", label: "contract react developer" },
];

export function KeywordChips({ values, onChange, placeholder }: Props) {
  return (
    <ChipMultiSelect
      values={values}
      onChange={onChange}
      placeholder={placeholder ?? "Type a role then press Enter — react developer, next.js, …"}
      staticSuggestions={SUGGESTIONS}
      allowFreeText={true}
      minQueryLength={1}
      ariaLabel="Keywords"
    />
  );
}
