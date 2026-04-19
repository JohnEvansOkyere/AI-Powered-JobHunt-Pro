from AlgorithmImports import *
import json
from datetime import datetime, timedelta
import statistics
import pandas as pd

class NuminValidationBacktest(QCAlgorithm):
    
    def Initialize(self):
        """
        Multi-period backtest to validate the projection-based trading logic.
        Tests the strategy across different 60-90 day periods to identify strengths/weaknesses.
        
        CORRECTED LOGIC:
        - LONG signal → Enter/Stay LONG position
        - SHORT signal → Enter/Stay SHORT position  
        - HOLD signal → MAINTAIN current position (do NOT exit)
        """
        
        # DEFINE TEST PERIODS (2-4 periods from past 2 years)
        self.test_periods = [
            (datetime(2023, 1, 1), datetime(2023, 3, 31), "Q1_2023_89days"),
            (datetime(2023, 6, 1), datetime(2023, 8, 31), "Q2Q3_2023_91days"),
            (datetime(2024, 1, 1), datetime(2024, 3, 31), "Q1_2024_90days"),
            (datetime(2024, 9, 1), datetime(2024, 11, 30), "Q3Q4_2024_90days"),
        ]
        
        # SELECT WHICH TEST TO RUN (0, 1, 2, or 3)
        self.current_test_index = 0  # ← CHANGE THIS TO TEST DIFFERENT PERIODS
        
        # Set up the selected test period
        start_date, end_date, test_name = self.test_periods[self.current_test_index]
        self.SetStartDate(start_date.year, start_date.month, start_date.day)
        self.SetEndDate(end_date.year, end_date.month, end_date.day)
        self.test_name = test_name
        
        self.SetCash(100000)
        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.api_key = "numin_Y4FR2IC4Squ68H7z-WjuqeMOzrksWCfnh8ZAUDGilTw"
        
        # State tracking
        self.last_fetch_date = None
        self.last_signal = "HOLD"  # Start with no position
        
        # Performance tracking
        self.trades = []  # All completed trades
        self.signals_log = []  # Daily signal tracking
        self.trade_entry_price = None
        self.trade_entry_date = None
        self.trade_entry_signal = None
        
        # Log test configuration
        self.Debug(f"\n{'='*100}")
        self.Debug(f"VALIDATION BACKTEST: {self.test_name}")
        self.Debug(f"Testing Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        self.Debug(f"Duration: {(end_date - start_date).days} days")
        self.Debug(f"Initial Capital: ${self.Portfolio.Cash:,.2f}")
        self.Debug(f"Strategy: BUY on LONG, SHORT on SHORT, HOLD maintains position")
        self.Debug(f"{'='*100}\n")
        
        # Schedule daily execution
        self.Schedule.On(
            self.DateRules.EveryDay(self.symbol),
            self.TimeRules.AfterMarketClose(self.symbol, 15),
            self.FetchAndTrade
        )
    
    def OnEndOfAlgorithm(self):
        """Generate comprehensive performance report at end of backtest"""
        
        self.Debug(f"\n{'='*100}")
        self.Debug(f"VALIDATION RESULTS: {self.test_name}")
        self.Debug(f"{'='*100}\n")
        
        # Overall Performance
        initial_capital = 100000
        final_value = self.Portfolio.TotalPortfolioValue
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        
        self.Debug(f"OVERALL PERFORMANCE:")
        self.Debug(f"  Test Period:        {self.test_name}")
        self.Debug(f"  Initial Capital:    ${initial_capital:,.2f}")
        self.Debug(f"  Final Value:        ${final_value:,.2f}")
        self.Debug(f"  Total Return:       {total_return:.2f}%")
        self.Debug(f"  Total Trades:       {len(self.trades)}")
        
        # Buy & Hold Comparison
        if len(self.signals_log) > 0:
            first_price = self.signals_log[0]['price']
            last_price = self.signals_log[-1]['price']
            buy_hold_return = ((last_price - first_price) / first_price) * 100
            alpha = total_return - buy_hold_return
            self.Debug(f"  Buy & Hold Return:  {buy_hold_return:.2f}%")
            self.Debug(f"  Alpha:              {alpha:.2f}%")
            self.Debug(f"  Strategy Status:    {'OUTPERFORMED' if alpha > 0 else 'UNDERPERFORMED'}")
        
        # Trade Statistics
        if self.trades:
            self.Debug(f"\nTRADE STATISTICS:")
            
            winning_trades = [t for t in self.trades if t['pnl'] > 0]
            losing_trades = [t for t in self.trades if t['pnl'] < 0]
            win_rate = (len(winning_trades) / len(self.trades)) * 100
            
            self.Debug(f"  Winning Trades:     {len(winning_trades)}")
            self.Debug(f"  Losing Trades:      {len(losing_trades)}")
            self.Debug(f"  Win Rate:           {win_rate:.2f}%")
            
            if winning_trades:
                avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
                max_win = max(t['pnl'] for t in winning_trades)
                self.Debug(f"  Average Win:        ${avg_win:,.2f}")
                self.Debug(f"  Largest Win:        ${max_win:,.2f}")
            
            if losing_trades:
                avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
                max_loss = min(t['pnl'] for t in losing_trades)
                self.Debug(f"  Average Loss:       ${avg_loss:,.2f}")
                self.Debug(f"  Largest Loss:       ${max_loss:,.2f}")
            
            # Profit Factor
            total_wins = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
            total_losses = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 1
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            self.Debug(f"  Profit Factor:      {profit_factor:.2f}")
            
            # Average holding period
            avg_days = sum(t['days_held'] for t in self.trades) / len(self.trades)
            self.Debug(f"  Avg Hold Period:    {avg_days:.1f} days")
        else:
            self.Debug(f"\n⚠️  NO TRADES EXECUTED - Strategy remained in HOLD throughout period")
        
        # Signal Accuracy Analysis
        self.Debug(f"\nSIGNAL ACCURACY:")
        long_signals = [s for s in self.signals_log if s['signal'] == 'LONG']
        short_signals = [s for s in self.signals_log if s['signal'] == 'SHORT']
        hold_signals = [s for s in self.signals_log if s['signal'] == 'HOLD']
        
        self.Debug(f"  LONG Signals:       {len(long_signals)}")
        self.Debug(f"  SHORT Signals:      {len(short_signals)}")
        self.Debug(f"  HOLD Signals:       {len(hold_signals)}")
        
        # Check signal accuracy (did LONG go up? did SHORT go down?)
        if long_signals:
            correct_longs = sum(1 for s in long_signals if s.get('actual_direction') == 'UP')
            long_accuracy = (correct_longs / len(long_signals)) * 100 if long_signals else 0
            self.Debug(f"  LONG Accuracy:      {long_accuracy:.1f}% ({correct_longs}/{len(long_signals)} correct)")
        
        if short_signals:
            correct_shorts = sum(1 for s in short_signals if s.get('actual_direction') == 'DOWN')
            short_accuracy = (correct_shorts / len(short_signals)) * 100 if short_signals else 0
            self.Debug(f"  SHORT Accuracy:     {short_accuracy:.1f}% ({correct_shorts}/{len(short_signals)} correct)")
        
        # Detailed Trade Log
        if self.trades:
            self.Debug(f"\nDETAILED TRADE LOG:")
            for i, trade in enumerate(self.trades, 1):
                outcome = "✓ WIN" if trade['pnl'] > 0 else "✗ LOSS"
                self.Debug(f"  Trade {i} ({outcome}): {trade['signal']} | "
                          f"Entry: ${trade['entry_price']:.2f} on {trade['entry_date']} | "
                          f"Exit: ${trade['exit_price']:.2f} on {trade['exit_date']} | "
                          f"Hold: {trade['days_held']} days | "
                          f"P&L: ${trade['pnl']:,.2f} ({trade['return']:.2f}%)")
        
        # Identify Outliers & Failures
        if self.trades:
            self.Debug(f"\nOUTLIERS & FAILURES:")
            worst_trades = sorted(self.trades, key=lambda x: x['pnl'])[:3]
            for i, trade in enumerate(worst_trades, 1):
                self.Debug(f"  Worst Trade {i}: {trade['signal']} | "
                          f"P&L: ${trade['pnl']:,.2f} ({trade['return']:.2f}%) | "
                          f"{trade['entry_date']} to {trade['exit_date']} ({trade['days_held']} days)")
        
        # Summary for easy comparison across test periods
        self.Debug(f"\n{'='*100}")
        self.Debug(f"QUICK SUMMARY FOR {self.test_name}:")
        self.Debug(f"  Return: {total_return:.2f}% | Trades: {len(self.trades)} | "
                  f"Win Rate: {(len([t for t in self.trades if t['pnl'] > 0]) / len(self.trades) * 100) if self.trades else 0:.1f}%")
        self.Debug(f"{'='*100}\n")
    
    def FetchAndTrade(self):
        """
        Main validation logic - fetches projections, computes rankings, generates signal.
        CORRECTED: HOLD now maintains current position instead of exiting.
        """
        today = self.Time.date()
        
        # Prevent duplicate execution
        if self.last_fetch_date == today:
            return
        
        self.last_fetch_date = today
        start_date_str = today.strftime("%Y-%m-%d")
        
        # Build API URL
        url = f"https://api.staging.numin.com/projection/single-ticker?ticker=SPY&timeframe=daily&start_date={start_date_str}&apiKey={self.api_key}"
        headers = {"Accept": "application/json"}
        
        try:
            # Fetch projections
            json_text = self.Download(url, headers=headers)
            
            if not json_text or json_text.strip() == "":
                self.Error(f"Empty API response for {start_date_str}")
                return
            
            data = json.loads(json_text)
            
            # Helper function
            def safe_get_dict(d, key):
                val = d.get(key)
                return val if isinstance(val, dict) else {}
            
            # Extract projections
            cons = self._parse_projection(safe_get_dict(data, "consolidatedProjection"))
            clus = self._parse_projection(safe_get_dict(data, "clusteredProjection"))
            posi = self._parse_projection(safe_get_dict(data, "positiveProjection"))
            high = self._parse_projection(safe_get_dict(data, "highProjection"))
            low  = self._parse_projection(safe_get_dict(data, "lowProjection"))
            nega = self._parse_projection(safe_get_dict(data, "negativeProjection"))
            
            # Collect non-empty projections
            all_dicts = [d for d in [cons, clus, posi, nega, high, low] if d]
            
            # Validate data quality
            if len(all_dicts) < 3:
                self.Debug(f"Insufficient projection types: {len(all_dicts)}/6")
                return
            
            # Find common dates
            all_date_sets = [set(d.keys()) for d in all_dicts]
            common_dates_all = set.intersection(*all_date_sets) if len(all_date_sets) > 1 else all_date_sets[0]
            future_dates = sorted(d for d in common_dates_all if d >= today)
            
            if len(future_dates) < 3:
                self.Debug(f"Too few future dates ({len(future_dates)})")
                return
            
            # Build projection lists
            consolidated = []
            clustered = []
            positive = []
            negative = []
            high_proj = []
            low_proj = []
            
            for d in future_dates:
                cons_val = cons.get(d, cons.get(future_dates[0], 0.0))
                clus_val = clus.get(d, clus.get(future_dates[0], 0.0))
                posi_val = posi.get(d, posi.get(future_dates[0], 0.0))
                
                consolidated.append(cons_val)
                clustered.append(clus_val)
                positive.append(posi_val)
                negative.append(nega.get(d, cons_val))
                high_proj.append(high.get(d, cons_val))
                low_proj.append(low.get(d, cons_val))
            
            n = len(future_dates)
            
            # Compute Rankings (EXACT validation logic)
            cons_r, clus_r, comp_r, hl_r = [], [], [], []
            
            for i in range(n):
                c   = consolidated[i]
                clu = clustered[i]
                p   = positive[i]
                ne  = negative[i]
                h   = high_proj[i]
                l   = low_proj[i]
                
                # Consolidated Ranking
                cons_r.append(1 if c == p else -1)
                
                # Clustered Ranking
                clus_r.append(1 if clu > (p + ne)/2 else -1)
                
                # Comparative Ranking
                avg = (p + ne + h + l) / 4
                if c > avg and clu > avg:
                    comp = 1
                elif c < avg and clu < avg:
                    comp = -1
                else:
                    comp = 0
                comp_r.append(comp)
                
                # High-Low Ranking
                hlr = 0
                if i > 0:
                    prev_cl = clustered[:i]
                    min_p = min(prev_cl)
                    max_p = max(prev_cl)
                    if comp < 0 and clu < min_p:
                        hlr = -1
                    elif comp > 0 and clu > max_p:
                        hlr = 1
                hl_r.append(hlr)
            
            # Sum of Comparative Rankings
            summed = []
            for i in range(n):
                window_end = min(i + 3, n)
                window_sum = sum(comp_r[i:window_end])
                summed.append(window_sum)
            
            # Percentage changes 2 steps ahead
            pct = []
            for i in range(n - 2):
                if consolidated[i] != 0:
                    pct.append((consolidated[i+2] / consolidated[i]) - 1)
                else:
                    pct.append(0.0)
            
            # Standard deviation
            values_std = consolidated[:5] + clustered[:5]
            if len(values_std) >= 2:
                raw_stddev = statistics.pstdev(values_std)
                stddev = raw_stddev / 1000
            else:
                stddev = 0.001
            
            # Key decision values
            d1 = summed[0] if summed else 0
            d2 = pct[0] if pct else 0.0
            sum_next = sum(pct[:3]) if len(pct) >= 3 else sum(pct)
            
            # VALIDATION LOGIC (unchanged)
            if sum_next > stddev or (d1 >= 0 and d2 > stddev):
                signal = "LONG"
            elif sum_next < -stddev or (d1 <= 0 and d2 < -stddev):
                signal = "SHORT"
            else:
                signal = "HOLD"
            
            # Get current price
            current_price = self.Securities[self.symbol].Close
            
            # Log signal for analysis
            signal_record = {
                'date': today,
                'signal': signal,
                'price': current_price,
                'd1': d1,
                'd2': d2,
                'sum_next': sum_next,
                'stddev': stddev
            }
            
            # Calculate actual direction for previous signal
            if len(self.signals_log) > 0:
                prev_signal = self.signals_log[-1]
                if current_price > prev_signal['price']:
                    prev_signal['actual_direction'] = 'UP'
                elif current_price < prev_signal['price']:
                    prev_signal['actual_direction'] = 'DOWN'
                else:
                    prev_signal['actual_direction'] = 'FLAT'
            
            self.signals_log.append(signal_record)
            
            # Save old signal
            old_signal = self.last_signal
            
            # ============================================================
            # CORRECTED TRADE LOGIC - HOLD MAINTAINS POSITION
            # ============================================================
            
            if signal != old_signal:
                self.Debug(f"Signal changed: {old_signal} → {signal}")
                
                # Record trade if we're closing a position (changing from LONG/SHORT to something else)
                if old_signal in ["LONG", "SHORT"] and self.Portfolio[self.symbol].Invested:
                    exit_price = current_price
                    shares = self.Portfolio[self.symbol].Quantity
                    pnl = (exit_price - self.trade_entry_price) * shares
                    trade_return = ((exit_price - self.trade_entry_price) / self.trade_entry_price) * 100
                    days_held = (today - self.trade_entry_date).days
                    
                    trade_record = {
                        'entry_date': self.trade_entry_date.strftime('%Y-%m-%d'),
                        'exit_date': today.strftime('%Y-%m-%d'),
                        'signal': self.trade_entry_signal,
                        'entry_price': self.trade_entry_price,
                        'exit_price': exit_price,
                        'shares': shares,
                        'pnl': pnl,
                        'return': trade_return,
                        'days_held': days_held
                    }
                    self.trades.append(trade_record)
                    
                    outcome = "✓" if pnl > 0 else "✗"
                    self.Debug(f"{outcome} TRADE CLOSED: {self.trade_entry_signal} | "
                              f"Entry: ${self.trade_entry_price:.2f} ({trade_record['entry_date']}) | "
                              f"Exit: ${exit_price:.2f} ({today.strftime('%Y-%m-%d')}) | "
                              f"P&L: ${pnl:,.2f} ({trade_return:.2f}%)")
                
                # Execute new position based on signal
                if signal == "LONG":
                    # Enter LONG position (100% allocation)
                    self.SetHoldings(self.symbol, 1.0)
                    self.trade_entry_price = current_price
                    self.trade_entry_date = today
                    self.trade_entry_signal = signal
                    self.Debug(f"→ TRADE OPENED: LONG at ${current_price:.2f}")
                
                elif signal == "SHORT":
                    # Enter SHORT position (-100% allocation)
                    self.SetHoldings(self.symbol, -1.0)
                    self.trade_entry_price = current_price
                    self.trade_entry_date = today
                    self.trade_entry_signal = signal
                    self.Debug(f"→ TRADE OPENED: SHORT at ${current_price:.2f}")
                
                elif signal == "HOLD":
                    # HOLD = Do nothing, maintain current position
                    if self.Portfolio[self.symbol].Invested:
                        current_pos = "LONG" if self.Portfolio[self.symbol].Quantity > 0 else "SHORT"
                        self.Debug(f"→ HOLD: Maintaining {current_pos} position from {self.trade_entry_date.strftime('%Y-%m-%d')}")
                    else:
                        self.Debug(f"→ HOLD: No position to maintain (staying in cash)")
                
                # Update last signal
                self.last_signal = signal
            
            else:
                # Signal unchanged - no action needed
                pass
        
        except json.JSONDecodeError as jde:
            self.Error(f"JSON decode error: {str(jde)}")
        except Exception as ex:
            self.Error(f"Error in FetchAndTrade: {str(ex)}")
            import traceback
            self.Error(traceback.format_exc())
    
    def _parse_projection(self, raw):
        """Convert raw dict of {date_str: value} → {date: float}"""
        result = {}
        if not isinstance(raw, dict):
            return result
        for ds, v in raw.items():
            if not isinstance(ds, str):
                continue
            try:
                dt = datetime.strptime(ds, "%Y-%m-%d").date()
                result[dt] = float(v)
            except (ValueError, TypeError):
                pass
        return result








