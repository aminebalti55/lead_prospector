import { useMemo } from "react";
import { DataGrid, GridColDef, GridRowModel, GridRenderCellParams, GridActionsCellItem } from "@mui/x-data-grid";
import { Box, Chip, alpha } from "@mui/material";
import { Email as EmailIcon } from "@mui/icons-material";
import type { Lead, LeadUpdateRequest } from "../api/types";
import QualityBadge, { QualityTier } from "./QualityBadge";
import { chartColors } from "../theme";

type Props = {
  rows: Lead[];
  saving: boolean;
  onUpdate: (leadId: string, patch: LeadUpdateRequest) => Promise<void>;
  onSendEmail?: (lead: Lead) => void;
};

const EDITABLE_FIELDS: Array<keyof LeadUpdateRequest> = [
  "Outreach_Status",
  "Notes",
  "Owner",
  "Last_Contacted",
  "Follow_Up_Date",
];

// Priority cell renderer
function PriorityCell({ value }: { value: string }) {
  const priority = (value || "").toLowerCase();
  let color = chartColors.cold;

  if (priority === "hot") {
    color = chartColors.hot;
  } else if (priority === "warm") {
    color = chartColors.warning;
  }

  return (
    <Chip
      label={value || "—"}
      size="small"
      sx={{
        fontWeight: 600,
        fontSize: "0.7rem",
        color,
        bgcolor: alpha(color, 0.15),
        border: `1px solid ${alpha(color, 0.3)}`,
        textTransform: "capitalize",
      }}
    />
  );
}

// Quality cell renderer
function QualityCell({ row }: { row: Lead }) {
  if (!row.quality_score || !row.quality_tier) return null;
  return <QualityBadge score={row.quality_score} tier={row.quality_tier as QualityTier} size="small" />;
}

// Email cell renderer
function EmailCell({ value }: { value: string }) {
  if (!value) return <span style={{ color: "#52525b" }}>—</span>;
  return (
    <Box
      component="a"
      href={`mailto:${value}`}
      sx={{
        color: chartColors.cyan,
        textDecoration: "none",
        fontWeight: 500,
        "&:hover": { textDecoration: "underline" },
      }}
    >
      {value}
    </Box>
  );
}

// Website cell renderer
function WebsiteCell({ value }: { value: string }) {
  if (!value) return <span style={{ color: "#52525b" }}>—</span>;
  const url = value.startsWith("http") ? value : `https://${value}`;
  return (
    <Box
      component="a"
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      sx={{
        color: chartColors.purple,
        textDecoration: "none",
        fontWeight: 500,
        maxWidth: 180,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        display: "block",
        "&:hover": { textDecoration: "underline" },
      }}
    >
      {value.replace(/^https?:\/\//, "").replace(/\/$/, "")}
    </Box>
  );
}

export default function LeadsTable({ rows, onUpdate, saving, onSendEmail }: Props) {
  const columns = useMemo<GridColDef[]>(() => {
    const base: GridColDef[] = [
      {
        field: "Priority",
        headerName: "Priority",
        width: 100,
        renderCell: (params: GridRenderCellParams) => <PriorityCell value={params.value as string} />,
      },
      {
        field: "quality_score",
        headerName: "Quality",
        width: 120,
        renderCell: (params: GridRenderCellParams) => <QualityCell row={params.row as Lead} />,
        sortable: true,
      },
      { field: "Score", headerName: "Score", width: 80, type: "number" },
      { field: "Recommended_Offer", headerName: "Offer", width: 160 },
      {
        field: "Business_Name",
        headerName: "Business",
        width: 220,
        renderCell: (params: GridRenderCellParams) => (
          <Box sx={{ fontWeight: 600, color: "grey.100" }}>{params.value as string}</Box>
        ),
      },
      { field: "Niche", headerName: "Niche", width: 120 },
      { field: "City", headerName: "City", width: 120 },
      { field: "State", headerName: "State", width: 70 },
      { field: "Phone", headerName: "Phone", width: 140 },
      {
        field: "Website",
        headerName: "Website",
        width: 180,
        renderCell: (params: GridRenderCellParams) => <WebsiteCell value={params.value as string} />,
      },
      {
        field: "Email",
        headerName: "Email",
        width: 200,
        renderCell: (params: GridRenderCellParams) => <EmailCell value={params.value as string} />,
      },
      { field: "Email_Source", headerName: "Source", width: 100 },
      { field: "Pain_Tags", headerName: "Pain Tags", width: 180 },
      { field: "Outreach_Status", headerName: "Outreach", width: 120, editable: true },
      { field: "Owner", headerName: "Owner", width: 100, editable: true },
      { field: "Last_Contacted", headerName: "Contacted", width: 120, editable: true },
      { field: "Follow_Up_Date", headerName: "Follow Up", width: 120, editable: true },
      { field: "Notes", headerName: "Notes", width: 250, editable: true },
    ];

    // Add actions column if email handler provided
    if (onSendEmail) {
      base.push({
        field: "actions",
        type: "actions",
        headerName: "Actions",
        width: 80,
        getActions: (params) => {
          const lead = params.row as Lead;
          const hasEmail = lead.Email && (lead.Email as string).includes("@");
          return [
            <GridActionsCellItem
              key="email"
              icon={<EmailIcon sx={{ color: hasEmail ? chartColors.cyan : "#3f3f46" }} />}
              label="Send Email"
              onClick={() => onSendEmail(lead)}
              disabled={!hasEmail}
              showInMenu={false}
            />,
          ];
        },
      });
    }

    // Keep Lead_ID available for updates; hide it by default.
    base.unshift({ field: "Lead_ID", headerName: "Lead_ID", width: 180 });
    return base;
  }, [onSendEmail]);

  return (
    <Box sx={{ height: 680, width: "100%" }}>
      <DataGrid
        rows={rows as GridRowModel[]}
        columns={columns}
        getRowId={(row) => String((row as Lead).Lead_ID)}
        disableRowSelectionOnClick
        density="compact"
        loading={saving}
        processRowUpdate={async (newRow, oldRow) => {
          const leadId = String((newRow as Lead).Lead_ID);
          const patch: LeadUpdateRequest = {};

          for (const field of EDITABLE_FIELDS) {
            const n = (newRow as Record<string, unknown>)[field];
            const o = (oldRow as Record<string, unknown>)[field];
            if (n !== o) patch[field] = String(n ?? "");
          }

          if (Object.keys(patch).length) {
            await onUpdate(leadId, patch);
          }
          return newRow;
        }}
        onProcessRowUpdateError={(err) => {
          console.error(err);
        }}
        initialState={{
          pagination: { paginationModel: { pageSize: 50, page: 0 } },
          columns: { columnVisibilityModel: { Lead_ID: false } },
          sorting: { sortModel: [{ field: "quality_score", sort: "desc" }] },
        }}
        pageSizeOptions={[25, 50, 100]}
        sx={{
          border: "none",
          borderRadius: 0,
          "& .MuiDataGrid-main": {
            backgroundColor: alpha("#18181b", 0.5),
          },
          "& .MuiDataGrid-columnHeaders": {
            bgcolor: alpha("#8b5cf6", 0.08),
            borderBottom: `1px solid ${alpha("#fff", 0.06)}`,
          },
          "& .MuiDataGrid-columnHeader": {
            "&:focus, &:focus-within": {
              outline: "none",
            },
          },
          "& .MuiDataGrid-columnHeaderTitle": {
            fontWeight: 700,
            fontSize: "0.75rem",
            color: "#a1a1aa",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          },
          "& .MuiDataGrid-cell": {
            fontSize: "0.85rem",
            color: "#d4d4d8",
            borderBottom: `1px solid ${alpha("#fff", 0.03)}`,
            "&:focus, &:focus-within": {
              outline: "none",
            },
          },
          "& .MuiDataGrid-row": {
            "&:hover": {
              bgcolor: alpha("#8b5cf6", 0.06),
            },
            "&.Mui-selected": {
              bgcolor: alpha("#8b5cf6", 0.1),
              "&:hover": {
                bgcolor: alpha("#8b5cf6", 0.12),
              },
            },
          },
          "& .MuiDataGrid-footerContainer": {
            borderTop: `1px solid ${alpha("#fff", 0.06)}`,
            bgcolor: alpha("#18181b", 0.5),
          },
          "& .MuiTablePagination-root": {
            color: "#a1a1aa",
          },
          "& .MuiDataGrid-virtualScroller": {
            "&::-webkit-scrollbar": {
              width: 8,
              height: 8,
            },
            "&::-webkit-scrollbar-track": {
              background: "transparent",
            },
            "&::-webkit-scrollbar-thumb": {
              background: "#3f3f46",
              borderRadius: 4,
            },
          },
          "& .MuiDataGrid-cell--editable": {
            cursor: "text",
            "&:hover": {
              bgcolor: alpha("#8b5cf6", 0.1),
            },
          },
          "& .MuiDataGrid-cell--editing": {
            bgcolor: alpha("#8b5cf6", 0.15),
            boxShadow: `inset 0 0 0 1px ${alpha("#8b5cf6", 0.5)}`,
          },
          "& .MuiInputBase-input": {
            color: "#f4f4f5",
          },
        }}
      />
    </Box>
  );
}
