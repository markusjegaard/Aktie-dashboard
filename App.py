import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# Definer aktielister
market_stocks = {
    'Danske': ['NOVO-B.CO', 'MAERSK-B.CO', 'DSV.CO', 'CARLB.CO', 'DANSKE.CO', 'NZYM-B.CO', 'ORSTED.CO'],
    'Amerikanske': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'],
    'Europæiske': ['SIE.DE', 'ASML.AS', 'LVMH.PA', 'NESN.SW', 'ROG.SW', 'TTE.PA', 'SAP.DE']
}

class StockAnalyzer:
    def __init__(self):
        self.historical_data = None
        
    def calculate_rsi(self, prices, periods=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs.iloc[-1]))
        
    def get_recommendation(self, rating):
        if rating <= 1.5:
            return 'strongBuy'
        elif rating <= 2.2:
            return 'buy'
        elif rating <= 3.2:
            return 'hold'
        elif rating <= 4.2:
            return 'sell'
        else:
            return 'strongSell'
            
    def get_recommendation_dk(self, rating):
        if rating <= 1.5:
            return 'STÆRK KØB'
        elif rating <= 2.2:
            return 'KØB'
        elif rating <= 3.2:
            return 'HOLD'
        elif rating <= 4.2:
            return 'SÆLG'
        else:
            return 'STÆRK SÆLG'

    def get_stock_data(self, symbol):
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1mo")
            info = stock.info
            
            if hist.empty or not info:
                return None
                
            current_price = hist['Close'].iloc[-1]
            
            # Beregn RSI
            rsi = self.calculate_rsi(hist['Close'])
            
            return {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': current_price,
                'target_price': info.get('targetMeanPrice', current_price),
                'high_target': info.get('targetHighPrice', current_price),
                'low_target': info.get('targetLowPrice', current_price),
                'potential_return': ((info.get('targetMeanPrice', current_price) - current_price) / current_price * 100),
                'high_return': ((info.get('targetHighPrice', current_price) - current_price) / current_price * 100),
                'low_return': ((info.get('targetLowPrice', current_price) - current_price) / current_price * 100),
                'recommendation': self.get_recommendation(info.get('recommendationMean', 3.0)),
                'recommendation_dk': self.get_recommendation_dk(info.get('recommendationMean', 3.0)),
                'buy_rating': info.get('recommendationMean', 3.0),
                'analysts_total': info.get('numberOfAnalystOpinions', 0),
                'rsi': rsi,
                'company_info': {
                    'description': info.get('longBusinessSummary', 'Ingen beskrivelse tilgængelig'),
                    'sector': info.get('sector', 'Ukendt sektor'),
                    'industry': info.get('industry', 'Ukendt industri'),
                    'website': info.get('website', '#'),
                    'employees': info.get('fullTimeEmployees', 'Ukendt')
                }
            }
        except Exception as e:
            print(f"Fejl ved hentning af {symbol}: {str(e)}")
            return None

def create_dashboard():
    st.set_page_config(layout="wide", page_title="Aktie Anbefalinger")
    
    # Tilføj custom CSS for dark theme
    st.markdown("""
        <style>
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        .stExpander {
            background-color: #262730;
            border: 1px solid #4B4B4B;
        }
        .stMarkdown {
            color: #FAFAFA;
        }
        section[data-testid="stSidebar"] {
            background-color: #262730;
            color: #FAFAFA;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("Aktie Anbefalinger og Fremtidige Estimater")
    
    # Sidebar filtre
    st.sidebar.header("Filtre")
    
    selected_markets = st.sidebar.multiselect(
        "Vælg markeder",
        options=list(market_stocks.keys()),
        default=list(market_stocks.keys())
    )
    
    show_only_strong_buy = st.sidebar.checkbox("Vis kun Strong Buy anbefalinger")
    hide_risk = st.sidebar.checkbox("Fjern aktier med risiko for tab")
    
    min_rsi = st.sidebar.slider("Minimum RSI", 0, 100, 0)
    max_rsi = st.sidebar.slider("Maximum RSI", 0, 100, 100)
    min_analysts = st.sidebar.slider("Minimum antal analytikere", 0, 20, 3)
    min_return = st.sidebar.slider("Minimum forventet afkast %", -100, 100, 0)
    
    # Rating guide i sidebar
    st.sidebar.markdown("""
    ### Rating Forklaring:
    - 1.0-1.5: Stærk Køb (Bedst)
    - 1.6-2.2: Køb
    - 2.3-3.2: Hold
    - 3.3-4.2: Sælg
    - 4.3-5.0: Stærk Sælg
    """)
    
    # Hent og filtrer aktiedata
    analyzer = StockAnalyzer()
    stock_data = []
    
    for market in selected_markets:
        for symbol in market_stocks[market]:
            data = analyzer.get_stock_data(symbol)
            if data:
                stock_data.append(data)
    
    # Filtrer data
    filtered_data = [
        stock for stock in stock_data 
        if (not show_only_strong_buy or stock['recommendation'] == 'strongBuy')
        and stock['analysts_total'] >= min_analysts
        and stock['potential_return'] >= min_return
        and min_rsi <= stock['rsi'] <= max_rsi
        and (not hide_risk or stock['low_return'] >= 0)
    ]
    
    if not filtered_data:
        st.warning("Ingen aktier matcher de valgte kriterier. Prøv at justere filtrene.")
        return
        
    # Vis aktier
    for stock in filtered_data:
        with st.expander(f"{stock['name']} ({stock['symbol']})"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write(f"Sektor: {stock['company_info']['sector']}")
                st.write(f"Industri: {stock['company_info']['industry']}")
                st.write(f"Antal ansatte: {stock['company_info']['employees']}")
                
            with col2:
                st.write(stock['company_info']['description'])
            
            st.markdown("---")
            
            # Analytiker vurdering og estimater
            col3, col4 = st.columns(2)
            
            with col3:
                st.subheader("Nuværende Status")
                st.write(f"Aktuel Kurs: {stock['current_price']:.2f}")
                st.write(f"Konsensus Målkurs: {stock['target_price']:.2f}")
                st.write(f"Forventet Afkast: {stock['potential_return']:.1f}%")
                st.write(f"RSI: {stock['rsi']:.1f}")
                st.write(f"Anbefaling: {stock['recommendation_dk']}")
                st.write(f"Rating: {stock['buy_rating']:.1f}/5.0")
                st.write(f"Antal Analytikere: {stock['analysts_total']}")
            
            with col4:
                st.subheader("12 Måneders Estimater")
                st.write(f"Højeste Kursmål: {stock['high_target']:.2f} (+{stock['high_return']:.1f}%)")
                st.write(f"Laveste Kursmål: {stock['low_target']:.2f} ({stock['low_return']:.1f}%)")
                
                # Gauge chart
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = stock['potential_return'],
                    title = {'text': "Forventet Afkast %"},
                    gauge = {
                        'axis': {'range': [stock['low_return'], stock['high_return']]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [stock['low_return'], stock['potential_return']], 'color': "lightgray"},
                            {'range': [stock['potential_return'], stock['high_return']], 'color': "gray"}
                        ],
                    }
                ))
                
                fig.update_layout(
                    paper_bgcolor = '#262730',
                    font = {'color': '#FAFAFA'},
                    plot_bgcolor = '#262730'
                )
                
                st.plotly_chart(fig)

if __name__ == "__main__":
    create_dashboard()
