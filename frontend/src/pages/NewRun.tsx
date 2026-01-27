import { useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  FormControlLabel,
  Grid,
  Slider,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  alpha,
} from "@mui/material";
import {
  RocketLaunch as RocketIcon,
  LocationOn as LocationIcon,
  Tune as TuneIcon,
  Speed as SpeedIcon,
  Source as SourceIcon,
} from "@mui/icons-material";
import { motion } from "framer-motion";
import { useRuns } from "../context/RunContext";
import type { RunCreateRequest } from "../api/types";
import { glassEffect, gradients } from "../theme";

const ALL_NICHES: Array<RunCreateRequest["niches"][number]> = [
  "plumbing",
  "dental",
  "pest_control",
];

const ALL_SCRAPERS = ["google_maps", "yelp", "yellowpages", "bbb", "manta"];

const nicheLabels: Record<string, string> = {
  plumbing: "Plumbing",
  dental: "Dental",
  pest_control: "Pest Control",
};

const nicheEmoji: Record<string, string> = {
  plumbing: "🔧",
  dental: "🦷",
  pest_control: "🐜",
};

// US Cities
const US_CITIES = [
  { city: "Austin", state: "TX", label: "Austin, TX" },
  { city: "Houston", state: "TX", label: "Houston, TX" },
  { city: "Dallas", state: "TX", label: "Dallas, TX" },
  { city: "San Antonio", state: "TX", label: "San Antonio, TX" },
  { city: "Fort Worth", state: "TX", label: "Fort Worth, TX" },
  { city: "Los Angeles", state: "CA", label: "Los Angeles, CA" },
  { city: "San Francisco", state: "CA", label: "San Francisco, CA" },
  { city: "San Diego", state: "CA", label: "San Diego, CA" },
  { city: "San Jose", state: "CA", label: "San Jose, CA" },
  { city: "Sacramento", state: "CA", label: "Sacramento, CA" },
  { city: "Miami", state: "FL", label: "Miami, FL" },
  { city: "Tampa", state: "FL", label: "Tampa, FL" },
  { city: "Orlando", state: "FL", label: "Orlando, FL" },
  { city: "Jacksonville", state: "FL", label: "Jacksonville, FL" },
  { city: "New York", state: "NY", label: "New York, NY" },
  { city: "Buffalo", state: "NY", label: "Buffalo, NY" },
  { city: "Chicago", state: "IL", label: "Chicago, IL" },
  { city: "Phoenix", state: "AZ", label: "Phoenix, AZ" },
  { city: "Tucson", state: "AZ", label: "Tucson, AZ" },
  { city: "Scottsdale", state: "AZ", label: "Scottsdale, AZ" },
  { city: "Denver", state: "CO", label: "Denver, CO" },
  { city: "Colorado Springs", state: "CO", label: "Colorado Springs, CO" },
  { city: "Atlanta", state: "GA", label: "Atlanta, GA" },
  { city: "Charlotte", state: "NC", label: "Charlotte, NC" },
  { city: "Raleigh", state: "NC", label: "Raleigh, NC" },
  { city: "Seattle", state: "WA", label: "Seattle, WA" },
  { city: "Boston", state: "MA", label: "Boston, MA" },
  { city: "Las Vegas", state: "NV", label: "Las Vegas, NV" },
  { city: "Columbus", state: "OH", label: "Columbus, OH" },
  { city: "Cleveland", state: "OH", label: "Cleveland, OH" },
  { city: "Detroit", state: "MI", label: "Detroit, MI" },
  { city: "Philadelphia", state: "PA", label: "Philadelphia, PA" },
  { city: "Pittsburgh", state: "PA", label: "Pittsburgh, PA" },
  { city: "Nashville", state: "TN", label: "Nashville, TN" },
  { city: "Memphis", state: "TN", label: "Memphis, TN" },
  { city: "Portland", state: "OR", label: "Portland, OR" },
  { city: "Minneapolis", state: "MN", label: "Minneapolis, MN" },
  { city: "Kansas City", state: "MO", label: "Kansas City, MO" },
  { city: "St. Louis", state: "MO", label: "St. Louis, MO" },
  { city: "Indianapolis", state: "IN", label: "Indianapolis, IN" },
  { city: "Salt Lake City", state: "UT", label: "Salt Lake City, UT" },
  { city: "New Orleans", state: "LA", label: "New Orleans, LA" },
  { city: "Oklahoma City", state: "OK", label: "Oklahoma City, OK" },
  { city: "Louisville", state: "KY", label: "Louisville, KY" },
  { city: "Baltimore", state: "MD", label: "Baltimore, MD" },
  { city: "Milwaukee", state: "WI", label: "Milwaukee, WI" },
  { city: "Albuquerque", state: "NM", label: "Albuquerque, NM" },
].sort((a, b) => a.label.localeCompare(b.label));

type CityOption = (typeof US_CITIES)[number];

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

function SectionCard({ 
  icon: Icon, 
  title, 
  subtitle, 
  children 
}: { 
  icon: any; 
  title: string; 
  subtitle?: string; 
  children: React.ReactNode;
}) {
  return (
    <Card
      component={motion.div}
      variants={itemVariants}
      sx={{ height: "100%" }}
    >
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2.5 }}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: 2,
              background: alpha("#8b5cf6", 0.15),
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon sx={{ fontSize: 18, color: "primary.main" }} />
          </Box>
          <Box>
            <Typography variant="body1" sx={{ fontWeight: 700, color: "grey.100" }}>
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="caption" sx={{ color: "grey.500" }}>
                {subtitle}
              </Typography>
            )}
          </Box>
        </Stack>
        {children}
      </CardContent>
    </Card>
  );
}

export default function NewRun() {
  const { startRun } = useRuns();
  const [selectedCities, setSelectedCities] = useState<CityOption[]>([
    US_CITIES.find((c) => c.label === "Austin, TX")!,
  ]);
  const [niches, setNiches] = useState<RunCreateRequest["niches"]>([
    "plumbing",
    "dental",
    "pest_control",
  ]);
  const [skipAudit, setSkipAudit] = useState(true);
  const [fetchDetails, setFetchDetails] = useState(false);
  const [fetchEmails, setFetchEmails] = useState(false);
  const [skipScrapers, setSkipScrapers] = useState<string[]>([]);
  const [maxResults, setMaxResults] = useState<number>(20);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const locations = selectedCities.map((c) => c.label);
  const canSubmit = locations.length > 0 && niches.length > 0 && !isSubmitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    
    setIsSubmitting(true);
    try {
      await startRun({
        locations,
        niches,
        skip_audit: skipAudit,
        fetch_details: fetchDetails,
        fetch_emails: fetchEmails,
        skip_scrapers: skipScrapers,
        output_format: "xlsx",
        max_results: maxResults,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalEstimate = locations.length * niches.length * (5 - skipScrapers.length) * maxResults;

  return (
    <Stack
      component={motion.div}
      variants={containerVariants}
      initial="hidden"
      animate="show"
      spacing={4}
    >
      {/* Header */}
      <Box component={motion.div} variants={itemVariants}>
        <Stack direction="row" alignItems="center" spacing={2}>
          <Box
            sx={{
              width: 56,
              height: 56,
              borderRadius: 3,
              background: gradients.primary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: `0 12px 32px ${alpha("#8b5cf6", 0.4)}`,
            }}
          >
            <RocketIcon sx={{ color: "#fff", fontSize: 28 }} />
          </Box>
          <Box>
            <Typography variant="h3" sx={{ fontWeight: 700, color: "grey.100" }}>
              New Prospecting Run
            </Typography>
            <Typography sx={{ color: "grey.500", mt: 0.5 }}>
              Configure your search parameters and launch
            </Typography>
          </Box>
        </Stack>
      </Box>

      {/* Main Form */}
      <Grid container spacing={3}>
        {/* Left Column */}
        <Grid item xs={12} lg={8}>
          <Stack spacing={3}>
            {/* Locations */}
            <SectionCard
              icon={LocationIcon}
              title="Target Locations"
              subtitle="Select cities to search for businesses"
            >
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
                    placeholder="Search cities..."
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
                      sx={{
                        bgcolor: alpha("#8b5cf6", 0.2),
                        color: "primary.light",
                        "& .MuiChip-deleteIcon": {
                          color: alpha("#fff", 0.5),
                          "&:hover": { color: "#fff" },
                        },
                      }}
                    />
                  ))
                }
                groupBy={(option) => option.state}
              />
            </SectionCard>

            {/* Niches */}
            <SectionCard
              icon={TuneIcon}
              title="Business Niches"
              subtitle="Choose which industries to target"
            >
              <ToggleButtonGroup
                value={niches}
                onChange={(_, value) => setNiches(value ?? [])}
                sx={{ flexWrap: "wrap", gap: 1.5 }}
              >
                {ALL_NICHES.map((n) => (
                  <ToggleButton
                    key={n}
                    value={n}
                    sx={{
                      px: 3,
                      py: 1.5,
                      borderRadius: "14px !important",
                      border: "1px solid",
                      borderColor: alpha("#fff", 0.1),
                    }}
                  >
                    <span style={{ marginRight: 8 }}>{nicheEmoji[n]}</span>
                    {nicheLabels[n]}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
            </SectionCard>

            {/* Data Sources */}
            <SectionCard
              icon={SourceIcon}
              title="Data Sources"
              subtitle="Click to enable/disable scrapers"
            >
              <Stack direction="row" flexWrap="wrap" gap={1}>
                {ALL_SCRAPERS.map((s) => {
                  const isDisabled = skipScrapers.includes(s);
                  return (
                    <Chip
                      key={s}
                      label={s.replace("_", " ")}
                      onClick={() =>
                        setSkipScrapers((prev) =>
                          isDisabled ? prev.filter((x) => x !== s) : [...prev, s]
                        )
                      }
                      sx={{
                        px: 1,
                        py: 2,
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        textTransform: "capitalize",
                        bgcolor: isDisabled 
                          ? alpha("#fff", 0.03) 
                          : alpha("#06b6d4", 0.15),
                        color: isDisabled ? "grey.600" : "secondary.light",
                        border: "1px solid",
                        borderColor: isDisabled 
                          ? alpha("#fff", 0.05) 
                          : alpha("#06b6d4", 0.3),
                        textDecoration: isDisabled ? "line-through" : "none",
                        transition: "all 0.2s ease",
                        "&:hover": {
                          bgcolor: isDisabled 
                            ? alpha("#fff", 0.05) 
                            : alpha("#06b6d4", 0.25),
                        },
                      }}
                    />
                  );
                })}
              </Stack>
            </SectionCard>
          </Stack>
        </Grid>

        {/* Right Column */}
        <Grid item xs={12} lg={4}>
          <Stack spacing={3}>
            {/* Results Limit */}
            <SectionCard
              icon={SpeedIcon}
              title="Results Per Scraper"
              subtitle={`${maxResults} businesses per source`}
            >
              <Slider
                value={maxResults}
                onChange={(_, value) => setMaxResults(value as number)}
                min={5}
                max={50}
                step={5}
                marks={[
                  { value: 5, label: "5" },
                  { value: 25, label: "25" },
                  { value: 50, label: "50" },
                ]}
                valueLabelDisplay="auto"
              />
            </SectionCard>

            {/* Options */}
            <Card component={motion.div} variants={itemVariants}>
              <CardContent>
                <Typography variant="body1" sx={{ fontWeight: 700, color: "grey.100", mb: 2 }}>
                  Advanced Options
                </Typography>
                <Stack spacing={0.5}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={!skipAudit}
                        onChange={(e) => setSkipAudit(!e.target.checked)}
                        size="small"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ color: "grey.300" }}>
                        Website audit (slower)
                      </Typography>
                    }
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={fetchDetails}
                        onChange={(e) => setFetchDetails(e.target.checked)}
                        size="small"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ color: "grey.300" }}>
                        Fetch extra details
                      </Typography>
                    }
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={fetchEmails}
                        onChange={(e) => setFetchEmails(e.target.checked)}
                        size="small"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ color: "grey.300" }}>
                        Extract emails
                      </Typography>
                    }
                  />
                </Stack>
              </CardContent>
            </Card>

            {/* Summary & Launch */}
            <Card
              component={motion.div}
              variants={itemVariants}
              sx={{
                background: gradients.card,
                border: `1px solid ${alpha("#8b5cf6", 0.2)}`,
              }}
            >
              <CardContent>
                <Typography variant="body1" sx={{ fontWeight: 700, color: "grey.100", mb: 2 }}>
                  Run Summary
                </Typography>
                
                <Stack spacing={1.5} sx={{ mb: 3 }}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2" sx={{ color: "grey.500" }}>
                      Locations
                    </Typography>
                    <Typography variant="body2" sx={{ color: "grey.200", fontWeight: 600 }}>
                      {locations.length}
                    </Typography>
                  </Stack>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2" sx={{ color: "grey.500" }}>
                      Niches
                    </Typography>
                    <Typography variant="body2" sx={{ color: "grey.200", fontWeight: 600 }}>
                      {niches.length}
                    </Typography>
                  </Stack>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography variant="body2" sx={{ color: "grey.500" }}>
                      Active Scrapers
                    </Typography>
                    <Typography variant="body2" sx={{ color: "grey.200", fontWeight: 600 }}>
                      {5 - skipScrapers.length}
                    </Typography>
                  </Stack>
                  <Box sx={{ borderTop: `1px solid ${alpha("#fff", 0.1)}`, pt: 1.5, mt: 1 }}>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" sx={{ color: "grey.400", fontWeight: 600 }}>
                        Max Results
                      </Typography>
                      <Typography variant="body2" sx={{ color: "primary.light", fontWeight: 700 }}>
                        ~{Math.min(totalEstimate, 500).toLocaleString()}
                      </Typography>
                    </Stack>
                  </Box>
                </Stack>

                <Button
                  fullWidth
                  size="large"
                  disabled={!canSubmit}
                  onClick={handleSubmit}
                  sx={{
                    py: 1.5,
                    fontSize: "1rem",
                    fontWeight: 700,
                    background: gradients.primary,
                    "&:hover": {
                      background: gradients.primary,
                    },
                    "&:disabled": {
                      background: alpha("#fff", 0.1),
                      color: "grey.600",
                    },
                  }}
                >
                  {isSubmitting ? "Starting..." : "Launch Scraping"}
                </Button>
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>
    </Stack>
  );
}
