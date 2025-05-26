import React from 'react';
import {
  Paper,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Chip,
  Stack,
  Box,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import BoltIcon from '@mui/icons-material/Bolt';
import { keyframes } from '@mui/material/styles';

// Dark AI tech palette
const DARK_BG = '#121212';
const PANEL_BG = 'rgba(18,18,18,0.85)';
const ACCORDION_BG = 'rgba(30,30,30,0.8)';
const TEXT_PRIMARY = '#E0E0E0';
const TEXT_SECONDARY = '#90A4AE';
const ACCENT = 'linear-gradient(90deg, #0ff, #06f, #a3f)';
const CHIP_BG = 'rgba(50,50,50,0.6)';
const CHIP_HOVER = '#0ff';

const glow = keyframes`
  from { box-shadow: 0 0 0 rgba(15,255,255,0); }
  to   { box-shadow: 0 0 12px 4px rgba(15,255,255,0.6); }
`;

interface MacroPanelProps {
  data: {
    summary?: string;
    key_indicators?: Record<string, any>;
    macro_catalysts?: string[];
  };
}

const MacroPanel: React.FC<MacroPanelProps> = ({ data }) => (
  <Paper
    elevation={6}
    sx={{
      maxWidth: 960,
      mx: 'auto',
      p: { xs: 3, md: 5 },
      borderRadius: 3,
      overflow: 'hidden',
      bgcolor: PANEL_BG,
      border: '1px solid #333',
    }}
  >
    <Alert
      icon={false}
      severity="info"
      sx={{
        mb: 4,
        bgcolor: 'rgba(30,30,30,0.9)',
        borderLeft: `6px solid ${CHIP_HOVER}`,
        '& .MuiAlert-message': { color: TEXT_PRIMARY, fontWeight: 600 },
      }}
    >
      <Typography variant="body1" sx={{ color: TEXT_PRIMARY }}>
        {data.summary || '—'}
      </Typography>
    </Alert>

    <Accordion defaultExpanded disableGutters sx={{ bgcolor: ACCORDION_BG, color: TEXT_PRIMARY }}>
      <AccordionSummary
        expandIcon={<ExpandMoreIcon htmlColor={TEXT_SECONDARY} />}
        sx={{
          '& .MuiAccordionSummary-content': { alignItems: 'center' },
          '.MuiAccordionSummary-content': {
            fontWeight: 700,
            '&::before': {
              content: '""',
              display: 'block',
              width: 4,
              height: 20,
              mr: 1.5,
              background: ACCENT,
              borderRadius: 2,
            },
            color: TEXT_PRIMARY,
          },
        }}
      >
        Key Indicators
      </AccordionSummary>
      <AccordionDetails sx={{ px: 0 }}>
        <List dense disablePadding>
          {Object.entries(data.key_indicators || {}).map(([k, v]) => (
            <ListItem key={k} sx={{ py: 1.2, bgcolor: 'transparent' }}>
              <ListItemIcon sx={{ minWidth: 28 }}>
                <BoltIcon sx={{ color: CHIP_HOVER }} />
              </ListItemIcon>
              <ListItemText
                primary={
                  <Typography variant="body2" sx={{ color: TEXT_SECONDARY, fontWeight: 600 }}>
                    {k.replace(/_/g, ' ')}
                  </Typography>
                }
                secondary={
                  <Typography
                    component="span"
                    sx={{
                      fontFamily: 'Roboto Mono, monospace',
                      fontWeight: 700,
                      color: TEXT_PRIMARY,
                    }}
                  >
                    {String(v)}
                  </Typography>
                }
              />
            </ListItem>
          ))}
        </List>
      </AccordionDetails>
    </Accordion>

    <Accordion disableGutters sx={{ mt: 2, bgcolor: ACCORDION_BG, color: TEXT_PRIMARY }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon htmlColor={TEXT_SECONDARY} />}>
        <Typography fontWeight={700} sx={{ color: TEXT_PRIMARY }}>
          Catalysts
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {(data.macro_catalysts || []).map((c, i) => (
          <Chip
            key={i}
            label={
              <Typography sx={{ color: TEXT_PRIMARY, fontWeight: 600 }}>{c}</Typography>
            }
            clickable
            sx={{
              fontWeight: 600,
              border: '1px solid transparent',
              borderImage: `${ACCENT} 1`,
              bgcolor: CHIP_BG,
              '&:hover': {
                animation: `${glow} .5s forwards`,
                cursor: 'pointer',
                bgcolor: 'rgba(30,30,30,0.95)',
              },
            }}
          />
        ))}
      </AccordionDetails>
    </Accordion>
  </Paper>
);

export default MacroPanel;
