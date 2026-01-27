import { useMemo, useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  FormControlLabel,
  FormGroup,
  Slider,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import type { RunCreateRequest } from "../api/types";

type Props = {
  loading: boolean;
  onSubmit: (body: RunCreateRequest) => void;
};

const ALL_NICHES: Array<RunCreateRequest["niches"][number]> = [
  "plumbing",
  "dental",
  "pest_control",
];

const ALL_SCRAPERS = ["google_maps", "yelp", "yellowpages", "bbb", "manta"];

// Popular US cities for lead prospecting
const US_CITIES = [
  // Texas
  { city: "Austin", state: "TX", label: "Austin, TX" },
  { city: "Houston", state: "TX", label: "Houston, TX" },
  { city: "Dallas", state: "TX", label: "Dallas, TX" },
  { city: "San Antonio", state: "TX", label: "San Antonio, TX" },
  { city: "Fort Worth", state: "TX", label: "Fort Worth, TX" },
  // California
  { city: "Los Angeles", state: "CA", label: "Los Angeles, CA" },
  { city: "San Francisco", state: "CA", label: "San Francisco, CA" },
  { city: "San Diego", state: "CA", label: "San Diego, CA" },
  { city: "San Jose", state: "CA", label: "San Jose, CA" },
  { city: "Sacramento", state: "CA", label: "Sacramento, CA" },
  // Florida
  { city: "Miami", state: "FL", label: "Miami, FL" },
  { city: "Tampa", state: "FL", label: "Tampa, FL" },
  { city: "Orlando", state: "FL", label: "Orlando, FL" },
  { city: "Jacksonville", state: "FL", label: "Jacksonville, FL" },
  // New York
  { city: "New York", state: "NY", label: "New York, NY" },
  { city: "Buffalo", state: "NY", label: "Buffalo, NY" },
  // Illinois
  { city: "Chicago", state: "IL", label: "Chicago, IL" },
  // Arizona
  { city: "Phoenix", state: "AZ", label: "Phoenix, AZ" },
  { city: "Tucson", state: "AZ", label: "Tucson, AZ" },
  { city: "Scottsdale", state: "AZ", label: "Scottsdale, AZ" },
  // Colorado
  { city: "Denver", state: "CO", label: "Denver, CO" },
  { city: "Colorado Springs", state: "CO", label: "Colorado Springs, CO" },
  // Georgia
  { city: "Atlanta", state: "GA", label: "Atlanta, GA" },
  // North Carolina
  { city: "Charlotte", state: "NC", label: "Charlotte, NC" },
  { city: "Raleigh", state: "NC", label: "Raleigh, NC" },
  // Washington
  { city: "Seattle", state: "WA", label: "Seattle, WA" },
  // Massachusetts
  { city: "Boston", state: "MA", label: "Boston, MA" },
  // Nevada
  { city: "Las Vegas", state: "NV", label: "Las Vegas, NV" },
  // Ohio
  { city: "Columbus", state: "OH", label: "Columbus, OH" },
  { city: "Cleveland", state: "OH", label: "Cleveland, OH" },
  // Michigan
  { city: "Detroit", state: "MI", label: "Detroit, MI" },
  // Pennsylvania
  { city: "Philadelphia", state: "PA", label: "Philadelphia, PA" },
  { city: "Pittsburgh", state: "PA", label: "Pittsburgh, PA" },
  // Tennessee
  { city: "Nashville", state: "TN", label: "Nashville, TN" },
  { city: "Memphis", state: "TN", label: "Memphis, TN" },
  // Oregon
  { city: "Portland", state: "OR", label: "Portland, OR" },
  // Minnesota
  { city: "Minneapolis", state: "MN", label: "Minneapolis, MN" },
  // Missouri
  { city: "Kansas City", state: "MO", label: "Kansas City, MO" },
  { city: "St. Louis", state: "MO", label: "St. Louis, MO" },
  // Indiana
  { city: "Indianapolis", state: "IN", label: "Indianapolis, IN" },
  // Utah
  { city: "Salt Lake City", state: "UT", label: "Salt Lake City, UT" },
  // Louisiana
  { city: "New Orleans", state: "LA", label: "New Orleans, LA" },
  // Oklahoma
  { city: "Oklahoma City", state: "OK", label: "Oklahoma City, OK" },
  // Kentucky
  { city: "Louisville", state: "KY", label: "Louisville, KY" },
  // Maryland
  { city: "Baltimore", state: "MD", label: "Baltimore, MD" },
  // Wisconsin
  { city: "Milwaukee", state: "WI", label: "Milwaukee, WI" },
  // New Mexico
  { city: "Albuquerque", state: "NM", label: "Albuquerque, NM" },
].sort((a, b) => a.label.localeCompare(b.label));

type CityOption = (typeof US_CITIES)[number];

export default function RunForm({ loading, onSubmit }: Props) {
  const [selectedCities, setSelectedCities] = useState<CityOption[]>([
    US_CITIES.find((c) => c.label === "Austin, TX")!,
  ]);
  const [niches, setNiches] = useState<RunCreateRequest["niches"]>([
    "plumbing",
    "dental",
    "pest_control",
  ]);
  const [skipAudit, setSkipAudit] = useState(false);
  const [fetchDetails, setFetchDetails] = useState(false);
  const [fetchEmails, setFetchEmails] = useState(false);
  const [skipScrapers, setSkipScrapers] = useState<string[]>([]);
  const [maxResults, setMaxResults] = useState<number>(20);

  const locations = useMemo(
    () => selectedCities.map((c) => c.label),
    [selectedCities]
  );

  const canSubmit = locations.length > 0 && niches.length > 0 && !loading;

  return (
    <Card>
      <CardContent>
        <Stack spacing={2.5}>
          <Box>
            <Typography sx={{ fontWeight: 700, mb: 1 }}>Locations</Typography>
            <Autocomplete
              multiple
              options={US_CITIES}
              value={selectedCities}
              onChange={(_, newValue) => setSelectedCities(newValue)}
              getOptionLabel={(option) => option.label}
              isOptionEqualToValue={(option, value) =>
                option.city === value.city && option.state === value.state
              }
              renderInput={(params) => (
                <TextField
                  {...params}
                  placeholder="Select cities..."
                  size="small"
                />
              )}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip
                    label={option.label}
                    size="small"
                    {...getTagProps({ index })}
                    key={option.label}
                  />
                ))
              }
              groupBy={(option) => option.state}
              sx={{ minWidth: 300 }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
              Select one or more US cities to search for businesses
            </Typography>
          </Box>

          <Box>
            <Typography sx={{ fontWeight: 700, mb: 0.5 }}>Niches</Typography>
            <ToggleButtonGroup
              value={niches}
              onChange={(_, value) => setNiches(value ?? [])}
              size="small"
            >
              {ALL_NICHES.map((n) => (
                <ToggleButton key={n} value={n}>
                  {n.replace("_", " ")}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>

          <Box>
            <Typography sx={{ fontWeight: 700, mb: 1 }}>
              Max Results Per Scraper: {maxResults}
            </Typography>
            <Slider
              value={maxResults}
              onChange={(_, value) => setMaxResults(value as number)}
              min={5}
              max={50}
              step={5}
              marks={[
                { value: 5, label: "5" },
                { value: 20, label: "20" },
                { value: 35, label: "35" },
                { value: 50, label: "50" },
              ]}
              valueLabelDisplay="auto"
              sx={{ maxWidth: 400 }}
            />
            <Typography variant="caption" color="text.secondary">
              Each scraper will return up to this many results per location
            </Typography>
          </Box>

          <Box>
            <Typography sx={{ fontWeight: 700, mb: 0.5 }}>Options</Typography>
            <FormGroup row>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={skipAudit}
                    onChange={(e) => setSkipAudit(e.target.checked)}
                  />
                }
                label="Skip website audit (faster)"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={fetchDetails}
                    onChange={(e) => setFetchDetails(e.target.checked)}
                  />
                }
                label="Fetch details (BBB/Yelp)"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={fetchEmails}
                    onChange={(e) => setFetchEmails(e.target.checked)}
                  />
                }
                label="Extract emails (slower)"
              />
            </FormGroup>
          </Box>

          <Box>
            <Typography sx={{ fontWeight: 700, mb: 0.5 }}>Skip Scrapers</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {ALL_SCRAPERS.map((s) => {
                const selected = skipScrapers.includes(s);
                return (
                  <Chip
                    key={s}
                    label={s.replace("_", " ")}
                    variant={selected ? "filled" : "outlined"}
                    color={selected ? "secondary" : "default"}
                    onClick={() =>
                      setSkipScrapers((prev) =>
                        selected ? prev.filter((x) => x !== s) : [...prev, s]
                      )
                    }
                  />
                );
              })}
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
              Click to disable specific scrapers
            </Typography>
          </Box>

          <Stack direction="row" justifyContent="flex-end" spacing={2}>
            <Typography variant="body2" color="text.secondary" sx={{ alignSelf: "center" }}>
              {locations.length} location(s), {niches.length} niche(s), {5 - skipScrapers.length} scraper(s)
            </Typography>
            <Button
              variant="contained"
              size="large"
              disabled={!canSubmit}
              onClick={() =>
                onSubmit({
                  locations,
                  niches,
                  skip_audit: skipAudit,
                  fetch_details: fetchDetails,
                  fetch_emails: fetchEmails,
                  skip_scrapers: skipScrapers,
                  output_format: "xlsx",
                  max_results: maxResults,
                })
              }
            >
              {loading ? "Starting…" : "Start Scraping"}
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
