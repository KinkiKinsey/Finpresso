// src/pages/DetailPage.tsx
import React, { useState, useEffect } from 'react';
import {
  Box,
  Stack,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Paper,
  Button,
  LinearProgress,
  Chip,
  Tooltip,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HomeIcon from '@mui/icons-material/Home';
import SchemaIcon from '@mui/icons-material/Schema';
import LockIcon from '@mui/icons-material/Lock';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import BlockIcon from '@mui/icons-material/Block';
import { keyframes, styled } from '@mui/material/styles';
import { motion, AnimatePresence } from 'framer-motion';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import axios from '../utils/axiosConfig';
import { meta, PanelKey } from './App';

// Panel components
import MacroPanel from '../components/panels/MacroPanel';
import MicroPanel from '../components/panels/MicroPanel';
import PricePanel from '../components/panels/PricePanel';
import FancyStrategyPanel, { toFancy } from '../components/panels/FancyStrategyPanel';

// ---- API response type -------------------------------------------------------
interface StatusResp {
  job_id: string;
  state: 'pending' | 'running' | 'finished' | 'error';
  message?: string;
  panel_progress: Record<PanelKey, number>;
  panel_data: Record<PanelKey, any>;
  new_logs: string[];
  next_cursor: number;
}

// ---- Animations ----
const glow = keyframes`
  0% { box-shadow: 0 0 5px rgba(0,255,255,0.5); }
  50% { box-shadow: 0 0 25px rgba(0,255,255,0.8), 0 0 35px rgba(168,85,247,0.6); }
  100% { box-shadow: 0 0 5px rgba(0,255,255,0.5); }
`;

const pulse = keyframes`
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
`;

const shimmer = keyframes`
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
`;

const lockedPulse = keyframes`
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.1); }
`;

// ---- Styled Components ----
const StyledBox = styled(Box)({
  position: 'relative',
  background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundImage: `
      linear-gradient(rgba(0,255,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,255,255,0.03) 1px, transparent 1px)
    `,
    backgroundSize: '50px 50px',
    pointerEvents: 'none',
  },
});

const NavButton = styled(IconButton)({
  background: 'rgba(255,255,255,0.05)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(0,255,255,0.2)',
  color: '#00ffff',
  transition: 'all 0.3s ease',
  '&:hover': {
    background: 'rgba(0,255,255,0.1)',
    borderColor: '#00ffff',
    transform: 'translateY(-2px)',
    boxShadow: '0 5px 20px rgba(0,255,255,0.4)',
  },
});

const MindMapButton = styled(Button)<{ isReady: boolean }>(({ isReady }) => ({
  position: 'relative',
  padding: '10px 24px',
  fontWeight: 700,
  background: isReady 
    ? 'linear-gradient(135deg, #00e5ff 0%, #3b82f6 45%, #8b5cf6 100%)'
    : 'linear-gradient(135deg, #333 0%, #444 50%, #333 100%)',
  color: isReady ? '#fff' : '#888',
  textTransform: 'none',
  border: `1px solid ${isReady ? 'transparent' : 'rgba(255,255,255,0.1)'}`,
  overflow: 'hidden',
  transition: 'all 0.3s ease',
  ...(isReady && {
    animation: `${glow} 3s ease-in-out infinite`,
    '&::before': {
      content: '""',
      position: 'absolute',
      top: 0,
      left: '-100%',
      width: '100%',
      height: '100%',
      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
      animation: `${shimmer} 2s infinite`,
    },
  }),
  '&:hover': isReady ? {
    transform: 'translateY(-3px)',
    boxShadow: '0 10px 30px rgba(0,229,255,0.6)',
  } : {
    background: 'linear-gradient(135deg, #444 0%, #555 50%, #444 100%)',
  },
  '&:disabled': {
    background: 'linear-gradient(135deg, #333 0%, #444 50%, #333 100%)',
    color: '#666',
  },
}));

const StyledTabs = styled(Tabs)({
  background: 'rgba(30,30,30,0.6)',
  backdropFilter: 'blur(10px)',
  borderRadius: 12,
  padding: 4,
  '& .MuiTabs-indicator': {
    height: 3,
    borderRadius: 2,
    background: 'linear-gradient(90deg, #00e5ff, #8b5cf6)',
  },
  '& .MuiTab-root': {
    fontWeight: 600,
    textTransform: 'none',
    color: '#888',
    minHeight: 48,
    borderRadius: 8,
    margin: '0 4px',
    transition: 'all 0.3s ease',
    position: 'relative',
    '&:hover': {
      color: '#aaa',
      background: 'rgba(255,255,255,0.05)',
    },
    '&.Mui-disabled': {
      color: '#555',
      opacity: 0.7,
      cursor: 'not-allowed',
      '&:hover': {
        background: 'transparent',
      },
    },
  },
  '& .Mui-selected': {
    color: '#00e5ff !important',
    background: 'rgba(0,229,255,0.1)',
  },
});

const ContentPaper = styled(Paper)({
  background: 'rgba(30,30,30,0.85)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(0,255,255,0.15)',
  position: 'relative',
  overflow: 'hidden',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 2,
    background: 'linear-gradient(90deg, #00e5ff, #8b5cf6)',
    animation: `${pulse} 3s ease-in-out infinite`,
  },
});

const TabIcon = styled(Box)<{ active: boolean }>(({ active }) => ({
  width: 8,
  height: 8,
  borderRadius: '50%',
  background: active ? '#00e5ff' : 'rgba(255,255,255,0.3)',
  marginRight: 8,
  display: 'inline-block',
  animation: active ? `${pulse} 2s ease-in-out infinite` : 'none',
}));

const DetailPage: React.FC = () => {
  const { id = '', panel = 'macro' } = useParams<{ id: string; panel: PanelKey }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { state } = location as { state?: { ticker?: string } };
  const ticker = state?.ticker;
  const [cur, setCur] = useState<PanelKey>(panel as PanelKey);

  // sync tab when URL changes
  useEffect(() => {
    setCur(panel as PanelKey);
  }, [panel]);

  // poll /status for panel data
  const { data: statusData } = useQuery<StatusResp>(
    ['status', id],
    () => axios.get<StatusResp>(`/api/v1/analysis/${id}/status`).then(r => r.data),
    { refetchInterval: 1500 }
  );

  const panelData = statusData?.panel_data?.[cur] ?? {};
  const panelProgress = statusData?.panel_progress ?? {} as Record<PanelKey, number>;
  const jobState = statusData?.state;
  
  // Check if strategy panel is ready (for mindmap)
  const isStrategyReady = (panelProgress.strategy ?? 0) >= 100 || jobState === 'finished';
  const isCurrentPanelReady = (panelProgress[cur] ?? 0) >= 100;

  const renderPanel = () => {
    switch (cur) {
      case 'macro':
        return <MacroPanel data={panelData} />;
      case 'micro':
        return <MicroPanel data={panelData} />;
      case 'price':
        return <PricePanel data={panelData} />;
      case 'strategy':
        return <FancyStrategyPanel data={toFancy(panelData)} rawData={panelData} />;
      default:
        return null;
    }
  };

  const getTabStatus = (key: PanelKey) => {
    const progress = panelProgress[key] ?? 0;
    if (progress >= 100) return 'complete';
    if (progress > 0) return 'loading';
    return 'pending';
  };

  return (
    <StyledBox
      sx={{
        width: '100vw',
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        py: { xs: 4, md: 6 },
        boxSizing: 'border-box',
      }}
    >
      <Box
        sx={{
          flexGrow: 1,
          maxWidth: { xs: '100%', sm: '92vw', md: '86vw', xl: 1800 },
          px: { xs: 2, md: 4 },
          display: 'flex',
          flexDirection: 'column',
          gap: 3,
        }}
      >
        {/* -------- Enhanced Top Nav Bar -------- */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Stack direction="row" alignItems="center" spacing={2}>
            <Tooltip title="Back to Progress">
              <span>
                <NavButton onClick={() => navigate(`/analysis/progress/${id}`, { state: { ticker } })}>
                  <ArrowBackIcon />
                </NavButton>
              </span>
            </Tooltip>
            <Tooltip title="Home">
              <span>
                <NavButton onClick={() => navigate('/')}>
                  <HomeIcon />
                </NavButton>
              </span>
            </Tooltip>

            {/* Enhanced Mind Map button with status */}
            <Tooltip 
              title={
                isStrategyReady 
                  ? "View complete investment mindmap" 
                  : "Analysis in progress - mindmap will be available when complete"
              }
            >
              <span>
                <MindMapButton
                  variant="contained"
                  startIcon={
                    isStrategyReady ? <SchemaIcon /> : <LockIcon />
                  }
                  endIcon={
                    isStrategyReady ? (
                      <CheckCircleIcon sx={{ fontSize: 16, color: '#10b981' }} />
                    ) : (
                      <AccessTimeIcon sx={{ fontSize: 16, animation: `${float} 2s ease-in-out infinite` }} />
                    )
                  }
                  onClick={() => navigate(`/analysis/mindmap/${id}`)}
                  disabled={!isStrategyReady}
                  isReady={isStrategyReady}
                >
                  Mind Map
                </MindMapButton>
              </span>
            </Tooltip>

            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography 
                variant="h5" 
                fontWeight={700} 
                sx={{
                  background: 'linear-gradient(135deg, #00e5ff, #8b5cf6)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                {meta[cur].title}
              </Typography>
              
              {ticker && (
                <Chip
                  label={ticker}
                  size="small"
                  sx={{
                    background: 'rgba(0,255,255,0.1)',
                    border: '1px solid rgba(0,255,255,0.3)',
                    color: '#00e5ff',
                    fontWeight: 600,
                  }}
                />
              )}
              
              {!isCurrentPanelReady && (
                <Chip
                  icon={<AccessTimeIcon sx={{ fontSize: 16 }} />}
                  label="Loading..."
                  size="small"
                  sx={{
                    background: 'rgba(255,195,0,0.1)',
                    border: '1px solid rgba(255,195,0,0.3)',
                    color: '#ffc300',
                    fontWeight: 600,
                    animation: `${pulse} 2s ease-in-out infinite`,
                  }}
                />
              )}
            </Box>
          </Stack>
        </motion.div>

        {/* -------- Enhanced Tabs with Status Indicators and Disabled State -------- */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <StyledTabs
            value={cur}
            onChange={(_, v) => {
              // Only navigate if the target panel is ready
              const targetProgress = panelProgress[v as PanelKey] ?? 0;
              if (targetProgress >= 100) {
                navigate(`/analysis/detail/${id}/${v}`, { state: { ticker } });
              }
            }}
            variant="scrollable"
            scrollButtons="auto"
          >
            {(Object.keys(meta) as PanelKey[]).map(k => {
              const status = getTabStatus(k);
              const Icon = meta[k].Icon;
              const isDisabled = status !== 'complete' && k !== cur;
              const progress = panelProgress[k] ?? 0;
              
              return (
                <Tab 
                  key={k} 
                  value={k}
                  disabled={isDisabled}
                  label={
                    <Tooltip 
                      title={
                        isDisabled 
                          ? `${meta[k].title} analysis in progress (${progress}%)`
                          : status === 'complete'
                          ? `${meta[k].title} - Click to view`
                          : ''
                      }
                    >
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <Box sx={{ position: 'relative' }}>
                          <Icon sx={{ 
                            fontSize: 20, 
                            color: status === 'complete' ? '#00e5ff' 
                                 : status === 'loading' ? '#ffc300' 
                                 : 'inherit',
                            opacity: isDisabled ? 0.5 : 1,
                          }} />
                          {isDisabled && status === 'pending' && (
                            <LockIcon 
                              sx={{ 
                                position: 'absolute',
                                top: -5,
                                right: -5,
                                fontSize: 12,
                                color: '#666',
                                animation: `${lockedPulse} 2s ease-in-out infinite`,
                              }} 
                            />
                          )}
                        </Box>
                        <span style={{ opacity: isDisabled ? 0.7 : 1 }}>{meta[k].title}</span>
                        {status === 'complete' && (
                          <CheckCircleIcon sx={{ fontSize: 16, color: '#10b981' }} />
                        )}
                        {status === 'loading' && (
                          <Stack direction="row" alignItems="center" spacing={0.5}>
                            <Box
                              sx={{
                                width: 16,
                                height: 16,
                                borderRadius: '50%',
                                border: '2px solid',
                                borderColor: 'transparent',
                                borderTopColor: '#ffc300',
                                animation: 'spin 1s linear infinite',
                                '@keyframes spin': {
                                  '0%': { transform: 'rotate(0deg)' },
                                  '100%': { transform: 'rotate(360deg)' },
                                },
                              }}
                            />
                            <Typography variant="caption" sx={{ color: '#ffc300' }}>
                              {progress}%
                            </Typography>
                          </Stack>
                        )}
                        {isDisabled && status === 'loading' && (
                          <BlockIcon sx={{ fontSize: 14, color: '#ffc300' }} />
                        )}
                      </Stack>
                    </Tooltip>
                  } 
                />
              );
            })}
          </StyledTabs>
        </motion.div>

        {/* -------- Enhanced Panel Content -------- */}
        <AnimatePresence mode="wait">
          <motion.div
            key={cur}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.3 }}
          >
            <ContentPaper
              elevation={0}
              sx={{
                width: '100%',
                mx: 'auto',
                maxWidth: { xs: '100%', lg: '86vw', xl: 1600 },
                p: { xs: 3, md: 5 },
                borderRadius: 3,
              }}
            >
              {/* Loading overlay for incomplete panels */}
              {!isCurrentPanelReady && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    zIndex: 1,
                    p: 2,
                    background: 'linear-gradient(to bottom, rgba(30,30,30,0.9), transparent)',
                  }}
                >
                  <LinearProgress
                    variant="determinate"
                    value={panelProgress[cur] ?? 0}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      backgroundColor: 'rgba(255,255,255,0.1)',
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 3,
                        background: 'linear-gradient(90deg, #00e5ff, #8b5cf6)',
                      },
                    }}
                  />
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: '#ffc300', 
                      mt: 1, 
                      display: 'block',
                      textAlign: 'center',
                    }}
                  >
                    Analysis Progress: {panelProgress[cur] ?? 0}%
                  </Typography>
                </Box>
              )}
              
              <Box sx={{ opacity: isCurrentPanelReady ? 1 : 0.6, transition: 'opacity 0.3s ease' }}>
                {renderPanel()}
              </Box>
            </ContentPaper>
          </motion.div>
        </AnimatePresence>
      </Box>
    </StyledBox>
  );
};

export default DetailPage;