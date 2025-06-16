import React, { useState, useEffect } from 'react';
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
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import { keyframes, styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import InfoIcon from '@mui/icons-material/Info';

// Enhanced dark theme
const PANEL_BG = 'rgba(18,18,18,0.95)';
const CARD_BG = 'rgba(30,30,30,0.9)';
const TEXT_PRIMARY = '#E0E0E0';
const TEXT_SECONDARY = '#90A4AE';
const ACCENT_CYAN = '#00ffff';
const ACCENT_PURPLE = '#a855f7';
const ACCENT_GREEN = '#10b981';
const ACCENT_RED = '#ef4444';
const ACCENT_GRADIENT = 'linear-gradient(135deg, #00ffff, #a855f7)';

// Animations
const pulse = keyframes`
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
`;

const shine = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

const glow = keyframes`
  0% { box-shadow: 0 0 5px rgba(0,255,255,0.5); }
  50% { box-shadow: 0 0 20px rgba(0,255,255,0.8), 0 0 30px rgba(168,85,247,0.6); }
  100% { box-shadow: 0 0 5px rgba(0,255,255,0.5); }
`;

// Styled components
const StyledPaper = styled(Paper)({
  background: PANEL_BG,
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(0,255,255,0.2)',
  position: 'relative',
  overflow: 'hidden',
});

const ChartContainer = styled(Box)({
  position: 'relative',
  background: CARD_BG,
  borderRadius: 12,
  overflow: 'hidden',
  border: '1px solid rgba(0,255,255,0.2)',
  '&:hover .zoom-overlay': {
    opacity: 1,
  },
});

const TabButton = styled(Button)<{ active?: boolean }>(({ active }) => ({
  borderRadius: 25,
  padding: '8px 24px',
  textTransform: 'none',
  fontWeight: 600,
  color: active ? '#000' : TEXT_PRIMARY,
  background: active ? ACCENT_GRADIENT : 'transparent',
  backgroundSize: '200% 100%',
  border: active ? 'none' : '1px solid rgba(255,255,255,0.2)',
  position: 'relative',
  overflow: 'hidden',
  transition: 'all 0.3s ease',
  ...(active && {
    animation: `${shine} 3s linear infinite`,
  }),
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: active 
      ? '0 8px 25px rgba(0,255,255,0.4)' 
      : '0 4px 15px rgba(255,255,255,0.1)',
    borderColor: active ? 'transparent' : ACCENT_CYAN,
  },
}));

const DetailCard = styled(Box)<{ variant?: 'long' | 'short' }>(({ variant }) => ({
  flex: 1,
  padding: 20,
  background: variant === 'long' 
    ? 'linear-gradient(135deg, rgba(16,185,129,0.1), rgba(16,185,129,0.05))' 
    : 'linear-gradient(135deg, rgba(239,68,68,0.1), rgba(239,68,68,0.05))',
  border: `1px solid ${variant === 'long' ? ACCENT_GREEN : ACCENT_RED}`,
  borderRadius: 12,
  position: 'relative',
  overflow: 'hidden',
  transition: 'all 0.3s ease',
  '&:hover': {
    transform: 'translateY(-5px)',
    boxShadow: `0 10px 30px ${variant === 'long' 
      ? 'rgba(16,185,129,0.3)' 
      : 'rgba(239,68,68,0.3)'}`,
  },
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 3,
    background: variant === 'long' ? ACCENT_GREEN : ACCENT_RED,
  },
}));

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
    analysis?: {
      summary?: string;
    };
  };
};

function parseLines(text?: string): string[] {
  if (!text) return [];
  return text
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(line => line && !/^=+$/g.test(line));
}

// Helper function to get the correct relative path for static server
function getStaticPath(fullPath: string): string {
  // Extract just the TICKER_Graph/filename.png part
  const parts = fullPath.split('/');
  const graphIndex = parts.findIndex(p => p === 'Graph');
  if (graphIndex !== -1 && graphIndex < parts.length - 1) {
    return parts.slice(graphIndex + 1).join('/');
  }
  return fullPath;
}

export default function PricePanel({ data }: PricePanelProps) {
  const keys = (Object.keys(nameMap) as ChartKey[]).filter(k => data.graph_paths?.[k]);
  const [selected, setSelected] = useState<ChartKey>(keys[0]);
  const [imageError, setImageError] = useState(false);

  const imgUrl = data.graph_paths?.[selected]
    ? `${GRAPHS_BASE}/${getStaticPath(data.graph_paths[selected])}`
    : '';

  // DEBUG LOGGING BLOCK
  useEffect(() => {
    console.log('DEBUG: imgUrl for price chart:', imgUrl);
    console.log('DEBUG: selected chart key:', selected);
    console.log('DEBUG: data.graph_paths:', data.graph_paths);
    setTimeout(() => {
      const img = document.querySelector('img[alt]');
      if (img) {
        console.log('DEBUG: <img> src attribute:', img.getAttribute('src'));
      } else {
        console.log('DEBUG: <img> element not found');
      }
    }, 1000);
  }, [imgUrl, selected, data.graph_paths]);

  const riskLines = parseLines(data.risk_reward_summary);
  const smaLines = parseLines(data.sma_crossovers_summary);
  const emaLines = parseLines(data.ema_crossovers_summary);
  const macdLines = parseLines(data.vw_macd_summary);

  const longLine = riskLines.find(l => /^Long Position:/i.test(l)) || '';
  const shortLine = riskLines.find(l => /^Short Position:/i.test(l)) || '';

  const summaryMap: Record<ChartKey, string[]> = {
    risk_reward: riskLines,
    sma_crossovers: smaLines,
    ema_crossovers: emaLines,
    vw_macd: macdLines,
  };

  const getChartIcon = (key: ChartKey) => {
    switch (key) {
      case 'risk_reward':
        return '📊';
      case 'sma_crossovers':
        return '📈';
      case 'ema_crossovers':
        return '📉';
      case 'vw_macd':
        return '📊';
      default:
        return '📈';
    }
  };

  return (
    <StyledPaper
      elevation={0}
      sx={{ p: { xs: 3, md: 4 }, borderRadius: 3 }}
    >
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <ShowChartIcon sx={{ fontSize: 36, color: ACCENT_CYAN }} />
        <Box>
          <Typography variant="h4" sx={{
            fontWeight: 700,
            background: ACCENT_GRADIENT,
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            Price AI
          </Typography>
          <Typography variant="subtitle2" sx={{ color: ACCENT_CYAN, fontWeight: 400, mt: 0.5 }}>
            This AI will show some tech index win-rate on this ticker
          </Typography>
        </Box>
      </Box>

      {/* Chart Section */}
      <Stack spacing={3} alignItems="center">
        {/* Chart Image */}
        <ChartContainer sx={{ width: '100%' }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={selected}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              style={{ width: '100%' }}
            >
              {imgUrl && !imageError ? (
                <Box
                  component="img"
                  src={imgUrl}
                  alt={nameMap[selected]}
                  onError={() => setImageError(true)}
                  sx={{ 
                    width: '100%', 
                    aspectRatio: '16/9', 
                    objectFit: 'contain',
                    display: 'block',
                  }}
                />
              ) : (
                <Box
                  sx={{
                    width: '100%',
                    aspectRatio: '16/9',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'rgba(0,255,255,0.05)',
                  }}
                >
                  <Typography color="text.secondary">
                    Chart unavailable
                  </Typography>
                </Box>
              )}
            </motion.div>
          </AnimatePresence>
          
          {/* Zoom overlay */}
          <Box
            className="zoom-overlay"
            sx={{
              position: 'absolute',
              top: 16,
              right: 16,
              opacity: 0,
              transition: 'opacity 0.3s ease',
            }}
          >
            <Tooltip title="View full size">
              <IconButton
                sx={{
                  background: 'rgba(0,0,0,0.7)',
                  color: ACCENT_CYAN,
                  '&:hover': {
                    background: 'rgba(0,0,0,0.9)',
                  },
                }}
                onClick={() => window.open(imgUrl, '_blank')}
              >
                <ZoomInIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </ChartContainer>

        {/* Chart Tabs */}
        <Stack direction="row" spacing={2} flexWrap="wrap" justifyContent="center">
          {keys.map(key => (
            <motion.div
              key={key}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <TabButton
                onClick={() => {
                  setSelected(key);
                  setImageError(false);
                }}
                active={selected === key}
              >
                <span style={{ marginRight: 8 }}>{getChartIcon(key)}</span>
                {nameMap[key]}
              </TabButton>
            </motion.div>
          ))}
        </Stack>
      </Stack>

      <Divider sx={{ my: 4, borderColor: 'rgba(255,255,255,0.1)' }} />

      {/* Analysis Summary */}
      {data.analysis?.summary && (
        <Box
          sx={{
            mb: 4,
            p: 3,
            background: 'rgba(0,255,255,0.05)',
            border: '1px solid rgba(0,255,255,0.2)',
            borderRadius: 2,
            animation: `${glow} 3s ease-in-out infinite`,
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
            <InfoIcon sx={{ color: ACCENT_CYAN }} />
            <Typography variant="subtitle1" sx={{ color: ACCENT_CYAN, fontWeight: 600 }}>
              Summary Analysis
            </Typography>
          </Stack>
          <Typography sx={{ color: TEXT_PRIMARY }}>
            {data.analysis.summary}
          </Typography>
        </Box>
      )}

      {/* Chart Details */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" sx={{ color: TEXT_PRIMARY, mb: 2, fontWeight: 600 }}>
          {nameMap[selected]} Details
        </Typography>
        <List dense>
          {summaryMap[selected].map((line, idx) => {
            const isImportant = /^(Long|Short|Entry|Exit|Signal|Target)/i.test(line);
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <ListItem sx={{ 
                  pl: 0,
                  py: 1,
                  borderLeft: isImportant ? `3px solid ${ACCENT_PURPLE}` : 'none',
                  paddingLeft: isImportant ? 2 : 0,
                }}>
                  <ListItemText
                    primary={
                      <Typography
                        variant="body2"
                        sx={{ 
                          color: isImportant ? TEXT_PRIMARY : TEXT_SECONDARY, 
                          fontWeight: isImportant ? 600 : 400,
                          fontSize: isImportant ? '0.95rem' : '0.875rem',
                        }}
                      >
                        {line}
                      </Typography>
                    }
                  />
                </ListItem>
              </motion.div>
            );
          })}
        </List>
      </Box>

      {/* Long/Short Position Cards (for risk_reward) */}
      {selected === 'risk_reward' && (longLine || shortLine) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} mt={3}>
            {longLine && (
              <DetailCard variant="long">
                <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
                  <motion.div
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <TrendingUpIcon sx={{ color: ACCENT_GREEN, fontSize: 28 }} />
                  </motion.div>
                  <Typography variant="h6" sx={{ color: ACCENT_GREEN, fontWeight: 700 }}>
                    LONG Position
                  </Typography>
                  <Chip
                    label="BULLISH"
                    size="small"
                    sx={{
                      background: 'rgba(16,185,129,0.2)',
                      color: ACCENT_GREEN,
                      border: '1px solid',
                      borderColor: ACCENT_GREEN,
                      fontWeight: 600,
                      animation: `${pulse} 2s ease-in-out infinite`,
                    }}
                  />
                </Stack>
                <Typography sx={{ color: TEXT_PRIMARY, lineHeight: 1.6 }}>
                  {longLine.replace(/^Long Position:\s*/i, '')}
                </Typography>
              </DetailCard>
            )}
            
            {shortLine && (
              <DetailCard variant="short">
                <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
                  <motion.div
                    animate={{ y: [0, 5, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <TrendingDownIcon sx={{ color: ACCENT_RED, fontSize: 28 }} />
                  </motion.div>
                  <Typography variant="h6" sx={{ color: ACCENT_RED, fontWeight: 700 }}>
                    SHORT Position
                  </Typography>
                  <Chip
                    label="BEARISH"
                    size="small"
                    sx={{
                      background: 'rgba(239,68,68,0.2)',
                      color: ACCENT_RED,
                      border: '1px solid',
                      borderColor: ACCENT_RED,
                      fontWeight: 600,
                      animation: `${pulse} 2s ease-in-out infinite`,
                    }}
                  />
                </Stack>
                <Typography sx={{ color: TEXT_PRIMARY, lineHeight: 1.6 }}>
                  {shortLine.replace(/^Short Position:\s*/i, '')}
                </Typography>
              </DetailCard>
            )}
          </Stack>
        </motion.div>
      )}
    </StyledPaper>
  );
}