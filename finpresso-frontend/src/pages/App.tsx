// src/App.tsx
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// —— 先把面板元数据和类型导出 ——
// 注意：这里要用到的图标，需要先 import
import PublicIcon from '@mui/icons-material/Public';
import BusinessIcon from '@mui/icons-material/Business';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import InsightsIcon from '@mui/icons-material/Insights';

export type AnalysisBundle = {
  macro: any;
  micro: any;
  price: any;
  strategy: any;
};
export type PanelKey = keyof AnalysisBundle;
export const meta: Record<
  PanelKey,
  { title: string; color: string; Icon: React.FC<any> }
> = {
  macro:    { title: 'Macro Analysis',     color: '#6366f1', Icon: PublicIcon },
  micro:    { title: 'Fundamentals',        color: '#06b6d4', Icon: BusinessIcon },
  price:    { title: 'Technical Analysis',  color: '#10b981', Icon: ShowChartIcon },
  strategy: { title: 'Investment Strategy', color: '#f59e0b', Icon: InsightsIcon },
};

// 全局 axios 配置已经放到 src/utils/axiosConfig.ts
import axios from '../utils/axiosConfig';

// 自动滚动顶部的组件，放在 src/components/ScrollTop.tsx
import ScrollTop from '../components/ScrollTop';

// 下面三个组件和 App.tsx 在同一个目录
import Hero from './Hero';
import ProgressPage from './ProgressPage';
import DetailPage from './DetailPage';

// 新增：Mind Map 可视化页
import AnalysisResultPage from './InvestmentMindMap';

const queryClient = new QueryClient();

const App: React.FC = () => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      {/* 每次路由切换自动滚到顶部 */}
      <ScrollTop />

      <Routes>
        {/* 首页：搜索 ticker */}
        <Route path="/" element={<Hero />} />

        {/* 进度页：show loading bars & logs */}
        <Route path="/progress/:id" element={<ProgressPage />} />

        {/* 详情页：四个面板 (macro/micro/price/strategy) */}
        <Route path="/detail/:id/:panel" element={<DetailPage />} />

        {/* Mind-map 可视化页 */}
        <Route path="/mindmap/:job_id" element={<AnalysisResultPage />} />

        {/* 兜底重定向：其它路径都跳回首页 */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
);

export default App;
