// src/pages/MainNavigation.tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import AutoGraphIcon from '@mui/icons-material/AutoGraph';
import VerifiedIcon from '@mui/icons-material/Verified';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { Box, Typography, IconButton } from '@mui/material';
import { styled } from '@mui/material/styles';

/* ─────────────────────────  布局容器  ───────────────────────── */
const PageContainer = styled(Box)({
  minHeight: '100vh',
  width: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)',
  position: 'relative',
  overflow: 'hidden',
  padding: '40px 20px',
});

/* ─────────────────────────  背景雾化层  ───────────────────────── */
const AnimatedBackground = styled(Box)({
  position: 'absolute',
  inset: 0,
  '&::before': {
    content: '""',
    position: 'absolute',
    inset: 0,
    background: `
      radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
      radial-gradient(circle at 40% 20%, rgba(119, 198, 255, 0.3) 0%, transparent 50%)
    `,
    filter: 'blur(120px)',
    animation: 'pulse 10s ease-in-out infinite',
  },
  '@keyframes pulse': {
    '0%, 100%': { opacity: 1 },
    '50%':      { opacity: 0.6 },
  },
});

/* ─────────────────────────  网格纹理层  ───────────────────────── */
const GridPattern = styled(Box)({
  position: 'absolute',
  inset: 0,
  backgroundImage: `
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px)
  `,
  backgroundSize: '50px 50px',
  opacity: 0.25,
});

/* ─────────────────────────  导航卡片  ───────────────────────── */
const NavCard = styled(motion.div)({
  background: 'rgba(255, 255, 255, 0.08)',  // 提高背景亮度
  backdropFilter: 'blur(20px)',
  borderRadius: '24px',
  padding: '40px',
  border: '1px solid rgba(255, 255, 255, 0.15)',  // 边框更亮
  boxShadow: '0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1)',  // 添加内部高光
  cursor: 'pointer',
  position: 'relative',
  overflow: 'hidden',
  height: '400px',
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'space-between',
  width: '100%',
  maxWidth: '480px',
  '&::before': {
    content: '""',
    position: 'absolute',
    inset: 0,
    background: 'linear-gradient(135deg, transparent 0%, rgba(255, 255, 255, 0.08) 100%)',
    opacity: 0.3,
    transition: 'opacity 0.3s ease',
  },
  '&:hover::before': {
    opacity: 0.5,
  },
});

/* ─────────────────────────  图标背景  ───────────────────────── */
const IconWrapper = styled(Box)({
  width: '80px',
  height: '80px',
  borderRadius: '20px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: '24px',
  background: 'rgba(255, 255, 255, 0.1)',
  backdropFilter: 'blur(10px)',
});

/* ─────────────────────────  漂浮粒子  ───────────────────────── */
const FloatingParticle = styled(motion.div)<{ color: string }>(({ color }) => ({
  position: 'absolute',
  width: '4px',
  height: '4px',
  borderRadius: '50%',
  background: color,
  boxShadow: `0 0 10px ${color}`,
}));

/* ─────────────────────────  主组件  ───────────────────────── */
const MainNavigation: React.FC = () => {
  const navigate = useNavigate();
  const [particles, setParticles] = useState<
    Array<{ id: number; x: number; y: number; color: string }>
  >([]);

  /* 生成粒子 */
  useEffect(() => {
    const newParticles = Array.from({ length: 20 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      color: ['#6366f1', '#06b6d4', '#10b981', '#f59e0b'][
        Math.floor(Math.random() * 4)
      ],
    }));
    setParticles(newParticles);
  }, []);

  /* 导航配置 */
  const navigationItems = [
    {
      title: 'Market Analysis',
      subtitle: 'Deep dive into stocks, sectors, and market trends',
      description: 'Comprehensive financial analysis powered by AI agents',
      icon: <TrendingUpIcon sx={{ fontSize: 40 }} />,
      color: '#6366f1',
      path: '/analysis',
      features: ['Macro Analysis', 'Fundamental Research', 'Technical Indicators', 'Investment Strategy'],
    },
    {
      title: 'Fact Checker',
      subtitle: 'Verify news and statements with multi-layer AI validation',
      description: 'Real-time fact verification with source authentication',
      icon: <FactCheckIcon sx={{ fontSize: 40 }} />,
      color: '#10b981',
      path: '/verify',
      features: ['Source Verification', 'Video Analysis', 'Evidence Gathering', 'Decision Engine'],
    },
  ];

  /* ──────────────────── 渲染 ──────────────────── */
  return (
    <PageContainer>
      <AnimatedBackground />
      <GridPattern />

      {/* 粒子动画 */}
      <AnimatePresence>
        {particles.map((p) => (
          <FloatingParticle
            key={p.id}
            color={p.color}
            initial={{ x: `${p.x}%`, y: `${p.y}%` }}
            animate={{
              x: [`${p.x}%`, `${(p.x + 30) % 100}%`, `${p.x}%`],
              y: [`${p.y}%`, `${(p.y + 20) % 100}%`, `${p.y}%`],
            }}
            transition={{
              duration: 20 + Math.random() * 10,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        ))}
      </AnimatePresence>

      {/* 头部 & 卡片 */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100vw',
          maxWidth: '100vw',
          px: 4,
        }}
      >
        {/* 标题 */}
        <Box textAlign="center" mb={8}>
          <Box display="flex" alignItems="center" justifyContent="center" mb={4}>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            >
              <AutoGraphIcon sx={{ fontSize: 60, color: '#6366f1', mr: 2 }} />
            </motion.div>
            <Typography
              variant="h1"
              sx={{
                fontSize: { xs: '3rem', md: '4.5rem' },
                fontWeight: 900,
                background: 'linear-gradient(135deg, #6366f1 0%, #10b981 50%, #06b6d4 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.02em',
              }}
            >
              Fintegrate AI
            </Typography>
          </Box>
          <Typography
            variant="h5"
            sx={{
              color: 'rgba(255, 255, 255, 0.9)',  // 提高透明度
              fontWeight: 300,
              letterSpacing: '0.05em',
            }}
          >
            Advanced Financial Intelligence Platform
          </Typography>
        </Box>

        {/* 导航卡片区域 */}
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: 4,
          }}
        >
          {navigationItems.map((item) => (
            <NavCard
              key={item.title}
              whileHover={{ scale: 1.02, y: -5 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate(item.path)}
            >
              {/* 卡片主体 */}
              <Box>
                <IconWrapper sx={{ background: `${item.color}20` }}>
                  <Box sx={{ color: item.color }}>{item.icon}</Box>
                </IconWrapper>

                <Typography
                  variant="h3"
                  sx={{ 
                    fontSize: '2rem', 
                    fontWeight: 700, 
                    color: '#fff', 
                    mb: 1,
                    textShadow: '0 2px 4px rgba(0,0,0,0.3)'  // 添加文字阴影增强可读性
                  }}
                >
                  {item.title}
                </Typography>

                <Typography
                  variant="subtitle1"
                  sx={{
                    color: 'rgba(255, 255, 255, 1)',  // 完全不透明
                    mb: 2,
                    fontWeight: 500,
                    textShadow: '0 1px 2px rgba(0,0,0,0.2)'
                  }}
                >
                  {item.subtitle}
                </Typography>

                <Typography
                  variant="body2"
                  sx={{
                    color: 'rgba(255, 255, 255, 0.85)',  // 提高到 0.85
                    mb: 3,
                    lineHeight: 1.6,
                    textShadow: '0 1px 2px rgba(0,0,0,0.2)'
                  }}
                >
                  {item.description}
                </Typography>

                {/* 功能标签 */}
                <Box sx={{ mt: 'auto' }}>
                  {item.features.map((feat, i) => (
                    <Box
                      key={i}
                      sx={{ display: 'inline-flex', alignItems: 'center', mr: 2, mb: 1 }}
                    >
                      <VerifiedIcon sx={{ fontSize: 16, color: item.color, mr: 0.5 }} />
                      <Typography
                        variant="caption"
                        sx={{ 
                          color: 'rgba(255,255,255,0.9)',  // 提高到 0.9
                          textShadow: '0 1px 2px rgba(0,0,0,0.2)'
                        }}
                      >
                        {feat}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>

              {/* 底部 Explore 按钮行 */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mt: 3,
                }}
              >
                <Typography 
                  variant="button" 
                  sx={{ 
                    color: item.color, 
                    fontWeight: 600,
                    textShadow: `0 0 20px ${item.color}50`  // 添加发光效果
                  }}
                >
                  EXPLORE NOW
                </Typography>
                <IconButton
                  sx={{
                    background: `${item.color}20`,
                    color: item.color,
                    boxShadow: `0 0 20px ${item.color}30`,
                    '&:hover': { 
                      background: `${item.color}30`,
                      boxShadow: `0 0 30px ${item.color}50`
                    },
                  }}
                >
                  <ArrowForwardIcon />
                </IconButton>
              </Box>

              {/* 发光边框 */}
              <Box
                sx={{
                  position: 'absolute',
                  inset: 0,
                  borderRadius: '24px',
                  padding: '2px',
                  background: `linear-gradient(135deg, ${item.color}, transparent)`,
                  opacity: 0.5,
                  transition: 'opacity 0.3s ease',
                  '&:hover': { opacity: 1 },
                }}
              >
                <Box
                  sx={{
                    width: '100%',
                    height: '100%',
                    borderRadius: '22px',
                    background: 'rgba(0, 0, 0, 0.85)',  // 稍微透明一点让卡片更亮
                  }}
                />
              </Box>
            </NavCard>
          ))}
        </Box>
      </Box>
    </PageContainer>
  );
};

export default MainNavigation;