import { useState, useEffect } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  FormControl,
  IconButton,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  alpha,
  Alert,
  Chip,
  Divider,
  Collapse,
  Paper,
} from "@mui/material";
import {
  Close as CloseIcon,
  Send as SendIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Email as EmailIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Schedule as DelayIcon,
  Preview as PreviewIcon,
  Business as BusinessIcon,
} from "@mui/icons-material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { getEmailTemplates, sendBatchEmails, previewEmail } from "../api/client";
import type { Lead, BatchEmailRecipient, BatchEmailResult } from "../api/types";
import { chartColors, glassEffect, gradients } from "../theme";

type Props = {
  open: boolean;
  onClose: () => void;
  leads: Lead[];
  filename?: string;  // Excel filename to update after sending
};

export default function BatchEmailDialog({ open, onClose, leads, filename }: Props) {
  const [selectedTemplate, setSelectedTemplate] = useState<string>("initial");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [results, setResults] = useState<BatchEmailResult[] | null>(null);
  const [delaySeconds, setDelaySeconds] = useState(3);
  const [showPreview, setShowPreview] = useState(false);
  const [previewLead, setPreviewLead] = useState<Lead | null>(null);

  // Only leads with emails
  const leadsWithEmail = leads.filter(
    (l) => l.Email && (l.Email as string).includes("@")
  );

  // Set preview lead when leadsWithEmail changes
  useEffect(() => {
    if (leadsWithEmail.length > 0 && !previewLead) {
      setPreviewLead(leadsWithEmail[0]);
    }
  }, [leadsWithEmail, previewLead]);

  const templatesQuery = useQuery({
    queryKey: ["email-templates"],
    queryFn: getEmailTemplates,
    enabled: open,
  });

  const previewMutation = useMutation({
    mutationFn: (templateId: string) =>
      previewEmail({
        template_id: templateId,
        variables: {
          business_name: "{business_name}",
          contact_name: "{contact_name}",
          city: "{city}",
          niche: "{niche}",
          website: "{website}",
          website_review: "{website_review}",
        },
      }),
    onSuccess: (data) => {
      setSubject(data.subject);
      setBody(data.body);
    },
  });

  // Generate preview with actual lead data
  const getPreviewContent = () => {
    if (!previewLead) return { subject: "", body: "" };
    
    const painTags = (previewLead.Pain_Tags as string) || "";
    const formattedReview = painTags
      .split(",")
      .map((tag: string) => {
        const t = tag.trim();
        if (t === "no_website") return "• No website or website not found";
        if (t === "few_reviews") return "• Limited online reviews";
        if (t === "slow_site") return "• Website loads slowly";
        if (t === "no_ssl") return "• Missing security certificate (HTTPS)";
        if (t === "not_mobile_friendly") return "• Not optimized for mobile devices";
        if (t === "no_booking") return "• No online booking option";
        if (t === "no_contact_form") return "• No contact form found";
        return t ? `• ${t}` : "";
      })
      .filter(Boolean)
      .join("\n") || "• Opportunities to improve online visibility";

    const replacements: Record<string, string> = {
      "{business_name}": (previewLead.Business_Name as string) || "Your Business",
      "{city}": (previewLead.City as string) || "your city",
      "{niche}": (previewLead.Niche as string) || "business",
      "{website}": (previewLead.Website as string) || "your website",
      "{website_review}": formattedReview,
    };

    let previewSubject = subject;
    let previewBody = body;

    Object.entries(replacements).forEach(([key, value]) => {
      previewSubject = previewSubject.replace(new RegExp(key.replace(/[{}]/g, "\\$&"), "g"), value);
      previewBody = previewBody.replace(new RegExp(key.replace(/[{}]/g, "\\$&"), "g"), value);
    });

    return { subject: previewSubject, body: previewBody };
  };

  const sendMutation = useMutation({
    mutationFn: () => {
      const recipients: BatchEmailRecipient[] = leadsWithEmail.map((lead) => {
        // Format pain tags into readable review
        const painTags = (lead.Pain_Tags as string) || "";
        const formattedReview = painTags
          .split(",")
          .map((tag: string) => {
            const t = tag.trim();
            if (t === "no_website") return "• No website or website not found";
            if (t === "few_reviews") return "• Limited online reviews";
            if (t === "slow_site") return "• Website loads slowly";
            if (t === "no_ssl") return "• Missing security certificate (HTTPS)";
            if (t === "not_mobile_friendly") return "• Not optimized for mobile devices";
            if (t === "no_booking") return "• No online booking option";
            if (t === "no_contact_form") return "• No contact form found";
            return t ? `• ${t}` : "";
          })
          .filter(Boolean)
          .join("\n") || "• Opportunities to improve online visibility";

        return {
          to_email: lead.Email as string,
          to_name: (lead.Business_Name as string) || "Business",
          lead_id: lead.Lead_ID as string,
          variables: {
            business_name: (lead.Business_Name as string) || "there",
            contact_name: (lead.Business_Name as string) || "there",
            city: (lead.City as string) || "",
            niche: (lead.Niche as string)?.toLowerCase() || "business",
            website: (lead.Website as string) || "your website",
            website_review: formattedReview,
          },
        };
      });

      return sendBatchEmails({
        template_id: selectedTemplate,
        recipients,
        custom_subject: subject || undefined,
        custom_body: body || undefined,
        delay_seconds: delaySeconds,
        filename: filename,  // Pass filename to update Excel
      });
    },
    onSuccess: (data) => {
      setResults(data.results);
    },
  });

  const handleTemplateChange = (templateId: string) => {
    setSelectedTemplate(templateId);
    if (templateId) {
      previewMutation.mutate(templateId);
    }
  };

  const handleClose = () => {
    setResults(null);
    setSelectedTemplate("initial");
    setSubject("");
    setBody("");
    setShowPreview(false);
    setPreviewLead(null);
    onClose();
  };

  // Load initial template
  useEffect(() => {
    if (open && !body) {
      previewMutation.mutate("initial");
    }
  }, [open]);

  const successCount = results?.filter((r) => r.success).length || 0;
  const failedCount = results?.filter((r) => !r.success).length || 0;
  const preview = getPreviewContent();

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        component: motion.div,
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.2 },
        sx: {
          borderRadius: 3,
          bgcolor: "#0a0a0f",
          border: `1px solid ${alpha("#fff", 0.08)}`,
          boxShadow: `0 24px 48px ${alpha("#000", 0.6)}`,
          maxHeight: "90vh",
          overflow: "hidden",
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 3,
          py: 2.5,
          borderBottom: `1px solid ${alpha("#fff", 0.06)}`,
          background: `linear-gradient(180deg, ${alpha("#fff", 0.02)} 0%, transparent 100%)`,
        }}
      >
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Stack direction="row" alignItems="center" spacing={2}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: 2,
                background: gradients.primary,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <SendIcon sx={{ color: "white", fontSize: 24 }} />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "grey.100" }}>
                Send Outreach Campaign
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip
                  size="small"
                  icon={<EmailIcon sx={{ fontSize: 14 }} />}
                  label={`${leadsWithEmail.length} recipients`}
                  sx={{
                    bgcolor: alpha(chartColors.success, 0.15),
                    color: chartColors.success,
                    fontWeight: 600,
                    fontSize: 12,
                    "& .MuiChip-icon": { color: chartColors.success },
                  }}
                />
                {leads.length - leadsWithEmail.length > 0 && (
                  <Chip
                    size="small"
                    label={`${leads.length - leadsWithEmail.length} skipped`}
                    sx={{
                      bgcolor: alpha(chartColors.warning, 0.1),
                      color: alpha(chartColors.warning, 0.8),
                      fontWeight: 500,
                      fontSize: 12,
                    }}
                  />
                )}
              </Stack>
            </Box>
          </Stack>
          <IconButton onClick={handleClose} sx={{ color: "grey.500" }}>
            <CloseIcon />
          </IconButton>
        </Stack>
      </Box>

      <DialogContent sx={{ p: 0 }}>
        {/* Results View */}
        {results ? (
          <Box sx={{ p: 3 }}>
            <Alert
              severity={failedCount === 0 ? "success" : "warning"}
              sx={{ mb: 3, borderRadius: 2 }}
            >
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                Campaign Complete
              </Typography>
              <Typography variant="body2">
                Successfully sent {successCount} of {results.length} emails
                {failedCount > 0 && ` (${failedCount} failed)`}
              </Typography>
            </Alert>

            <Box
              sx={{
                maxHeight: 400,
                overflow: "auto",
                borderRadius: 2,
                border: `1px solid ${alpha("#fff", 0.06)}`,
              }}
            >
              {results.map((result, i) => (
                <Box
                  key={i}
                  sx={{
                    px: 2,
                    py: 1.5,
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    borderBottom: i < results.length - 1 ? `1px solid ${alpha("#fff", 0.04)}` : "none",
                    bgcolor: result.success ? "transparent" : alpha(chartColors.hot, 0.03),
                  }}
                >
                  {result.success ? (
                    <SuccessIcon sx={{ color: chartColors.success, fontSize: 20 }} />
                  ) : (
                    <ErrorIcon sx={{ color: chartColors.hot, fontSize: 20 }} />
                  )}
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: 600, color: "grey.200", truncate: true }}
                    >
                      {result.to_name}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{ color: result.success ? "grey.500" : chartColors.hot }}
                    >
                      {result.success ? result.to_email : result.message}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        ) : (
          <Stack sx={{ height: "100%" }}>
            {/* Settings Section */}
            <Box sx={{ p: 3 }}>
              <Stack spacing={2.5}>
                {/* Template & Delay Row */}
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <FormControl sx={{ flex: 2 }}>
                    <InputLabel size="small">Template</InputLabel>
                    <Select
                      size="small"
                      value={selectedTemplate}
                      label="Template"
                      onChange={(e) => handleTemplateChange(e.target.value)}
                      sx={{ bgcolor: alpha("#fff", 0.02) }}
                    >
                      {templatesQuery.data?.templates.map((template) => (
                        <MenuItem key={template.id} value={template.id}>
                          {template.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl sx={{ flex: 1 }}>
                    <InputLabel size="small">Send Delay</InputLabel>
                    <Select
                      size="small"
                      value={delaySeconds}
                      label="Send Delay"
                      onChange={(e) => setDelaySeconds(Number(e.target.value))}
                      sx={{ bgcolor: alpha("#fff", 0.02) }}
                    >
                      <MenuItem value={2}>2s (fast)</MenuItem>
                      <MenuItem value={3}>3s (normal)</MenuItem>
                      <MenuItem value={5}>5s (safe)</MenuItem>
                      <MenuItem value={10}>10s (very safe)</MenuItem>
                    </Select>
                  </FormControl>
                </Stack>

                {/* Subject */}
                <TextField
                  size="small"
                  label="Subject Line"
                  fullWidth
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  sx={{
                    "& .MuiOutlinedInput-root": { bgcolor: alpha("#fff", 0.02) },
                  }}
                />

                {/* Body */}
                <TextField
                  size="small"
                  label="Email Body"
                  fullWidth
                  multiline
                  rows={8}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      bgcolor: alpha("#fff", 0.02),
                      fontFamily: "monospace",
                      fontSize: 13,
                    },
                  }}
                />
              </Stack>
            </Box>

            {/* Preview Section */}
            <Box sx={{ borderTop: `1px solid ${alpha("#fff", 0.06)}` }}>
              <Button
                fullWidth
                onClick={() => setShowPreview(!showPreview)}
                sx={{
                  py: 1.5,
                  justifyContent: "space-between",
                  px: 3,
                  color: "grey.400",
                  "&:hover": { bgcolor: alpha("#fff", 0.02) },
                }}
                endIcon={showPreview ? <CollapseIcon /> : <ExpandIcon />}
                startIcon={<PreviewIcon />}
              >
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Preview with Real Data
                </Typography>
              </Button>

              <Collapse in={showPreview}>
                <Box sx={{ px: 3, pb: 3 }}>
                  {/* Lead Selector */}
                  {leadsWithEmail.length > 0 && (
                    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                      <InputLabel size="small">Preview as</InputLabel>
                      <Select
                        size="small"
                        value={previewLead?.Lead_ID || ""}
                        label="Preview as"
                        onChange={(e) => {
                          const lead = leadsWithEmail.find((l) => l.Lead_ID === e.target.value);
                          if (lead) setPreviewLead(lead);
                        }}
                        sx={{ bgcolor: alpha("#fff", 0.02) }}
                      >
                        {leadsWithEmail.slice(0, 10).map((lead) => (
                          <MenuItem key={lead.Lead_ID as string} value={lead.Lead_ID as string}>
                            {lead.Business_Name} ({lead.City})
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  )}

                  {/* Preview Card */}
                  <Paper
                    sx={{
                      p: 2.5,
                      borderRadius: 2,
                      bgcolor: "#12121a",
                      border: `1px solid ${alpha("#fff", 0.08)}`,
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: chartColors.cyan,
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: 1,
                      }}
                    >
                      Email Preview
                    </Typography>

                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" sx={{ color: "grey.500" }}>
                        To:
                      </Typography>
                      <Typography variant="body2" sx={{ color: "grey.200", mb: 1 }}>
                        {previewLead?.Email || "recipient@email.com"}
                      </Typography>

                      <Typography variant="caption" sx={{ color: "grey.500" }}>
                        Subject:
                      </Typography>
                      <Typography variant="body2" sx={{ color: "grey.100", fontWeight: 600, mb: 2 }}>
                        {preview.subject}
                      </Typography>

                      <Divider sx={{ borderColor: alpha("#fff", 0.06), my: 2 }} />

                      <Typography
                        variant="body2"
                        sx={{
                          color: "grey.300",
                          whiteSpace: "pre-wrap",
                          lineHeight: 1.7,
                          fontSize: 13,
                        }}
                      >
                        {preview.body}
                      </Typography>
                    </Box>
                  </Paper>
                </Box>
              </Collapse>
            </Box>

            {/* Progress */}
            {sendMutation.isPending && (
              <Box sx={{ px: 3, pb: 2 }}>
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                  <DelayIcon sx={{ fontSize: 16, color: chartColors.cyan }} />
                  <Typography variant="caption" sx={{ color: "grey.400" }}>
                    Sending emails with {delaySeconds}s delay between each...
                  </Typography>
                </Stack>
                <LinearProgress
                  sx={{
                    borderRadius: 1,
                    bgcolor: alpha(chartColors.cyan, 0.1),
                    "& .MuiLinearProgress-bar": { bgcolor: chartColors.cyan },
                  }}
                />
              </Box>
            )}

            {/* Warnings */}
            {leadsWithEmail.length === 0 && (
              <Alert severity="warning" sx={{ mx: 3, mb: 2, borderRadius: 2 }}>
                No leads with valid email addresses in this list.
              </Alert>
            )}

            {leadsWithEmail.length > 30 && (
              <Alert severity="info" sx={{ mx: 3, mb: 2, borderRadius: 2 }}>
                Sending to {leadsWithEmail.length} recipients. This will take about{" "}
                {Math.ceil((leadsWithEmail.length * delaySeconds) / 60)} minutes.
              </Alert>
            )}
          </Stack>
        )}
      </DialogContent>

      {/* Footer */}
      <Box
        sx={{
          px: 3,
          py: 2,
          borderTop: `1px solid ${alpha("#fff", 0.06)}`,
          bgcolor: alpha("#fff", 0.01),
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="caption" sx={{ color: "grey.600" }}>
            Emails sent from: amine.balti@rhis-solutions.com
          </Typography>
          <Stack direction="row" spacing={1.5}>
            <Button onClick={handleClose} variant="outlined" size="small">
              {results ? "Close" : "Cancel"}
            </Button>
            {!results && (
              <Button
                variant="contained"
                size="small"
                startIcon={<SendIcon />}
                disabled={leadsWithEmail.length === 0 || sendMutation.isPending}
                onClick={() => sendMutation.mutate()}
                sx={{
                  background: gradients.primary,
                  "&:hover": { background: gradients.primary, opacity: 0.9 },
                }}
              >
                {sendMutation.isPending
                  ? "Sending..."
                  : `Send to ${leadsWithEmail.length} Leads`}
              </Button>
            )}
          </Stack>
        </Stack>
      </Box>
    </Dialog>
  );
}
