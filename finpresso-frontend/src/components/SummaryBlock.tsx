import React from 'react';
import { Box, Stack, Typography, Paper, Chip } from '@mui/material';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import SouthEastIcon from '@mui/icons-material/SouthEast';

interface Props { text: string }
interface Parsed { rr: string; profit: string; loss: string }

function parseLine(l?: string): Parsed {
  if (!l) return { rr: '-', profit: '-', loss: '-' };
  const m = l.match(/R\/R\s*=\s*([-\d.]+).*?Profit\s*=\s*([-\d.]+).*?Loss\s*=\s*([-\d.]+)/i);
  return { rr: m?.[1] ?? '-', profit: m?.[2] ?? '-', loss: m?.[3] ?? '-' };
}

const SummaryBlock: React.FC<Props> = ({ text }) => {
  if (!text) return null;
  const lines = text.split(/\\r?\\n/).filter(Boolean);
  const title = lines[0].replace(/:+$/, '') || 'Risk/Reward Analysis';
  const long = parseLine(lines.find(l => /^long/i.test(l)));
  const short = parseLine(lines.find(l => /^short/i.test(l)));
  const recommended = (lines.find(l => /^recommended/i.test(l)) || '')
    .split(':')[1]?.trim().toUpperCase();

  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="subtitle1" sx={{
        fontWeight: 700,
        mb: 2,
        background: 'linear-gradient(90deg,#005F8C 0%,#00A8E0 100%)',
        WebkitBackgroundClip: 'text',
        color: 'transparent'
      }}>
        {title}
      </Typography>

      <Box sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
        gap: 2,
        mb: 2
      }}>
        {/* Long */}
        <Paper variant="outlined" sx={{ p:2, borderRadius:2, borderColor:'#00A8E0' }}>
          <Stack direction="row" alignItems="center" spacing={1} mb={1}>
            <ArrowUpwardIcon sx={{ color: '#059669' }} />
            <Typography fontWeight={700}>LONG</Typography>
          </Stack>
          <Typography variant="body2" sx={{ mb:0.5 }}>
            R/R: <Box component="span" sx={{ fontFamily:'Roboto Mono', fontWeight:700 }}>{long.rr}</Box>
          </Typography>
          <Typography variant="body2" sx={{ mb:0.5, color:'#059669' }}>
            Exp. Profit: {long.profit}
          </Typography>
          <Typography variant="body2" sx={{ color:'#B91C1C' }}>
            Exp. Loss: {long.loss}
          </Typography>
        </Paper>
        {/* Short */}
        <Paper variant="outlined" sx={{ p:2, borderRadius:2, borderColor:'#94A3B8' }}>
          <Stack direction="row" alignItems="center" spacing={1} mb={1}>
            <SouthEastIcon sx={{ color:'#B91C1C' }} />
            <Typography fontWeight={700}>SHORT</Typography>
          </Stack>
          <Typography variant="body2" sx={{ mb:0.5 }}>
            R/R: <Box component="span" sx={{ fontFamily:'Roboto Mono', fontWeight:700 }}>{short.rr}</Box>
          </Typography>
          <Typography variant="body2" sx={{ mb:0.5, color:'#059669' }}>
            Exp. Profit: {short.profit}
          </Typography>
          <Typography variant="body2" sx={{ color:'#B91C1C' }}>
            Exp. Loss: {short.loss}
          </Typography>
        </Paper>
      </Box>

      {recommended && (
        <Stack direction="row" justifyContent="center">
          <Chip
            label={`Recommended: ${recommended}`}
            color={recommended==='LONG'?'success':'error'}
            sx={{
              px:2, fontWeight:700,
              bgcolor: recommended==='LONG'? '#059669':'#B91C1C',
              color:'#fff'
            }}
          />
        </Stack>
      )}
    </Box>
  );
};

export default SummaryBlock;