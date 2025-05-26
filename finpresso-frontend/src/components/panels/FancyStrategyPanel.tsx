import React from 'react';
import {
  Paper,
  Stepper,
  Step,
  StepLabel,
  Tooltip,
  Divider,
  Stack,
  Typography,
  Chip,
  Box
} from '@mui/material';
import { keyframes } from '@mui/material/styles';
import GaugeChart from 'react-gauge-chart';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import FlagIcon from '@mui/icons-material/Flag';

export interface FancyData {
  steps: { label: string; note?: string }[];
  riskScore: number;
  rrRatio: number;
  pnlTarget: number;
  stopLoss: number;
  conviction: 'low' | 'med' | 'high';
}

export function toFancy(data: any): FancyData {
  const riskScoreMap: Record<string, number> = {
    LOW: 0.25,
    MEDIUM: 0.5,
    HIGH: 0.75,
  };
  return {
    steps: [
      { label: 'ENTRY', note: (data.entry_signals || []).join(', ') },
      { label: 'MANAGE', note: `Risk: ${data.risk_level}, Horizon: ${data.time_horizon}` },
      { label: 'EXIT', note: (data.exit_triggers || []).join(', ') },
    ],
    riskScore: riskScoreMap[(data.risk_level || 'MEDIUM').toUpperCase()] ?? 0.5,
    rrRatio: data.expected_reward ? parseFloat(String(data.expected_reward)) / 15 : 1.5,
    pnlTarget: data.expected_reward ? parseFloat(String(data.expected_reward)) : 10,
    stopLoss: 5,
    conviction:
      data.recommended_action === 'BUY' || data.recommended_action === 'LONG'
        ? 'high'
        : data.recommended_action === 'WAIT'
        ? 'med'
        : 'low',
  };
}

// Dark AI-tech styling constants
const PANEL_BG = 'rgba(18,18,18,0.9)';
const STEP_BG = 'rgba(30,30,30,0.85)';
const TEXT_PRIMARY = '#E0E0E0';
const TEXT_SECONDARY = '#90A4AE';
const ACCENT_GRAD = 'linear-gradient(135deg, #0ff, #06f, #a3f)';
const CHIP_COLORS: Record<FancyData['conviction'], string> = {
  low: '#eab308',
  med: '#6366f1',
  high: '#10b981',
};

// Glow animation for active elements
const glow = keyframes`
  from { box-shadow: 0 0 0 rgba(15,255,255,0); }
  to { box-shadow: 0 0 12px 4px rgba(15,255,255,0.6); }
`;

interface FancyStrategyPanelProps {
  data: FancyData;
}

const FancyStrategyPanel: React.FC<FancyStrategyPanelProps> = ({ data }) => (
  <Paper
    elevation={8}
    sx={{
      width: '100%',
      maxWidth: 1200,
      mx: 'auto',
      p: { xs: 3, md: 5 },
      borderRadius: 4,
      bgcolor: PANEL_BG,
      border: '1px solid #333',
    }}
  >
    {/* Stepper */}
    <Stepper alternativeLabel sx={{ mb: 4, bgcolor: STEP_BG, borderRadius: 2 }}>
      {data.steps.map(({ label, note }, idx) => (
        <Step key={idx} completed={idx < data.steps.length - 1}>
          <Tooltip title={note || ''} arrow placement="top">
            <StepLabel
              StepIconComponent={() => (
                <Box
                  sx={{
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    bgcolor:
                      idx === 0
                        ? '#06b6d4'
                        : idx === data.steps.length - 1
                        ? '#ef4444'
                        : '#6366f1',
                    boxShadow: '0 0 6px rgba(255,255,255,0.2)',
                  }}
                />
              )}
            >
              <Typography variant="body2" sx={{ color: TEXT_PRIMARY, fontWeight: 600 }}>
                {label}
              </Typography>
            </StepLabel>
          </Tooltip>
        </Step>
      ))}
    </Stepper>

    <Divider sx={{ borderColor: '#444', my: 3 }} />

    {/* Gauges and stats */}
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={4} justifyContent="space-between">
      {/* Risk Level Gauge */}
      <Stack spacing={1} alignItems="center" sx={{ flex: 1 }}>
        <Typography variant="subtitle2" sx={{ color: TEXT_SECONDARY }}>Risk Level</Typography>
        <Box sx={{ width: '100%', bgcolor: STEP_BG, p: 2, borderRadius: 2 }}>
          <GaugeChart
            id="risk-gauge"
            nrOfLevels={5}
            colors={['#ef4444', '#f97316', '#eab308', '#84cc16', '#10b981']}
            percent={data.riskScore}
            arcPadding={0.04}
            animate={false}
          />
        </Box>
      </Stack>

      {/* Risk/Reward Ratio */}
      <Stack spacing={1} alignItems="center" sx={{ flex: 1 }}>
        <Typography variant="subtitle2" sx={{ color: TEXT_SECONDARY }}>Risk / Reward</Typography>
        <Box
          sx={{
            width: '100%',
            textAlign: 'center',
            bgcolor: STEP_BG,
            p: 2,
            borderRadius: 2,
          }}
        >
          <Typography
            sx={{
              fontSize: 32,
              fontFamily: 'Roboto Mono, monospace',
              fontWeight: 700,
              color: data.rrRatio >= 2 ? '#10b981' : '#eab308',
            }}
          >
            {data.rrRatio.toFixed(2)}
          </Typography>
        </Box>
      </Stack>

      {/* Targets */}
      <Stack spacing={1} alignItems="center" sx={{ flex: 1 }}>
        <Typography variant="subtitle2" sx={{ color: TEXT_SECONDARY }}>Targets</Typography>
        <Chip
          icon={<TrendingUpIcon />}
          label={`TP ${data.pnlTarget}%`}
          sx={{
            fontWeight: 600,
            bgcolor: '#10b981',
            color: '#000',
            animation: `${glow} .6s infinite alternate`,
          }}
        />
        <Chip
          icon={<TrendingDownIcon />}
          label={`SL ${data.stopLoss}%`}
          sx={{ fontWeight: 600, bgcolor: '#ef4444', color: '#000' }}
        />
      </Stack>
    </Stack>

    <Divider sx={{ borderColor: '#444', my: 3 }} />

    {/* Conviction badge */}
    <Stack direction="row" justifyContent="center">
      <Chip
        icon={<FlagIcon />}
        label={`Conviction: ${data.conviction.toUpperCase()}`}
        sx={{
          fontWeight: 700,
          bgcolor: CHIP_COLORS[data.conviction],
          color: '#000',
          px: 3,
          py: 1,
          animation: `${glow} 1s infinite alternate`,
        }}
      />
    </Stack>
  </Paper>
);
export default FancyStrategyPanel;
