import React, { useState, useRef } from 'react';
import {
  Box,
  Typography,
  Stack,
  LinearProgress,
  CssBaseline,
  IconButton,
} from '@mui/material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from '../utils/axiosConfig';
import { meta, PanelKey } from './App';

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
    background: { default: '#121212', paper: '#1e1e1e' },
    primary: { main: '#00e5ff' },
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
          // 带上 ticker 传给 DetailPage
          navigate(
            `/detail/${jobId}/macro`,
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
        }}
      >
        <Typography variant="h5" color="text.primary" gutterBottom>
          Running analysis
        </Typography>
        <Typography color="text.secondary" gutterBottom>
          {data?.message || 'Waiting in queue…'}
        </Typography>

        {/* progress bars */}
        <Stack direction="row" spacing={8} justifyContent="center" sx={{ mt: 8, mb: 4, flexWrap: 'wrap' }}>
          {(Object.keys(meta) as PanelKey[]).map(k => (
            <Box key={k} sx={{ width: 160 }}>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mb: 1, display: 'block' }}
              >
                {meta[k].title}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={prog[k]}
                sx={{
                  width: '100%',
                  height: 8,
                  borderRadius: 5,
                  bgcolor: '#2a2a2a',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: 'primary.main',
                    boxShadow: prog[k] > 0 ? `0 0 8px ${darkTheme.palette.primary.main}` : 'none',
                  },
                }}
              />
            </Box>
          ))}
        </Stack>

        {/* icons with left-to-right fill */}
        <Stack direction="row" spacing={8} justifyContent="center" sx={{ mb: 6, flexWrap: 'wrap' }}>
          {(Object.keys(meta) as PanelKey[]).map(k => {
            const { Icon, title } = meta[k];
            const fillPct = prog[k];
            const clickable = fillPct >= 100;

            return (
              <Box key={k} sx={{ width: 160, textAlign: 'center' }}>
                <Box
                  onClick={() =>
                    clickable &&
                    navigate(
                      `/detail/${jobId}/${k}`,
                      { state: { ...panelData[k], ticker } }
                    )
                  }
                  sx={{
                    position: 'relative',
                    width: 80,
                    height: 80,
                    mx: 'auto',
                    cursor: clickable ? 'pointer' : 'default',
                  }}
                >
                  {/* background icon */}
                  <Icon
                    sx={{
                      fontSize: 80,
                      color: 'text.disabled',
                      position: 'absolute',
                      top: 0,
                      left: 0,
                    }}
                  />
                  {/* colored overlay */}
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: `${fillPct}%`,
                      height: '100%',
                      overflow: 'hidden',
                    }}
                  >
                    <Icon
                      sx={{
                        fontSize: 80,
                        color: 'primary.main',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                      }}
                    />
                  </Box>
                </Box>
                <Typography variant="body2" color="text.primary">
                  {title}
                </Typography>
              </Box>
            );
          })}
        </Stack>

        {/* logs */}
        <Box
          sx={{
            mt: 2,
            p: 2,
            maxHeight: 200,
            overflow: 'auto',
            bgcolor: 'background.paper',
            borderRadius: 2,
            fontFamily: 'monospace',
            fontSize: 12,
            textAlign: 'left',
            width: '80%',
          }}
        >
          {logs.map((l, i) => (
            <div key={i} style={{ color: '#ccc', marginBottom: 4 }}>
              {l}
            </div>
          ))}
        </Box>
      </Box>
    </ThemeProvider>
  );
}
