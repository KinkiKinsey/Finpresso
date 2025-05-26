import React, { useState } from 'react';
import {
  Paper,
  Box,
  Stack,
  Button,
  Typography,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { keyframes } from '@mui/material/styles';

// Dark AI tech theme
const PANEL_BG = 'rgba(18,18,18,0.9)';
const CARD_BG = 'rgba(30,30,30,0.85)';
const TEXT_PRIMARY = '#E0E0E0';
const TEXT_SECONDARY = '#90A4AE';
const ACCENT = 'linear-gradient(135deg, #0ff, #06f, #a3f)';
const BTN_ACTIVE = ACCENT;
const shine = keyframes`
  from { background-position: 0% 50%; }
  to   { background-position: 100% 50%; }
`;

const GRAPHS_BASE = 'http://localhost:8000/static/graphs';
const nameMap = {
  risk_reward: 'Risk • Reward',
  sma_crossovers: 'SMA Cross',
  ema_crossovers: 'EMA Cross',
  vw_macd: 'VW-MACD',
} as const;
type ChartKey = keyof typeof nameMap;

type PricePanelProps = {
  data: {
    graph_paths?: Record<ChartKey, string>;
    risk_reward_summary?: string;
    sma_crossovers_summary?: string;
    ema_crossovers_summary?: string;
    vw_macd_summary?: string;
  };
};

// utility to clean and split summary text
function parseLines(text?: string): string[] {
  if (!text) return [];
  return text
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(line => line && !/^=+$/g.test(line));
}

export default function PricePanel({ data }: PricePanelProps) {
  const keys = (Object.keys(nameMap) as ChartKey[]).filter(k => data.graph_paths?.[k]);
  const [selected, setSelected] = useState<ChartKey>(keys[0]);

  // build image URL
  const imgUrl = data.graph_paths?.[selected]
    ? `${GRAPHS_BASE}/${data.graph_paths[selected].split('/').slice(-2).join('/')}`
    : '';

  // parse summaries
  const riskLines = parseLines(data.risk_reward_summary);
  const smaLines = parseLines(data.sma_crossovers_summary);
  const emaLines = parseLines(data.ema_crossovers_summary);
  const macdLines = parseLines(data.vw_macd_summary);

  // extract long/short details
  const longLine = riskLines.find(l => /^Long Position:/i.test(l)) || '';
  const shortLine = riskLines.find(l => /^Short Position:/i.test(l)) || '';

  const summaryMap: Record<ChartKey, string[]> = {
    risk_reward: riskLines,
    sma_crossovers: smaLines,
    ema_crossovers: emaLines,
    vw_macd: macdLines,
  };

  return (
    <Paper
      elevation={6}
      sx={{ p: 4, borderRadius: 3, bgcolor: PANEL_BG, border: '1px solid #333' }}
    >
      {/* Chart + tabs */}
      <Stack spacing={2} alignItems="center">
        <Box sx={{ width: '100%', height: 3, background: ACCENT }} />
        {imgUrl && (
          <Box
            component="img"
            src={imgUrl}
            alt={nameMap[selected]}
            sx={{ width: '100%', aspectRatio: '16/9', objectFit: 'contain', bgcolor: CARD_BG }}
          />
        )}
        <Stack direction="row" spacing={2} flexWrap="wrap" justifyContent="center">
          {keys.map(key => (
            <Button
              key={key}
              onClick={() => setSelected(key)}
              variant={selected === key ? 'contained' : 'outlined'}
              sx={{
                px: 3,
                textTransform: 'none',
                fontWeight: 600,
                borderRadius: 20,
                color: selected === key ? '#000' : TEXT_PRIMARY,
                borderColor: TEXT_SECONDARY,
                ...(selected === key && {
                  background: BTN_ACTIVE,
                  backgroundSize: '200% 200%',
                  animation: `${shine} 1.2s ease-in-out infinite`,
                  border: 'none',
                }),
              }}
            >
              {nameMap[key]}
            </Button>
          ))}
        </Stack>
      </Stack>

      <Divider sx={{ my: 4, borderColor: '#444' }} />

      {/* Structured summary */}
      <Typography variant="h6" sx={{ color: TEXT_PRIMARY, mb: 2 }}>
        {nameMap[selected]} Details
      </Typography>
      <List dense>
        {summaryMap[selected].map((line, idx) => (
          <ListItem key={idx} sx={{ pl: 0 }}>
            <ListItemText
              primary={
                <Typography
                  variant="body2"
                  sx={{ color: TEXT_SECONDARY, fontWeight: /^Long|Short/.test(line) ? 700 : 400 }}
                >
                  {line}
                </Typography>
              }
            />
          </ListItem>
        ))}
      </List>

      {/* Special Long/Short cards if risk_reward */}
      {selected === 'risk_reward' && (
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} mt={3}>
          <Box sx={{ flex: 1, p: 2, bgcolor: CARD_BG, border: '1px solid #444', borderRadius: 2 }}>
            <Typography variant="subtitle1" sx={{ color: '#0f0', fontWeight: 700, mb: 1 }}>
              ↑ LONG Details
            </Typography>
            <Typography sx={{ color: TEXT_PRIMARY }}>{longLine}</Typography>
          </Box>
          <Box sx={{ flex: 1, p: 2, bgcolor: CARD_BG, border: '1px solid #444', borderRadius: 2 }}>
            <Typography variant="subtitle1" sx={{ color: '#f55', fontWeight: 700, mb: 1 }}>
              ↓ SHORT Details
            </Typography>
            <Typography sx={{ color: TEXT_PRIMARY }}>{shortLine}</Typography>
          </Box>
        </Stack>
      )}
    </Paper>
  );
}
