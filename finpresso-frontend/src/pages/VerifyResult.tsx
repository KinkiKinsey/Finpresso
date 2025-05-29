// src/VerifyResult.tsx
import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Box,
  Typography,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  CircularProgress,
  Chip,
  Link,
} from "@mui/material";
import { styled } from "@mui/material/styles";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import VisibilityIcon from "@mui/icons-material/Visibility";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import BoltIcon from "@mui/icons-material/Bolt";
import VideocamIcon from "@mui/icons-material/Videocam";
import PsychologyIcon from "@mui/icons-material/Psychology";
import PublicIcon from "@mui/icons-material/Public";
import GavelIcon from "@mui/icons-material/Gavel";
import SkipNextIcon from "@mui/icons-material/SkipNext";
import ReactJson from "react-json-view";

/* ───────── 全局容器 / 返回按钮 ───────── */
const PageContainer = styled(Box)({
  minHeight: "100vh",
  background: "linear-gradient(135deg,#0a0a0a 0%,#0f172a 100%)",
  position: "relative",
});

const BackButton = styled(IconButton)({
  position: "absolute",
  top: "2rem",
  left: "2rem",
  background: "rgba(255,255,255,0.05)",
  backdropFilter: "blur(10px)",
  border: "1px solid rgba(255,255,255,0.1)",
  color: "#fff",
  zIndex: 10,
  "&:hover": { background: "rgba(255,255,255,0.1)" },
});

/* ───────── FilterCard / StatusCircle / FinalResultCard ───────── */
const FilterCard = styled(motion.div, {
  shouldForwardProp: (prop) => prop !== "status",
})<{ status: string }>(({ status }) => ({
  background: "rgba(255,255,255,0.05)",
  backdropFilter: "blur(20px)",
  borderRadius: 16,
  padding: 24,
  border: `2px solid ${
    status === "passed"
      ? "rgba(16,185,129,.5)"
      : status === "failed"
      ? "rgba(239,68,68,.5)"
      : status === "processing"
      ? "rgba(6,182,212,.5)"
      : status === "skipped"
      ? "rgba(107,114,128,.3)"
      : "rgba(255,255,255,.1)"
  }`,
  position: "relative",
  overflow: "hidden",
  transition: "all 0.3s ease",
  "&::before": {
    content: '""',
    position: "absolute",
    inset: 0,
    background: status === "processing" 
      ? "linear-gradient(90deg, transparent, rgba(6, 182, 212, 0.3), transparent)"
      : "none",
    animation: status === "processing" ? "shimmer 2s infinite" : "none",
  },
  "@keyframes shimmer": {
    "0%": { transform: "translateX(-100%)" },
    "100%": { transform: "translateX(100%)" },
  },
}));

const StatusCircle = styled(Box, {
  shouldForwardProp: (prop) => prop !== "status",
})<{ status: string }>(({ status }) => ({
  width: 60,
  height: 60,
  borderRadius: "50%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background:
    status === "passed"
      ? "rgba(16,185,129,.2)"
      : status === "failed"
      ? "rgba(239,68,68,.2)"
      : status === "processing"
      ? "rgba(6,182,212,.2)"
      : status === "skipped"
      ? "rgba(107,114,128,.2)"
      : "rgba(255,255,255,.1)",
  border: `2px solid ${
    status === "passed"
      ? "#10b981"
      : status === "failed"
      ? "#ef4444"
      : status === "processing"
      ? "#06b6d4"
      : status === "skipped"
      ? "#6b7280"
      : "rgba(255,255,255,.2)"
  }`,
}));

const FinalResultCard = styled(Box, {
  shouldForwardProp: (prop) => prop !== "decision",
})<{ decision: string }>(({ decision }) => ({
  background: "rgba(255,255,255,.05)",
  backdropFilter: "blur(20px)",
  borderRadius: 24,
  padding: 32,
  border:
    decision === "Likely to Happen"
      ? "2px solid rgba(16,185,129,.5)"
      : "2px solid rgba(239,68,68,.5)",
  marginTop: 32,
}));

/* ───────── 数据接口定义 ───────── */
interface FilterStatus {
  name: string;
  status: "pending" | "processing" | "passed" | "failed" | "skipped";
  details: string;
  result?: any;
  icon: React.ReactElement;
}

interface FinalResult {
  decision: string;
  reasoning: string;
  references: { reason: string; url: string }[];
}

/* ───────── Verifier Summary 解析 + 组件 ───────── */
const parseVerifier = (raw: string) => {
  const getPart = (tag: string) => {
    const match = raw.match(
      new RegExp(`\\*\\*${tag}\\*\\*\\s*:?\\s*([\\s\\S]*?)(?=\\*\\*|$)`, "i")
    );
    return match ? match[1].trim() : "";
  };
  return {
    source: getPart("SOURCE"),
    analysis: getPart("ANALYSIS"),
    verdict: getPart("VERDICT"),
  };
};

const VerifierSummary: React.FC<{ raw: string }> = ({ raw }) => {
  const { source, analysis, verdict } = parseVerifier(raw);
  
  let name = "";
  let link = "";
  let cred = "";
  let date = "";
  
  if (source) {
    const linkMatch = source.match(/\[([^\]]+)]\(([^)]+)\)/);
    if (linkMatch) {
      name = linkMatch[1];
      link = linkMatch[2];
    }
    const parts = source.split("|").map((t) => t.trim());
    cred = parts[1] || "";
    date = parts[2] || "";
  }
  
  const verdictType =
    verdict.toLowerCase().includes("misleading") ||
    verdict.toLowerCase().includes("unverifiable")
      ? "failed"
      : "passed";
      
  return (
    <Box sx={{ mb: 4 }}>
      {source && (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
          {name && (
            <Chip
              label={name}
              size="small"
              component={Link}
              href={link}
              target="_blank"
              sx={{
                background: "rgba(6,182,212,.15)",
                color: "#06b6d4",
                "&:hover": { textDecoration: "underline" },
              }}
            />
          )}
          {cred && (
            <Chip
              label={cred}
              size="small"
              sx={{ background: "rgba(34,197,94,.15)", color: "#22c55e" }}
            />
          )}
          {date && (
            <Chip
              label={date}
              size="small"
              sx={{ background: "rgba(107,114,128,.25)", color: "#e5e7eb" }}
            />
          )}
        </Box>
      )}
      
      {analysis && (
        <Box
          sx={{
            background: "rgba(255,255,255,.05)",
            borderRadius: 1,
            p: 2,
            lineHeight: 1.6,
            color: "rgba(255,255,255,.85)",
            mb: 2,
          }}
        >
          {analysis}
        </Box>
      )}
      
      {verdict && (
        <Box
          sx={{
            p: 2,
            borderRadius: 1,
            fontWeight: 700,
            color: verdictType === "passed" ? "#10b981" : "#ef4444",
            background:
              verdictType === "passed"
                ? "rgba(16,185,129,.15)"
                : "rgba(239,68,68,.15)",
            border:
              verdictType === "passed"
                ? "2px solid rgba(16,185,129,.5)"
                : "2px solid rgba(239,68,68,.5)",
          }}
        >
          {verdict}
        </Box>
      )}
    </Box>
  );
};

/* ───────── 主组件 VerifyResult ───────── */
const VerifyResult: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const wsRef = useRef<WebSocket | null>(null);

  const [filters, setFilters] = useState<FilterStatus[]>([
    { name: "Verifier Agent", status: "pending", details: "", icon: <BoltIcon /> },
    { name: "Video Verifier", status: "pending", details: "", icon: <VideocamIcon /> },
    { name: "Reason Agent", status: "pending", details: "", icon: <PsychologyIcon /> },
    { name: "Online Data Agent", status: "pending", details: "", icon: <PublicIcon /> },
    { name: "Decision Agent", status: "pending", details: "", icon: <GavelIcon /> },
  ]);
  
  const [finalResult, setFinalResult] = useState<FinalResult | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<FilterStatus | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [statement, setStatement] = useState("");

  /* ---------- WebSocket ---------- */
  useEffect(() => {
    if (!sessionId) return;
    
    const ws = new WebSocket(`ws://localhost:8000/api/v1/verify/ws/${sessionId}`);
    
    ws.onopen = () => {
      console.log("WebSocket connected");
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
    
    ws.onclose = () => {
      console.log("WebSocket disconnected");
    };
    
    wsRef.current = ws;
    
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [sessionId]);

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case "verification_started":
        setStatement(data.statement);
        break;
      case "filter_update":
        updateFilterStatus(data.filter_name, data.status, data.details, data.result);
        break;
      case "verification_completed":
        setFinalResult({
          decision: data.final_decision,
          reasoning: data.final_reasoning,
          references: data.reference_links || [],
        });
        break;
      case "error":
        console.error("Verification error:", data.message);
        break;
    }
  };

  const updateFilterStatus = (filterName: string, status: string, details: string, result: any) => {
    setFilters((prev) =>
      prev.map((filter) =>
        filter.name === filterName
          ? { ...filter, status: status as any, details, result }
          : filter
      )
    );
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "passed":
        return <CheckCircleIcon sx={{ fontSize: 30, color: "#10b981" }} />;
      case "failed":
        return <CancelIcon sx={{ fontSize: 30, color: "#ef4444" }} />;
      case "processing":
        return <CircularProgress size={30} sx={{ color: "#06b6d4" }} />;
      case "skipped":
        return <SkipNextIcon sx={{ fontSize: 30, color: "#6b7280" }} />;
      default:
        return <HourglassEmptyIcon sx={{ fontSize: 30, color: "#6b7280" }} />;
    }
  };

  return (
    <PageContainer>
      <BackButton onClick={() => navigate("/verify")}>
        <ArrowBackIcon />
      </BackButton>

      {/* ───────── 主可视区域 ───────── */}
      <Box
        sx={{
          width: "100vw",
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-start",
          px: 3,
          py: 8,
          position: "relative",
          zIndex: 1,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          style={{ width: "100%", maxWidth: "900px" }}
        >
          {/* 顶部标题 */}
          <Box textAlign="center" mb={6}>
            <Typography
              variant="h3"
              sx={{
                fontSize: { xs: "2rem", md: "3rem" },
                fontWeight: 800,
                background: "linear-gradient(135deg,#10b981 0%,#06b6d4 100%)",
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                mb: 2,
              }}
            >
              Verification in Progress
            </Typography>
            {statement && (
              <Typography
                variant="h6"
                sx={{
                  color: "rgba(255,255,255,.7)",
                  fontStyle: "italic",
                  maxWidth: "800px",
                  mx: "auto",
                }}
              >
                "{statement}"
              </Typography>
            )}
          </Box>

          {/* Filter 列表 */}
          <Box>
            {filters.map((filter, index) => (
              <motion.div
                key={filter.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <FilterCard status={filter.status} sx={{ mb: 3 }}>
                  <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <Box sx={{ display: "flex", alignItems: "center", flex: 1 }}>
                      <Box sx={{ mr: 3, color: "#06b6d4" }}>{filter.icon}</Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="h6" sx={{ color: "#fff", mb: 0.5 }}>
                          {filter.name}
                        </Typography>
                        {filter.status === "processing" && (
                          <Typography variant="body2" sx={{ color: "rgba(255,255,255,.6)" }}>
                            {filter.details || "Processing..."}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                    
                    <Box sx={{ display: "flex", alignItems: "center" }}>
                      <StatusCircle status={filter.status}>
                        {getStatusIcon(filter.status)}
                      </StatusCircle>
                      {filter.status !== "pending" && filter.status !== "skipped" && (
                        <IconButton
                          sx={{ ml: 2, color: "rgba(255,255,255,.7)" }}
                          onClick={() => {
                            setSelectedFilter(filter);
                            setShowDetails(true);
                          }}
                        >
                          <VisibilityIcon />
                        </IconButton>
                      )}
                    </Box>
                  </Box>
                </FilterCard>
              </motion.div>
            ))}

            {/* 最终决策 */}
            {finalResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
              >
                <FinalResultCard decision={finalResult.decision}>
                  <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
                    {finalResult.decision === "Likely to Happen" ? (
                      <CheckCircleIcon sx={{ fontSize: 40, color: "#10b981", mr: 2 }} />
                    ) : (
                      <CancelIcon sx={{ fontSize: 40, color: "#ef4444", mr: 2 }} />
                    )}
                    <Typography variant="h4" sx={{ color: "#fff", fontWeight: 700 }}>
                      {finalResult.decision}
                    </Typography>
                  </Box>
                  
                  <Typography variant="body1" sx={{ color: "rgba(255,255,255,.85)", mb: 3 }}>
                    {finalResult.reasoning}
                  </Typography>
                  
                  {finalResult.references.length > 0 && (
                    <Box>
                      <Typography variant="subtitle1" sx={{ color: "#fff", mb: 2, fontWeight: 600 }}>
                        Reference Links:
                      </Typography>
                      {finalResult.references.map((ref, index) => (
                        <Box key={index} sx={{ mb: 2 }}>
                          <Typography variant="body2" sx={{ color: "rgba(255,255,255,.6)", mb: 0.5 }}>
                            {ref.reason}
                          </Typography>
                          <Link
                            href={ref.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            sx={{ color: "#06b6d4", fontSize: "0.875rem" }}
                          >
                            {ref.url}
                          </Link>
                        </Box>
                      ))}
                    </Box>
                  )}
                </FinalResultCard>
              </motion.div>
            )}
          </Box>
        </motion.div>
      </Box>

      {/* ───────── 详情对话框 ───────── */}
      <Dialog
        open={showDetails}
        onClose={() => setShowDetails(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            background: "rgba(15,23,42,.95)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(255,255,255,.1)",
          },
        }}
      >
        <DialogTitle sx={{ color: "#fff", borderBottom: "1px solid rgba(255,255,255,.1)" }}>
          {selectedFilter?.name} - Details
        </DialogTitle>

        <DialogContent sx={{ mt: 2 }}>
          {selectedFilter && (
            <Box>
              {/* Status */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,.6)", mb: 1 }}>
                  Status
                </Typography>
                <Chip
                  label={selectedFilter.status}
                  sx={{
                    background:
                      selectedFilter.status === "passed"
                        ? "rgba(16,185,129,.2)"
                        : selectedFilter.status === "failed"
                        ? "rgba(239,68,68,.2)"
                        : "rgba(107,114,128,.2)",
                    color: "#fff",
                    textTransform: "capitalize",
                  }}
                />
              </Box>

              {/* Summary */}
              {selectedFilter.name === "Verifier Agent" ? (
                <VerifierSummary raw={selectedFilter.details} />
              ) : (
                selectedFilter.details && (
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,.6)", mb: 1 }}>
                      Summary
                    </Typography>
                    <Typography variant="body2" sx={{ color: "rgba(255,255,255,.85)" }}>
                      {selectedFilter.details}
                    </Typography>
                  </Box>
                )
              )}

              {/* JSON Result using react-json-view */}
              {selectedFilter.result && (
                <Box>
                  <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,.6)", mb: 1 }}>
                    Detailed Result
                  </Typography>
                  
                  <Box
                    sx={{
                      background: "rgba(0,0,0,.45)",
                      borderRadius: 1,
                      p: 2,
                      maxHeight: 400,
                      overflow: "auto",
                      "& .react-json-view": {
                        backgroundColor: "transparent !important",
                      },
                    }}
                  >
                    <ReactJson
                      src={selectedFilter.result}
                      theme="monokai"
                      collapsed={1}
                      displayDataTypes={false}
                      displayObjectSize={true}
                      enableClipboard={true}
                      name={false}
                      style={{
                        backgroundColor: "transparent",
                        fontSize: "13px",
                      }}
                    />
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
};

export default VerifyResult;