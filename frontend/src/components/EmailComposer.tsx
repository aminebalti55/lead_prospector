import { useState } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  alpha,
  CircularProgress,
  Alert,
} from "@mui/material";
import { Close as CloseIcon, Send as SendIcon } from "@mui/icons-material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { getEmailTemplates, sendEmail, previewEmail } from "../api/client";
import type { Lead, EmailTemplate } from "../api/types";
import { chartColors, glassEffect, gradients } from "../theme";

type Props = {
  open: boolean;
  onClose: () => void;
  lead: Lead | null;
  filename?: string;  // Excel filename to update after sending
};

export default function EmailComposer({ open, onClose, lead, filename }: Props) {
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sendSuccess, setSendSuccess] = useState(false);

  const templatesQuery = useQuery({
    queryKey: ["email-templates"],
    queryFn: getEmailTemplates,
    enabled: open,
  });

  // Format pain tags into readable review
  const getFormattedReview = () => {
    const painTags = (lead?.Pain_Tags as string) || "";
    return painTags
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
  };

  const previewMutation = useMutation({
    mutationFn: (templateId: string) =>
      previewEmail({
        template_id: templateId,
        variables: {
          business_name: (lead?.Business_Name as string) || "",
          contact_name: (lead?.Business_Name as string) || "there",
          city: (lead?.City as string) || "",
          niche: (lead?.Niche as string)?.toLowerCase() || "business",
          website: (lead?.Website as string) || "your website",
          website_review: getFormattedReview(),
        },
      }),
    onSuccess: (data) => {
      setSubject(data.subject);
      setBody(data.body);
    },
  });

  const sendMutation = useMutation({
    mutationFn: () =>
      sendEmail({
        to_email: (lead?.Email as string) || "",
        to_name: (lead?.Business_Name as string) || "",
        subject,
        body,
        lead_id: (lead?.Lead_ID as string) || undefined,
        filename: filename,  // Pass filename to update Excel
      }),
    onSuccess: () => {
      setSendSuccess(true);
      setTimeout(() => {
        onClose();
        setSendSuccess(false);
        setSelectedTemplate("");
        setSubject("");
        setBody("");
      }, 2000);
    },
  });

  const handleTemplateChange = (templateId: string) => {
    setSelectedTemplate(templateId);
    if (templateId) {
      previewMutation.mutate(templateId);
    } else {
      setSubject("");
      setBody("");
    }
  };

  const canSend = lead?.Email && subject && body && !sendMutation.isPending;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        component: motion.div,
        initial: { opacity: 0, scale: 0.95 },
        animate: { opacity: 1, scale: 1 },
        sx: { 
          borderRadius: 4,
          ...glassEffect,
          boxShadow: `0 32px 64px ${alpha("#000", 0.5)}`,
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid",
          borderColor: alpha("#fff", 0.06),
          background: `linear-gradient(135deg, ${alpha(chartColors.purple, 0.1)} 0%, ${alpha(chartColors.cyan, 0.1)} 100%)`,
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box
            sx={{
              width: 44,
              height: 44,
              borderRadius: 2.5,
              background: gradients.primary,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: `0 8px 20px ${alpha(chartColors.purple, 0.4)}`,
            }}
          >
            <SendIcon sx={{ color: "white", fontSize: 20 }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2, color: "grey.100" }}>
              Send Email
            </Typography>
            <Typography variant="body2" sx={{ color: "grey.500" }}>
              to {lead?.Business_Name || "Lead"}
            </Typography>
          </Box>
        </Stack>
        <IconButton 
          onClick={onClose} 
          size="small"
          sx={{ 
            color: "grey.500",
            "&:hover": { bgcolor: alpha("#fff", 0.05) },
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pt: 3 }}>
        <Stack spacing={3}>
          {/* Recipient Info */}
          <Box
            sx={{
              p: 2.5,
              borderRadius: 3,
              bgcolor: alpha("#fff", 0.03),
              border: `1px solid ${alpha("#fff", 0.06)}`,
            }}
          >
            <Stack direction="row" spacing={4} flexWrap="wrap" useFlexGap>
              <Box>
                <Typography variant="caption" sx={{ color: "grey.500", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                  Recipient
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, color: chartColors.cyan, mt: 0.5 }}>
                  {lead?.Email || "No email available"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: "grey.500", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                  Business
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, color: "grey.200", mt: 0.5 }}>
                  {lead?.Business_Name || "-"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: "grey.500", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                  Location
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, color: "grey.200", mt: 0.5 }}>
                  {lead?.City}, {lead?.State}
                </Typography>
              </Box>
            </Stack>
          </Box>

          {/* Template Selector */}
          <FormControl fullWidth>
            <InputLabel>Email Template</InputLabel>
            <Select
              value={selectedTemplate}
              label="Email Template"
              onChange={(e) => handleTemplateChange(e.target.value)}
            >
              <MenuItem value="">
                <em>Write custom email</em>
              </MenuItem>
              {templatesQuery.data?.templates.map((template) => (
                <MenuItem key={template.id} value={template.id}>
                  {template.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Subject */}
          <TextField
            label="Subject"
            fullWidth
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Email subject line..."
          />

          {/* Body */}
          <TextField
            label="Message"
            fullWidth
            multiline
            minRows={8}
            maxRows={12}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your email message here..."
          />

          {/* Error/Success Messages */}
          {sendMutation.isError && (
            <Alert severity="error">
              {(sendMutation.error as Error)?.message || "Failed to send email"}
            </Alert>
          )}

          {sendSuccess && (
            <Alert severity="success">
              Email sent successfully!
            </Alert>
          )}

          {!lead?.Email && (
            <Alert severity="warning">
              This lead does not have an email address. You cannot send an email.
            </Alert>
          )}
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2, borderTop: "1px solid", borderColor: alpha("#fff", 0.06) }}>
        <Button onClick={onClose} variant="outlined">
          Cancel
        </Button>
        <Button
          variant="contained"
          startIcon={sendMutation.isPending ? <CircularProgress size={18} color="inherit" /> : <SendIcon />}
          disabled={!canSend}
          onClick={() => sendMutation.mutate()}
        >
          {sendMutation.isPending ? "Sending..." : "Send Email"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
