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
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HomeIcon from '@mui/icons-material/Home';
import SchemaIcon from '@mui/icons-material/Schema';           // network-like icon
import { useParams, useNavigate } from 'react-router-dom';
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

const DetailPage: React.FC = () => {
  const { id = '', panel = 'macro' } = useParams<{ id: string; panel: PanelKey }>();
  const navigate = useNavigate();
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

  const renderPanel = () => {
    switch (cur) {
      case 'macro':
        return <MacroPanel data={panelData} />;
      case 'micro':
        return <MicroPanel data={panelData} />;
      case 'price':
        return <PricePanel data={panelData} />;
      case 'strategy':
        return <FancyStrategyPanel data={toFancy(panelData)} />;
      default:
        return null;
    }
  };

  return (
    <Box
      component="main"
      sx={{
        width: '100vw',
        minHeight: '100vh',
        bgcolor: '#121212',      // dark tech background
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
        {/* -------- top nav bar -------- */}
        <Stack direction="row" alignItems="center" spacing={2}>
          <IconButton onClick={() => navigate(-1)} sx={{ color: '#fff' }}>
            <ArrowBackIcon />
          </IconButton>
          <IconButton onClick={() => navigate('/')} sx={{ color: '#fff' }}>
            <HomeIcon />
          </IconButton>

          {/* 🚀 Neon “Mind Map” button */}
          <Button
            variant="contained"
            startIcon={<SchemaIcon />}
            onClick={() => navigate(`/mindmap/${id}`)}
            sx={{
              ml: 1,
              py: 0.5,
              px: 2.5,
              fontWeight: 700,
              background:
                'linear-gradient(135deg,#00e5ff 0%,#3b82f6 45%,#8b5cf6 100%)',
              color: '#fff',
              textTransform: 'none',
              boxShadow: '0 0 14px rgba(0,229,255,.6)',
              transition: 'all .2s',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 0 22px rgba(0,229,255,.9)',
                background:
                  'linear-gradient(135deg,#00e5ff 0%,#00b0ff 45%,#5e3bff 100%)',
              },
            }}
          >
            Mind&nbsp;Map
          </Button>

          <Typography variant="h5" fontWeight={700} color="#00e5ff">
            {meta[cur].title}
          </Typography>
        </Stack>

        {/* -------- tabs -------- */}
        <Tabs
          value={cur}
          onChange={(_, v) => navigate(`/detail/${id}/${v}`)}
          textColor="primary"
          indicatorColor="primary"
          variant="scrollable"
          sx={{
            '& .MuiTab-root': {
              fontWeight: 600,
              textTransform: 'none',
              color: '#888',
            },
            '& .Mui-selected': { color: '#00e5ff !important' },
          }}
        >
          {(Object.keys(meta) as PanelKey[]).map(k => (
            <Tab key={k} value={k} label={meta[k].title} />
          ))}
        </Tabs>

        {/* -------- panel content -------- */}
        <Paper
          elevation={4}
          sx={{
            width: '100%',
            mx: 'auto',
            maxWidth: { xs: '100%', lg: '86vw', xl: 1600 },
            p: { xs: 3, md: 5 },
            borderRadius: 3,
            backdropFilter: 'blur(12px)',
            background: 'rgba(30,30,30,0.75)',
          }}
        >
          {renderPanel()}
        </Paper>
      </Box>
    </Box>
  );
};

export default DetailPage;
