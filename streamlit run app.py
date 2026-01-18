# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from market_fetcher import MarketDataFetcher
from news_aggregator import NewsAggregator
from sentiment_analyzer import SentimentAnalyzer
from scoring_engine import ScoringEngine
from report_generator import ReportGenerator

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
    }
    .stocks-table {
        font-size: 0.9rem;
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
</style>
""", unsafe_allow_html=True)

class TradingScannerApp:
    def __init__(self):
        self.data_fetcher = MarketDataFetcher()
        self.news_aggregator = NewsAggregator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.scoring_engine = ScoringEngine()
        self.report_generator = ReportGenerator()
        
        # Initialize session state
        if 'scan_results' not in st.session_state:
            st.session_state.scan_results = None
        if 'last_scan_time' not in st.session_state:
            st.session_state.last_scan_time = None
        
    def run(self):
        # Header
        st.markdown('<h1 class="main-header">🚀 Ultimate Trading Scanner v4.0</h1>', unsafe_allow_html=True)
        
        # Sidebar
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
            st.title("⚙️ التحكم")
            
            # Scan options
            st.subheader("إعدادات الفحص")
            scan_type = st.radio(
                "نوع الفحص:",
                ["سريع (Top 30)", "كامل (جميع الأسهم)"],
                index=0
            )
            
            sectors = st.multiselect(
                "القطاعات:",
                ["التكنولوجيا", "الصحة", "الطاقة", "المالية", "الخدمات", "جميع القطاعات"],
                default=["جميع القطاعات"]
            )
            
            min_score = st.slider("الحد الأدنى للدرجة:", 0, 100, 50)
            
            # Scan button
            if st.button("🔍 بدء الفحص", type="primary", use_container_width=True):
                with st.spinner("جاري فحص السوق..."):
                    results = self.perform_scan(
                        scan_type=scan_type,
                        sectors=sectors,
                        min_score=min_score
                    )
                    st.session_state.scan_results = results
                    st.session_state.last_scan_time = datetime.now()
                    st.rerun()
            
            st.divider()
            
            # API Status
            st.subheader("🔌 حالة النظام")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📰 مصادر الأخبار", "5/5", "✅")
            with col2:
                st.metric("🤖 الذكاء الاصطناعي", "متصل", "✅")
            
            st.divider()
            
            # Export options
            st.subheader("💾 تصدير النتائج")
            if st.session_state.scan_results:
                csv = self.results_to_csv()
                st.download_button(
                    label="📥 تحميل CSV",
                    data=csv,
                    file_name=f"scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        
        # Main Content
        if st.session_state.scan_results:
            self.display_results()
        else:
            self.display_welcome()
    
    def perform_scan(self, scan_type, sectors, min_score):
        """إجراء فحص السوق"""
        # Determine tickers based on scan type
        if scan_type == "سريع (Top 30)":
            tickers = self.data_fetcher.focus_tickers[:30]
        else:
            tickers = self.data_fetcher.focus_tickers
        
        # Fetch data in parallel
        stocks_data = self.data_fetcher.fetch_multiple_stocks_data(
            tickers=tickers,
            max_workers=10
        )
        
        # Filter by sectors if specified
        if "جميع القطاعات" not in sectors:
            # Translate Arabic sectors to English
            sector_mapping = {
                "التكنولوجيا": "Technology",
                "الصحة": "Healthcare",
                "الطاقة": "Energy",
                "المالية": "Financial Services",
                "الخدمات": "Communication Services"
            }
            english_sectors = [sector_mapping.get(s, s) for s in sectors]
            stocks_data = [
                s for s in stocks_data 
                if s.get('Sector') in english_sectors
            ]
        
        # Process top 20 stocks with news analysis
        enhanced_stocks = []
        top_stocks = stocks_data[:20]
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, stock in enumerate(top_stocks):
            ticker = stock['Ticker']
            status_text.text(f"📊 تحليل {ticker}...")
            
            try:
                # Get news
                news = self.news_aggregator.get_stock_news(ticker, max_articles=3)
                
                # Analyze sentiment
                sentiment = self.sentiment_analyzer.analyze_sentiment(news, ticker)
                
                # Calculate score
                score_result = self.scoring_engine.calculate_comprehensive_score(stock, sentiment)
                
                # Create enhanced record
                enhanced_stock = {
                    **stock,
                    'News_Count': len(news),
                    'News_Sentiment': sentiment['sentiment'],
                    'Sentiment_Score': sentiment['score'],
                    'Confidence': sentiment['confidence'],
                    'Catalysts': ", ".join(sentiment['catalysts']) if sentiment['catalysts'] else "None",
                    'Keywords': ", ".join(sentiment['keywords'][:3]) if sentiment['keywords'] else "",
                    'Latest_News': news[0]['title'][:50] + "..." if news else "No news",
                    'Score': score_result['total_score'],
                    'Risk_Level': score_result['risk_level'],
                    'Recommendation': score_result['recommendation']
                }
                
                enhanced_stocks.append(enhanced_stock)
                
            except Exception as e:
                st.error(f"خطأ في {ticker}: {str(e)[:50]}")
                continue
            
            # Update progress
            progress_bar.progress((i + 1) / len(top_stocks))
        
        progress_bar.empty()
        status_text.empty()
        
        # Filter by minimum score
        enhanced_stocks = [s for s in enhanced_stocks if s['Score'] >= min_score]
        
        # Sort by score
        enhanced_stocks.sort(key=lambda x: x['Score'], reverse=True)
        
        return enhanced_stocks
    
    def display_results(self):
        """عرض النتائج"""
        results = st.session_state.scan_results
        
        # Summary Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📈 إجمالي الأسهم", len(results))
        with col2:
            avg_score = sum(s['Score'] for s in results) / len(results)
            st.metric("🎯 متوسط الدرجة", f"{avg_score:.1f}")
        with col3:
            bullish = sum(1 for s in results if s['News_Sentiment'] == 'BULLISH')
            st.metric("🟢 إيجابية", bullish)
        with col4:
            if st.session_state.last_scan_time:
                st.metric("🕒 آخر تحديث", st.session_state.last_scan_time.strftime("%H:%M"))
        
        st.divider()
        
        # Top Stocks Table
        st.subheader("🏆 أفضل الأسهم")
        
        # Create DataFrame for display
        df_display = pd.DataFrame(results)
        
        # Format columns
        if not df_display.empty:
            df_display = df_display[[
                'Ticker', 'Company', 'Price', 'Change %', 
                'News_Sentiment', 'Score', 'Risk_Level', 'Recommendation'
            ]]
            
            # Apply formatting
            def color_sentiment(val):
                if val == 'BULLISH':
                    return 'color: #28a745'
                elif val == 'BEARISH':
                    return 'color: #dc3545'
                else:
                    return 'color: #6c757d'
            
            def color_score(val):
                if val >= 70:
                    return 'background-color: #d4edda'
                elif val >= 50:
                    return 'background-color: #fff3cd'
                else:
                    return 'background-color: #f8d7da'
            
            # Display styled table
            st.dataframe(
                df_display.style
                .applymap(color_sentiment, subset=['News_Sentiment'])
                .applymap(color_score, subset=['Score'])
                .format({
                    'Price': '${:.2f}',
                    'Change %': '{:.2f}%',
                    'Score': '{:.1f}'
                }),
                use_container_width=True,
                height=400
            )
        
        # Charts
        st.divider()
        st.subheader("📊 التصورات البيانية")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Score Distribution
            fig1 = go.Figure(data=[go.Histogram(x=df_display['Score'], nbinsx=20)])
            fig1.update_layout(
                title='توزيع الدرجات',
                xaxis_title='الدرجة',
                yaxis_title='عدد الأسهم',
                template='plotly_white'
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Sentiment Pie Chart
            sentiment_counts = df_display['News_Sentiment'].value_counts()
            fig2 = go.Figure(data=[go.Pie(
                labels=sentiment_counts.index,
                values=sentiment_counts.values,
                hole=.3
            )])
            fig2.update_layout(
                title='توزيع المشاعر',
                template='plotly_white'
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Detailed Analysis
        st.divider()
        st.subheader("🔍 تحليل مفصل")
        
        if not df_display.empty:
            selected_ticker = st.selectbox(
                "اختر سهم للتحليل المفصل:",
                df_display['Ticker'].tolist()
            )
            
            if selected_ticker:
                stock_details = next(
                    (s for s in results if s['Ticker'] == selected_ticker), 
                    None
                )
                
                if stock_details:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 📈 البيانات الأساسية")
                        st.metric("السعر", f"${stock_details['Price']:.2f}")
                        st.metric("التغير اليومي", f"{stock_details['Change %']:.2f}%")
                        st.metric("الحجم النسبي", f"{stock_details['Rel_Volume']:.2f}x")
                        st.metric("القيمة السوقية", f"{stock_details['Market_Cap_B']:.2f}B")
                    
                    with col2:
                        st.markdown("### 📰 تحليل الأخبار")
                        st.metric("المشاعر", stock_details['News_Sentiment'])
                        st.metric("الثقة", f"{stock_details['Confidence']}%")
                        st.metric("المحفزات", stock_details['Catalysts'])
                        
                        if stock_details['Latest_News'] != 'No news':
                            with st.expander("آخر الأخبار"):
                                st.write(stock_details['Latest_News'])
    
    def display_welcome(self):
        """عرض شاشة الترحيب"""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=200)
            
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <h2>مرحباً بك في Ultimate Trading Scanner</h2>
                <p style="color: #666; font-size: 1.1rem;">
                    نظام متكامل لفحص الأسهم باستخدام الذكاء الاصطناعي وتحليل الأخبار في الوقت الحقيقي
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("""
            **🎯 الميزات المتوفرة:**
            - 📊 فحص 88 سهم في الوقت الحقيقي
            - 📰 تحليل الأخبار من 10+ مصادر
            - 🤖 تحليل المشاعر باستخدام Groq AI
            - 📈 مؤشرات فنية متقدمة (RSI، المتوسطات المتحركة)
            - ⚠️ تقييم المخاطر والتوصيات
            """)
            
            st.warning("💡 **تعليمات سريعة:** استخدم الشريط الجانبي لبدء الفحص الأول!")
    
    def results_to_csv(self):
        """تحويل النتائج إلى CSV"""
        if st.session_state.scan_results:
            df = pd.DataFrame(st.session_state.scan_results)
            return df.to_csv(index=False, encoding='utf-8-sig')
        return ""

def main():
    app = TradingScannerApp()
    app.run()

if __name__ == "__main__":
    main()
