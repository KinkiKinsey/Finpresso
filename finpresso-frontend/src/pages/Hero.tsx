import React, { useState } from 'react';
import { Box, Stack, Typography, TextField, Button, Chip } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { keyframes, styled } from '@mui/material/styles';
import axios from '../utils/axiosConfig';
import SmartToyIcon from '@mui/icons-material/SmartToy';

const hot: string[] = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOG', 'AMZN'];

// Neon glow animations
const neonText = keyframes`
  0%,100% { text-shadow: 0 0 8px #0ff, 0 0 16px #06f; }
  50%    { text-shadow: 0 0 16px #0ff, 0 0 24px #a3f; }
`;
const glowPulse = keyframes`
  0% { box-shadow: 0 0 8px rgba(15,255,255,0.4); }
  50% { box-shadow: 0 0 16px rgba(15,255,255,0.8); }
  100% { box-shadow: 0 0 8px rgba(15,255,255,0.4); }
`;
// Robot float animation
const float = keyframes`
  0% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0px); }
`;

// Styled components
const Root = styled(Box)(() => ({
  position: 'relative',
  width: '100vw',
  height: '100vh',
  background: '#121212',
  backgroundImage: 'radial-gradient(circle at top left, #0e0e1a, #121212)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center',
  overflow: 'hidden',
}));

const NeonTitle = styled(Typography)(() => ({
  fontSize: '2.5rem',
  fontWeight: 800,
  color: '#0ff',
  animation: `${neonText} 2s ease-in-out infinite`,
}));

const NeonButton = styled(Button)(() => ({
  minWidth: 120,
  fontWeight: 700,
  background: 'linear-gradient(135deg, #00e5ff 0%, #3b82f6 60%, #8b5cf6 100%)',
  color: '#fff',
  textTransform: 'none',
  boxShadow: '0 0 12px rgba(0,229,255,0.6)',
  transition: 'all .2s',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: '0 0 24px rgba(0,229,255,0.9)',
    background: 'linear-gradient(135deg, #00e5ff 0%, #00b0ff 60%, #5e3bff 100%)',
  },
  '&.Mui-disabled': {
    opacity: 0.6,
    boxShadow: 'none',
    color: '#555',
  },
}));

const NeonChip = styled(Chip)(() => ({
  fontWeight: 700,
  margin: '4px',
  background: '#1f1f2e',
  color: '#0ff',
  border: '1px solid #0ff',
  '&:hover': {
    animation: `${glowPulse} 1.5s infinite alternate`,
    background: '#0e0e1a',
    cursor: 'pointer',
  },
}));

// Floating robot decorations
const RobotLeft = styled(SmartToyIcon)(() => ({
  position: 'absolute',
  left: 20,
  bottom: 20,
  fontSize: 64,
  color: 'rgba(15,255,255,0.4)',
  animation: `${float} 4s ease-in-out infinite`,
}));
const RobotRight = styled(SmartToyIcon)(() => ({
  position: 'absolute',
  right: 20,
  top: 40,
  fontSize: 48,
  color: 'rgba(15,255,255,0.3)',
  animation: `${float} 5s ease-in-out infinite`,
}));

const Hero: React.FC = () => {
  const [ticker, setTicker] = useState<string>('');
  const navigate = useNavigate();

  const mCreate = useMutation<{ job_id: string }, unknown, string>({
    mutationFn: (t: string) =>
      axios.post('/api/v1/analysis', { ticker: t }).then(res => res.data),
    onSuccess: (data, t) => navigate(`/progress/${data.job_id}`, { state: { ticker: t } }),
  });

  return (
    <Root>
      <RobotLeft />
      <RobotRight />

      <Stack spacing={4} sx={{ width: { xs: '100%', sm: 480 } }}>
        <NeonTitle>
          Fintegrate <Box component="span" sx={{ color: '#a3f', ml: 1 }}>AI</Box>
        </NeonTitle>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
          <TextField
            fullWidth
            placeholder="Enter ticker e.g. NVDA"
            variant="filled"
            InputProps={{
              sx: {
                bgcolor: '#1f1f2e',
                borderRadius: 1,
                color: '#fff',
                '& .MuiFilledInput-input': { color: '#fff' },
                '& .MuiFilledInput-underline:before': { borderBottomColor: '#444' },
                '& .MuiFilledInput-underline:after': { borderBottomColor: '#0ff' },
              },
            }}
            value={ticker}
            onChange={e => setTicker(e.target.value.toUpperCase())}
          />
          <NeonButton disabled={!ticker} onClick={() => mCreate.mutate(ticker)}>
            Analyze
          </NeonButton>
        </Stack>

        <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap">
          {hot.map((t, i) => (
            <NeonChip
              key={i}
              label={t}
              onClick={() => {
                setTicker(t);
                mCreate.mutate(t);
              }}
            />
          ))}
        </Stack>
      </Stack>
    </Root>
  );
};

export default Hero;
