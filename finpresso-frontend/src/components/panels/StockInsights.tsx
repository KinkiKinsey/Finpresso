// src/components/panels/StockInsights.tsx
import React from 'react';
import { Helmet } from 'react-helmet';
import { parseAnalysis, ParsedAnalysis } from '../../utils/parseAnalysis';

interface StockInsightsPageProps {
  /** 原始 micro 面板数据（来自 status 接口的 panel_data.micro） */
  microRaw: any;
  /** 股票代码 */
  symbol: string;
}

const StockInsightsPage: React.FC<StockInsightsPageProps> = ({ microRaw, symbol }) => {
  // 从 microRaw 里取出各工具的结果
  const toolResults = microRaw.tool_results ?? {};
  // 调用 parseAnalysis 得到所有我们需要的字段
  const parsed: ParsedAnalysis = parseAnalysis(
    toolResults,
    microRaw,
    symbol,
    [] // peerSymbols 留空，下面会自动从 parsed.peerRadar 推出
  );

  const {
    dcf,
    keyMetrics,
    financial,
    peerValuation,
    peerRadar,
    earnings,
    earningsSummary,
  } = parsed;

  // 推出所有 peer tickers（包含主 symbol）
  const peerSymbols = peerRadar.length > 0
    ? Object.keys(peerRadar[0]).filter(k => k !== 'metric')
    : [];

  // 计算拨盘角度（-90° 到 +90°）
  const iv = parseFloat(dcf.intrinsicValue.replace(/[$,]/g, '')) || 0;
  const cp = parseFloat(dcf.currentPrice.replace(/[$,]/g, '')) || 0;
  const ratio = iv > 0 ? Math.min(cp / iv, 1) : 0;
  const angle = -90 + ratio * 180;

  // 计算雷达图每个指标的极坐标方向
  const metrics = peerRadar.map(pt => pt.metric);
  const angleStep = (2 * Math.PI) / metrics.length;
  const coords = metrics.reduce((acc, m, i) => {
    const a = -Math.PI / 2 + i * angleStep;
    acc[m] = { x: Math.cos(a), y: Math.sin(a) };
    return acc;
  }, {} as Record<string, { x: number; y: number }>);

  return (
    <>
      <Helmet>
        <meta charSet="utf-8" />
        <title>{symbol} Stock Analysis</title>
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?display=swap&family=Noto+Sans:wght@400;500;700;900&family=Space+Grotesk:wght@400;500;700"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"
          rel="stylesheet"
        />
        <style>{`
          .tooltip { position: relative; display: inline-block; }
          .tooltip .tooltiptext {
            visibility: hidden; width: 160px; background-color: #161B22; color: #fff;
            text-align: center; border-radius: 6px; padding: 5px 0;
            position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -80px;
            opacity: 0; transition: opacity 0.3s; font-size: 0.75rem;
            border: 1px solid #38e07b;
          }
          .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
          .dial-container { width: 200px; height: 100px; position: relative; overflow: hidden; }
          .dial-bg { width: 200px; height: 100px; border-radius: 100px 100px 0 0;
            background: conic-gradient(from -90deg at 50% 100%, #ef4444 0%, #f97316 25%, #eab308 50%, #84cc16 75%, #22c55e 100%);
            position: absolute; top: 0; left: 0;
          }
          .dial-mask {
            width: 180px; height: 90px; background: #010409;
            border-radius: 90px 90px 0 0; position: absolute; top: 10px; left: 10px;
          }
          .dial-needle {
            width: 4px; height: 85px; background: #38e07b;
            position: absolute; bottom: 5px; left: 50%; transform-origin: 50% 100%;
            transition: transform 0.5s ease-in-out;
            border-radius: 2px;
          }
          .dial-center-dot {
            width: 10px; height: 10px; background: #38e07b;
            border-radius: 50%; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
          }
          .sparkline-container { width: 100px; height: 30px; }
          .radar-chart-container { width: 100%; max-width: 400px; margin: auto; position: relative; }
          .radar-chart-axis { stroke: #374151; stroke-width: 1; }
          .radar-chart-label { fill: #9ca3af; font-size: 0.7rem; text-anchor: middle; }
          .radar-chart-polygon { stroke-width: 2; fill-opacity: 0.3; }
        `}</style>
      </Helmet>

      <div
        className="bg-[#0D1117] text-white min-h-screen flex flex-col overflow-x-hidden"
        style={{ fontFamily: '"Space Grotesk", "Noto Sans", sans-serif' }}
      >
        {/* HEADER */}
        {/* 精简后的 Header */}
        <header className="sticky top-0 z-50 bg-[#0D1117]/80 backdrop-blur-md border-b border-[#161B22]">
          <div className="container mx-auto px-10 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3 text-[#38e07b]">
              <span className="material-symbols-outlined text-3xl">insights</span>
              <h2 className="text-xl font-bold tracking-wider">StockInsights</h2>
            </div>
            {/* 右侧仅保留搜索框 */}
            <div className="relative w-80 h-10">
              <div className="absolute inset-y-0 left-0 flex items-center pl-3">
                <span className="material-symbols-outlined text-gray-400">search</span>
              </div>
              <input
                className="w-full h-full rounded-lg bg-[#010409] border border-[#161B22] placeholder-gray-500 text-gray-200 pl-10 focus:outline-none focus:ring-2 focus:ring-[#38e07b] text-sm"
                placeholder="Search Stocks..."
                type="text"
              />
            </div>
          </div>
        </header>


        {/* MAIN */}
        <main className="flex-1 px-10 lg:px-20 xl:px-40 py-8 flex justify-center">
          <div className="max-w-[1280px] w-full">
            <div className="flex flex-wrap justify-between items-center gap-3 mb-6 p-4">
              <h1 className="text-4xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-[#38e07b] to-[#00A3FF]">
                {symbol} Stock Analysis
              </h1>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* LEFT TWO COLUMNS */}
              <div className="lg:col-span-2 space-y-8">
                {/* DCF Valuation */}
                <section className="bg-[#010409] border border-[#161B22] rounded-xl p-6 shadow-xl hover:border-[#38e07b] transition transform hover:-translate-y-1">
                  <h2 className="flex items-center gap-2 text-2xl font-semibold text-[#00A3FF] mb-4">
                    <span className="material-symbols-outlined">analytics</span>
                    DCF Valuation Analysis
                  </h2>
                  <div className="md:flex md:items-center gap-6">
                    <div className="flex-1">
                      <p className="text-gray-300 mb-4 leading-relaxed">
                        The Discounted Cash Flow (DCF) valuation model projects {symbol}'s intrinsic value. Our analysis indicates an intrinsic value of{' '}
                        <strong className="text-[#38e07b]">{dcf.intrinsicValue}</strong> compared to the current price of{' '}
                        <strong className="text-[#38e07b]">{dcf.currentPrice}</strong>. This suggests potential mispricing.
                      </p>
                      <p className="text-gray-400 text-xs mb-4">Key assumptions: WACC 10%, Terminal Growth Rate 3%.</p>
                      <div className="mt-4 p-4 bg-[#0D1117] border border-[#38e07b]/50 rounded-lg">
                        <p className="text-sm text-[#38e07b] font-semibold">Key Takeaway:</p>
                        <p className="text-gray-200 text-sm">{dcf.analysisText}</p>
                      </div>
                    </div>
                    <div className="flex flex-col items-center">
                      <div className="dial-container mb-2">
                        <div className="dial-bg" />
                        <div className="dial-mask" />
                        <div className="dial-needle" style={{ transform: `translateX(-50%) rotate(${angle}deg)` }} />
                        <div className="dial-center-dot" />
                      </div>
                      <div className="flex justify-between w-full text-xs text-gray-400 px-2">
                        <span>Undervalued</span>
                        <span>Fair Value</span>
                        <span>Overvalued</span>
                      </div>
                    </div>
                  </div>
                </section>

                {/* Peer Valuation */}
                <section className="bg-[#010409] border border-[#161B22] rounded-xl p-6 shadow-xl hover:border-[#38e07b] transition transform hover:-translate-y-1">
                  <h2 className="flex items-center gap-2 text-2xl font-semibold text-[#00A3FF] mb-4">
                    <span className="material-symbols-outlined">compare_arrows</span>
                    Peer Valuation Comparison Analysis
                  </h2>
                  <p className="text-gray-300 leading-relaxed mb-4">Forward P/E: {peerValuation.forwardPE}</p>
                  {peerValuation.peers.map(p => (
                    <p key={p.name} className="text-gray-200 text-sm">
                      {p.name}: {p.forwardPE}
                    </p>
                  ))}
                  <div className="mt-4 p-4 bg-[#0D1117] border border-[#00A3FF]/50 rounded-lg">
                    <p className="text-sm text-[#00A3FF] font-semibold">Key Takeaway:</p>
                    <p className="text-gray-200 text-sm">{peerValuation.analysisText}</p>
                  </div>
                </section>

                {/* Financial Health */}
                <section className="bg-[#010409] border border-[#161B22] rounded-xl p-6 shadow-xl hover:border-[#38e07b] transition transform hover:-translate-y-1">
                  <h2 className="flex items-center gap-2 text-2xl font-semibold text-[#38e07b] mb-6">
                    <span className="material-symbols-outlined">ssid_chart</span>
                    Financial Health & Growth Analysis
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
                    {/* Cash Reserves */}
                    <div className="tooltip">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-sm text-gray-300 font-medium">Cash Reserves</span>
                        <span className="text-sm text-[#38e07b] font-semibold">{financial.cashReserves}</span>
                      </div>
                      <div className="w-full bg-[#161B22] rounded-full h-2.5">
                        <div className="h-2.5 rounded-full bg-gradient-to-r from-[#38e07b] to-[#00A3FF]" style={{ width: '80%' }} />
                      </div>
                      <span className="tooltiptext">Total cash and cash equivalents.</span>
                    </div>
                    {/* Operating Margin */}
                    <div className="tooltip">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-sm text-gray-300 font-medium">Operating Margin</span>
                        <span className="text-sm text-[#38e07b] font-semibold">{financial.operatingMargin}</span>
                      </div>
                      <div className="w-full bg-[#161B22] rounded-full h-2.5">
                        <div className="h-2.5 rounded-full bg-gradient-to-r from-[#38e07b] to-[#00A3FF]" style={{ width: '65%' }} />
                      </div>
                      <span className="tooltiptext">Efficiency in generating profit from core operations.</span>
                    </div>
                    {/* Quick Ratio */}
                    <div className="tooltip">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-sm text-gray-300 font-medium">Quick Ratio</span>
                        <span className="text-sm text-[#38e07b] font-semibold">{financial.quickRatio}</span>
                      </div>
                      <div className="w-full bg-[#161B22] rounded-full h-2.5 mb-1">
                        <div className="h-2.5 rounded-full bg-gradient-to-r from-[#38e07b] to-[#00A3FF]" style={{ width: '70%' }} />
                      </div>
                      <span className="tooltiptext">Ability to meet short-term obligations.</span>
                    </div>
                  </div>
                </section>
              </div>

              {/* ASIDE: Key Metrics, Radar, Earnings */}
              <aside className="space-y-8">
                {/* Key Metrics */}
                <section className="mb-10">
                  <h2 className="flex items-center gap-2 text-2xl font-semibold text-[#38e07b] border-b border-[#161B22] pb-4 px-4 mb-6">
                    <span className="material-symbols-outlined">monitoring</span> Key Metrics
                  </h2>
                  <div className="grid grid-cols-2 gap-4 p-4">
                    {[
                      ['Price', keyMetrics.price, 'Latest closing price.'],
                      ['Beta', keyMetrics.beta, 'Market volatility (>1 higher).'],
                      ['Market Cap', keyMetrics.marketCap, 'Total market value.'],
                      ['52-Wk Range', keyMetrics.range52, '52-week high / low.'],
                    ].map(([label, value, tip]) => (
                      <div key={label} className="tooltip bg-[#010409] border border-[#161B22] rounded-lg p-4 hover:border-[#38e07b] transition">
                        <p className="text-gray-400 text-xs font-medium">{label}</p>
                        <p className={`text-2xl font-bold ${label === 'Beta' ? 'text-white' : 'text-[#38e07b]'}`}>
                          {value}
                        </p>
                        <span className="tooltiptext">{tip}</span>
                      </div>
                    ))}
                  </div>
                </section>

                {/* Peer Radar */}
                <section className="mb-10">
                  <h2 className="flex items-center gap-2 text-2xl font-semibold text-[#00A3FF] border-b border-[#161B22] pb-4 px-4 mb-6">
                    <span className="material-symbols-outlined">groups</span> Peer Comparison
                  </h2>
                  <div className="radar-chart-container bg-[#010409] p-4 rounded-lg">
                    <svg viewBox="0 0 300 300" className="w-full h-auto">
                      <defs>
                        {peerSymbols.map(tkr => (
                          <radialGradient
                            key={tkr}
                            id={`radarGradient${tkr}`}
                            cx="50%"
                            cy="50%"
                            r="50%"
                          >
                            <stop offset="0%" stopColor={tkr === symbol ? '#38e07b' : '#38bdf8'} stopOpacity={0.7} />
                            <stop offset="100%" stopColor={tkr === symbol ? '#38e07b' : '#38bdf8'} stopOpacity={0.2} />
                          </radialGradient>
                        ))}
                      </defs>
                      <g transform="translate(150,150)">
                        {[30, 60, 90, 120].map(r => (
                          <circle key={r} className="radar-chart-axis" cx={0} cy={0} r={r} fill="none" />
                        ))}
                        {/* 轴线 & 标签 */}
                        {metrics.map((m, i) => {
                          const a = -Math.PI/2 + i*angleStep;
                          const x = Math.cos(a)*120;
                          const y = Math.sin(a)*120;
                          return (
                            <React.Fragment key={m}>
                              <line className="radar-chart-axis" x1={0} y1={0} x2={x} y2={y} />
                              <text className="radar-chart-label" x={x*1.1} y={y*1.1}>{m}</text>
                            </React.Fragment>
                          );
                        })}
                        {/* 多边形 */}
                        {peerSymbols.map(tkr => {
                          const pts = peerRadar.map(pt => {
                            const norm = Math.max(...peerRadar.map(r => r[tkr] as number)) || 1;
                            const rVal = (pt[tkr] as number) / norm * 120;
                            const { x, y } = coords[pt.metric];
                            return `${x * rVal},${y * rVal}`;
                          }).join(' ');
                          return (
                            <polygon
                              key={tkr}
                              className="radar-chart-polygon"
                              fill={`url(#radarGradient${tkr})`}
                              stroke={tkr === symbol ? '#38e07b' : '#38bdf8'}
                              points={pts}
                            />
                          );
                        })}
                      </g>
                    </svg>
                    {/* Legend */}
                    <div className="flex justify-center space-x-4 mt-4 text-xs">
                      {peerSymbols.map(tkr => (
                        <div key={tkr} className="flex items-center gap-1">
                          <span
                            className="h-3 w-3 rounded-full"
                            style={{ backgroundColor: tkr === symbol ? '#38e07b' : '#38bdf8' }}
                          /> {tkr}
                        </div>
                      ))}
                    </div>
                  </div>
                </section>

                {/* Earnings Surprises */}
                <section className="mb-10">
                  <h2 className="flex items-center gap-2 text-2xl font-semibold text-[#38e07b] border-b border-[#161B22] pb-4 px-4 mb-6">
                    <span className="material-symbols-outlined">trending_up</span> Earnings Surprises
                  </h2>
                  <div className="relative px-4 py-6">
                    <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-[#161B22]" />
                    <div className="space-y-6">
                      {earnings.map(e => (
                        <div key={e.date} className="relative pl-12 group">
                          <div
                            className={`absolute left-0 top-1.5 flex items-center justify-center size-8 rounded-full border-4 border-[#0D1117] transition-transform ${
                              e.beat ? 'bg-[#38e07b]' : 'bg-red-500'
                            } group-hover:scale-110`}
                          />
                          <div
                            className={`bg-[#010409] border border-[#161B22] rounded-lg p-3 shadow-md transition-colors tooltip ${
                              e.beat ? 'hover:border-[#38e07b]' : 'hover:border-red-500'
                            }`}
                          >
                            <p className="text-white text-sm font-medium">
                              {`${e.date} - ${e.beat ? 'Beat' : 'Missed'}`}
                            </p>
                            <span className="tooltiptext">
                              EPS: ${e.actual} vs Est. ${e.estimate}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <p className="text-gray-400 text-xs leading-relaxed pb-3 pt-1 px-4">
                    {symbol}'s earnings history shows{' '}
                    <strong className="text-[#38e07b]">{earningsSummary.beats} beats</strong> and{' '}
                    <strong className="text-red-500">{earningsSummary.misses} misses</strong> in the last{' '}
                    {earnings.length} quarters.
                  </p>
                </section>
              </aside>
            </div>
          </div>
        </main>

        {/* FOOTER */}
        <footer className="text-center p-6 text-xs text-gray-500 border-t border-[#161B22]">
          © 2025 StockInsights. All rights reserved. Data provided for informational purposes only.
        </footer>
      </div>
    </>
  );
};

export default StockInsightsPage;
