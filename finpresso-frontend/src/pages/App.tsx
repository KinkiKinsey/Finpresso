// src/pages/App.tsx
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate
} from 'react-router-dom';

// —— 面板元数据和类型（不改）
import PublicIcon    from '@mui/icons-material/Public';
import BusinessIcon  from '@mui/icons-material/Business';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import InsightsIcon  from '@mui/icons-material/Insights';

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
  macro:    { title: 'Macro Analysis',     color: '#6366f1', Icon: PublicIcon   },
  micro:    { title: 'Fundamentals',        color: '#06b6d4', Icon: BusinessIcon },
  price:    { title: 'Technical Analysis',  color: '#10b981', Icon: ShowChartIcon },
  strategy: { title: 'Investment Strategy', color: '#f59e0b', Icon: InsightsIcon  },
};

// 自动滚动顶部
import ScrollTop from '../components/ScrollTop';

// —— 同级导入页面组件 —— 
import Hero               from './Hero';
import ProgressPage       from './ProgressPage';
import DetailPage         from './DetailPage';
import AnalysisResultPage from './InvestmentMindMap';

import MainNavigation     from './MainNavigation';
import VerifySearch       from './VerifySearch';
import VerifyResult       from './VerifyResult';

const queryClient = new QueryClient();

const App: React.FC = () => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      {/* 切换路由时滚到顶部 */}
      <ScrollTop />

      <Routes>
        {/* 1. 根路径直接跳到主导航 */}
        <Route path="/" element={<Navigate to="/main" replace />} />

        {/* 2. 主导航 */}
        <Route path="/main" element={<MainNavigation />} />

        {/* 3. 市场分析相关（原有） */}
        <Route path="/analysis" element={<Hero />} />
        <Route path="/analysis/progress/:id" element={<ProgressPage />} />
        <Route path="/analysis/detail/:id/:panel" element={<DetailPage />} />
        <Route path="/analysis/mindmap/:job_id" element={<AnalysisResultPage />} />

        {/* 4. 事实核查相关 */}
        <Route path="/verify" element={<VerifySearch />} />
        <Route path="/verify/result/:sessionId" element={<VerifyResult />} />

        {/* 兜底：其它任何路径都跳回主导航 */}
        <Route path="*" element={<Navigate to="/main" replace />} />
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
);

export default App;
