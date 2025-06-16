import React, { useState } from 'react';
import { Box, Stack, Typography, TextField, Button, Chip, IconButton, Snackbar, Alert } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { keyframes, styled } from '@mui/material/styles';
import axios from '../utils/axiosConfig';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { motion } from 'framer-motion';

const hot: string[] = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOG', 'AMZN'];

// Animations
const neonText = keyframes`
  0%,100% { text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff, 0 0 30px #00ffff; }
  50%    { text-shadow: 0 0 20px #00ffff, 0 0 30px #00ffff, 0 0 40px #a855f7; }
`;

const glowPulse = keyframes`
  0% { box-shadow: 0 0 5px rgba(0,255,255,0.5), inset 0 0 5px rgba(0,255,255,0.1); }
  50% { box-shadow: 0 0 20px rgba(0,255,255,0.8), inset 0 0 10px rgba(0,255,255,0.3); }
  100% { box-shadow: 0 0 5px rgba(0,255,255,0.5), inset 0 0 5px rgba(0,255,255,0.1); }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(10deg); }
`;

const gridAnimation = keyframes`
  0% { transform: translateX(0); }
  100% { transform: translateX(30px); }
`;

const shake = keyframes`
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
  20%, 40%, 60%, 80% { transform: translateX(2px); }
`;

// Styled components
const Root = styled(Box)(() => ({
  position: 'relative',
  width: '100vw',
  height: '100vh',
  background: 'linear-gradient(135deg, #0a0a0a 0%, #0f172a 100%)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center',
  overflow: 'hidden',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundImage: `
      linear-gradient(rgba(0,255,255,0.1) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,255,255,0.1) 1px, transparent 1px)
    `,
    backgroundSize: '30px 30px',
    animation: `${gridAnimation} 8s linear infinite`,
    opacity: 0.3,
  },
}));

const BackButton = styled(IconButton)(() => ({
  position: 'absolute',
  top: '2rem',
  left: '2rem',
  background: 'rgba(255,255,255,0.05)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(0,255,255,0.3)',
  color: '#00ffff',
  zIndex: 10,
  transition: 'all 0.3s ease',
  '&:hover': {
    background: 'rgba(0,255,255,0.1)',
    borderColor: '#00ffff',
    transform: 'translateY(-2px)',
    boxShadow: '0 5px 20px rgba(0,255,255,0.4)',
  },
}));

const NeonTitle = styled(Typography)(() => ({
  fontSize: '4rem',
  fontWeight: 900,
  background: 'linear-gradient(135deg, #00ffff 0%, #a855f7 100%)',
  backgroundClip: 'text',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  animation: `${neonText} 3s ease-in-out infinite`,
  position: 'relative',
  '&::after': {
    content: '"AI"',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'linear-gradient(135deg, #00ffff 0%, #a855f7 100%)',
    backgroundClip: 'text',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    filter: 'blur(10px)',
    opacity: 0.5,
    zIndex: -1,
  },
}));

const SubTitle = styled(Typography)(() => ({
  fontSize: '1.2rem',
  color: 'rgba(255,255,255,0.7)',
  marginTop: '1rem',
  marginBottom: '3rem',
  fontWeight: 300,
  letterSpacing: '0.1em',
}));

const StyledTextField = styled(TextField)<{ error?: boolean }>(({ error }) => ({
  '& .MuiFilledInput-root': {
    background: error ? 'rgba(255,0,0,0.05)' : 'rgba(255,255,255,0.05)',
    backdropFilter: 'blur(10px)',
    border: `1px solid ${error ? 'rgba(255,0,0,0.5)' : 'rgba(0,255,255,0.3)'}`,
    borderRadius: '12px',
    transition: 'all 0.3s ease',
    animation: error ? `${shake} 0.5s ease-in-out` : 'none',
    '&:hover': {
      background: error ? 'rgba(255,0,0,0.08)' : 'rgba(255,255,255,0.08)',
      borderColor: error ? 'rgba(255,0,0,0.7)' : 'rgba(0,255,255,0.5)',
    },
    '&.Mui-focused': {
      background: 'rgba(255,255,255,0.1)',
      borderColor: error ? '#ff0000' : '#00ffff',
      boxShadow: `0 0 20px ${error ? 'rgba(255,0,0,0.3)' : 'rgba(0,255,255,0.3)'}`,
    },
  },
  '& .MuiFilledInput-input': {
    color: '#fff',
    fontSize: '1.1rem',
    padding: '16px',
    '&::placeholder': {
      color: 'rgba(255,255,255,0.5)',
    },
  },
  '& .MuiFilledInput-underline:before, & .MuiFilledInput-underline:after': {
    display: 'none',
  },
}));

const NeonButton = styled(Button)(() => ({
  minWidth: 140,
  padding: '12px 32px',
  fontWeight: 700,
  fontSize: '1.1rem',
  background: 'linear-gradient(135deg, #00ffff 0%, #a855f7 100%)',
  color: '#000',
  textTransform: 'none',
  borderRadius: '12px',
  position: 'relative',
  overflow: 'hidden',
  transition: 'all 0.3s ease',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: '-100%',
    width: '100%',
    height: '100%',
    background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
    transition: 'left 0.5s ease',
  },
  '&:hover': {
    transform: 'translateY(-3px)',
    boxShadow: '0 10px 30px rgba(0,255,255,0.5)',
    '&::before': {
      left: '100%',
    },
  },
  '&.Mui-disabled': {
    opacity: 0.5,
    background: 'rgba(255,255,255,0.1)',
    color: 'rgba(255,255,255,0.3)',
  },
}));

const NeonChip = styled(Chip)(() => ({
  fontWeight: 600,
  fontSize: '0.9rem',
  padding: '20px 12px',
  margin: '6px',
  background: 'rgba(255,255,255,0.05)',
  color: '#00ffff',
  border: '1px solid rgba(0,255,255,0.5)',
  backdropFilter: 'blur(10px)',
  transition: 'all 0.3s ease',
  '&:hover': {
    animation: `${glowPulse} 1.5s infinite`,
    background: 'rgba(0,255,255,0.1)',
    transform: 'translateY(-2px) scale(1.05)',
    cursor: 'pointer',
  },
}));

// Floating elements
const FloatingElement = styled(Box)(() => ({
  position: 'absolute',
  opacity: 0.3,
  animation: `${float} 6s ease-in-out infinite`,
}));

const ParticleField = styled(Box)(() => ({
  position: 'absolute',
  width: '100%',
  height: '100%',
  overflow: 'hidden',
  '& .particle': {
    position: 'absolute',
    width: '2px',
    height: '2px',
    background: '#00ffff',
    borderRadius: '50%',
    opacity: 0.5,
  },
}));

// Particle component
const Particles: React.FC = () => {
  const particles = Array.from({ length: 50 }, (_, i) => ({
    id: i,
    left: `${Math.random() * 100}%`,
    animationDelay: `${Math.random() * 5}s`,
    animationDuration: `${5 + Math.random() * 10}s`,
  }));

  return (
    <ParticleField>
      {particles.map((p) => (
        <Box
          key={p.id}
          className="particle"
          sx={{
            left: p.left,
            animation: `${float} ${p.animationDuration} ${p.animationDelay} ease-in-out infinite`,
          }}
        />
      ))}
    </ParticleField>
  );
};

const Hero: React.FC = () => {
  const [ticker, setTicker] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [showError, setShowError] = useState<boolean>(false);
  const navigate = useNavigate();

  const mCreate = useMutation<{ job_id: string }, any, string>({
    mutationFn: (t: string) => {
      // Trim spaces and ensure uppercase before sending to backend
      const cleanTicker = t.trim().toUpperCase();
      return axios.post('/api/v1/analysis', { ticker: cleanTicker }).then(res => res.data);
    },
    onSuccess: (data, t) => navigate(`/analysis/progress/${data.job_id}`, { state: { ticker: t } }),
    onError: (err: any) => {
      const errorMessage = err.response?.data?.detail || 'Failed to analyze ticker. Please try again.';
      setError(errorMessage);
      setShowError(true);
    },
  });

  const handleAnalyze = (tickerSymbol: string) => {
    // Trim spaces and validate before analysis
    const cleanTicker = tickerSymbol.trim();
    if (!cleanTicker) {
      setError('Please enter a valid ticker symbol');
      setShowError(true);
      return;
    }
    setError('');
    mCreate.mutate(cleanTicker);
  };

  return (
    <Root>
      <Particles />
      
      <BackButton onClick={() => navigate('/')}>
        <ArrowBackIcon />
      </BackButton>

      {/* Floating decorations */}
      <FloatingElement sx={{ left: 80, top: 120 }}>
        <SmartToyIcon sx={{ fontSize: 48, color: '#00ffff' }} />
      </FloatingElement>
      <FloatingElement sx={{ right: 100, top: 80, animationDelay: '2s' }}>
        <TrendingUpIcon sx={{ fontSize: 56, color: '#a855f7' }} />
      </FloatingElement>
      <FloatingElement sx={{ left: 120, bottom: 100, animationDelay: '4s' }}>
        <ShowChartIcon sx={{ fontSize: 52, color: '#00ffff' }} />
      </FloatingElement>
      <FloatingElement sx={{ right: 60, bottom: 140, animationDelay: '3s' }}>
        <SmartToyIcon sx={{ fontSize: 44, color: '#a855f7' }} />
      </FloatingElement>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
      >
        <Stack spacing={4} sx={{ width: { xs: '90%', sm: 600 }, maxWidth: '100%' }}>
          <Box>
            <NeonTitle>Fintegrate AI</NeonTitle>
            <SubTitle>Advanced Market Analysis Powered by AI</SubTitle>
          </Box>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="stretch">
            <StyledTextField
              fullWidth
              placeholder="Enter ticker symbol (e.g., NVDA)"
              variant="filled"
              value={ticker}
              error={!!error && showError}
              onChange={e => {
                // Trim spaces on input change
                const inputValue = e.target.value.trim();
                setTicker(inputValue.toUpperCase());
                setError('');
                setShowError(false);
              }}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && ticker.trim()) {
                  handleAnalyze(ticker);
                }
              }}
            />
            <NeonButton 
              disabled={!ticker || mCreate.isLoading} 
              onClick={() => handleAnalyze(ticker)}
              startIcon={<TrendingUpIcon />}
            >
              {mCreate.isLoading ? 'Analyzing...' : 'Analyze'}
            </NeonButton>
          </Stack>

          <Box>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mb: 2 }}>
              Popular Tickers
            </Typography>
            <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap">
              {hot.map((t, i) => (
                <motion.div
                  key={t}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.1 }}
                >
                  <NeonChip
                    label={t}
                    onClick={() => {
                      setTicker(t);
                      setError('');
                      setShowError(false);
                      handleAnalyze(t);
                    }}
                    icon={<TrendingUpIcon />}
                  />
                </motion.div>
              ))}
            </Stack>
          </Box>
        </Stack>
      </motion.div>

      {/* Error Snackbar */}
      <Snackbar
        open={showError}
        autoHideDuration={6000}
        onClose={() => setShowError(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setShowError(false)}
          severity="error"
          icon={<ErrorOutlineIcon />}
          sx={{
            bgcolor: 'rgba(255,0,0,0.1)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,0,0,0.5)',
            color: '#fff',
            '& .MuiAlert-icon': {
              color: '#ff0000',
            },
          }}
        >
          {error}
        </Alert>
      </Snackbar>
    </Root>
  );
};

export default Hero;