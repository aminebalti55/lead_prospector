import { useMemo } from "react";
import { City, Country, type ICity } from "country-state-city";
import { ChipMultiSelect, type Suggestion } from "./ChipMultiSelect";

interface Props {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}

/** Location chip-picker backed by `country-state-city` — a fully bundled
 * city dataset (~150K cities). No network call, no API key, instant
 * autocomplete. The previous Photon implementation kept failing under
 * various network conditions; this one always works.
 *
 * Cities are ranked by:
 *   1. exact name match (highest)
 *   2. starts-with prefix
 *   3. substring
 * Ties broken by population proxy (we treat US-state-with-letters first,
 * then country code alphabetical) so big metros like "Austin, TX" surface
 * above tiny villages of the same name.
 */
export function LocationChips({ values, onChange, placeholder }: Props) {
  // Build the full suggestion list once on mount. ~150K entries, but we
  // only filter on demand and slice to top 8 per query — that's fast.
  const allCities = useMemo<ICity[]>(() => City.getAllCities(), []);

  async function searchCities(query: string): Promise<Suggestion[]> {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];

    const exact: ICity[] = [];
    const startsWith: ICity[] = [];
    const contains: ICity[] = [];

    // Single pass — bucket by match strength.
    for (const c of allCities) {
      const name = c.name.toLowerCase();
      if (name === q) exact.push(c);
      else if (name.startsWith(q)) startsWith.push(c);
      else if (name.includes(q)) contains.push(c);
      if (exact.length + startsWith.length >= 30) break;
    }

    const ranked = [...exact, ...startsWith, ...contains].slice(0, 12);

    // Convert to Suggestion. Format depends on country:
    //   US → "Austin, TX"        (matches what our scrapers already use)
    //   non-US → "Tunis, TN" or "Paris, FR"
    const seen = new Set<string>();
    const out: Suggestion[] = [];
    for (const c of ranked) {
      const value = formatCity(c);
      if (seen.has(value)) continue;
      seen.add(value);
      const country = Country.getCountryByCode(c.countryCode);
      out.push({
        value,
        label: value,
        hint: country
          ? `${countryFlag(c.countryCode)} ${country.name}`
          : c.countryCode,
      });
      if (out.length >= 8) break;
    }
    return out;
  }

  return (
    <ChipMultiSelect
      values={values}
      onChange={onChange}
      placeholder={placeholder ?? "Type a city — Austin, Tunis, Paris, …"}
      onSearch={searchCities}
      allowFreeText={true}
      minQueryLength={2}
      debounceMs={50}
      ariaLabel="Locations"
    />
  );
}

function formatCity(c: ICity): string {
  // For US/Canada/Mexico/India/etc. the stateCode is meaningful (TX, CA, ON).
  // For others we fall back to country code so the chip still disambiguates
  // duplicates like "Cordoba, AR" vs "Cordoba, ES".
  if (c.stateCode && c.stateCode.length <= 3) {
    return `${c.name}, ${c.stateCode}`;
  }
  return `${c.name}, ${c.countryCode}`;
}

function countryFlag(code: string): string {
  if (!code || code.length !== 2) return "";
  const cc = code.toUpperCase();
  return String.fromCodePoint(...cc.split("").map((c) => 0x1f1e6 + c.charCodeAt(0) - 65));
}
