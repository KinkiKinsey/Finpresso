import React, { useState, useEffect, useRef } from "react";
import {
  Box,
  Stack,
  Typography,
  TextField,
  Button,
  Chip,
  LinearProgress,
  IconButton,
  Tabs,
  Tab,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  Paper,
  Divider,
  Step,
  StepLabel,
  Stepper,
  Tooltip,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import PublicIcon from "@mui/icons-material/Public";
import BusinessIcon from "@mui/icons-material/Business";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import InsightsIcon from "@mui/icons-material/Insights";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import HomeIcon from "@mui/icons-material/Home";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { QueryClient, QueryClientProvider, useMutation, useQuery } from "@tanstack/react-query";
import axios from "axios";
import { BrowserRouter, Routes, Route, useNavigate, useParams, useLocation, Navigate } from "react-router-dom";
import FlagIcon from "@mui/icons-material/Flag";
import GaugeChart from "react-gauge-chart";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import InfoIcon from "@mui/icons-material/Info";
import StarIcon from "@mui/icons-material/Star";
import ArrowCircleRightIcon from "@mui/icons-material/ArrowCircleRight";
import { keyframes } from "@mui/material/styles";
import BoltIcon from "@mui/icons-material/Bolt";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import SouthEastIcon from "@mui/icons-material/SouthEast";
/* ---------- axios ---------- */
axios.defaults.baseURL = "http://localhost:8000";
axios.defaults.headers.common["X-API-KEY"] = "Wmx@20020413";


/* ---------- 工具 ---------- */
const queryClient = new QueryClient();
function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo({ top: 0 }), [pathname]);
  return null;
}

interface Props {
  text: string;
}
const SummaryBlock: React.FC<Props> = ({ text }) => {
  if (!text) return null;

  // 粗拆分行
  const lines = text.split(/\r?\n/).filter(Boolean);
  const title = lines[0]?.replace(/:+$/, "") ?? "Risk/Reward Analysis";
  const longLine = lines.find(l => l.toLowerCase().startsWith("long"));
  const shortLine = lines.find(l => l.toLowerCase().startsWith("short"));
  const recommended = (lines.find(l => l.toLowerCase().startsWith("recommended")) || "")
    .split(":")[1]
    ?.trim()
    .toUpperCase();

  // 提取数字
  const parseLine = (l?: string) => {
    if (!l) return { rr: "-", profit: "-", loss: "-" };
    const m = l.match(/R\/R\s*=\s*([-\d.]+).*?Profit\s*=\s*([-\d.]+).*?Loss\s*=\s*([-\d.]+)/i);
    return { rr: m?.[1] ?? "-", profit: m?.[2] ?? "-", loss: m?.[3] ?? "-" };
  };
  const long = parseLine(longLine);
  const short = parseLine(shortLine);

  return (
    <Box sx={{ mt: 3 }}>
      {/* 标题 */}
      <Typography
        variant="subtitle1"
        sx={{
          fontWeight: 700,
          mb: 2,
          background: "linear-gradient(90deg,#005F8C 0%,#00A8E0 100%)",
          WebkitBackgroundClip: "text",
          color: "transparent",
        }}
      >
        {title}
      </Typography>

      {/* KPI Grid */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
          gap: 2,
          mb: 2,
        }}
      >
        {/* Long */}
        <Paper
          variant="outlined"
          sx={{ p: 2, borderRadius: 2, borderColor: "#00A8E0" }}
        >
          <Stack direction="row" alignItems="center" spacing={1} mb={1}>
            <ArrowUpwardIcon sx={{ color: "#059669" }} />
            <Typography fontWeight={700}>LONG</Typography>
          </Stack>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            R/R:{" "}
            <Box component="span" sx={{ fontFamily: "Roboto Mono", fontWeight: 700 }}>
              {long.rr}
            </Box>
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5, color: "#059669" }}>
            Exp. Profit: {long.profit}
          </Typography>
          <Typography variant="body2" sx={{ color: "#B91C1C" }}>
            Exp. Loss: {long.loss}
          </Typography>
        </Paper>

        {/* Short */}
        <Paper
          variant="outlined"
          sx={{ p: 2, borderRadius: 2, borderColor: "#94A3B8" }}
        >
          <Stack direction="row" alignItems="center" spacing={1} mb={1}>
            <SouthEastIcon sx={{ color: "#B91C1C" }} />
            <Typography fontWeight={700}>SHORT</Typography>
          </Stack>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            R/R:{" "}
            <Box component="span" sx={{ fontFamily: "Roboto Mono", fontWeight: 700 }}>
              {short.rr}
            </Box>
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5, color: "#059669" }}>
            Exp. Profit: {short.profit}
          </Typography>
          <Typography variant="body2" sx={{ color: "#B91C1C" }}>
            Exp. Loss: {short.loss}
          </Typography>
        </Paper>
      </Box>

      {/* 推荐 Chip */}
      {recommended && (
        <Stack direction="row" justifyContent="center">
          <Chip
            label={`Recommended: ${recommended}`}
            color={recommended === "LONG" ? "success" : "error"}
            sx={{
              px: 2,
              fontWeight: 700,
              bgcolor: recommended === "LONG" ? "#059669" : "#B91C1C",
              color: "#fff",
            }}
          />
        </Stack>
      )}
    </Box>
  );
};

/* ---------- 类型 ---------- */
type AnalysisBundle = { macro: any; micro: any; price: any; strategy: any };
type PanelKey = keyof AnalysisBundle;
const meta: Record<PanelKey, { title: string; color: string; Icon: typeof PublicIcon }> = {
  macro: { title: "Macro Analysis", color: "#6366f1", Icon: PublicIcon },
  micro: { title: "Fundamentals", color: "#06b6d4", Icon: BusinessIcon },
  price: { title: "Technical Analysis", color: "#10b981", Icon: ShowChartIcon },
  strategy: { title: "Investment Strategy", color: "#f59e0b", Icon: InsightsIcon },
};

/** Strategy 面板所需的数据模型 */
export interface FancyData {
  /** 决策步骤流：通常 “Entry → Manage → Exit” */
  steps: { label: string; note?: string }[];

  /** 风险等级，用 0–1 归一化（0 = 极低风险, 1 = 极高风险） */
  riskScore: number;

  /** Risk / Reward 比例，>1 更优 */
  rrRatio: number;

  /** 止盈目标（%）——例如 12 代表 +12% */
  pnlTarget: number;

  /** 止损阈值（%）——例如 4 代表 -4% */
  stopLoss: number;

  /** 策略信心：low / med / high */
  conviction: "low" | "med" | "high";
}



/* ---------- 首页 ---------- */
const Hero: React.FC = () => {
  const [ticker, setTicker] = useState("");
  const navigate = useNavigate();
  const mCreate = useMutation({
    mutationFn: (t: string) =>
      axios.post("/api/v1/analysis", { ticker: t }).then((r) => r.data),
    onSuccess: (d) => navigate(`/progress/${d.job_id}`),
  });
  const hot = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOG", "AMZN"];
  return (
    <Box
      sx={{
        width: "100vw",
        height: "100vh",
        bgcolor: "#f5f9ff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        px: 2,
      }}
    >
      <Stack spacing={3} sx={{ width: { xs: "100%", sm: 480 } }}>
        <Typography
          variant="h3"
          fontWeight={700}
          sx={{
            background: "linear-gradient(90deg,#4f46e5 20%,#06b6d4 80%)",
            WebkitBackgroundClip: "text",
            color: "transparent",
          }}
        >
          Finpresso&nbsp;AI
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <TextField
            fullWidth
            placeholder="Search a ticker… e.g. NVDA"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
          />
          <Button
            variant="contained"
            disabled={!ticker}
            sx={{ minWidth: 120 }}
            onClick={() => mCreate.mutate(ticker)}
          >
            Analyze
          </Button>
        </Stack>
        <Stack
          direction="row"
          spacing={1}
          justifyContent="center"
          flexWrap="wrap"
        >
          {hot.map((t, i) => (
            <Chip
              key={i}
              label={t}
              color="primary"
              onClick={() => mCreate.mutate(t)}
              sx={{ animation: `float${i % 3} 6s ease-in-out infinite` }}
            />
          ))}
        </Stack>
      </Stack>
    </Box>
  );
};

/* ---------- 进度页 unchanged ---------- */
type StatusResp = {
  state: "pending" | "running" | "finished" | "error";
  message?: string;
  panel_progress: Record<PanelKey, number>;
  new_logs: string[];
  next_cursor: number;
};
const ProgressPage: React.FC = () => {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [cursor, setCursor] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const jumped = useRef(false);

  const qStatus = useQuery({
    queryKey: ["status", id],
    refetchInterval: 1500,
    queryFn: () =>
      axios
        .get<StatusResp>(`/api/v1/analysis/${id}/status`, { params: { cursor } })
        .then((r) => r.data),
    onSuccess: (d) => {
      setCursor(d.next_cursor);
      setLogs((old) => [...old, ...d.new_logs]);
    },
  });

  const st = qStatus.data;
  const prog = st?.panel_progress ?? {
    macro: 0,
    micro: 0,
    price: 0,
    strategy: 0,
  };
  const done = st?.state === "finished";

  useEffect(() => {
    if (done && !jumped.current) {
      jumped.current = true;
      navigate(`/detail/${id}/macro`, { replace: true });
    }
  }, [done]);

  return (
    <Box
      sx={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        textAlign: "center",
        px: 2,
      }}
    >
      <Typography variant="h5" gutterBottom>
        Running analysis
      </Typography>
      <Typography color="text.secondary" gutterBottom>
        {st?.message || "Waiting in queue…"}
      </Typography>

      <Stack
        direction="row"
        spacing={8}
        justifyContent="center"
        sx={{ mt: 8, mb: 4, flexWrap: "wrap" }}
      >
        {(Object.keys(meta) as PanelKey[]).map((k) => {
          const { color, Icon, title } = meta[k];
          return (
            <Stack key={k} spacing={1} alignItems="center" sx={{ width: 160 }}>
              <Icon sx={{ fontSize: 80, color }} />
              <LinearProgress
                variant="determinate"
                value={prog[k]}
                sx={{
                  width: "100%",
                  height: 8,
                  borderRadius: 5,
                  bgcolor: "#e5e7eb",
                  "& .MuiLinearProgress-bar": { bgcolor: color },
                }}
              />
              <Typography variant="body2">{title}</Typography>
            </Stack>
          );
        })}
      </Stack>

      <Box
        sx={{
          mt: 6,
          p: 2,
          maxHeight: 200,
          overflow: "auto",
          bgcolor: "#f3f4f6",
          borderRadius: 2,
          fontFamily: "monospace",
          fontSize: 12,
          textAlign: "left",
        }}
      >
        {logs.map((l, i) => (
          <div key={i}>{l}</div>
        ))}
      </Box>
    </Box>
  );
};

const glow = keyframes`
  from { box-shadow: 0 0 0 rgba(0,168,224,0); }
  to   { box-shadow: 0 0 8px 2px rgba(0,168,224,.45); }
`;

/* JPM 品牌蓝渐变 — 用于标题饰条/Chip 边框 */

const MacroPanel: React.FC<{ data: any }> = ({ data }) => (
  <Paper
    elevation={4}
    sx={{
      maxWidth: 960,
      mx: "auto",
      p: { xs: 3, md: 5 },
      borderRadius: 3,
      overflow: "hidden",
    }}
  >
    {/* ——— 概览条 • Info banner ——— */}
    <Alert
      icon={false}
      severity="info"
      sx={{
        mb: 4,
        bgcolor: "rgba(0,95,140,.06)",
        borderLeft: `6px solid #00A8E0`,
        "& .MuiAlert-message": { color: "#004B71", fontWeight: 600 },
      }}
    >
      {data.summary || "—"}
    </Alert>

    {/* ——— Key Indicators ——— */}
    <Accordion defaultExpanded disableGutters>
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          "& .MuiAccordionSummary-content": {
            alignItems: "center",
          },
          ".MuiAccordionSummary-content": {
            fontWeight: 700,
            "&::before": {
              content: '""',
              display: "block",
              width: 4,
              height: 20,
              mr: 1.5,
              background: JPM_GRAD,
              borderRadius: 2,
            },
          },
        }}
      >
        Key Indicators
      </AccordionSummary>

      <AccordionDetails sx={{ px: 0 }}>
        <List dense disablePadding>
          {Object.entries(data.key_indicators || {}).map(([k, v]) => (
            <ListItem key={k} sx={{ py: 1.2 }}>
              <ListItemIcon sx={{ minWidth: 28 }}>
                <BoltIcon sx={{ color: "#00A8E0" }} />
              </ListItemIcon>

              <ListItemText
                primary={
                  <Typography
                    variant="body2"
                    sx={{ color: "#4B5563", fontWeight: 600 }}
                  >
                    {k.replace(/_/g, " ")}
                  </Typography>
                }
                secondary={
                  <Typography
                    component="span"
                    sx={{
                      fontFamily: "Roboto Mono, monospace",
                      fontWeight: 700,
                      color: "#1F2937",
                    }}
                  >
                    {String(v)}
                  </Typography>
                }
              />
            </ListItem>
          ))}
        </List>
      </AccordionDetails>
    </Accordion>

    {/* ——— Catalysts / Watch-list Chips ——— */}
    <Accordion disableGutters sx={{ mt: 2 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={700}>Catalysts</Typography>
      </AccordionSummary>
      <AccordionDetails
        sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}
      >
        {(data.macro_catalysts || []).map((c: string, i: number) => (
          <Chip
            key={i}
            label={c}
            clickable
            sx={{
              fontWeight: 600,
              border: "1px solid transparent",
              borderImage: `${JPM_GRAD} 1`,
              bgcolor: "rgba(0,168,224,.05)",
              "&:hover": {
                animation: `${glow} .4s forwards`,
                cursor: "pointer",
              },
            }}
          />
        ))}
      </AccordionDetails>
    </Accordion>
  </Paper>
);


const MicroPanel: React.FC<{ data: any }> = ({ data }) => {
  // 1) 取出原始 Three_Key_Takeaways
  const raw = data.Three_Key_Takeaways;

  // 2) 规范成字符串数组，兼容 Array、String、Object
  let takeaways: string[] = [];
  if (Array.isArray(raw)) {
    takeaways = raw.map(item => String(item).trim()).filter(Boolean);
  } else if (typeof raw === "string") {
    takeaways = raw
      .split(/\r?\n+/)          // 按换行拆分
      .map(line => line.trim()) // 去两端空白
      .filter(Boolean);         // 丢掉空行
  } else if (raw && typeof raw === "object") {
    takeaways = Object.values(raw)
      .map(item => String(item).trim())
      .filter(Boolean);
  }

  return (
    <Box
      sx={{
        maxWidth: 900,
        mx: "auto",
        p: { xs: 3, md: 5 },
        borderRadius: 4,
        backdropFilter: "blur(18px)",
        background: "rgba(255,255,255,0.75)",
        border: "1px solid rgba(255,255,255,.6)",
        boxShadow: "0 10px 32px rgba(0,0,0,.06)",
        transition: "box-shadow .25s",
        "&:hover": { boxShadow: "0 14px 40px rgba(0,0,0,.12)" },
      }}
    >
      {/* —— Top Info Banner —— */}
      <Alert
        icon={<InfoIcon fontSize="inherit" />}
        severity="info"
        sx={{
          mb: 3,
          bgcolor: "rgba(99,102,241,.12)",
          ".MuiAlert-message": { fontSize: 18, fontWeight: 600 },
        }}
      >
        {data.Micro_Expectation || "—"}
      </Alert>

      {/* —— Three Key Takeaways —— */}
      <Card
        variant="outlined"
        sx={{
          borderRadius: 3,
          overflow: "hidden",
          ":before": {
            content: '""',
            display: "block",
            width: "100%",
            height: 4,
            background: "linear-gradient(90deg,#06b6d4 0%,#6366f1 100%)",
          },
        }}
      >
        <CardContent sx={{ pt: 3 }}>
          <Typography
            variant="subtitle1"
            sx={{ fontWeight: 700, mb: 2, letterSpacing: 0.2 }}
          >
            ✨ Three Key Takeaways
          </Typography>
          <List disablePadding>
            {takeaways.map((t, i) => (
              <ListItem key={i} sx={{ py: 1 }}>
                <ListItemIcon>
                  <StarIcon sx={{ color: "#10b981" }} />
                </ListItemIcon>
                <ListItemText
                  primaryTypographyProps={{
                    fontFamily: "Roboto Mono, monospace",
                    fontWeight: 700,
                  }}
                  primary={t}
                />
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>

      {/* —— Next-Step Hint —— */}
      {data.Next_Inference_Hint_Micro_News && (
        <Alert
          icon={<ArrowCircleRightIcon fontSize="inherit" />}
          severity="warning"
          sx={{
            mt: 3,
            bgcolor: "rgba(234,179,8,.15)",
            ".MuiAlert-message": { fontWeight: 600 },
          }}
        >
          {data.Next_Inference_Hint_Micro_News}
        </Alert>
      )}
    </Box>
  );
};

/* ---------- Price (Technical) Panel ---------- */
const GRAPHS_BASE = "http://localhost:8000/static/graphs";
const rel = (p?: string) => (p ? p.split("/").slice(-2).join("/") : "");

const nameMap: Record<string, string> = {
  ema_crossovers: "EMA Cross",
  sma_crossovers: "SMA Cross",
  risk_reward: "Risk • Reward",
  vw_macd: "VW-MACD",
};

/* ================================================ */

const JPM_GRAD = "linear-gradient(90deg,#005F8C 0%,#00A8E0 100%)";
const shine = keyframes`
  from { background-position: 0% }
  to   { background-position: 100% }
`;

const PricePanel: React.FC<{ data: any }> = ({ data }) => {
  /* ——— 图片 & 标签生成（逻辑与旧版*完全一致*） ——— */
  const raw = Object.values(data.graph_paths || {}) as string[];
  const imgs = raw.map((p) => {
    const r = rel(p);
    const key =
      Object.keys(nameMap).find((k) => r.includes(k)) || "chart";
    return { url: `${GRAPHS_BASE}/${r}`, label: nameMap[key] || "Chart" };
  });
  const [cur, setCur] = useState(imgs[0]?.url || "");

  if (!imgs.length)
    return (
      <Typography color="text.secondary">No charts generated.</Typography>
    );

  /* ——— UI 渲染（JPMorgan 白卡风） ——— */
  return (
    <Paper
      elevation={4}
      sx={{
        p: { xs: 3, md: 4 },
        borderRadius: 3,
        overflow: "hidden",
        "&:hover": { boxShadow: 8 },
      }}
    >
      {/* 顶部 3 px 品牌渐变饰条 */}
      <Box sx={{ height: 3, width: "100%", background: JPM_GRAD, mb: 3 }} />

      <Box
  sx={{
    /* 新：固定宽高比例且居中 */
    width: "96%",           // 留 2 % 左右白边
    maxWidth: 880,          // 大屏不会拉得更宽
    aspectRatio: "16 / 9",  // ⾯积自动撑满，⾼度≈56.25%
    position: "relative",
    mx: "auto",
    mb: 3,

    /* 旧浏览器 fallback */
    "@supports not (aspect-ratio: 16 / 9)": {
      height: 0,
      pt: "56.25%",
    },
  }}
>
  {imgs.map((img) => (
    <Box
      key={img.url}
      component="img"
      src={img.url}
      alt={img.label}
      sx={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "contain",
        display: img.url === cur ? "block" : "none",
      }}
    />
  ))}
</Box>

      {/* 切换按钮：选中渐变闪光 */}
      <Stack
        direction="row"
        spacing={2}
        justifyContent="center"
        flexWrap="wrap"
        mb={4}
      >
        {imgs.map((img) => (
          <Button
            key={img.url}
            onClick={() => setCur(img.url)}
            variant={img.url === cur ? "contained" : "outlined"}
            sx={{
              textTransform: "none",
              fontWeight: 600,
              px: 3,
              borderRadius: 20,
              ...(img.url === cur && {
                background: JPM_GRAD,
                backgroundSize: "200% 100%",
                animation: `${shine} 1s linear infinite alternate`,
                color: "#fff",
                border: "none",
              }),
            }}
          >
            {img.label}
          </Button>
        ))}
      </Stack>

      {/* 文字总结：品牌蓝标题 + 等宽正文 */}
      <Typography
        variant="h6"
        sx={{ fontWeight: 700, mb: 1, color: "#004B71" }}
      >
        Key Observations
      </Typography>
      <Divider sx={{ mb: 2 }} />
      <SummaryBlock text={data.risk_reward_summary} />
    </Paper>
  );
};
function toFancy(data: any): FancyData {
  const riskScoreMap: Record<string, number> = {
    LOW: 0.25,
    MEDIUM: 0.5,
    HIGH: 0.75,
  };
  return {
    /* —— 横向步骤 —— */
    steps: [
      { label: "ENTRY", note: (data.entry_signals || []).join(", ") },
      { label: "MANAGE", note: `Risk: ${data.risk_level}, Horizon: ${data.time_horizon}` },
      { label: "EXIT",  note: (data.exit_triggers || []).join(", ") },
    ],
    /* —— 仪表 & 数值 —— */
    riskScore: riskScoreMap[(data.risk_level || "MEDIUM").toUpperCase()] ?? 0.5,
    rrRatio:  data.expected_reward
      ? parseFloat(String(data.expected_reward)) / 15   // 简单映射，可按需调整
      : 1.5,
    pnlTarget: data.expected_reward
      ? parseFloat(String(data.expected_reward))
      : 10,
    stopLoss: 5,                // 后端暂无 → 固定占位
    conviction: (data.recommended_action === "BUY" || data.recommended_action === "LONG")
      ? "high"
      : data.recommended_action === "WAIT"
      ? "med"
      : "low",
  };
}
type StrategyData = {
  steps: { label: string; note?: string }[];
  riskScore: number;            // 0-1
  rrRatio: number;              // Risk/Reward
  pnlTarget: number;            // %
  stopLoss: number;             // %
  conviction: "low" | "med" | "high";
};

const convictionColor: Record<StrategyData["conviction"], string> = {
  low: "#eab308",   // amber-400
  med: "#6366f1",   // indigo-500
  high: "#10b981",  // emerald-500
};

const FancyStrategyPanel: React.FC<{ data: StrategyData }> = ({ data }) => (
  <Paper
    elevation={8}
    sx={{
      width: "100%",
      maxWidth: 1200,
      mx: "auto",
      p: { xs: 3, md: 5 },
      borderRadius: 4,
      backdropFilter: "blur(18px)",
      background: "rgba(255,255,255,0.7)",
      border: "1px solid rgba(255,255,255,.6)",
      boxShadow: "0 8px 24px rgba(0,0,0,.08)",
    }}
  >
    {/* —— 横向步骤流 —— */}
    <Stepper alternativeLabel sx={{ mb: 4 }}>
      {data.steps.map(({ label, note }, idx) => (
        <Step key={idx} completed={idx < data.steps.length - 1}>
          <Tooltip title={note || ""} arrow placement="top">
            <StepLabel
              StepIconComponent={() => (
                <Box
                  sx={{
                    width: 14,
                    height: 14,
                    borderRadius: "50%",
                    bgcolor:
                      idx === 0
                        ? "#06b6d4"
                        : idx === data.steps.length - 1
                        ? "#ef4444"
                        : "#6366f1",
                  }}
                />
              )}
            >
              <Typography variant="body2" fontWeight={600}>
                {label}
              </Typography>
            </StepLabel>
          </Tooltip>
        </Step>
      ))}
    </Stepper>

    <Divider sx={{ my: 3 }} />

    {/* —— 三列指标 —— */}
    <Stack
      direction={{ xs: "column", md: "row" }}
      spacing={4}
      justifyContent="space-between"
    >
      {/* ▸ Risk Gauge */}
      <Stack spacing={1} alignItems="center" sx={{ flex: 1 }}>
        <Typography variant="subtitle2" gutterBottom>
          Risk Level
        </Typography>
        <GaugeChart
          id="risk-gauge"
          nrOfLevels={5}
          colors={["#ef4444", "#f97316", "#eab308", "#84cc16", "#10b981"]}
          percent={data.riskScore}
          arcPadding={0.04}
          animate={false}
        />
      </Stack>

      {/* ▸ R/R Ratio */}
      <Stack spacing={1} alignItems="center" sx={{ flex: 1 }}>
        <Typography variant="subtitle2">Risk / Reward</Typography>
        <Typography
          sx={{
            fontSize: 36,
            fontFamily: "Roboto Mono, monospace",
            fontWeight: 700,
            color: data.rrRatio >= 2 ? "success.main" : "warning.main",
          }}
        >
          {data.rrRatio.toFixed(2)}
        </Typography>
        <LinearProgress
          variant="determinate"
          value={(Math.min(data.rrRatio, 3) / 3) * 100}
          sx={{
            width: "100%",
            height: 6,
            borderRadius: 3,
            bgcolor: "#e5e7eb",
            "& .MuiLinearProgress-bar": { bgcolor: "#6366f1" },
          }}
        />
      </Stack>

      {/* ▸ Price Targets */}
      <Stack spacing={1} alignItems="center" sx={{ flex: 1 }}>
        <Typography variant="subtitle2">Targets</Typography>
        <Chip
          icon={<TrendingUpIcon />}
          label={`TP ${data.pnlTarget}%`}
          color="success"
          sx={{ fontWeight: 600 }}
        />
        <Chip
          icon={<TrendingDownIcon />}
          label={`SL ${data.stopLoss}%`}
          color="error"
          sx={{ fontWeight: 600 }}
        />
      </Stack>
    </Stack>

    <Divider sx={{ my: 3 }} />

    {/* —— 投资者情绪/信心 —— */}
    <Stack direction="row" justifyContent="center" spacing={1}>
      <Chip
        icon={<FlagIcon />}
        label={`Conviction: ${data.conviction.toUpperCase()}`}
        sx={{
          bgcolor: convictionColor[data.conviction],
          color: "#fff",
          fontWeight: 700,
        }}
      />
    </Stack>
  </Paper>
);

/* ---------- 详情页 ---------- */



const DetailPage: React.FC = () => {  
  const { id = "", panel = "macro" } = useParams();  
  const navigate = useNavigate();  
  const [cur, setCur] = useState<PanelKey>(panel as PanelKey);  
  useEffect(() => setCur(panel as PanelKey), [panel]);  

  const { data } = useQuery<AnalysisBundle>({  
    queryKey: ["result", id],  
    queryFn: () => axios.get(`/api/v1/analysis/${id}/result`).then(r => r.data),  
  });  
  const bundle = data || ({} as AnalysisBundle);  

  const renderPanel = () => {  
    switch (cur) {  
      case "macro": return <MacroPanel data={bundle.macro || {}} />;  
      case "micro": return <MicroPanel data={bundle.micro || {}} />;  
      case "price": return <PricePanel data={bundle.price || {}} />;  
      case "strategy": return <FancyStrategyPanel data={toFancy(bundle.strategy || {})} />;  
      default: return null;  
    }  
  };  
  return (
    /* ===== 背景层：用 viewport 宽度撑满，并用 flex 居中 ===== */
    <Box
      component="main"
      sx={{
        width: "100vw",           // 一律按视口宽度算，甭管外层有多窄
        minHeight: "100vh",
        bgcolor: "#f5f7fc",
        display: "flex",
        justifyContent: "center", // 水平居中放下一层
        py: { xs: 4, md: 6 },
        boxSizing: "border-box",  // 让 padding 算在 width:100vw 里
      }}
    >
      {/* ===== 内容层：限制最大宽度，内部再自由排版 ===== */}
      <Box
        sx={{
          flexGrow: 1,            // 在超小屏时能自动拉伸
          maxWidth:  { xs: "100%", sm: "92vw", md: "86vw", xl: 1800 },         // 你想要的最大内容宽度
          px: { xs: 2, md: 4 },
          display: "flex",
          flexDirection: "column",
          gap: 3,
        }}
      >
        {/* ---------- 顶部导航 ---------- */}
        <Stack direction="row" alignItems="center" spacing={2}>
          <IconButton onClick={() => navigate(-1)}>
            <ArrowBackIcon />
          </IconButton>
          <IconButton onClick={() => navigate("/")}>
            <HomeIcon />
          </IconButton>
          <Typography variant="h5" fontWeight={700}>
            {meta[cur].title}
          </Typography>
        </Stack>
  
        {/* ---------- Tabs ---------- */}
        <Tabs
          value={cur}
          onChange={(_, v) => navigate(`/detail/${id}/${v}`)}
          textColor="primary"
          indicatorColor="primary"
          variant="scrollable"
          sx={{ "& .MuiTab-root": { fontWeight: 600, textTransform: "none" } }}
        >
          {(Object.keys(meta) as PanelKey[]).map((k) => (
            <Tab key={k} value={k} label={meta[k].title} />
          ))}
        </Tabs>
  
        {/* ---------- 主内容卡片 ---------- */}
        <Paper
          elevation={2}
          sx={{
            width: "100%",
            mx:"auto",
            maxWidth: { xs: "100%", lg: "86vw", xl: 1600 },
            p: { xs: 3, md: 5 },
            borderRadius: 3,
            backdropFilter: "blur(8px)",
            background: "rgba(255,255,255,0.85)",
          }}
        >
          {renderPanel()}
        </Paper>
      </Box>
    </Box>
  );
};


/* ---------- 根组件 ---------- */
const App: React.FC = () => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <ScrollTop />
      <Routes>
        <Route path="/" element={<Hero />} />
        <Route path="/progress/:id" element={<ProgressPage />} />
        <Route path="/detail/:id/:panel" element={<DetailPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
);

export default App;

/* ---------- 注入动画 ---------- */
const style = document.createElement("style");
style.innerHTML = `
@keyframes float0{0%{transform:translateY(0)}50%{transform:translateY(-4px)}100%{transform:translateY(0)}}
@keyframes float1{0%{transform:translateY(0)}50%{transform:translateY(-6px)}100%{transform:translateY(0)}}
@keyframes float2{0%{transform:translateY(0)}50%{transform:translateY(-8px)}100%{transform:translateY(0)}}
`;
document.head.appendChild(style);
