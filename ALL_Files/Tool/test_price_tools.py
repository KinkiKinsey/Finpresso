#!/usr/bin/env python
# coding: utf-8

import unittest
import pandas as pd
import numpy as np
from price_level_tools import (
    calculate_risk_reward,
    analyze_both_positions,
    analyze_sma_crossovers,
    analyze_ema_crossovers,
    analyze_vw_macd,
    get_available_history
)

class TestPriceTools(unittest.TestCase):
    def setUp(self):
        """Set up test cases with common test data"""
        self.test_ticker = "AAPL"  # Using AAPL as a test case
        self.test_price = 150.0    # Example price
        self.test_shares = 10      # Example number of shares

    def test_get_available_history(self):
        """Test the history determination function"""
        n_years, rr_interval, other_interval = get_available_history(self.test_ticker)
        
        # Check that we got valid intervals
        self.assertIsNotNone(n_years)
        self.assertIsNotNone(rr_interval)
        self.assertIsNotNone(other_interval)
        
        # Check that intervals are positive
        self.assertGreater(n_years, 0)
        self.assertGreater(rr_interval, 0)
        self.assertGreater(other_interval, 0)
        
        # Check that intervals are reasonable
        self.assertLessEqual(rr_interval, 365)  # Max 1 year for risk/reward
        self.assertLessEqual(other_interval, 730)  # Max 2 years for other analyses

    def test_calculate_risk_reward(self):
        """Test the risk/reward calculation function"""
        # Test long position
        analysis, graphs = calculate_risk_reward(
            stock_ticker=self.test_ticker,
            N=360,
            share=self.test_shares,
            position_type='long'
        )
        
        # Check that we got valid output
        self.assertIsInstance(analysis, str)
        self.assertIsInstance(graphs, dict)
        self.assertIn('main_plot', graphs)
        
        # Check that analysis contains expected information
        self.assertIn('Risk/Reward Ratio', analysis)
        self.assertIn('Expected Loss', analysis)
        self.assertIn('Expected Profit', analysis)

    def test_analyze_both_positions(self):
        """Test the combined position analysis function"""
        analysis, graphs = analyze_both_positions(
            stock_ticker=self.test_ticker,
            price=self.test_price,
            share=self.test_shares
        )
        
        # Check that we got valid output
        self.assertIsInstance(analysis, str)
        self.assertIsInstance(graphs, dict)
        self.assertIn('combined_plot', graphs)
        
        # Check that analysis contains expected information
        self.assertIn('Combined Risk/Reward Analysis', analysis)
        self.assertIn('Long Position', analysis)
        self.assertIn('Short Position', analysis)

    def test_analyze_sma_crossovers(self):
        """Test the SMA crossover analysis function"""
        analysis, graphs = analyze_sma_crossovers(
            ticker=self.test_ticker
        )
        
        # Check that we got valid output
        self.assertIsInstance(analysis, str)
        self.assertIsInstance(graphs, dict)
        self.assertIn('sma_plot', graphs)
        
        # Check that analysis contains expected information
        self.assertIn('SMA Crossover Analysis', analysis)
        self.assertIn('Bullish Crosses', analysis)
        self.assertIn('Bearish Crosses', analysis)

    def test_analyze_ema_crossovers(self):
        """Test the EMA crossover analysis function"""
        analysis, graphs = analyze_ema_crossovers(
            ticker=self.test_ticker
        )
        
        # Check that we got valid output
        self.assertIsInstance(analysis, str)
        self.assertIsInstance(graphs, dict)
        self.assertIn('ema_plot', graphs)
        
        # Check that analysis contains expected information
        self.assertIn('EMA Crossover Analysis', analysis)
        self.assertIn('Bullish Crosses', analysis)
        self.assertIn('Bearish Crosses', analysis)

    def test_analyze_vw_macd(self):
        """Test the volume-weighted MACD analysis function"""
        analysis, graphs = analyze_vw_macd(
            ticker=self.test_ticker
        )
        
        # Check that we got valid output
        self.assertIsInstance(analysis, str)
        self.assertIsInstance(graphs, dict)
        self.assertIn('vw_macd_plot', graphs)
        
        # Check that analysis contains expected information
        self.assertIn('VOLUME-WEIGHTED MACD ANALYSIS', analysis)
        self.assertIn('Current VW-MACD', analysis)
        self.assertIn('MOMENTUM ANALYSIS', analysis)

    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test with invalid ticker
        analysis, graphs = calculate_risk_reward(
            stock_ticker="INVALID_TICKER_123",
            N=360,
            share=self.test_shares,
            position_type='long'
        )
        
        # Should return error message
        self.assertIn("No data available", analysis)
        self.assertEqual(len(graphs), 0)

if __name__ == '__main__':
    unittest.main(verbosity=2) 