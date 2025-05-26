import React from 'react';
import {
  Box,
  Alert,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import StarIcon from '@mui/icons-material/Star';
import ArrowCircleRightIcon from '@mui/icons-material/ArrowCircleRight';
import { keyframes } from '@mui/material/styles';

// Dark AI tech palette
const DARK_BG = '#121212';
const PANEL_BG = 'rgba(18,18,18,0.85)';
const CARD_BG = 'rgba(30,30,30,0.8)';
const TEXT_PRIMARY = '#E0E0E0';
const TEXT_SECONDARY = '#90A4AE';
const ACCENT = 'linear-gradient(90deg, #0ff, #06f, #a3f)';
const ALERT_INFO_BG = 'rgba(15,255,255,0.1)';
const ALERT_WARN_BG = 'rgba(255,195,0,0.1)';

const glow = keyframes`
  from { box-shadow: 0 0 0 rgba(15,255,255,0); }
  to   { box-shadow: 0 0 12px 4px rgba(15,255,255,0.6); }
`;

interface MicroPanelProps {
  data: {
    Micro_Expectation?: string;
    Three_Key_Takeaways?: any;
    Next_Inference_Hint_Micro_News?: string;
  };
}

const MicroPanel: React.FC<MicroPanelProps> = ({ data }) => {
  const raw = data.Three_Key_Takeaways;
  let takeaways: string[] = [];

  if (Array.isArray(raw)) {
    takeaways = raw.map(item => String(item).trim()).filter(Boolean);
  } else if (typeof raw === 'string') {
    takeaways = raw.split(/\r?\n+/).map(line => line.trim()).filter(Boolean);
  } else if (raw && typeof raw === 'object') {
    takeaways = Object.values(raw).map(item => String(item).trim()).filter(Boolean);
  }

  return (
    <Box
      sx={{
        maxWidth: 900,
        mx: 'auto',
        p: { xs: 3, md: 5 },
        borderRadius: 4,
        backdropFilter: 'blur(18px)',
        background: PANEL_BG,
        border: '1px solid #333',
      }}
    >
      <Alert
        icon={<InfoIcon fontSize="inherit" style={{ color: '#0ff' }} />}
        severity="info"
        sx={{
          mb: 3,
          bgcolor: ALERT_INFO_BG,
          borderLeft: `6px solid #0ff`,
          '& .MuiAlert-message': { color: TEXT_PRIMARY, fontWeight: 600 },
        }}
      >
        <Typography variant="body1" sx={{ color: TEXT_PRIMARY }}>
          {data.Micro_Expectation || '—'}
        </Typography>
      </Alert>

      <Card
        variant="outlined"
        sx={{
          borderRadius: 3,
          overflow: 'hidden',
          bgcolor: CARD_BG,
          border: '1px solid #444',
          ':before': {
            content: '""',
            display: 'block',
            width: '100%',
            height: 4,
            background: ACCENT,
          },
        }}
      >
        <CardContent sx={{ pt: 3 }}>
          <Typography
            variant="subtitle1"
            sx={{ fontWeight: 700, mb: 2, letterSpacing: 0.2, color: TEXT_PRIMARY }}
          >
            ✨ Three Key Takeaways
          </Typography>
          <List disablePadding>
            {takeaways.map((t, i) => (
              <ListItem key={i} sx={{ py: 1, bgcolor: 'transparent' }}>
                <ListItemIcon>
                  <StarIcon sx={{ color: '#0ff' }} />
                </ListItemIcon>
                <ListItemText
                  primaryTypographyProps={{
                    fontFamily: 'Roboto Mono, monospace',
                    fontWeight: 700,
                    color: TEXT_PRIMARY,
                  }}
                  primary={t}
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>

      {data.Next_Inference_Hint_Micro_News && (
        <Alert
          icon={<ArrowCircleRightIcon fontSize="inherit" style={{ color: '#ffc300' }} />}
          severity="warning"
          sx={{
            mt: 3,
            bgcolor: ALERT_WARN_BG,
            borderLeft: `6px solid #ffc300`,
            '& .MuiAlert-message': { color: TEXT_PRIMARY, fontWeight: 600 },
          }}
        >
          <Typography variant="body2" sx={{ color: TEXT_PRIMARY }}>
            {data.Next_Inference_Hint_Micro_News}
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default MicroPanel;
