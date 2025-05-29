import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Box,
  Typography,
  TextField,
  Button,
  IconButton,
  Switch,
  FormControlLabel,
  Chip,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SearchIcon from '@mui/icons-material/Search';
import VideocamIcon from '@mui/icons-material/Videocam';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import axios from 'axios';

const PageContainer = styled(Box)({
  minHeight: '100vh',
  background: 'linear-gradient(135deg, #0a0a0a 0%, #0f172a 100%)',
  position: 'relative',
  overflow: 'hidden',
});

const BackButton = styled(IconButton)({
  position: 'absolute',
  top: '2rem',
  left: '2rem',
  background: 'rgba(255, 255, 255, 0.05)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  color: '#fff',
  zIndex: 2,
  '&:hover': {
    background: 'rgba(255, 255, 255, 0.1)',
  },
});

const SearchContainer = styled(Box)({
  background: 'rgba(255, 255, 255, 0.05)',
  backdropFilter: 'blur(20px)',
  borderRadius: '24px',
  padding: '48px',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  position: 'relative',
  overflow: 'hidden',
  maxWidth: '600px',
  width: '100%',
});

const StyledTextField = styled(TextField)({
  '& .MuiOutlinedInput-root': {
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '12px',
    '& fieldset': {
      borderColor: 'rgba(255, 255, 255, 0.2)',
    },
    '&:hover fieldset': {
      borderColor: 'rgba(16, 185, 129, 0.5)',
    },
    '&.Mui-focused fieldset': {
      borderColor: '#10b981',
    },
  },
  '& .MuiInputBase-input': {
    color: '#fff',
    fontSize: '1.1rem',
    padding: '20px',
  },
  '& .MuiInputLabel-root': {
    color: 'rgba(255, 255, 255, 0.6)',
  },
});

const AnimatedGrid = styled(Box)({
  position: 'absolute',
  inset: 0,
  backgroundImage: `
    linear-gradient(rgba(16, 185, 129, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(16, 185, 129, 0.1) 1px, transparent 1px)
  `,
  backgroundSize: '30px 30px',
  animation: 'grid-move 20s linear infinite',
  '@keyframes grid-move': {
    '0%': { transform: 'translate(0, 0)' },
    '100%': { transform: 'translate(30px, 30px)' },
  },
});

const VerifyButton = styled(Button)({
  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
  color: '#fff',
  padding: '16px 48px',
  borderRadius: '12px',
  fontSize: '1.1rem',
  fontWeight: 600,
  textTransform: 'none',
  boxShadow: '0 8px 32px rgba(16, 185, 129, 0.3)',
  '&:hover': {
    background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
    boxShadow: '0 12px 48px rgba(16, 185, 129, 0.4)',
  },
  '&:disabled': {
    background: 'rgba(255, 255, 255, 0.1)',
    color: 'rgba(255, 255, 255, 0.5)',
  },
});

const ExampleChip = styled(Chip)({
  background: 'rgba(16, 185, 129, 0.1)',
  color: '#10b981',
  border: '1px solid rgba(16, 185, 129, 0.3)',
  cursor: 'pointer',
  transition: 'all 0.3s ease',
  '&:hover': {
    background: 'rgba(16, 185, 129, 0.2)',
    borderColor: '#10b981',
  },
});

const VerifySearch: React.FC = () => {
  const navigate = useNavigate();
  const [statement, setStatement] = useState('');
  const [useVideo, setUseVideo] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const exampleStatements = [
    "Tesla is building a new Gigafactory in India",
    "Federal Reserve plans to cut interest rates by 0.5%",
    "Apple announces partnership with OpenAI",
    "Bitcoin ETF approved by SEC",
  ];

  const handleVerify = async () => {
    if (!statement.trim()) return;

    setIsLoading(true);
    try {
      const response = await axios.post('/api/v1/verify', {
        statement: statement.trim(),
        use_video: useVideo,
      });

      const { session_id } = response.data;
      navigate(`/verify/result/${session_id}`);
    } catch (error) {
      console.error('Error starting verification:', error);
      setIsLoading(false);
    }
  };

  return (
    <PageContainer>
      <AnimatedGrid />

      <BackButton onClick={() => navigate('/main')}>
        <ArrowBackIcon />
      </BackButton>

      <Box
        sx={{
          width: '100vw',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1,
          px: 3,
          py: 8,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          style={{ width: '100%', maxWidth: '600px' }}
        >
          <Box textAlign="center" mb={6}>
            <Typography
              variant="h2"
              sx={{
                fontSize: { xs: '2.5rem', md: '3.5rem' },
                fontWeight: 800,
                background: 'linear-gradient(135deg, #10b981 0%, #06b6d4 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                mb: 2,
              }}
            >
              AI Fact Checker
            </Typography>
            <Typography
              variant="h5"
              sx={{
                color: 'rgba(255, 255, 255, 0.7)',
                fontWeight: 300,
              }}
            >
              Verify statements with multi-layer AI analysis
            </Typography>
          </Box>

          <SearchContainer>
            <StyledTextField
              fullWidth
              multiline
              rows={4}
              label="Enter statement to verify"
              placeholder="e.g., 'Company X announces new product launch' or 'Market trend prediction'"
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleVerify();
                }
              }}
            />

            <Box sx={{ mt: 3, mb: 4 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={useVideo}
                    onChange={(e) => setUseVideo(e.target.checked)}
                    sx={{
                      '& .MuiSwitch-track': {
                        backgroundColor: 'rgba(255, 255, 255, 0.2)',
                      },
                      '& .Mui-checked + .MuiSwitch-track': {
                        backgroundColor: '#10b981',
                      },
                    }}
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <VideocamIcon sx={{ mr: 1, fontSize: 20 }} />
                    <Typography sx={{ color: 'rgba(255, 255, 255, 0.8)' }}>
                      Include video verification
                    </Typography>
                  </Box>
                }
              />
            </Box>

            <Box sx={{ mb: 4 }}>
              <Typography
                variant="subtitle2"
                sx={{ color: 'rgba(255, 255, 255, 0.6)', mb: 2, display: 'flex', alignItems: 'center' }}
              >
                <LightbulbIcon sx={{ mr: 1, fontSize: 18 }} />
                Try these examples:
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {exampleStatements.map((example, index) => (
                  <ExampleChip
                    key={index}
                    label={example}
                    onClick={() => setStatement(example)}
                  />
                ))}
              </Box>
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <VerifyButton
                variant="contained"
                size="large"
                disabled={!statement.trim() || isLoading}
                onClick={handleVerify}
                startIcon={<SearchIcon />}
              >
                {isLoading ? 'Starting Verification...' : 'Start Verification'}
              </VerifyButton>
            </Box>

            <Typography
              variant="caption"
              sx={{
                display: 'block',
                textAlign: 'center',
                mt: 3,
                color: 'rgba(255, 255, 255, 0.5)',
              }}
            >
              Press Ctrl+Enter to start verification
            </Typography>
          </SearchContainer>
        </motion.div>
      </Box>
    </PageContainer>
  );
};

export default VerifySearch;
