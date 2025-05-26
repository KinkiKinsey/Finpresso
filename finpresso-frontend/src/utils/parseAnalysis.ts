// src/utils/parseAnalysis.ts

/**
 * Parses raw back-end JSON and text analysis into structured data for the StockInsights page.
 * 全字段防御式处理，不会因为缺少文本抛错。
 */

// ----- Helpers ----

// 从 "Market_Cap = $3239.40B" 里提取数值（单位 B/M/T）
function parseMarketCap(val: string = ''): number {
  const m = val.match(/\$?([0-9.]+)\s*([MBT]?)/i);
  if (!m) return 0;
  const num = parseFloat(m[1]);
  const unit = m[2].toUpperCase();
  if (unit === 'T') return num * 1000;
  if (unit === 'M') return num / 1000;
  // 默认单位 B
  return num;
}

// 从 text.match 里拿数字
function extractNum(src: string, rx: RegExp): number {
  const m = src.match(rx);
  return m ? parseFloat(m[1]) : 0;
}

// ----- DCF -----
export interface DcfData {
  intrinsicValue: string;
  currentPrice: string;
  analysisText: string;
}
export function parseDcf(raw: string = ''): DcfData {
  const [p1 = '', p2 = ''] = raw.split(/PART\s*2:/i);
  const lines = p1.split('\n').map(l => l.trim());
  const getVal = (r: RegExp) =>
    lines.find(l => r.test(l))?.split('=').pop()?.trim() || '—';
  return {
    intrinsicValue: getVal(/DCF\s*(=|Value)/i),
    currentPrice:   getVal(/Stock[_\s]?Price/i),
    analysisText:   p2.trim(),
  };
}

// ----- Key Metrics -----
export interface KeyMetrics {
  price: string;
  beta: string;
  marketCap: string;
  range52: string;
}
export function parseKeyMetrics(
  raw: string = '',
  symbol: string
): KeyMetrics {
  const lines = raw
    .split('\n')
    .map(l => l.trim())
    .filter(l => l.startsWith('-'));
  const map: Record<string,string> = {};
  for (const l of lines) {
    const [kRaw, vRaw] = l.slice(1).split('=').map(s => s.trim());
    const key = kRaw
      .replace(new RegExp(symbol,'i'),'')
      .replace(/[_\s]+/g,'')
      .toLowerCase();
    map[key] = vRaw;
  }
  return {
    price:     map['price']      || '—',
    beta:      map['beta']       || '—',
    marketCap: map['mktcap']     || map['marketcap'] || '—',
    range52:   map['range']      || map['52wrange']   || '—',
  };
}

// ----- Financial Health -----
export interface FinancialHealth {
  cashReserves: string;
  operatingMargin: string;
  quickRatio: string;
  keyTakeaway: string;
}
export function parseFinancialHealth(raw: string = ''): FinancialHealth {
  const [p1 = '', p2 = ''] = raw.split(/PART\s*2:/i);
  const lines = p1.split('\n').map(l => l.trim());
  const getVal = (r: RegExp) =>
    lines.find(l => r.test(l))?.split('=').pop()?.trim() || '—';
  return {
    cashReserves:    getVal(/Free[_\s]?Cash[_\s]?Flow/i),
    operatingMargin: getVal(/Operating[_\s]?Margin/i),
    quickRatio:      getVal(/Quick[_\s]?Ratio/i),
    keyTakeaway:     p2.trim(),
  };
}

// ----- Peer Valuation -----
export interface Peer {
  name: string;
  forwardPE: number;
  marketCapNum: number;
}
export interface PeerValuation {
  forwardPE: number;
  peers: Peer[];
  analysisText: string;
}
export function parsePeerValuation(
  raw: string = '',
  symbol: string
): PeerValuation {
  const [p1 = '', p2 = ''] = raw.split(/PART\s*2:/i);

  // 主标的 forwardPE
  const mainPE = extractNum(
    p1,
    new RegExp(`${symbol}[\\s\\S]*?Forward[_\\s]?PE[_\\s]?Rank\\s*=\\s*([0-9.]+)`, 'i')
  );

  // peers array
  const peers: Peer[] = [];
  // 匹配 "- AVGO Price = ..., Market_Cap = $1083.94B, Forward_PE_Rank = 0.933333"
  const peerRe = /-\s*([A-Za-z0-9]+)[\s\S]*?Market[_\s]?Cap\s*=\s*\$?([0-9.]+[MBT]?)[\s\S]*?Forward[_\s]?PE[_\s]?Rank\s*=\s*([0-9.]+)/gi;
  let m: RegExpExecArray | null;
  while ((m = peerRe.exec(p1)) !== null) {
    const [, name, capRaw, peRaw] = m;
    if (name.toUpperCase() === symbol.toUpperCase()) continue;
    peers.push({
      name,
      forwardPE: parseFloat(peRaw),
      marketCapNum: parseMarketCap(capRaw),
    });
  }

  // 按市值降序，取前三
  peers.sort((a, b) => b.marketCapNum - a.marketCapNum);
  const topPeers = peers.slice(0, 3);

  return {
    forwardPE:    mainPE,
    peers:        topPeers,
    analysisText: p2.replace(/^ANALYSIS\s*/i, '').trim(),
  };
}

// ----- Peer Radar Data -----
export interface PeerRadarPoint {
  metric: string;
  [ticker: string]: number | string;
}
export function parsePeerRadar(
  toolResults: Record<string, any>,
  symbol: string,
  peerSymbols: string[]
): PeerRadarPoint[] {
  const metricsRaw  = toolResults.get_stock_metrics?.result || '';
  const betaRaw     = toolResults.get_stock_beta?.result || '';
  const peerBetaRaw = toolResults.get_peer_beta_comparison?.result || '';
  const peerValRaw  = toolResults.get_peer_valuation_comparison?.result || '';

  // 拿到 PeerValuation.peers（已限3家）
  const pv = parsePeerValuation(peerValRaw, symbol);
  const peerPEMap = Object.fromEntries(
    pv.peers.map(p => [p.name, p.forwardPE])
  );

  const METRICS = [
    'Revenue Growth',
    'Beta',
    'ROIC',
    'Forward PE',
    'Debt/Equity',
  ] as const;

  return METRICS.map(metric => {
    const pt: PeerRadarPoint = { metric };

    // 主标的
    let baseVal = 0;
    switch (metric) {
      case 'Revenue Growth':
        baseVal = extractNum(metricsRaw, /Revenue[_\s]?Growth[^0-9]*([0-9.]+)/i);
        break;
      case 'ROIC':
        baseVal = extractNum(metricsRaw, /ROIC[^0-9]*([0-9.]+)/i);
        break;
      case 'Debt/Equity':
        baseVal = extractNum(metricsRaw, /Debt[_\s]?to[_\s]?Equity[^0-9]*([0-9.]+)/i);
        break;
      case 'Forward PE':
        baseVal = pv.forwardPE;
        break;
      case 'Beta':
        baseVal = extractNum(betaRaw, /Beta[^0-9]*([0-9.]+)/i);
        break;
    }
    pt[symbol] = +baseVal.toFixed(2);

    // peers
    for (const peer of pv.peers) {
      let v = 0;
      switch (metric) {
        case 'Forward PE':
          v = peerPEMap[peer.name] || 0;
          break;
        case 'Beta':
          v = extractNum(
            peerBetaRaw,
            new RegExp(`${peer.name}[\\s\\S]*?Beta[^0-9]*([0-9.]+)`, 'i')
          );
          break;
        // 其余项目只显示主标的
      }
      pt[peer.name] = +v.toFixed(2);
    }

    return pt;
  });
}

// ----- Earnings Surprises -----
export interface EarningsSurprise {
  date: string;
  actual: number;
  estimate: number;
  beat: boolean;
}
export function parseEarningsSurprises(raw: string = ''): EarningsSurprise[] {
  return raw
    .split('\n')
    .map(l => l.trim())
    .filter(l => /^-\s*\d{4}-\d{2}-\d{2}/.test(l))
    .map(line => {
      const m = line.match(
        /-\s*(\d{4}-\d{2}-\d{2}):\s*Actual\s*=\s*\$?([0-9.]+)[\s\S]*?Estimate(?:d)?\s*=\s*\$?([0-9.]+)/i
      );
      if (!m) return null;
      const [, date, a, e] = m;
      const act = parseFloat(a);
      const est = parseFloat(e);
      return { date, actual: act, estimate: est, beat: act >= est };
    })
    .filter((x): x is EarningsSurprise => x != null);
}

// ----- Earnings Summary -----
export interface EarningsSummary {
  beats: number;
  misses: number;
  beatRate: number;           // 百分比
  avgSurprisePercent: number; // 百分比
}
export function summarizeEarnings(
  recs: EarningsSurprise[]
): EarningsSummary {
  const beats  = recs.filter(r => r.beat).length;
  const total  = recs.length;
  const misses = total - beats;
  const beatRate = total ? +((beats/total)*100).toFixed(2) : 0;
  const avgSurprisePercent = total
    ? +(recs
        .map(r => ((r.actual - r.estimate)/r.estimate)*100)
        .reduce((a,b) => a+b, 0) / total
      ).toFixed(2)
    : 0;
  return { beats, misses, beatRate, avgSurprisePercent };
}

// ----- Micro -----
export interface MicroData {
  threeKeyTakeaways: string[];
  microExpectation: string;
  nextInferenceHint: string;
  reasoning: string;
  toolsUsed: string[];
}
export function parseMicro(raw: any = {}): MicroData {
  return {
    threeKeyTakeaways: raw.Three_Key_Takeaways               || [],
    microExpectation:  raw.Micro_Expectation                 || '',
    nextInferenceHint: raw.Next_Inference_Hint_Micro_News    || '',
    reasoning:         raw.reasoning                         || '',
    toolsUsed:         raw.tools_used || raw.toolsUsed || [],
  };
}

// ----- Aggregator -----
export interface ParsedAnalysis {
  dcf: DcfData;
  keyMetrics: KeyMetrics;
  financial: FinancialHealth;
  peerValuation: PeerValuation;
  peerRadar: PeerRadarPoint[];
  earnings: EarningsSurprise[];
  earningsSummary: EarningsSummary;
  micro: MicroData;
}
export function parseAnalysis(
toolResults: Record<string, any> = {}, microRaw: any = {}, symbol: string, p0: never[]): ParsedAnalysis {
  const dcf           = parseDcf(toolResults.get_stock_dcf_valuation?.result);
  const keyMetrics    = parseKeyMetrics(toolResults.get_company_profile?.result, symbol);
  const financial     = parseFinancialHealth(toolResults.get_stock_metrics?.result);
  const peerValuation = parsePeerValuation(
                          toolResults.get_peer_valuation_comparison?.result,
                          symbol
                        );

  // 3 家市值最大的 peers
  const peerRadar     = parsePeerRadar(toolResults, symbol, peerValuation.peers.map(p => p.name));

  const earnings        = parseEarningsSurprises(toolResults.get_earnings_surprises?.result);
  const earningsSummary = summarizeEarnings(earnings);

  const micro           = parseMicro(microRaw);

  return {
    dcf,
    keyMetrics,
    financial,
    peerValuation,
    peerRadar,
    earnings,
    earningsSummary,
    micro,
  };
}
