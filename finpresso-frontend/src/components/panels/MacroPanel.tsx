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
  LinearProgress,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import BoltIcon from '@mui/icons-material/Bolt';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import BalanceIcon from '@mui/icons-material/Balance';
import { keyframes, styled } from '@mui/material/styles';
import { motion } from 'framer-motion';

// Enhanced dark theme with neon accents
const DARK_BG = '#0a0a0a';
const PANEL_BG = 'rgba(18,18,18,0.95)';
const ACCORDION_BG = 'rgba(30,30,30,0.9)';
const TEXT_PRIMARY = '#E0E0E0';
const TEXT_SECONDARY = '#90A4AE';
const ACCENT_CYAN = '#00ffff';
const ACCENT_PURPLE = '#a855f7';
const ACCENT_GRADIENT = 'linear-gradient(135deg, #00ffff, #a855f7)';
const CHIP_BG = 'rgba(0,255,255,0.1)';

// Animations
const glow = keyframes`
  0% { box-shadow: 0 0 5px rgba(0,255,255,0.3); }
  50% { box-shadow: 0 0 20px rgba(0,255,255,0.6), 0 0 30px rgba(168,85,247,0.4); }
  100% { box-shadow: 0 0 5px rgba(0,255,255,0.3); }
`;

const pulse = keyframes`
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
`;

const slideIn = keyframes`
  from { transform: translateX(-20px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
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
    height: '2px',
    background: ACCENT_GRADIENT,
    animation: `${pulse} 3s ease-in-out infinite`,
  },
});

const NeonAlert = styled(Alert)({
  background: 'rgba(0,255,255,0.05)',
  borderLeft: `4px solid ${ACCENT_CYAN}`,
  backdropFilter: 'blur(10px)',
  '& .MuiAlert-message': {
    color: TEXT_PRIMARY,
    fontWeight: 500,
  },
  animation: `${slideIn} 0.5s ease-out`,
});

const StyledAccordion = styled(Accordion)({
  background: ACCORDION_BG,
  color: TEXT_PRIMARY,
  border: '1px solid rgba(0,255,255,0.1)',
  marginBottom: '1rem',
  '&:hover': {
    borderColor: 'rgba(0,255,255,0.3)',
    animation: `${glow} 2s ease-in-out infinite`,
  },
  '&.Mui-expanded': {
    borderColor: ACCENT_CYAN,
  },
});

const IndicatorChip = styled(Chip)<{ trend?: 'up' | 'down' | 'neutral' }>(({ trend }) => ({
  background: trend === 'up' ? 'rgba(16,185,129,0.2)' : 
              trend === 'down' ? 'rgba(239,68,68,0.2)' : 
              'rgba(0,255,255,0.1)',
  color: trend === 'up' ? '#10b981' : 
         trend === 'down' ? '#ef4444' : 
         ACCENT_CYAN,
  border: `1px solid ${trend === 'up' ? '#10b981' : 
                       trend === 'down' ? '#ef4444' : 
                       ACCENT_CYAN}`,
  fontWeight: 600,
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: `0 5px 15px ${trend === 'up' ? 'rgba(16,185,129,0.4)' : 
                             trend === 'down' ? 'rgba(239,68,68,0.4)' : 
                             'rgba(0,255,255,0.4)'}`,
  },
  transition: 'all 0.3s ease',
}));

interface MacroPanelProps {
  data: {
    summary?: string;
    sentiment?: string;
    trend?: string;
    key_indicators?: Record<string, any>;
    macro_catalysts?: string[];
    next_inference_hint?: string;
  };
}

const MacroPanel: React.FC<MacroPanelProps> = ({ data }) => {
  // Determine sentiment icon and color
  const getSentimentIcon = () => {
    const sentiment = data.sentiment?.toLowerCase() || '';
    if (sentiment.includes('bullish') || sentiment.includes('positive')) 
      return <TrendingUpIcon sx={{ color: '#10b981' }} />;
    if (sentiment.includes('bearish') || sentiment.includes('negative')) 
      return <TrendingDownIcon sx={{ color: '#ef4444' }} />;
    return <BalanceIcon sx={{ color: ACCENT_CYAN }} />;
  };

  const getTrend = (key: string, value: any): 'up' | 'down' | 'neutral' => {
    const val = String(value).toLowerCase();
    if (val.includes('increase') || val.includes('growth') || val.includes('positive')) return 'up';
    if (val.includes('decrease') || val.includes('decline') || val.includes('negative')) return 'down';
    return 'neutral';
  };

  return (
    <StyledPaper
      elevation={0}
      sx={{
        maxWidth: 960,
        mx: 'auto',
        p: { xs: 3, md: 5 },
        borderRadius: 3,
      }}
    >
      {/* Header with sentiment */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <motion.div
          initial={{ rotate: 0 }}
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        >
          {getSentimentIcon()}
        </motion.div>
        <Typography variant="h4" sx={{ 
          fontWeight: 700, 
          background: ACCENT_GRADIENT,
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          Macro Analysis
        </Typography>
      </Box>

      {/* Summary Alert */}
      <NeonAlert
        icon={false}
        severity="info"
        sx={{ mb: 4 }}
      >
        <Typography variant="body1">
          {data.summary || 'No summary available'}
        </Typography>
      </NeonAlert>

      {/* Market Sentiment & Trend */}
      {(data.sentiment || data.trend) && (
        <Stack direction="row" spacing={2} sx={{ mb: 4 }}>
          {data.sentiment && (
            <Chip
              icon={getSentimentIcon()}
              label={`Sentiment: ${data.sentiment}`}
              sx={{
                background: 'rgba(0,255,255,0.1)',
                border: '1px solid rgba(0,255,255,0.3)',
                color: TEXT_PRIMARY,
                fontWeight: 600,
                px: 2,
                py: 1,
              }}
            />
          )}
          {data.trend && (
            <Chip
              label={`Trend: ${data.trend}`}
              sx={{
                background: 'rgba(168,85,247,0.1)',
                border: '1px solid rgba(168,85,247,0.3)',
                color: TEXT_PRIMARY,
                fontWeight: 600,
                px: 2,
                py: 1,
              }}
            />
          )}
        </Stack>
      )}

      {/* Key Indicators */}
      <StyledAccordion defaultExpanded>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon sx={{ color: ACCENT_CYAN }} />}
          sx={{
            '& .MuiAccordionSummary-content': {
              alignItems: 'center',
              gap: 2,
            },
          }}
        >
          <BoltIcon sx={{ color: ACCENT_CYAN }} />
          <Typography variant="h6" fontWeight={600}>
            Key Economic Indicators
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List dense disablePadding>
            {Object.entries(data.key_indicators || {}).map(([k, v], index) => (
              <motion.div
                key={k}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <ListItem sx={{ 
                  py: 1.5, 
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  '&:hover': {
                    background: 'rgba(0,255,255,0.05)',
                  },
                  transition: 'background 0.3s ease',
                }}>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <Box
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: ACCENT_GRADIENT,
                        boxShadow: `0 0 10px ${ACCENT_CYAN}`,
                      }}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Typography variant="body2" sx={{ color: TEXT_SECONDARY, fontWeight: 600 }}>
                        {k.replace(/_/g, ' ').toUpperCase()}
                      </Typography>
                    }
                    secondary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                        <Typography
                          component="span"
                          sx={{
                            fontFamily: 'monospace',
                            fontWeight: 700,
                            color: TEXT_PRIMARY,
                            fontSize: '1.1rem',
                          }}
                        >
                          {String(v)}
                        </Typography>
                        <IndicatorChip
                          size="small"
                          trend={getTrend(k, v)}
                          label={getTrend(k, v).toUpperCase()}
                        />
                      </Box>
                    }
                  />
                </ListItem>
              </motion.div>
            ))}
          </List>
        </AccordionDetails>
      </StyledAccordion>

      {/* Catalysts */}
      <StyledAccordion>
        <AccordionSummary 
          expandIcon={<ExpandMoreIcon sx={{ color: ACCENT_PURPLE }} />}
          sx={{
            '& .MuiAccordionSummary-content': {
              alignItems: 'center',
              gap: 2,
            },
          }}
        >
          <BoltIcon sx={{ color: ACCENT_PURPLE }} />
          <Typography variant="h6" fontWeight={600}>
            Upcoming Catalysts
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={1.5}>
            {(data.macro_catalysts || []).map((catalyst, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.1 }}
              >
                <Box
                  sx={{
                    p: 2,
                    background: 'rgba(168,85,247,0.05)',
                    border: '1px solid rgba(168,85,247,0.2)',
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    '&:hover': {
                      borderColor: ACCENT_PURPLE,
                      background: 'rgba(168,85,247,0.1)',
                      transform: 'translateX(5px)',
                    },
                    transition: 'all 0.3s ease',
                  }}
                >
                  <Box
                    sx={{
                      width: 4,
                      height: 40,
                      background: ACCENT_GRADIENT,
                      borderRadius: 2,
                    }}
                  />
                  <Typography sx={{ color: TEXT_PRIMARY, fontWeight: 500 }}>
                    {catalyst}
                  </Typography>
                </Box>
              </motion.div>
            ))}
          </Stack>
        </AccordionDetails>
      </StyledAccordion>

      {/* Next Inference Hint */}
      {data.next_inference_hint && (
        <Box
          sx={{
            mt: 4,
            p: 3,
            background: 'linear-gradient(135deg, rgba(0,255,255,0.05), rgba(168,85,247,0.05))',
            border: '1px solid rgba(0,255,255,0.2)',
            borderRadius: 2,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <Typography variant="subtitle2" sx={{ color: ACCENT_CYAN, fontWeight: 600, mb: 1 }}>
            🔮 Next Inference
          </Typography>
          <Typography sx={{ color: TEXT_PRIMARY }}>
            {data.next_inference_hint}
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
    </StyledPaper>
  );
};

export default MacroPanel;