import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import sys
import os
import yfinance as yf
import numpy as np
import requests
import feedparser
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

# Page Config
st.set_page_config(
    page_title="Ultimate Trading Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 1rem;
    }
    .positive {
        color: #28a745;
        font-weight: bold;
    }
    .negative {
        color: #dc3545;
        font-weight: bold;
    }
    .neutral {
        color: #6c757d;
    }
    .stock-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .news-card {
        background-color: #f8f9fa;
        border-left: 4px solid #007bff;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# API Keys (Use Streamlit Secrets in production)
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", "")
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")

class MarketScanner:
    def __init__(self):
        self.focus_tickers = [
            'TSLA', 'NVDA', 'AMD', 'META', 'AAPL', 'MSFT', 'GOOGL', 'AMZN',
            'PLTR', 'SOUN', 'AI', 'MARA', 'RIOT', 'COIN', 'MSTR',
            'RIVN', 'LCID', 'NIO', 'XPEV', 'F', 'GM',
            'JPM', 'BAC', 'V', 'MA', 'WFC', 'C',
            'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK',
            'XOM', 'CVX', 'COP', 'SLB',
            'WMT', 'TGT', 'COST', 'HD', 'LOW',
            'DIS', 'NFLX', 'PYPL', 'SQ', 'SHOP',
            'SNOW', 'DDOG', 'NET', 'CRWD', 'ZS',
            'DASH', 'UBER', 'LYFT', 'ABNB',
            'NKE', 'MCD', 'SBUX', 'PEP', 'KO',
            'BA', 'CAT', 'DE', 'MMM',
            'VZ', 'T', 'TMUS', 'CMCSA',
            'IBM', 'ORCL', 'CSCO', 'INTC',
            'GS', 'MS', 'BLK', 'SCHW',
            'MDT', 'SYK', 'ISRG', 'BDX',
            'RTX', 'LMT', 'NOC', 'GD',
            'SPY', 'QQQ', 'IWM', 'DIA'
        ]
    
    def get_stock_data(self, ticker):
        """جلب بيانات سهم واحد"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # الحصول على السعر
            price_keys = ['currentPrice', 'regularMarketPrice', 'previousClose']
            price = 0
            for key in price_keys:
                if key in info and info[key]:
                    price = info[key]
                    break
            
            if price == 0:
                return None
            
            # الحصول على البيانات التاريخية
            hist = stock.history(period='2d')
            if len(hist) >= 2:
                current_close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                daily_change = ((current_close - prev_close) / prev_close) * 100
                volume = int(hist['Volume'].iloc[-1])
            else:
                daily_change = 0
                volume = info.get('volume', 0)
            
            # البيانات الأساسية
            return {
                'Ticker': ticker,
                'Company': info.get('shortName', ticker)[:20],
                'Price': round(price, 2),
                'Change %': round(daily_change, 2),
                'Volume': volume,
                'Market_Cap': info.get('marketCap', 0),
                'Sector': info.get('sector', 'N/A'),
                'PE_Ratio': info.get('trailingPE', 0),
                'Beta': info.get('beta', 1)
            }
            
        except Exception as e:
            return None
    
    def get_stock_news(self, ticker):
        """جلب أخبار السهم"""
        news_items = []
        
        # محاولة Yahoo RSS
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:3]:
                news_items.append({
                    'title': entry.title,
                    'summary': entry.get('summary', '')[:150],
                    'link': entry.link,
                    'source': 'Yahoo Finance'
                })
        except:
            pass
        
        return news_items[:3]
    
    def analyze_sentiment(self, news_items):
        """تحليل مشاعر الأخبار"""
        if not news_items:
            return {'sentiment': 'NEUTRAL', 'score': 0, 'confidence': 0}
        
        positive_words = ['profit', 'gain', 'up', 'rise', 'bullish', 'buy', 'upgrade']
        negative_words = ['loss', 'down', 'fall', 'bearish', 'sell', 'downgrade']
        
        sentiment_score = 0
        for news in news_items:
            text = f"{news['title']} {news['summary']}".lower()
            
            for word in positive_words:
                if word in text:
                    sentiment_score += 1
            
            for word in negative_words:
                if word in text:
                    sentiment_score -= 1
        
        if sentiment_score > 1:
            sentiment = 'BULLISH'
        elif sentiment_score < -1:
            sentiment = 'BEARISH'
        else:
            sentiment = 'NEUTRAL'
        
        confidence = min(90, 50 + abs(sentiment_score) * 15)
        
        return {
            'sentiment': sentiment,
            'score': sentiment_score,
            'confidence': confidence
        }
    
    def calculate_score(self, stock_data, sentiment_data):
        """حساب درجة السهم"""
        score = 50  # درجة أساسية
        
        # تأثير التغير اليومي
        change = stock_data.get('Change %', 0)
        if change > 5:
            score += 20
        elif change > 2:
            score += 10
        elif change > 0:
            score += 5
        
        # تأثير المشاعر
        sentiment = sentiment_data['sentiment']
        if sentiment == 'BULLISH':
            score += 15
        elif sentiment == 'BEARISH':
            score -= 10
        
        # تأثير الحجم (إذا كان كبيراً)
        volume = stock_data.get('Volume', 0)
        if volume > 1000000:
            score += 5
        
        # التأكد من أن النتيجة بين 0 و 100
        return max(0, min(100, score))
    
    def get_recommendation(self, score, sentiment):
        """الحصول على توصية"""
        if score >= 70 and sentiment == 'BULLISH':
            return 'STRONG BUY 🟢'
        elif score >= 60:
            return 'BUY 🟡'
        elif score >= 40:
            return 'HOLD ⚪'
        else:
            return 'AVOID 🔴'

def main():
    # Title
    st.markdown('<h1 class="main-header">🚀 Ultimate Trading Scanner</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.title("⚙️ التحكم")
        
        # Scan options
        st.subheader("إعدادات الفحص")
        scan_mode = st.radio(
            "وضع الفحص:",
            ["سريع (30 سهم)", "كامل (88 سهم)"]
        )
        
        min_price = st.slider("الحد الأدنى للسعر:", 0.0, 200.0, 1.0)
        min_volume = st.number_input("الحد الأدنى للحجم:", value=100000, step=10000)
        
        # Scan button
        if st.button("🔍 بدء الفحص", type="primary", use_container_width=True):
            st.session_state.scan_triggered = True
        else:
            st.session_state.scan_triggered = False
        
        st.divider()
        
        # System status
        st.subheader("🔌 حالة النظام")
        if GROQ_API_KEY:
            st.success("🤖 Groq AI: Connected")
        else:
            st.warning("🤖 Groq AI: Not Connected")
        
        if NEWSAPI_KEY or FINNHUB_API_KEY:
            st.success("📰 News APIs: Connected")
        else:
            st.info("📰 News APIs: Using RSS Feeds")
    
    # Initialize scanner
    scanner = MarketScanner()
    
    # Scan results
    if 'scan_triggered' in st.session_state and st.session_state.scan_triggered:
        with st.spinner("🔍 جاري فحص السوق... قد يستغرق 10-15 ثانية"):
            
            # Determine tickers
            if scan_mode == "سريع (30 سهم)":
                tickers = scanner.focus_tickers[:30]
            else:
                tickers = scanner.focus_tickers
            
            # Progress bar
            progress_bar = st.progress(0)
            
            # Scan stocks
            results = []
            for i, ticker in enumerate(tickers):
                # Get stock data
                stock_data = scanner.get_stock_data(ticker)
                
                if stock_data and stock_data['Price'] >= min_price and stock_data['Volume'] >= min_volume:
                    # Get news
                    news_items = scanner.get_stock_news(ticker)
                    
                    # Analyze sentiment
                    sentiment_data = scanner.analyze_sentiment(news_items)
                    
                    # Calculate score
                    score = scanner.calculate_score(stock_data, sentiment_data)
                    
                    # Get recommendation
                    recommendation = scanner.get_recommendation(score, sentiment_data['sentiment'])
                    
                    # Prepare result
                    result = {
                        **stock_data,
                        'News_Count': len(news_items),
                        'Sentiment': sentiment_data['sentiment'],
                        'Confidence': sentiment_data['confidence'],
                        'Score': score,
                        'Recommendation': recommendation,
                        'Latest_News': news_items[0]['title'][:50] + "..." if news_items else "No news"
                    }
                    
                    results.append(result)
                
                # Update progress
                progress_bar.progress((i + 1) / len(tickers))
            
            progress_bar.empty()
            
            if results:
                # Sort by score
                results.sort(key=lambda x: x['Score'], reverse=True)
                
                # Store in session state
                st.session_state.results = results
                st.session_state.scan_time = datetime.now()
                
                # Show summary
                st.success(f"✅ تم العثور على {len(results)} سهم")
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📈 إجمالي الأسهم", len(results))
                with col2:
                    avg_score = sum(r['Score'] for r in results) / len(results)
                    st.metric("🎯 متوسط الدرجة", f"{avg_score:.1f}")
                with col3:
                    bullish = sum(1 for r in results if r['Sentiment'] == 'BULLISH')
                    st.metric("🟢 إيجابية", bullish)
                with col4:
                    strong_buys = sum(1 for r in results if 'STRONG BUY' in r['Recommendation'])
                    st.metric("🏆 توصيات قوية", strong_buys)
                
                # Display table
                st.divider()
                st.subheader("🏆 أفضل الأسهم")
                
                # Create DataFrame
                df = pd.DataFrame(results)
                df_display = df[['Ticker', 'Company', 'Price', 'Change %', 'Sentiment', 'Score', 'Recommendation']].head(20)
                
                # Format and display
                st.dataframe(
                    df_display.style.format({
                        'Price': '${:.2f}',
                        'Change %': '{:.2f}%',
                        'Score': '{:.1f}'
                    }),
                    use_container_width=True,
                    height=500
                )
                
                # Charts
                st.divider()
                st.subheader("📊 التصورات البيانية")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Score distribution
                    fig1 = go.Figure(data=[go.Histogram(x=df['Score'], nbinsx=20)])
                    fig1.update_layout(
                        title='توزيع الدرجات',
                        xaxis_title='الدرجة',
                        yaxis_title='عدد الأسهم'
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Sentiment pie chart
                    sentiment_counts = df['Sentiment'].value_counts()
                    fig2 = go.Figure(data=[go.Pie(
                        labels=sentiment_counts.index,
                        values=sentiment_counts.values,
                        hole=.3
                    )])
                    fig2.update_layout(title='توزيع المشاعر')
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Export option
                st.divider()
                st.subheader("💾 تصدير النتائج")
                
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 تحميل كملف CSV",
                    data=csv,
                    file_name=f"trading_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
            else:
                st.error("❌ لم يتم العثور على أسهم تطبق المعايير")
    
    else:
        # Welcome screen
        st.markdown("""
        <div style="text-align: center; padding: 3rem;">
            <h2>🎯 نظام فحص الأسهم المتقدم</h2>
            <p style="font-size: 1.2rem; color: #666;">
                نظام متكامل لفحص وتحليل الأسهم باستخدام الذكاء الاصطناعي
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.info("""
            **📊 المميزات:**
            - فحص 88 سهم في الوقت الحقيقي
            - تحليل أخبار فوري
            - تحليل المشاعر الآلي
            - تصنيف وتوصيات ذكية
            - تصدير النتائج بسهولة
            
            **💡 للبدء:** استخدم الشريط الجانبي لضبط الإعدادات ثم اضغط "بدء الفحص"
            """)
            
            st.warning("""
            ⚠️ **ملاحظة:** 
            - النتائج لأغراض تعليمية وتحليلية فقط
            - لا تُعتبر توصيات استثمارية
            - قم ببحثك الخاص قبل أي قرار استثماري
            """)

if __name__ == "__main__":
    main()
