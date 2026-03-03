#!/usr/bin/env python3
"""
S&P 500 Golden Cross Live Screener
Flask server + yfinance data backend

Usage:
    pip install flask yfinance pandas
    python app.py

Then open http://localhost:5050 in your browser.
"""

import json
import os
import threading
import time
import webbrowser
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, send_file

app = Flask(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────
MA_SHORT = 5
MA_LONG = 10
LOOKBACK_DAYS = 365
PORT = 5050

# ─── S&P 500 Tickers ────────────────────────────────────────────────────────
SP500 = [
    "AAPL","ABBV","ABT","ACN","ADBE","ADI","ADM","ADP","ADSK","AEE","AEP","AES",
    "AFL","AIG","AIZ","AJG","AKAM","ALB","ALGN","ALK","ALL","ALLE","AMAT","AMCR",
    "AMD","AME","AMGN","AMP","AMT","AMZN","ANET","ANSS","AON","AOS","APA","APD",
    "APH","APTV","ARE","ATO","AVGO","AVY","AWK","AXP","AZO","BA","BAC","BAX",
    "BBY","BDX","BEN","BIIB","BIO","BK","BKNG","BKR","BLK","BMY","BR","BRK-B",
    "BRO","BSX","BWA","BXP","C","CAG","CAH","CARR","CAT","CB","CBOE","CBRE",
    "CCI","CCL","CDNS","CDW","CE","CEG","CF","CFG","CHD","CHRW","CHTR","CI",
    "CINF","CL","CLX","CMA","CMCSA","CME","CMG","CMI","CMS","CNC","CNP","COF",
    "COP","COST","CPB","CPRT","CPT","CRL","CRM","CSCO","CSGP","CSX","CTAS",
    "CTRA","CTSH","CTVA","CVS","CVX","D","DAL","DD","DE","DFS","DG","DGX","DHI",
    "DHR","DIS","DLTR","DOV","DOW","DPZ","DRI","DTE","DUK","DVA","DVN","DXCM",
    "EA","EBAY","ECL","ED","EFX","EIX","EL","EMN","EMR","ENPH","EOG","EPAM",
    "EQIX","EQR","EQT","ES","ESS","ETN","ETR","EVRG","EW","EXC","EXPD","EXPE",
    "EXR","F","FANG","FAST","FCX","FDS","FDX","FE","FFIV","FIS","FISV","FITB",
    "FMC","FOX","FOXA","FRT","FTNT","FTV","GD","GE","GILD","GIS","GL","GLW",
    "GM","GNRC","GOOG","GOOGL","GPC","GPN","GRMN","GS","GWW","HAL","HAS","HBAN",
    "HCA","HD","HOLX","HON","HPE","HPQ","HRL","HSIC","HST","HSY","HUM","HWM",
    "IBM","ICE","IDXX","IEX","IFF","ILMN","INCY","INTC","INTU","INVH","IP","IPG",
    "IQV","IR","IRM","ISRG","IT","ITW","IVZ","J","JBHT","JCI","JKHY","JNJ",
    "JNPR","JPM","K","KDP","KEY","KEYS","KHC","KIM","KLAC","KMB","KMI","KMX",
    "KO","KR","L","LDOS","LEN","LH","LHX","LIN","LKQ","LLY","LMT","LNC","LNT",
    "LOW","LRCX","LUV","LVS","LW","LYB","LYV","MA","MAA","MAR","MAS","MCD",
    "MCHP","MCK","MCO","MDLZ","MDT","MET","META","MGM","MHK","MKC","MKTX","MLM",
    "MMC","MMM","MNST","MO","MOH","MOS","MPC","MPWR","MRK","MRNA","MRO","MS",
    "MSCI","MSFT","MSI","MTB","MTCH","MTD","MU","NCLH","NDAQ","NDSN","NEE","NEM",
    "NFLX","NI","NKE","NOC","NOW","NRG","NSC","NTAP","NTRS","NUE","NVDA","NVR",
    "NWL","NWSA","NXPI","O","ODFL","OGN","OKE","OMC","ON","ORCL","ORLY","OTIS",
    "OXY","PARA","PAYC","PAYX","PCAR","PCG","PEG","PEP","PFE","PFG","PG","PGR",
    "PH","PHM","PKG","PKI","PLD","PM","PNC","PNR","PNW","POOL","PPG","PPL","PRU",
    "PSA","PSX","PTC","PVH","PWR","PYPL","QCOM","QRVO","RCL","RE","REG","REGN",
    "RF","RHI","RJF","RL","RMD","ROK","ROL","ROP","ROST","RSG","RTX","SBAC",
    "SBUX","SCHW","SEE","SHW","SJM","SLB","SNA","SNPS","SO","SPG","SPGI","SRE",
    "STE","STT","STX","STZ","SWK","SWKS","SYF","SYK","SYY","T","TAP","TDG",
    "TDY","TECH","TEL","TER","TFC","TFX","TGT","TMO","TMUS","TPR","TRGP","TRMB",
    "TROW","TRV","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL","UAL","UDR",
    "UHS","ULTA","UNH","UNP","UPS","URI","USB","V","VFC","VICI","VLO","VMC",
    "VNO","VRSK","VRSN","VRTX","VTR","VTRS","VZ","WAB","WAT","WBA","WBD","WDC",
    "WEC","WELL","WFC","WHR","WM","WMB","WMT","WRB","WRK","WST","WTW","WY",
    "WYNN","XEL","XOM","XRAY","XYL","YUM","ZBH","ZBRA","ZION","ZTS"
]


# ─── Analysis Engine ─────────────────────────────────────────────────────────

def fetch_and_analyze():
    """Fetch all S&P 500 data and compute crossover analysis."""
    end = datetime.now()
    start = end - timedelta(days=LOOKBACK_DAYS)
    today_str = end.strftime("%Y-%m-%d")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching {len(SP500)} tickers...")

    # Download in batches for reliability
    all_close = pd.DataFrame()
    batch_size = 100
    for i in range(0, len(SP500), batch_size):
        batch = SP500[i:i + batch_size]
        try:
            data = yf.download(
                batch, start=start, end=end,
                progress=False, threads=True, group_by='ticker'
            )
            if not data.empty:
                for ticker in batch:
                    try:
                        if len(batch) == 1:
                            closes = data['Close'].dropna()
                        else:
                            if isinstance(data.columns, pd.MultiIndex):
                                closes = data[ticker]['Close'].dropna()
                            else:
                                closes = data['Close'].dropna()
                        if len(closes) > MA_LONG + 2:
                            all_close[ticker] = closes
                    except (KeyError, TypeError):
                        pass
        except Exception as e:
            print(f"  Batch {i // batch_size + 1} error: {e}")

    print(f"  Got data for {len(all_close.columns)} tickers")

    # Compute MAs
    ma_short = all_close.rolling(window=MA_SHORT).mean()
    ma_long = all_close.rolling(window=MA_LONG).mean()

    # Cross signal: 1 when short > long
    cross = (ma_short > ma_long).astype(int)
    cross_diff = cross.diff()

    results = []
    for ticker in all_close.columns:
        prices = all_close[ticker].dropna()
        if len(prices) < MA_LONG + 2:
            continue

        m5 = ma_short[ticker].dropna()
        m10 = ma_long[ticker].dropna()
        sig = cross_diff[ticker].dropna()

        # Golden crosses (0→1) and death crosses (1→0)
        golden_dates = sig[sig == 1].index.tolist()
        death_dates = sig[sig == -1].index.tolist()

        # Current state
        last_cross_val = cross[ticker].dropna()
        if len(last_cross_val) == 0:
            continue
        current_state = 'golden' if last_cross_val.iloc[-1] == 1 else 'death'
        current_price = float(prices.iloc[-1])

        last_ma5 = float(m5.iloc[-1]) if len(m5) > 0 else None
        last_ma10 = float(m10.iloc[-1]) if len(m10) > 0 else None

        # Most recent golden/death cross dates
        last_gc = golden_dates[-1] if golden_dates else None
        last_dc = death_dates[-1] if death_dates else None

        is_today_golden = last_gc is not None and last_gc.strftime("%Y-%m-%d") == today_str
        is_today_death = last_dc is not None and last_dc.strftime("%Y-%m-%d") == today_str

        # Round trips: golden→death
        round_trips = []
        for gc in golden_dates:
            gc_price = float(prices.loc[gc])
            # Find next death cross
            next_dc = None
            for dc in death_dates:
                if dc > gc:
                    next_dc = dc
                    break

            if next_dc:
                dc_price = float(prices.loc[next_dc])
                hold = (next_dc - gc).days
                ret = (dc_price - gc_price) / gc_price * 100
                round_trips.append({
                    'entryDate': gc.strftime("%Y-%m-%d"),
                    'exitDate': next_dc.strftime("%Y-%m-%d"),
                    'entryPrice': round(gc_price, 2),
                    'exitPrice': round(dc_price, 2),
                    'returnPct': round(ret, 2),
                    'holdDays': hold,
                    'status': 'closed'
                })
            elif current_state == 'golden':
                hold = (prices.index[-1] - gc).days
                ret = (current_price - gc_price) / gc_price * 100
                round_trips.append({
                    'entryDate': gc.strftime("%Y-%m-%d"),
                    'exitDate': None,
                    'entryPrice': round(gc_price, 2),
                    'exitPrice': round(current_price, 2),
                    'returnPct': round(ret, 2),
                    'holdDays': hold,
                    'status': 'open'
                })

        # Stats
        closed = [rt for rt in round_trips if rt['status'] == 'closed']
        win_rate = avg_ret = avg_hold = None
        if closed:
            wins = sum(1 for rt in closed if rt['returnPct'] > 0)
            win_rate = round(wins / len(closed) * 100, 1)
            avg_ret = round(sum(rt['returnPct'] for rt in closed) / len(closed), 2)
            avg_hold = round(sum(rt['holdDays'] for rt in closed) / len(closed), 1)

        open_trip = next((rt for rt in round_trips if rt['status'] == 'open'), None)

        # Price history for detail chart (full series)
        date_strs = [d.strftime("%Y-%m-%d") for d in prices.index]
        price_list = [round(float(p), 2) for p in prices.values]
        ma5_full = [round(float(v), 2) if pd.notna(v) else None for v in m5.reindex(prices.index).values]
        ma10_full = [round(float(v), 2) if pd.notna(v) else None for v in m10.reindex(prices.index).values]

        # Golden/death cross indices in the price array
        gc_indices = []
        for gc in golden_dates:
            try:
                idx = list(prices.index).index(gc)
                gc_indices.append(idx)
            except ValueError:
                pass
        dc_indices = []
        for dc in death_dates:
            try:
                idx = list(prices.index).index(dc)
                dc_indices.append(idx)
            except ValueError:
                pass

        results.append({
            'ticker': ticker,
            'currentPrice': round(current_price, 2),
            'currentMA5': round(last_ma5, 2) if last_ma5 else None,
            'currentMA10': round(last_ma10, 2) if last_ma10 else None,
            'currentState': current_state,
            'lastGoldenDate': last_gc.strftime("%Y-%m-%d") if last_gc else None,
            'lastGoldenPrice': round(float(prices.loc[last_gc]), 2) if last_gc else None,
            'lastDeathDate': last_dc.strftime("%Y-%m-%d") if last_dc else None,
            'isTodayGolden': is_today_golden,
            'isTodayDeath': is_today_death,
            'isToday': is_today_golden or is_today_death,
            'totalGC': len(golden_dates),
            'totalDC': len(death_dates),
            'closedTrips': len(closed),
            'winRate': win_rate,
            'avgReturn': avg_ret,
            'avgHold': avg_hold,
            'openReturn': open_trip['returnPct'] if open_trip else None,
            'openHold': open_trip['holdDays'] if open_trip else None,
            'roundTrips': round_trips,
            # Full price data for detail chart
            'dates': date_strs,
            'prices': price_list,
            'ma5': ma5_full,
            'ma10': ma10_full,
            'gcIndices': gc_indices,
            'dcIndices': dc_indices,
        })

    print(f"  Analyzed {len(results)} tickers, "
          f"{sum(1 for r in results if r['currentState'] == 'golden')} in golden cross, "
          f"{sum(1 for r in results if r['isTodayGolden'])} new today")

    return {
        'timestamp': datetime.now().isoformat(),
        'today': today_str,
        'maShort': MA_SHORT,
        'maLong': MA_LONG,
        'totalTickers': len(results),
        'results': results
    }


# ─── Flask Routes ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    html_path = os.path.join(os.path.dirname(__file__), 'dashboard.html')
    return send_file(html_path)


@app.route('/api/data')
def api_data():
    data = fetch_and_analyze()
    return jsonify(data)


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"  S&P 500 Golden Cross Live Screener")
    print(f"  5d/10d MA Crossover Analysis")
    print(f"{'='*60}")
    print(f"\n  Open http://localhost:{PORT} in your browser")
    print(f"  Press Ctrl+C to stop\n")

    # Auto-open browser after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{PORT}')

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=PORT, debug=False)
