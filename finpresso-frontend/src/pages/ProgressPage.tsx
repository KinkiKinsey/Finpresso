import { useState, useRef } from 'react';
import {
  Box,
  Typography,
  Stack,
  LinearProgress,
  CssBaseline,
  IconButton,
  Tooltip,
  Chip,
} from '@mui/material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from '../utils/axiosConfig';
import { meta, PanelKey } from './App';
import { motion, AnimatePresence } from 'framer-motion';
import HomeIcon from '@mui/icons-material/Home';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

// StatusResp 类型要和后端 status 接口返回一致
interface StatusResp {
  state: 'pending' | 'running' | 'finished' | 'error';
  message?: string;
  panel_progress: Record<PanelKey, number>;
  panel_data: Record<PanelKey, any>;
  new_logs: string[];
  next_cursor: number;
}

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    background: { default: '#0a0a0a', paper: '#1a1a1a' },
    primary: { main: '#00e5ff' },
    success: { main: '#00ff88' },
    text: { primary: '#fff', secondary: '#888' },
  },
});

export default function ProgressPage() {
  const { id: jobId = '' } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { state } = location as { state: { ticker?: string } };
  const ticker = state?.ticker;

  const [cursor, setCursor] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const jumped = useRef(false);

  const { data } = useQuery(
    ['status', jobId],
    () =>
      axios.get(`/api/v1/analysis/${jobId}/status`, { params: { cursor } }).then(r => r.data),
    {
      refetchInterval: 1500,
      onSuccess: d => {
        setCursor(d.next_cursor);
        setLogs(old => [...old, ...d.new_logs]);
        if (d.state === 'finished' && !jumped.current) {
          jumped.current = true;
          navigate(
            `/analysis/detail/${jobId}/macro`,
            { replace: true, state: { ticker } }
          );
        }
      },
    }
  );

  const prog = data?.panel_progress ?? {
    macro: 0,
    micro: 0,
    price: 0,
    strategy: 0,
  };
  const panelData = data?.panel_data ?? ({} as Record<PanelKey, any>);

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box
        sx={{
          width: '100vw',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          bgcolor: 'background.default',
          px: 2,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Animated background effect */}
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            background: `
              radial-gradient(circle at 20% 50%, rgba(0, 229, 255, 0.1) 0%, transparent 50%),
              radial-gradient(circle at 80% 80%, rgba(0, 255, 136, 0.1) 0%, transparent 50%)
            `,
            filter: 'blur(100px)',
            animation: 'pulse 8s ease-in-out infinite',
            '@keyframes pulse': {
              '0%, 100%': { opacity: 0.5 },
              '50%': { opacity: 0.8 },
            },
          }}
        />

        {/* Home button */}
        <Tooltip title="Back to Home">
          <IconButton
            onClick={() => navigate('/')}
            sx={{
              position: 'absolute',
              top: 32,
              left: 32,
              bgcolor: 'rgba(255, 255, 255, 0.05)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              '&:hover': {
                bgcolor: 'rgba(255, 255, 255, 0.1)',
                transform: 'scale(1.05)',
              },
              transition: 'all 0.3s ease',
            }}
          >
            <HomeIcon sx={{ color: 'primary.main' }} />
          </IconButton>
        </Tooltip>

        {/* Main content */}
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Typography variant="h4" color="text.primary" gutterBottom sx={{ fontWeight: 700 }}>
            Running Analysis
          </Typography>
          <Typography color="text.secondary" gutterBottom sx={{ mb: 6 }}>
            {data?.message || 'Waiting in queue…'}
          </Typography>

          {/* Progress bars */}
          <Stack direction="row" spacing={4} justifyContent="center" sx={{ mb: 8, flexWrap: 'wrap' }}>
            {(Object.keys(meta) as PanelKey[]).map(k => {
              const isComplete = prog[k] >= 100;
              return (
                <Box key={k} sx={{ width: 180, mb: 2 }}>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <Typography
                      variant="body2"
                      color={isComplete ? 'success.main' : 'text.secondary'}
                      sx={{ fontWeight: isComplete ? 600 : 400 }}
                    >
                      {meta[k].title}
                    </Typography>
                    {isComplete && (
                      <CheckCircleIcon 
                        sx={{ 
                          fontSize: 16, 
                          color: 'success.main',
                          animation: 'fadeIn 0.5s ease',
                          '@keyframes fadeIn': {
                            from: { opacity: 0, transform: 'scale(0.5)' },
                            to: { opacity: 1, transform: 'scale(1)' },
                          },
                        }} 
                      />
                    )}
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={prog[k]}
                    sx={{
                      width: '100%',
                      height: 10,
                      borderRadius: 5,
                      bgcolor: 'rgba(255, 255, 255, 0.05)',
                      '& .MuiLinearProgress-bar': {
                        bgcolor: isComplete ? 'success.main' : 'primary.main',
                        borderRadius: 5,
                        boxShadow: prog[k] > 0 
                          ? `0 0 20px ${isComplete ? darkTheme.palette.success.main : darkTheme.palette.primary.main}40`
                          : 'none',
                        transition: 'all 0.5s ease',
                      },
                    }}
                  />
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      mt: 0.5, 
                      display: 'block',
                      color: isComplete ? 'success.main' : 'text.secondary',
                      fontWeight: isComplete ? 600 : 400,
                    }}
                  >
                    {prog[k]}%
                  </Typography>
                </Box>
              );
            })}
          </Stack>

          {/* Icons with enhanced interactivity */}
          <Stack direction="row" spacing={6} justifyContent="center" sx={{ mb: 6, flexWrap: 'wrap' }}>
            {(Object.keys(meta) as PanelKey[]).map(k => {
              const { Icon, title } = meta[k];
              const fillPct = prog[k];
              const isComplete = fillPct >= 100;
              const isActive = fillPct > 0 && fillPct < 100;

              return (
                <motion.div
                  key={k}
                  whileHover={isComplete ? { scale: 1.1 } : {}}
                  whileTap={isComplete ? { scale: 0.95 } : {}}
                >
                  <Box sx={{ width: 120, textAlign: 'center' }}>
                    <Box
                      onClick={() =>
                        isComplete &&
                        navigate(
                          `/analysis/detail/${jobId}/${k}`,
                          { state: { ...panelData[k], ticker } }
                        )
                      }
                      sx={{
                        position: 'relative',
                        width: 100,
                        height: 100,
                        mx: 'auto',
                        cursor: isComplete ? 'pointer' : 'default',
                        borderRadius: '50%',
                        bgcolor: isComplete ? 'rgba(0, 255, 136, 0.1)' : 'transparent',
                        border: isComplete ? '2px solid' : 'none',
                        borderColor: 'success.main',
                        transition: 'all 0.3s ease',
                        '&:hover': isComplete ? {
                          bgcolor: 'rgba(0, 255, 136, 0.2)',
                          boxShadow: '0 0 30px rgba(0, 255, 136, 0.5)',
                        } : {},
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {/* Background icon */}
                      <Icon
                        sx={{
                          fontSize: 60,
                          color: 'rgba(255, 255, 255, 0.1)',
                          position: 'absolute',
                        }}
                      />
                      {/* Colored overlay */}
                      <Box
                        sx={{
                          position: 'absolute',
                          inset: 0,
                          borderRadius: '50%',
                          overflow: 'hidden',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <Box
                          sx={{
                            position: 'absolute',
                            bottom: 0,
                            left: 0,
                            right: 0,
                            height: `${fillPct}%`,
                            bgcolor: isComplete ? 'success.main' : 'primary.main',
                            opacity: 0.2,
                            transition: 'all 0.5s ease',
                          }}
                        />
                        <Icon
                          sx={{
                            fontSize: 60,
                            color: isComplete ? 'success.main' : 'primary.main',
                            position: 'relative',
                            opacity: fillPct / 100,
                            filter: isActive ? 'drop-shadow(0 0 10px currentColor)' : 'none',
                            animation: isActive ? 'pulse 2s ease-in-out infinite' : 'none',
                            '@keyframes pulse': {
                              '0%, 100%': { transform: 'scale(1)' },
                              '50%': { transform: 'scale(1.05)' },
                            },
                          }}
                        />
                      </Box>
                      
                      {/* Status indicator */}
                      {isComplete && (
                        <CheckCircleIcon
                          sx={{
                            position: 'absolute',
                            bottom: -5,
                            right: -5,
                            fontSize: 28,
                            color: 'success.main',
                            bgcolor: 'background.default',
                            borderRadius: '50%',
                            animation: 'bounceIn 0.5s ease',
                            '@keyframes bounceIn': {
                              '0%': { transform: 'scale(0)', opacity: 0 },
                              '50%': { transform: 'scale(1.2)' },
                              '100%': { transform: 'scale(1)', opacity: 1 },
                            },
                          }}
                        />
                      )}
                      {isActive && (
                        <AccessTimeIcon
                          sx={{
                            position: 'absolute',
                            bottom: -5,
                            right: -5,
                            fontSize: 24,
                            color: 'primary.main',
                            bgcolor: 'background.default',
                            borderRadius: '50%',
                            animation: 'rotate 2s linear infinite',
                            '@keyframes rotate': {
                              from: { transform: 'rotate(0deg)' },
                              to: { transform: 'rotate(360deg)' },
                            },
                          }}
                        />
                      )}
                    </Box>
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        mt: 2,
                        color: isComplete ? 'success.main' : 'text.primary',
                        fontWeight: isComplete ? 600 : 400,
                      }}
                    >
                      {title}
                    </Typography>
                    {isComplete && (
                      <Chip
                        label="View Results"
                        size="small"
                        color="success"
                        sx={{ 
                          mt: 1,
                          height: 20,
                          fontSize: '0.7rem',
                          animation: 'fadeIn 0.5s ease 0.3s both',
                          '@keyframes fadeIn': {
                            from: { opacity: 0, transform: 'translateY(10px)' },
                            to: { opacity: 1, transform: 'translateY(0)' },
                          },
                        }}
                      />
                    )}
                  </Box>
                </motion.div>
              );
            })}
          </Stack>

          {/* Enhanced logs section */}
          <Box
            sx={{
              mt: 4,
              p: 3,
              maxHeight: 200,
              overflow: 'auto',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(10px)',
              borderRadius: 3,
              border: '1px solid rgba(255, 255, 255, 0.05)',
              fontFamily: 'monospace',
              fontSize: 12,
              textAlign: 'left',
              width: '80%',
              maxWidth: 800,
              mx: 'auto',
              boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.2)',
              '&::-webkit-scrollbar': {
                width: 8,
              },
              '&::-webkit-scrollbar-track': {
                background: 'rgba(255, 255, 255, 0.05)',
                borderRadius: 4,
              },
              '&::-webkit-scrollbar-thumb': {
                background: 'rgba(255, 255, 255, 0.2)',
                borderRadius: 4,
                '&:hover': {
                  background: 'rgba(255, 255, 255, 0.3)',
                },
              },
            }}
          >
            <AnimatePresence>
              {logs.map((l, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3 }}
                  style={{ 
                    color: '#00ff88', 
                    marginBottom: 8,
                    padding: '4px 8px',
                    borderLeft: '2px solid #00ff88',
                    background: 'rgba(0, 255, 136, 0.05)',
                  }}
                >
                  <span style={{ color: '#666', marginRight: 8 }}>[{new Date().toLocaleTimeString()}]</span>
                  {l}
                </motion.div>
              ))}
            </AnimatePresence>
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
}