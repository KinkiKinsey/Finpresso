/*  src/components/panels/MicroPanel.tsx
    —— 完整文件，一行不漏 —— */

import React from 'react';
import {
  Box,
  Alert,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Chip,
  Stack,
  LinearProgress,
} from '@mui/material';
import InfoIcon           from '@mui/icons-material/Info';
import StarIcon           from '@mui/icons-material/Star';
import ArrowCircleRightIcon from '@mui/icons-material/ArrowCircleRight';
import AutoAwesomeIcon    from '@mui/icons-material/AutoAwesome';
import LightbulbIcon      from '@mui/icons-material/Lightbulb';
import { keyframes, styled } from '@mui/material/styles';
import { motion } from 'framer-motion';
import type { AlertProps } from '@mui/material/Alert';
/* ─── 颜色常量 ─────────────────────────────────────────── */
const DARK_BG         = '#0a0a0a';
const PANEL_BG        = 'rgba(18,18,18,0.95)';
const CARD_BG         = 'rgba(30,30,30,0.9)';
const TEXT_PRIMARY    = '#E0E0E0';
const TEXT_SECONDARY  = '#90A4AE';
const ACCENT_CYAN     = '#00ffff';
const ACCENT_PURPLE   = '#a855f7';
const ACCENT_YELLOW   = '#ffc300';
const ACCENT_GRADIENT = 'linear-gradient(135deg, #00ffff, #a855f7)';

/* ─── 动效 ─────────────────────────────────────────────── */
const float = keyframes`
  0%, 100% { transform: translateY(0px); }
  50%      { transform: translateY(-10px); }
`;
const glow = keyframes`
  0%   { box-shadow: 0 0 5px rgba(0,255,255,0.5); }
  50%  { box-shadow: 0 0 20px rgba(0,255,255,0.8), 0 0 30px rgba(168,85,247,0.6); }
  100% { box-shadow: 0 0 5px rgba(0,255,255,0.5); }
`;
const shimmer = keyframes`
  0%   { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
`;

/* ─── 基础容器 ─────────────────────────────────────────── */
const StyledBox = styled(Box)({
  background      : PANEL_BG,
  backdropFilter  : 'blur(20px)',
  border          : '1px solid rgba(0,255,255,0.2)',
  position        : 'relative',
  overflow        : 'hidden',
  '&::before'     : {
    content         : '""',
    position        : 'absolute',
    inset           : 0,
    background      : 'linear-gradient(45deg,transparent 30%,rgba(0,255,255,0.1) 50%,transparent 70%)',
    backgroundSize  : '1000px 100%',
    animation       : `${shimmer} 3s infinite`,
    pointerEvents   : 'none',
  },
});

/* ─── 自定义 Alert（根据 severity 动态样式） ───────────── */
const NeonAlert = styled(Alert)<AlertProps>(({ severity = 'info' }) => ({
  /* 背景 & 边框颜色按  severity  切换 */
  background : severity === 'warning'
    ? 'rgba(255,195,0,0.1)'
    : 'rgba(0,255,255,0.05)',

  borderLeft : `4px solid ${
    severity === 'warning' ? ACCENT_YELLOW : ACCENT_CYAN
  }`,

  border     : `1px solid ${
    severity === 'warning'
      ? 'rgba(255,195,0,0.3)'
      : 'rgba(0,255,255,0.3)'
  }`,

  backdropFilter: 'blur(10px)',
  animation     : `${glow} 3s ease-in-out infinite`,

  '& .MuiAlert-message': {
    color     : TEXT_PRIMARY,
    fontWeight: 500,
  },
  '& .MuiAlert-icon': {
    color: severity === 'warning' ? ACCENT_YELLOW : ACCENT_CYAN,
  },
}));


/* ─── 卡片 ─────────────────────────────────────────────── */
const StyledCard = styled(Card)({
  background   : CARD_BG,
  border       : '1px solid rgba(168,85,247,0.2)',
  borderRadius : 16,
  overflow     : 'visible',
  position     : 'relative',
  transition   : 'all 0.3s ease',
  '&:hover': {
    transform : 'translateY(-5px)',
    boxShadow : '0 10px 40px rgba(168,85,247,0.3)',
    borderColor: ACCENT_PURPLE,
  },
  '&::before': {
    content   : '""',
    position  : 'absolute',
    inset     : -2,
    background: ACCENT_GRADIENT,
    borderRadius: 16,
    opacity   : 0,
    transition: 'opacity 0.3s ease',
    zIndex    : -1,
  },
  '&:hover::before': { opacity: 1 },
});

/* ─── 列表条目 ─────────────────────────────────────────── */
const TakeawayItem = styled(ListItem)({
  background   : 'rgba(0,255,255,0.03)',
  borderRadius : 12,
  marginBottom : 12,
  border       : '1px solid rgba(0,255,255,0.1)',
  transition   : 'all 0.3s ease',
  '&:hover': {
    background : 'rgba(0,255,255,0.08)',
    borderColor: ACCENT_CYAN,
    transform  : 'translateX(10px)',
  },
  '&:last-child': { marginBottom: 0 },
});

/* ─── props 类型 ───────────────────────────────────────── */
interface MicroPanelProps {
  data: {
    Micro_Expectation?: string;
    Three_Key_Takeaways?: any;
    Next_Inference_Hint_Micro_News?: string;
    analysis_results?: {
      key_findings?: string[];
      summary?: string;
    };
  };
}

/* ─── 主组件 ───────────────────────────────────────────── */
const MicroPanel: React.FC<MicroPanelProps> = ({ data }) => {
  const isEmpty = !data || Object.keys(data).length === 0 || (
    !data.Micro_Expectation && !data.Three_Key_Takeaways && !data.Next_Inference_Hint_Micro_News &&
    (!data.analysis_results || Object.keys(data.analysis_results).length === 0)
  );

  if (isEmpty) {
    return (
      <StyledBox sx={{ maxWidth: 900, mx: 'auto', p: { xs: 3, md: 5 }, borderRadius: 4 }}>
        <Typography variant="h5" sx={{ color: '#ffc300', fontWeight: 700, mb: 2 }}>
          No fundamental data available
        </Typography>
        <Typography variant="body1" sx={{ color: '#aaa' }}>
          The backend did not provide company analysis for this ticker. Please try again later or rerun the analysis.
        </Typography>
      </StyledBox>
    );
  }

  /* ── takeaways 解析 ── */
  const raw = data.Three_Key_Takeaways;
  let takeaways: string[] = [];

  if (Array.isArray(raw)) {
    takeaways = raw.map(String).map(t => t.trim()).filter(Boolean);
  } else if (typeof raw === 'string') {
    takeaways = raw.split(/\r?\n+/).map(t => t.trim()).filter(Boolean);
  } else if (raw && typeof raw === 'object') {
    takeaways = Object.values(raw).map(String).map(t => t.trim()).filter(Boolean);
  }

  const keyFindings = data.analysis_results?.key_findings || [];

  return (
    <StyledBox sx={{ maxWidth: 900, mx: 'auto', p: { xs: 3, md: 5 }, borderRadius: 4 }}>
      {/* ─── Header ─── */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <motion.div
          animate={{ rotate: [0, 360], scale: [1, 1.2, 1] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
          <AutoAwesomeIcon sx={{ fontSize: 32, color: ACCENT_PURPLE }} />
        </motion.div>
        <Box>
          <Typography
            variant="h4"
            sx={{
              fontWeight: 700,
              background: ACCENT_GRADIENT,
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Micro AI
          </Typography>
          <Typography variant="subtitle2" sx={{ color: ACCENT_CYAN, fontWeight: 400, mt: 0.5 }}>
            This AI will go through Fundamentals and read 300+ News & Sources in 1 ~ 2 min
          </Typography>
        </Box>
      </Box>

      {/* ─── Market Expectation ─── */}
      <NeonAlert
        icon={<InfoIcon />}
        severity="info"
        sx={{ mb: 4 }}
      >
        <Typography variant="body1">
          {data.Micro_Expectation || 'No market expectation data available'}
        </Typography>
      </NeonAlert>

      {/* ─── Key Takeaways ─── */}
      <StyledCard sx={{ mb: 4 }}>
        <CardContent sx={{ p: 3 }}>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
            <motion.div
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <StarIcon sx={{ color: ACCENT_CYAN, fontSize: 28 }} />
            </motion.div>
            <Typography variant="h5" sx={{ fontWeight: 700, color: TEXT_PRIMARY }}>
              Key Takeaways
            </Typography>
            <Chip
              label={`${takeaways.length} Insights`}
              size="small"
              sx={{
                background: 'rgba(0,255,255,0.1)',
                color: ACCENT_CYAN,
                border: '1px solid rgba(0,255,255,0.3)',
                fontWeight: 600,
              }}
            />
          </Stack>

          <List disablePadding>
            {takeaways.map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.15 }}
              >
                <TakeawayItem>
                  <ListItemIcon>
                    <Box
                      sx={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        background: ACCENT_GRADIENT,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        color: '#000',
                        animation: `${float} 3s ease-in-out infinite`,
                        animationDelay: `${i * 0.3}s`,
                      }}
                    >
                      {i + 1}
                    </Box>
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Typography sx={{ color: TEXT_PRIMARY, fontWeight: 500, lineHeight: 1.6 }}>
                        {t}
                      </Typography>
                    }
                  />
                </TakeawayItem>
              </motion.div>
            ))}
          </List>
        </CardContent>
      </StyledCard>

      {/* ─── Additional Findings ─── */}
      {keyFindings.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ mb: 2, color: TEXT_PRIMARY, fontWeight: 600 }}>
            Additional Findings
          </Typography>
          <Stack spacing={2}>
            {keyFindings.slice(0, 3).map((finding, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 + i * 0.1 }}
              >
                <Box
                  sx={{
                    p: 2,
                    background: 'rgba(168,85,247,0.05)',
                    border: '1px solid rgba(168,85,247,0.2)',
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 2,
                  }}
                >
                  <LightbulbIcon sx={{ color: ACCENT_PURPLE, mt: 0.5 }} />
                  <Typography sx={{ color: TEXT_PRIMARY, flex: 1 }}>
                    {finding}
                  </Typography>
                </Box>
              </motion.div>
            ))}
          </Stack>
        </Box>
      )}

      {/* ─── Next Hint ─── */}
      {data.Next_Inference_Hint_Micro_News && (
        <NeonAlert
          icon={<ArrowCircleRightIcon />}
          severity="warning"
          sx={{ position: 'relative', overflow: 'hidden' }}
        >
          <Typography variant="body2">
            {data.Next_Inference_Hint_Micro_News}
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
                background: `linear-gradient(90deg, ${ACCENT_YELLOW}, ${ACCENT_PURPLE})`,
              },
            }}
            variant="indeterminate"
          />
        </NeonAlert>
      )}
    </StyledBox>
  );
};

export default MicroPanel;
