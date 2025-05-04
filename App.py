from flask import Flask, request, jsonify
from binance.client import Client
import pandas as pd
import ta
import os

app = Flask(__name__)

api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET')
client = Client(api_key, api_secret)

def get_binance_klines(symbol='BTCUSDT', interval='1h', limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
    ])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df[['close', 'volume']]

def analyze_crypto(symbol):
    df = get_binance_klines(symbol)
    df['EMA20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['VolumeAvg'] = df['volume'].rolling(window=20).mean()

    df['BuySignal'] = (
        (df['RSI'] < 30) &
        (df['close'] > df['EMA20']) &
        (df['volume'] > df['VolumeAvg'])
    )
    df['SellSignal'] = (
        (df['RSI'] > 70) |
        (df['close'] < df['EMA20'])
    )

    latest = df.iloc[-1]
    return {
        "symbol": symbol,
        "price": float(latest['close']),
        "ema": float(latest['EMA20']),
        "rsi": float(latest['RSI']),
        "volume": float(latest['volume']),
        "volume_avg": float(latest['VolumeAvg']),
        "buy_signal": bool(latest['BuySignal']),
        "sell_signal": bool(latest['SellSignal']),
    }

@app.route('/analyze', methods=['GET'])
def analyze():
    symbol = request.args.get('symbol', default='BTCUSDT')
    try:
        result = analyze_crypto(symbol.upper())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
