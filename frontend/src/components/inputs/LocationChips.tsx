import { ChipMultiSelect, type Suggestion } from "./ChipMultiSelect";

interface Props {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}

/** Location chip-picker backed by Photon (Komoot's free OSM geocoder).
 *
 * Why Photon:
 *   - Free, no API key, no rate-limit auth
 *   - Fast (~150ms), city-level precision
 *   - Returns structured city/state/country we can normalize to the
 *     "City, ST" format our scrapers (YellowPages, Yelp, BBB, Manta,
 *     Google Maps) use
 *
 * We bias to populated places via osm_tag and limit to 8 results.
 */
export function LocationChips({ values, onChange, placeholder }: Props) {
  return (
    <ChipMultiSelect
      values={values}
      onChange={onChange}
      placeholder={placeholder ?? "Type a city — Austin, Tunis, …"}
      onSearch={searchPhoton}
      allowFreeText={true}     // user can still type a custom string if Photon misses
      minQueryLength={2}
      ariaLabel="Locations"
    />
  );
}


// ───────────────────────────────────────────────────────────────────────────


async function searchPhoton(query: string): Promise<Suggestion[]> {
  const url =
    `https://photon.komoot.io/api/?q=${encodeURIComponent(query)}` +
    `&limit=8&lang=en` +
    `&osm_tag=place:city&osm_tag=place:town&osm_tag=place:village&osm_tag=place:county`;

  const res = await fetch(url);
  if (!res.ok) return [];
  const data = await res.json();
  const features: any[] = data?.features ?? [];

  const seen = new Set<string>();
  const out: Suggestion[] = [];
  for (const f of features) {
    const props = f?.properties ?? {};
    const city = props.name as string | undefined;
    const stateRaw = (props.state as string | undefined) ?? "";
    const country = (props.country as string | undefined) ?? "";
    const cc = (props.countrycode as string | undefined) ?? "";
    if (!city) continue;

    // Normalize state to the 2-letter abbreviation when possible (US scrapers
    // use "Austin, TX" not "Austin, Texas"). Falls back to the full state name
    // for non-US results.
    const stateAbbr = US_STATE_ABBR[stateRaw] ?? stateRaw;
    const value = stateAbbr
      ? `${city}, ${stateAbbr}`
      : country
        ? `${city}, ${country}`
        : city;

    if (seen.has(value)) continue;
    seen.add(value);

    const flag = cc ? countryFlag(cc) : "";
    const hintParts = [stateRaw, country, cc].filter(Boolean);
    out.push({
      value,
      label: value,
      hint: `${flag ? flag + " " : ""}${hintParts.join(" · ")}`.trim() || undefined,
    });
  }
  return out;
}

function countryFlag(code: string): string {
  if (!code || code.length !== 2) return "";
  const cc = code.toUpperCase();
  return String.fromCodePoint(...cc.split("").map((c) => 0x1f1e6 + c.charCodeAt(0) - 65));
}

// US state-name → 2-letter abbreviation. Used to normalize Photon's
// "Texas" into "TX" because our cold scrapers parse "City, ST".
const US_STATE_ABBR: Record<string, string> = {
  Alabama: "AL", Alaska: "AK", Arizona: "AZ", Arkansas: "AR",
  California: "CA", Colorado: "CO", Connecticut: "CT", Delaware: "DE",
  "District of Columbia": "DC", Florida: "FL", Georgia: "GA", Hawaii: "HI",
  Idaho: "ID", Illinois: "IL", Indiana: "IN", Iowa: "IA", Kansas: "KS",
  Kentucky: "KY", Louisiana: "LA", Maine: "ME", Maryland: "MD",
  Massachusetts: "MA", Michigan: "MI", Minnesota: "MN", Mississippi: "MS",
  Missouri: "MO", Montana: "MT", Nebraska: "NE", Nevada: "NV",
  "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
  "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", Ohio: "OH",
  Oklahoma: "OK", Oregon: "OR", Pennsylvania: "PA", "Rhode Island": "RI",
  "South Carolina": "SC", "South Dakota": "SD", Tennessee: "TN", Texas: "TX",
  Utah: "UT", Vermont: "VT", Virginia: "VA", Washington: "WA",
  "West Virginia": "WV", Wisconsin: "WI", Wyoming: "WY",
};
