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
  Box,
  LinearProgress,
} from '@mui/material';
import { keyframes, styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import GaugeChart from 'react-gauge-chart';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import FlagIcon from '@mui/icons-material/Flag';
import AutoGraphIcon from '@mui/icons-material/AutoGraph';
import SecurityIcon from '@mui/icons-material/Security';
import TargetIcon from '@mui/icons-material/GpsFixed';
import SignalCellularAltIcon from '@mui/icons-material/SignalCellularAlt';

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

// Enhanced dark theme
const PANEL_BG = 'rgba(18,18,18,0.95)';
const STEP_BG = 'rgba(30,30,30,0.9)';
const TEXT_PRIMARY = '#E0E0E0';
const TEXT_SECONDARY = '#90A4AE';
const ACCENT_CYAN = '#00ffff';
const ACCENT_PURPLE = '#a855f7';
const ACCENT_GREEN = '#10b981';
const ACCENT_YELLOW = '#eab308';
const ACCENT_RED = '#ef4444';
const ACCENT_GRADIENT = 'linear-gradient(135deg, #00ffff, #a855f7)';

const CHIP_COLORS: Record<FancyData['conviction'], string> = {
  low: ACCENT_YELLOW,
  med: ACCENT_PURPLE,
  high: ACCENT_GREEN,
};

// Animations
const glow = keyframes`
  0% { box-shadow: 0 0 5px rgba(0,255,255,0.5); }
  50% { box-shadow: 0 0 25px rgba(0,255,255,0.8), 0 0 35px rgba(168,85,247,0.6); }
  100% { box-shadow: 0 0 5px rgba(0,255,255,0.5); }
`;

const pulse = keyframes`
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.9; }
`;

const rotate = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`;

const shimmer = keyframes`
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
`;

// Styled components
const StyledPaper = styled(Paper)({
  background: PANEL_BG,
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(0,255,255,0.2)',
  position: 'relative',
  overflow: 'hidden',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 3,
    background: ACCENT_GRADIENT,
    animation: `${shimmer} 3s linear infinite`,
  },
});

const StyledStepper = styled(Stepper)({
  background: STEP_BG,
  borderRadius: 16,
  padding: '20px',
  border: '1px solid rgba(0,255,255,0.1)',
  position: 'relative',
  '& .MuiStepConnector-line': {
    borderColor: ACCENT_PURPLE,
    borderWidth: 2,
  },
  '& .MuiStepConnector-root.Mui-completed .MuiStepConnector-line': {
    borderColor: ACCENT_CYAN,
  },
});

const MetricCard = styled(Box)({
  background: 'rgba(30,30,30,0.9)',
  borderRadius: 16,
  padding: 24,
  border: '1px solid rgba(0,255,255,0.2)',
  position: 'relative',
  overflow: 'hidden',
  transition: 'all 0.3s ease',
  '&:hover': {
    transform: 'translateY(-5px)',
    borderColor: ACCENT_CYAN,
    animation: `${glow} 2s ease-in-out infinite`,
  },
});

const ConvictionChip = styled(Chip)<{ conviction: string }>(({ conviction }) => ({
  fontWeight: 700,
  fontSize: '1rem',
  padding: '24px 32px',
  background: `linear-gradient(135deg, ${CHIP_COLORS[conviction as keyof typeof CHIP_COLORS]}, ${CHIP_COLORS[conviction as keyof typeof CHIP_COLORS]}dd)`,
  color: '#000',
  border: 'none',
  position: 'relative',
  overflow: 'hidden',
  animation: `${pulse} 2s ease-in-out infinite`,
  '&::before': {
    content: '""',
    position: 'absolute',
    top: '-2px',
    left: '-2px',
    right: '-2px',
    bottom: '-2px',
    background: ACCENT_GRADIENT,
    borderRadius: 'inherit',
    opacity: conviction === 'high' ? 1 : 0.5,
    zIndex: -1,
    animation: `${rotate} 3s linear infinite`,
  },
}));

interface FancyStrategyPanelProps {
  data: FancyData;
  rawData?: any;
}

const FancyStrategyPanel: React.FC<FancyStrategyPanelProps> = ({ data, rawData }) => {
  const isEmpty = !data || Object.keys(data).length === 0;
  if (isEmpty) {
    return (
      <StyledPaper elevation={0} sx={{ width: '100%', maxWidth: 1200, mx: 'auto', p: { xs: 3, md: 5 }, borderRadius: 4 }}>
        <Typography variant="h5" sx={{ color: '#ffc300', fontWeight: 700, mb: 2 }}>
          No investment strategy data available
        </Typography>
        <Typography variant="body1" sx={{ color: '#aaa' }}>
          The backend did not provide investment strategy for this ticker. Please try again later or rerun the analysis.
        </Typography>
      </StyledPaper>
    );
  }

  const getStepIcon = (index: number) => {
    const icons = [
      <AutoGraphIcon sx={{ color: ACCENT_CYAN }} />,
      <SecurityIcon sx={{ color: ACCENT_PURPLE }} />,
      <TargetIcon sx={{ color: ACCENT_RED }} />,
    ];
    return icons[index] || null;
  };

  return (
    <StyledPaper
      elevation={0}
      sx={{
        width: '100%',
        maxWidth: 1200,
        mx: 'auto',
        p: { xs: 3, md: 5 },
        borderRadius: 4,
      }}
    >
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <motion.div
          animate={{ 
            rotate: [0, 360],
            scale: [1, 1.1, 1],
          }}
          transition={{ 
            duration: 4,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        >
          <AutoGraphIcon sx={{ fontSize: 36, color: ACCENT_PURPLE }} />
        </motion.div>
        <Box>
          <Typography variant="h4" sx={{ 
            fontWeight: 700, 
            background: ACCENT_GRADIENT,
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            Investment AI
          </Typography>
          <Typography variant="subtitle2" sx={{ color: ACCENT_CYAN, fontWeight: 400, mt: 0.5 }}>
            This AI will show integrated investment thesis
          </Typography>
        </Box>
      </Box>

      {/* Investment Mindmap */}
      {rawData?.investment_mindmap && (
        <Box
          sx={{
            mb: 4,
            p: 3,
            background: 'linear-gradient(135deg, rgba(0,255,255,0.05), rgba(168,85,247,0.05))',
            border: '1px solid rgba(0,255,255,0.2)',
            borderRadius: 3,
            position: 'relative',
          }}
        >
          <Typography variant="h6" sx={{ color: ACCENT_CYAN, mb: 2, fontWeight: 600 }}>
            🧠 Strategic Overview
          </Typography>
          <Typography sx={{ color: TEXT_PRIMARY, whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
            {rawData.investment_mindmap}
          </Typography>
          <LinearProgress
            sx={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: 2,
              backgroundColor: 'transparent',
              '& .MuiLinearProgress-bar': {
                background: ACCENT_GRADIENT,
              },
            }}
            variant="indeterminate"
          />
        </Box>
      )}

      {/* Strategy Steps */}
      <StyledStepper alternativeLabel sx={{ mb: 5 }}>
        {data.steps.map(({ label, note }, idx) => (
          <Step key={idx} completed={idx < data.steps.length - 1}>
            <Tooltip title={note || ''} arrow placement="top">
              <StepLabel
                StepIconComponent={() => (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: idx * 0.2 }}
                  >
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: '50%',
                        background: idx === 0 ? 'rgba(0,255,255,0.2)' 
                                  : idx === data.steps.length - 1 ? 'rgba(239,68,68,0.2)'
                                  : 'rgba(168,85,247,0.2)',
                        border: '2px solid',
                        borderColor: idx === 0 ? ACCENT_CYAN 
                                   : idx === data.steps.length - 1 ? ACCENT_RED
                                   : ACCENT_PURPLE,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        animation: `${pulse} 2s ease-in-out infinite`,
                        animationDelay: `${idx * 0.3}s`,
                      }}
                    >
                      {getStepIcon(idx)}
                    </Box>
                  </motion.div>
                )}
              >
                <Typography variant="body1" sx={{ color: TEXT_PRIMARY, fontWeight: 600, mt: 1 }}>
                  {label}
                </Typography>
                {note && (
                  <Typography variant="caption" sx={{ color: TEXT_SECONDARY, display: 'block' }}>
                    {note}
                  </Typography>
                )}
              </StepLabel>
            </Tooltip>
          </Step>
        ))}
      </StyledStepper>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)', my: 4 }} />

      {/* Metrics Grid */}
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} justifyContent="space-between">
        {/* Risk Level */}
        <MetricCard sx={{ flex: 1 }}>
          <Stack spacing={2} alignItems="center">
            <Typography variant="subtitle1" sx={{ color: TEXT_SECONDARY, fontWeight: 600 }}>
              Risk Assessment
            </Typography>
            <Box sx={{ width: '100%', maxWidth: 200 }}>
              <AnimatePresence>
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.5 }}
                >
                  <GaugeChart
                    id="risk-gauge"
                    nrOfLevels={30}
                    colors={['#10b981', '#eab308', '#ef4444']}
                    percent={data.riskScore}
                    arcPadding={0.02}
                    animate={true}
                    animDelay={500}
                    textColor={TEXT_PRIMARY}
                    needleColor="#90A4AE"
                    needleBaseColor="#90A4AE"
                  />
                </motion.div>
              </AnimatePresence>
            </Box>
            <Chip
              label={data.riskScore <= 0.33 ? 'LOW RISK' : data.riskScore <= 0.66 ? 'MEDIUM RISK' : 'HIGH RISK'}
              sx={{
                background: data.riskScore <= 0.33 ? 'rgba(16,185,129,0.2)' 
                          : data.riskScore <= 0.66 ? 'rgba(234,179,8,0.2)' 
                          : 'rgba(239,68,68,0.2)',
                color: data.riskScore <= 0.33 ? ACCENT_GREEN 
                     : data.riskScore <= 0.66 ? ACCENT_YELLOW 
                     : ACCENT_RED,
                border: '1px solid',
                borderColor: 'currentColor',
                fontWeight: 600,
              }}
            />
          </Stack>
        </MetricCard>

        {/* Risk/Reward */}
        <MetricCard sx={{ flex: 1 }}>
          <Stack spacing={2} alignItems="center">
            <Typography variant="subtitle1" sx={{ color: TEXT_SECONDARY, fontWeight: 600 }}>
              Risk / Reward Ratio
            </Typography>
            <Box
              sx={{
                width: 120,
                height: 120,
                borderRadius: '50%',
                background: 'rgba(0,255,255,0.1)',
                border: '3px solid',
                borderColor: data.rrRatio >= 2 ? ACCENT_GREEN : ACCENT_YELLOW,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
                animation: `${glow} 3s ease-in-out infinite`,
              }}
            >
              <Typography
                sx={{
                  fontSize: 36,
                  fontFamily: 'monospace',
                  fontWeight: 700,
                  color: data.rrRatio >= 2 ? ACCENT_GREEN : ACCENT_YELLOW,
                }}
              >
                {data.rrRatio.toFixed(2)}
              </Typography>
              <Box
                sx={{
                  position: 'absolute',
                  top: -10,
                  right: -10,
                  width: 30,
                  height: 30,
                  borderRadius: '50%',
                  background: data.rrRatio >= 2 ? ACCENT_GREEN : ACCENT_YELLOW,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <SignalCellularAltIcon sx={{ color: '#000', fontSize: 16 }} />
              </Box>
            </Box>
            <Typography variant="caption" sx={{ color: TEXT_SECONDARY }}>
              {data.rrRatio >= 2 ? 'Favorable' : 'Moderate'} Risk/Reward
            </Typography>
          </Stack>
        </MetricCard>

        {/* Targets */}
        <MetricCard sx={{ flex: 1 }}>
          <Stack spacing={2} alignItems="center">
            <Typography variant="subtitle1" sx={{ color: TEXT_SECONDARY, fontWeight: 600 }}>
              Price Targets
            </Typography>
            <Stack spacing={2} sx={{ width: '100%' }}>
              <motion.div
                whileHover={{ scale: 1.05 }}
                transition={{ type: 'spring', stiffness: 300 }}
              >
                <Box
                  sx={{
                    p: 2,
                    background: 'rgba(16,185,129,0.1)',
                    border: '1px solid',
                    borderColor: ACCENT_GREEN,
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <TrendingUpIcon sx={{ color: ACCENT_GREEN }} />
                    <Typography sx={{ color: TEXT_PRIMARY, fontWeight: 600 }}>
                      Take Profit
                    </Typography>
                  </Stack>
                  <Typography sx={{ color: ACCENT_GREEN, fontWeight: 700, fontSize: '1.2rem' }}>
                    +{data.pnlTarget}%
                  </Typography>
                </Box>
              </motion.div>
              
              <motion.div
                whileHover={{ scale: 1.05 }}
                transition={{ type: 'spring', stiffness: 300 }}
              >
                <Box
                  sx={{
                    p: 2,
                    background: 'rgba(239,68,68,0.1)',
                    border: '1px solid',
                    borderColor: ACCENT_RED,
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <TrendingDownIcon sx={{ color: ACCENT_RED }} />
                    <Typography sx={{ color: TEXT_PRIMARY, fontWeight: 600 }}>
                      Stop Loss
                    </Typography>
                  </Stack>
                  <Typography sx={{ color: ACCENT_RED, fontWeight: 700, fontSize: '1.2rem' }}>
                    -{data.stopLoss}%
                  </Typography>
                </Box>
              </motion.div>
            </Stack>
          </Stack>
        </MetricCard>
      </Stack>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)', my: 4 }} />

      {/* Conviction Level */}
      <Stack direction="row" justifyContent="center">
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ 
            type: 'spring',
            stiffness: 260,
            damping: 20,
            delay: 0.5,
          }}
        >
          <ConvictionChip
            icon={<FlagIcon />}
            label={`${data.conviction.toUpperCase()} CONVICTION`}
            conviction={data.conviction}
          />
        </motion.div>
      </Stack>

      {/* Strategy Type & Recommendation */}
      {rawData && (
        <Stack spacing={2} sx={{ mt: 4, textAlign: 'center' }}>
          {rawData.strategy_type && (
            <Typography variant="h6" sx={{ color: TEXT_PRIMARY }}>
              Strategy: <span style={{ color: ACCENT_CYAN }}>{rawData.strategy_type}</span>
            </Typography>
          )}
          {rawData.recommended_action && (
            <Chip
              label={`Action: ${rawData.recommended_action}`}
              sx={{
                background: rawData.recommended_action === 'BUY' ? 'rgba(16,185,129,0.2)'
                          : rawData.recommended_action === 'SELL' ? 'rgba(239,68,68,0.2)'
                          : 'rgba(234,179,8,0.2)',
                color: rawData.recommended_action === 'BUY' ? ACCENT_GREEN
                     : rawData.recommended_action === 'SELL' ? ACCENT_RED
                     : ACCENT_YELLOW,
                border: '1px solid currentColor',
                fontWeight: 700,
                fontSize: '1rem',
                py: 3,
                px: 4,
              }}
            />
          )}
        </Stack>
      )}
    </StyledPaper>
  );
};

export default FancyStrategyPanel;