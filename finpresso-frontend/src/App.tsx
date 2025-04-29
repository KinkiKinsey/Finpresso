/* eslint-disable react-hooks/exhaustive-deps */
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
} from "@mui/material";
import PublicIcon from "@mui/icons-material/Public";
import BusinessIcon from "@mui/icons-material/Business";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import InsightsIcon from "@mui/icons-material/Insights";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import HomeIcon from "@mui/icons-material/Home";
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
} from "@tanstack/react-query";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import {
  BrowserRouter,
  Routes,
  Route,
  useNavigate,
  useParams,
  useLocation,
  Navigate,
} from "react-router-dom";

/* ---------- axios ---------- */
axios.defaults.baseURL = "http://localhost:8000";

/* ---------- 工具 ---------- */
const queryClient = new QueryClient();
function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo({ top: 0 }), [pathname]);
  return null;
}

/* ---------- 类型 ---------- */
type AnalysisBundle = {
  macro: object;
  micro: object;
  price: object;
  strategy: object;
};
type PanelKey = keyof AnalysisBundle;
const meta: Record<
  PanelKey,
  { title: string; color: string; Icon: typeof PublicIcon }
> = {
  macro: { title: "Macro Analysis", color: "#6366f1", Icon: PublicIcon },
  micro: { title: "Fundamentals", color: "#06b6d4", Icon: BusinessIcon },
  price: { title: "Technical Analysis", color: "#10b981", Icon: ShowChartIcon },
  strategy: {
    title: "Investment Strategy",
    color: "#f59e0b",
    Icon: InsightsIcon,
  },
};

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

/* ---------- 进度页 ---------- */
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

/* ---------- 详情页 ---------- */
const DetailPage: React.FC = () => {
  const { id = "", panel = "macro" } = useParams();
  const navigate = useNavigate();
  const [ticker, setTicker] = useState("");
  const mCreate = useMutation({
    mutationFn: (t: string) =>
      axios.post("/api/v1/analysis", { ticker: t }).then((r) => r.data),
    onSuccess: (d) => navigate(`/progress/${d.job_id}`),
  });

  const qResult = useQuery({
    queryKey: ["result", id],
    queryFn: () =>
      axios.get(`/api/v1/analysis/${id}/result`).then((r) => r.data),
  });

  const res = qResult.data as AnalysisBundle | undefined;
  const data = res ? (res[panel as PanelKey] as object) : {};
  const isEmpty = !data || Object.keys(data).length === 0;
  const { title, color, Icon } = meta[panel as PanelKey];

  return (
    <Box sx={{ maxWidth: 960, mx: "auto", p: 3 }}>
      <Stack direction="row" alignItems="center" spacing={1} mb={3}>
        <IconButton onClick={() => navigate(-1)}>
          <ArrowBackIcon />
        </IconButton>
        <IconButton onClick={() => navigate("/")}>
          <HomeIcon />
        </IconButton>
        <Typography variant="h5">{title}</Typography>
        {/* 搜索框（可选） */}
        <TextField
          size="small"
          placeholder="New ticker"
          sx={{ width: 140, ml: "auto" }}
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
        />
        <Button
          size="small"
          variant="contained"
          disabled={!ticker}
          onClick={() => mCreate.mutate(ticker)}
        >
          Analyze
        </Button>
      </Stack>

      {isEmpty ? (
        <Typography color="text.secondary">No data available.</Typography>
      ) : (
        <ReactMarkdown>{jsonToMd(data, 0)}</ReactMarkdown>
      )}

      <Stack direction="row" spacing={2} mt={4} justifyContent="center">
        {(Object.keys(meta) as PanelKey[]).map((k) => {
          const { Icon, color } = meta[k];
          return (
            <Icon
              key={k}
              sx={{
                fontSize: 40,
                cursor: "pointer",
                color: k === panel ? color : "#9ca3af",
              }}
              onClick={() => navigate(`/detail/${id}/${k}`)}
            />
          );
        })}
      </Stack>
    </Box>
  );
};

/* ---------- JSON → Markdown ---------- */
function jsonToMd(obj: any, depth = 0): string {
  if (obj === null || obj === undefined) return "";
  const indent = "  ".repeat(depth);
  if (typeof obj !== "object") return `${indent}- ${String(obj)}\n`;
  return Object.entries(obj)
    .map(([k, v]) =>
      typeof v === "object" && v !== null
        ? `${indent}- **${k}**\n${jsonToMd(v, depth + 1)}`
        : `${indent}- **${k}**: ${String(v)}\n`
    )
    .join("");
}

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
