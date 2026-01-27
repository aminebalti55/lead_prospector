import { Chip, Tooltip, alpha } from "@mui/material";
import { chartColors } from "../theme";

export type QualityTier = "excellent" | "good" | "fair" | "poor";

type Props = {
  score: number;
  tier: QualityTier;
  size?: "small" | "medium";
  showScore?: boolean;
};

const tierConfig: Record<QualityTier, { label: string; color: string }> = {
  excellent: {
    label: "Excellent",
    color: chartColors.success,
  },
  good: {
    label: "Good",
    color: chartColors.cyan,
  },
  fair: {
    label: "Fair",
    color: chartColors.warning,
  },
  poor: {
    label: "Poor",
    color: chartColors.cold,
  },
};

export function calculateQualityScore(lead: Record<string, unknown>): number {
  let score = 0;

  // Has email (+30)
  const email = lead.Email as string | undefined;
  if (email && email.includes("@")) score += 30;

  // Has phone (+15)
  if (lead.Phone) score += 15;

  // Has website (+15)
  if (lead.Website) score += 15;

  // Priority bonus
  const priority = (lead.Priority as string)?.toLowerCase();
  if (priority === "hot") score += 25;
  else if (priority === "warm") score += 15;
  else score += 5;

  // Base score contribution (+15 max)
  const baseScore = lead.Score as number | undefined;
  if (baseScore) score += Math.min(15, baseScore / 6.67);

  return Math.min(100, Math.round(score));
}

export function getQualityTier(score: number): QualityTier {
  if (score >= 80) return "excellent";
  if (score >= 60) return "good";
  if (score >= 40) return "fair";
  return "poor";
}

export default function QualityBadge({ score, tier, size = "small", showScore = true }: Props) {
  const config = tierConfig[tier];

  return (
    <Tooltip title={`Quality Score: ${score}/100`} arrow>
      <Chip
        size={size}
        label={showScore ? `${config.label} (${score})` : config.label}
        sx={{
          fontWeight: 600,
          fontSize: size === "small" ? "0.7rem" : "0.8rem",
          color: config.color,
          bgcolor: alpha(config.color, 0.15),
          border: `1px solid ${alpha(config.color, 0.3)}`,
          "& .MuiChip-label": {
            px: size === "small" ? 1 : 1.5,
          },
        }}
      />
    </Tooltip>
  );
}
