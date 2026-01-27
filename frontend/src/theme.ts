import { createTheme, alpha } from "@mui/material/styles";

// Sleek dark mode color palette
const colors = {
  primary: {
    main: "#8b5cf6",
    light: "#a78bfa",
    dark: "#7c3aed",
    contrastText: "#ffffff",
  },
  secondary: {
    main: "#06b6d4",
    light: "#22d3ee",
    dark: "#0891b2",
    contrastText: "#ffffff",
  },
  accent: {
    cyan: "#06b6d4",
    purple: "#8b5cf6",
    pink: "#ec4899",
    green: "#10b981",
    orange: "#f59e0b",
  },
  success: {
    main: "#10b981",
    light: "#34d399",
    dark: "#059669",
  },
  warning: {
    main: "#f59e0b",
    light: "#fbbf24",
    dark: "#d97706",
  },
  error: {
    main: "#ef4444",
    light: "#f87171",
    dark: "#dc2626",
  },
  grey: {
    50: "#fafafa",
    100: "#f4f4f5",
    200: "#e4e4e7",
    300: "#d4d4d8",
    400: "#a1a1aa",
    500: "#71717a",
    600: "#52525b",
    700: "#3f3f46",
    800: "#27272a",
    850: "#1f1f23",
    900: "#18181b",
    950: "#09090b",
  },
};

// Glass effect styles
export const glassEffect = {
  background: `linear-gradient(135deg, ${alpha(colors.grey[800], 0.8)} 0%, ${alpha(colors.grey[900], 0.9)} 100%)`,
  backdropFilter: "blur(20px)",
  border: `1px solid ${alpha(colors.grey[700], 0.5)}`,
};

export const glassEffectLight = {
  background: `linear-gradient(135deg, ${alpha(colors.grey[800], 0.6)} 0%, ${alpha(colors.grey[850], 0.7)} 100%)`,
  backdropFilter: "blur(12px)",
  border: `1px solid ${alpha(colors.grey[700], 0.3)}`,
};

export const gradients = {
  primary: `linear-gradient(135deg, ${colors.primary.main} 0%, ${colors.accent.pink} 100%)`,
  secondary: `linear-gradient(135deg, ${colors.secondary.main} 0%, ${colors.primary.main} 100%)`,
  success: `linear-gradient(135deg, ${colors.success.main} 0%, ${colors.accent.cyan} 100%)`,
  accent: `linear-gradient(135deg, ${colors.accent.purple} 0%, ${colors.accent.cyan} 100%)`,
  dark: `linear-gradient(180deg, ${colors.grey[900]} 0%, ${colors.grey[950]} 100%)`,
  card: `linear-gradient(145deg, ${alpha(colors.grey[800], 0.5)} 0%, ${alpha(colors.grey[900], 0.8)} 100%)`,
  glow: `radial-gradient(ellipse at 50% 0%, ${alpha(colors.primary.main, 0.15)} 0%, transparent 60%)`,
};

export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: colors.primary,
    secondary: colors.secondary,
    success: colors.success,
    warning: colors.warning,
    error: colors.error,
    grey: colors.grey,
    background: {
      default: colors.grey[950],
      paper: colors.grey[900],
    },
    text: {
      primary: colors.grey[100],
      secondary: colors.grey[400],
    },
    divider: alpha(colors.grey[700], 0.5),
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    h1: {
      fontSize: "2.5rem",
      fontWeight: 700,
      letterSpacing: "-0.025em",
      lineHeight: 1.2,
    },
    h2: {
      fontSize: "2rem",
      fontWeight: 700,
      letterSpacing: "-0.02em",
      lineHeight: 1.3,
    },
    h3: {
      fontSize: "1.5rem",
      fontWeight: 600,
      letterSpacing: "-0.015em",
      lineHeight: 1.4,
    },
    h4: {
      fontSize: "1.25rem",
      fontWeight: 600,
      letterSpacing: "-0.01em",
      lineHeight: 1.4,
    },
    h5: {
      fontSize: "1.125rem",
      fontWeight: 600,
      lineHeight: 1.5,
    },
    h6: {
      fontSize: "1rem",
      fontWeight: 600,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: "0.9375rem",
      lineHeight: 1.7,
    },
    body2: {
      fontSize: "0.875rem",
      lineHeight: 1.6,
    },
    caption: {
      fontSize: "0.75rem",
      lineHeight: 1.5,
      color: colors.grey[500],
    },
    button: {
      textTransform: "none",
      fontWeight: 600,
      letterSpacing: "0.01em",
    },
  },
  shape: {
    borderRadius: 16,
  },
  shadows: [
    "none",
    `0 1px 2px ${alpha("#000", 0.3)}`,
    `0 2px 4px ${alpha("#000", 0.3)}`,
    `0 4px 8px ${alpha("#000", 0.3)}`,
    `0 8px 16px ${alpha("#000", 0.3)}`,
    `0 12px 24px ${alpha("#000", 0.3)}`,
    `0 16px 32px ${alpha("#000", 0.3)}`,
    ...Array(18).fill("none"),
  ] as any,
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarWidth: "thin",
          scrollbarColor: `${colors.grey[700]} transparent`,
          "&::-webkit-scrollbar": {
            width: 8,
          },
          "&::-webkit-scrollbar-track": {
            background: "transparent",
          },
          "&::-webkit-scrollbar-thumb": {
            background: colors.grey[700],
            borderRadius: 4,
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: "10px 24px",
          fontSize: "0.875rem",
          fontWeight: 600,
          boxShadow: "none",
          transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        },
        contained: {
          background: gradients.primary,
          "&:hover": {
            background: gradients.primary,
            transform: "translateY(-1px)",
            boxShadow: `0 8px 24px ${alpha(colors.primary.main, 0.4)}`,
          },
          "&:active": {
            transform: "translateY(0)",
          },
        },
        outlined: {
          borderColor: alpha(colors.grey[600], 0.5),
          color: colors.grey[300],
          "&:hover": {
            borderColor: colors.primary.main,
            backgroundColor: alpha(colors.primary.main, 0.1),
            color: colors.primary.light,
          },
        },
        text: {
          color: colors.grey[400],
          "&:hover": {
            backgroundColor: alpha(colors.grey[700], 0.5),
            color: colors.grey[200],
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          ...glassEffect,
          boxShadow: `0 8px 32px ${alpha("#000", 0.3)}`,
          transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          overflow: "hidden",
          "&:hover": {
            boxShadow: `0 16px 48px ${alpha("#000", 0.4)}`,
            borderColor: alpha(colors.grey[600], 0.6),
          },
        },
      },
    },
    MuiCardContent: {
      styleOverrides: {
        root: {
          padding: 28,
          "&:last-child": {
            paddingBottom: 28,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          fontWeight: 600,
          fontSize: "0.75rem",
          height: 28,
        },
        filled: {
          backgroundColor: alpha(colors.grey[700], 0.6),
          color: colors.grey[200],
          "&:hover": {
            backgroundColor: alpha(colors.grey[600], 0.8),
          },
        },
        outlined: {
          borderColor: alpha(colors.grey[600], 0.5),
          color: colors.grey[300],
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          "& .MuiOutlinedInput-root": {
            borderRadius: 12,
            backgroundColor: alpha(colors.grey[800], 0.5),
            transition: "all 0.2s ease",
            "& fieldset": {
              borderColor: alpha(colors.grey[700], 0.5),
              transition: "all 0.2s ease",
            },
            "&:hover fieldset": {
              borderColor: colors.grey[600],
            },
            "&.Mui-focused": {
              backgroundColor: alpha(colors.grey[800], 0.8),
              "& fieldset": {
                borderColor: colors.primary.main,
                borderWidth: 1,
              },
              boxShadow: `0 0 0 4px ${alpha(colors.primary.main, 0.15)}`,
            },
          },
        },
      },
    },
    MuiAutocomplete: {
      styleOverrides: {
        paper: {
          borderRadius: 16,
          ...glassEffect,
          boxShadow: `0 16px 48px ${alpha("#000", 0.5)}`,
          marginTop: 8,
        },
        listbox: {
          padding: 8,
        },
        option: {
          borderRadius: 10,
          margin: "2px 0",
          "&:hover": {
            backgroundColor: alpha(colors.primary.main, 0.15),
          },
          "&[aria-selected='true']": {
            backgroundColor: alpha(colors.primary.main, 0.2),
          },
        },
        groupLabel: {
          color: colors.grey[500],
          fontWeight: 700,
          fontSize: "0.7rem",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          padding: "12px 16px 4px",
        },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          textTransform: "none",
          fontWeight: 600,
          padding: "10px 20px",
          borderColor: alpha(colors.grey[700], 0.5),
          color: colors.grey[400],
          transition: "all 0.2s ease",
          "&:hover": {
            backgroundColor: alpha(colors.grey[700], 0.3),
            borderColor: colors.grey[600],
          },
          "&.Mui-selected": {
            background: gradients.primary,
            color: "#fff",
            borderColor: "transparent",
            "&:hover": {
              background: gradients.primary,
              opacity: 0.9,
            },
          },
        },
      },
    },
    MuiSlider: {
      styleOverrides: {
        root: {
          height: 6,
        },
        rail: {
          backgroundColor: colors.grey[700],
          opacity: 1,
        },
        track: {
          background: gradients.primary,
          border: "none",
        },
        thumb: {
          width: 18,
          height: 18,
          backgroundColor: colors.grey[100],
          boxShadow: `0 2px 8px ${alpha("#000", 0.4)}`,
          "&:hover, &.Mui-focusVisible": {
            boxShadow: `0 0 0 8px ${alpha(colors.primary.main, 0.2)}`,
          },
        },
        mark: {
          backgroundColor: colors.grey[600],
          width: 4,
          height: 4,
          borderRadius: "50%",
        },
        markLabel: {
          color: colors.grey[500],
          fontSize: "0.7rem",
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          height: 6,
          backgroundColor: alpha(colors.grey[700], 0.5),
        },
        bar: {
          borderRadius: 10,
          background: gradients.primary,
        },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: {
          color: colors.primary.main,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 14,
          border: "1px solid",
          backdropFilter: "blur(8px)",
        },
        standardSuccess: {
          backgroundColor: alpha(colors.success.main, 0.15),
          borderColor: alpha(colors.success.main, 0.3),
          color: colors.success.light,
          "& .MuiAlert-icon": {
            color: colors.success.main,
          },
        },
        standardError: {
          backgroundColor: alpha(colors.error.main, 0.15),
          borderColor: alpha(colors.error.main, 0.3),
          color: colors.error.light,
          "& .MuiAlert-icon": {
            color: colors.error.main,
          },
        },
        standardWarning: {
          backgroundColor: alpha(colors.warning.main, 0.15),
          borderColor: alpha(colors.warning.main, 0.3),
          color: colors.warning.light,
          "& .MuiAlert-icon": {
            color: colors.warning.main,
          },
        },
        standardInfo: {
          backgroundColor: alpha(colors.primary.main, 0.15),
          borderColor: alpha(colors.primary.main, 0.3),
          color: colors.primary.light,
          "& .MuiAlert-icon": {
            color: colors.primary.main,
          },
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: colors.grey[800],
          borderRadius: 10,
          padding: "8px 14px",
          fontSize: "0.75rem",
          border: `1px solid ${alpha(colors.grey[700], 0.5)}`,
          boxShadow: `0 8px 24px ${alpha("#000", 0.4)}`,
        },
        arrow: {
          color: colors.grey[800],
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: {
          borderRadius: 14,
          ...glassEffect,
          boxShadow: `0 16px 48px ${alpha("#000", 0.5)}`,
        },
        list: {
          padding: 8,
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          margin: "2px 0",
          padding: "10px 16px",
          "&:hover": {
            backgroundColor: alpha(colors.primary.main, 0.1),
          },
          "&.Mui-selected": {
            backgroundColor: alpha(colors.primary.main, 0.2),
            "&:hover": {
              backgroundColor: alpha(colors.primary.main, 0.25),
            },
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: colors.grey[600],
          "&.Mui-checked": {
            color: colors.primary.main,
          },
        },
      },
    },
    MuiFormControlLabel: {
      styleOverrides: {
        label: {
          fontSize: "0.875rem",
        },
      },
    },
  },
});

// Chart colors for data visualization
export const chartColors = {
  primary: colors.primary.main,
  secondary: colors.secondary.main,
  success: colors.success.main,
  warning: colors.warning.main,
  error: colors.error.main,
  hot: colors.error.main,
  warm: colors.warning.main,
  cold: colors.grey[500],
  cyan: colors.accent.cyan,
  purple: colors.accent.purple,
  pink: colors.accent.pink,
  gradient: [colors.primary.main, colors.accent.cyan, colors.accent.pink, colors.warning.main],
};
