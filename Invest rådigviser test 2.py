from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import json
import plotly.io as pio
import streamlit as st

# Sæt standard renderer til browser
pio.renderers.default = "browser"

# Test plotly configuration
print("Tilgængelige plotly renderers:", pio.renderers)

class StockAnalyzer:
    def __init__(self):
        self.historical_data = None
        self.sma20_full = None
        self.sma50_full = None
        self.rsi_full = None
        self.historical_recommendations = {}

    def calculate_rsi(self, prices, periods=14):
        # Beregn RSI
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

    def get_stock_data(self, symbol: str) -> dict:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1mo")
            info = stock.info
            
            if hist.empty or not info:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            # Hent virksomhedsinformation
            company_info = {
                'description': info.get('longBusinessSummary', 'Ingen beskrivelse tilgængelig'),
                'logo_url': info.get('logo_url', None),
                'sector': info.get('sector', 'Ukendt sektor'),
                'industry': info.get('industry', 'Ukendt industri'),
                'website': info.get('website', '#'),
                'employees': info.get('fullTimeEmployees', 'Ukendt')
            }
            
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
                'company_info': company_info
            }
        except Exception as e:
            st.error(f"Fejl ved {symbol}: {str(e)}")
            return None

    def plot_analysis(self, symbol: str, detailed_rec: dict):
        """Lav interaktiv graf med Plotly"""
        if self.historical_data is None or detailed_rec is None:
            print("Ingen data tilgængelig for plotting")
            return

        # Opret subplot med pris, volumen og RSI
        fig = make_subplots(rows=4, cols=1, 
                           subplot_titles=(
                               f'{symbol} Aktiekurs og Tekniske Indikatorer', 
                               'Volumen og Markedsværdi',
                               'RSI (Relative Strength Index)',
                               'Risiko Metrics'
                           ),
                           vertical_spacing=0.08,
                           row_heights=[0.4, 0.2, 0.2, 0.2])

        # Tilføj candlestick chart
        fig.add_trace(go.Candlestick(
            x=self.historical_data.index,
            open=self.historical_data['Open'],
            high=self.historical_data['High'],
            low=self.historical_data['Low'],
            close=self.historical_data['Close'],
            name='Pris'
        ), row=1, col=1)

        # Tilføj SMA linjer
        fig.add_trace(go.Scatter(
            x=self.historical_data.index,
            y=self.sma20_full,
            name='SMA20',
            line=dict(color='orange', width=2)
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=self.historical_data.index,
            y=self.sma50_full,
            name='SMA50',
            line=dict(color='blue', width=2)
        ), row=1, col=1)

        # Tilføj volumen
        colors = ['red' if row['Open'] - row['Close'] > 0 
                 else 'green' for index, row in self.historical_data.iterrows()]
        
        fig.add_trace(go.Bar(
            x=self.historical_data.index,
            y=self.historical_data['Volume'],
            name='Volumen',
            marker_color=colors
        ), row=2, col=1)

        # Tilføj RSI
        fig.add_trace(go.Scatter(
            x=self.historical_data.index,
            y=self.rsi_full,
            name='RSI',
            line=dict(color='purple', width=2)
        ), row=3, col=1)

        # Tilføj overbought/oversold linjer for RSI
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        # Opdater layout
        fig.update_layout(
            title=dict(
                text=f"Udvidet Teknisk Analyse for {detailed_rec['name']} ({symbol})",
                y=0.95,
                x=0.5,
                xanchor='center',
                yanchor='top'
            ),
            xaxis_rangeslider_visible=False,
            height=1200,
            showlegend=True,
            template="plotly_white"
        )

        # Tilføj informationsbokse
        fig.add_annotation(
            x=0.01,
            y=0.99,
            xref="paper",
            yref="paper",
            text=f"<b>Aktie Information:</b><br>" +
                 f"Pris: {detailed_rec['current_price']:.2f} DKK<br>" +
                 f"Målpris: {detailed_rec['target_price']:.2f} DKK<br>" +
                 f"Potentielt Afkast: {detailed_rec['potential_return']:.1f}%<br>" +
                 f"Markedsværdi: {detailed_rec['market_cap']/1e9:.1f} mia. DKK",
            showarrow=False,
            font=dict(size=10),
            align="left",
            bgcolor="white",
            bordercolor="black",
            borderwidth=1
        )

        # Vis grafen
        fig.show()

    def get_detailed_recommendation(self, stock_data: dict) -> dict:
        """Genererer en detaljeret investeringsanbefaling med begrundelse"""
        if stock_data is None:
            return {
                'recommendation': 'INGEN ANBEFALING',
                'points': 0,
                'reasons': ['Kunne ikke hente aktiedata'],
                'technical_summary': {}
            }
            
        points = 0
        reasons = []
        
        # Analyse af trend
        if stock_data['trend'] == 'Bullish':
            points += 2
            reasons.append("Positiv trend: 20-dages SMA er over 50-dages SMA")
        elif stock_data['trend'] == 'Bearish':
            points -= 2
            reasons.append("Negativ trend: 20-dages SMA er under 50-dages SMA")
            
        # RSI analyse
        if stock_data['rsi'] > 70:
            points -= 2
            reasons.append(f"Overkøbt: RSI er høj ({stock_data['rsi']:.1f})")
        elif stock_data['rsi'] < 30:
            points += 2
            reasons.append(f"Oversolgt: RSI er lav ({stock_data['rsi']:.1f})")
        elif 40 <= stock_data['rsi'] <= 60:
            points += 1
            reasons.append(f"RSI er i neutralt område ({stock_data['rsi']:.1f})")
            
        # Momentum analyse
        price = stock_data['current_price']
        sma20 = self.sma20_full.iloc[-1]
        price_vs_sma20 = ((price - sma20) / sma20) * 100
        
        if price_vs_sma20 > 5:
            points -= 1
            reasons.append(f"Aktien handler {price_vs_sma20:.1f}% over 20-dages SMA")
        elif price_vs_sma20 < -5:
            points += 1
            reasons.append(f"Aktien handler {abs(price_vs_sma20):.1f}% under 20-dages SMA")
            
        # Generer den endelige anbefaling
        if points >= 3:
            recommendation = "STRONG BUY"
        elif points > 0:
            recommendation = "BUY"
        elif points < -3:
            recommendation = "STRONG SELL"
        elif points < 0:
            recommendation = "SELL"
        else:
            recommendation = "HOLD"
            
        return {
            'recommendation': recommendation,
            'points': points,
            'reasons': reasons,
            'current_price': price,
            'technical_summary': {
                'trend': stock_data['trend'],
                'rsi': stock_data['rsi'],
                'price_vs_sma20': f"{price_vs_sma20:.1f}%"
            }
        }

    def analyze_sentiment(self, news_text: str) -> dict:
        # Simpel sentiment analyse baseret på nøgleord
        positive_words = ['stiger', 'vækst', 'positiv', 'forbedring', 'succes', 'opgang']
        negative_words = ['falder', 'nedgang', 'negativ', 'tab', 'konkurs', 'risiko']
        
        news_text = news_text.lower()
        positive_count = sum(1 for word in positive_words if word in news_text)
        negative_count = sum(1 for word in negative_words if word in news_text)
        
        if positive_count > negative_count:
            sentiment = 'POSITIVE'
        elif negative_count > positive_count:
            sentiment = 'NEGATIVE'
        else:
            sentiment = 'NEUTRAL'
            
        return {
            'sentiment': sentiment,
            'confidence': abs(positive_count - negative_count) / (positive_count + negative_count + 1)
        }

class AIInvestmentAssistant:
    def __init__(self):
        self.stock_analyzer = StockAnalyzer()
        self.alerts = {}

    def get_market_insight(self, symbol: str, news_text: str = None) -> dict:
        """Generate comprehensive market insight for a stock"""
        # Get technical analysis
        stock_data = self.stock_analyzer.get_stock_data(symbol)
        if stock_data is None:
            return {
                'symbol': symbol,
                'error': 'Kunne ikke hente aktiedata'
            }
        
        # Get detailed recommendation
        detailed_rec = self.stock_analyzer.get_detailed_recommendation(stock_data)
        
        # Plot the analysis with detailed recommendation
        self.stock_analyzer.plot_analysis(symbol, detailed_rec)
        
        # Get sentiment if news provided
        sentiment_data = {}
        if news_text:
            sentiment_data = self.stock_analyzer.analyze_sentiment(news_text)
            if sentiment_data['sentiment'] == 'POSITIVE':
                detailed_rec['reasons'].append(f"Positiv nyhedssentiment med {sentiment_data['confidence']:.1%} konfidens")
            elif sentiment_data['sentiment'] == 'NEGATIVE':
                detailed_rec['reasons'].append(f"Negativ nyhedssentiment med {sentiment_data['confidence']:.1%} konfidens")
        
        return {
            'symbol': symbol,
            'market_status': {
                'current_price': stock_data['current_price'],
                'technical_indicators': detailed_rec['technical_summary'],
                'sentiment': sentiment_data
            },
            'analysis': {
                'recommendation': detailed_rec['recommendation'],
                'reasons': detailed_rec['reasons'],
                'technical_score': detailed_rec['points']
            }
        }

class StockAnalystRecommendations:
    def __init__(self):
        self.recommendations = []
        self.top_stocks = []
        
    def fetch_analyst_recommendations(self):
        """
        Henter aktie anbefalinger.
        Da Nordnet ikke har et offentligt API, bruger vi Yahoo Finance som eksempel.
        """
        # Liste over danske aktier vi vil analysere
        danish_stocks = [
            'NOVO-B.CO', 'MAERSK-B.CO', 'CARLB.CO', 'VWS.CO',
            'DSV.CO', 'DANSKE.CO', 'NZYM-B.CO', 'ORSTED.CO',
            'NETC.CO', 'ROCK-B.CO', 'GN.CO', 'CHR.CO',
            'DEMANT.CO', 'FLS.CO', 'TRYG.CO'
        ]
        
        for symbol in danish_stocks:
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                
                # Hent anbefalinger og analyser
                recommendation = {
                    'symbol': symbol,
                    'name': info.get('longName', symbol),
                    'current_price': info.get('currentPrice', 0),
                    'target_price': info.get('targetMeanPrice', 0),
                    'recommendation': info.get('recommendationKey', 'none'),
                    'analysts_total': info.get('numberOfAnalystOpinions', 0),
                    'buy_ratings': info.get('recommendationMean', 0),
                    'potential_return': 0
                }
                
                # Beregn potentielt afkast
                if recommendation['current_price'] and recommendation['target_price']:
                    recommendation['potential_return'] = (
                        (recommendation['target_price'] - recommendation['current_price']) 
                        / recommendation['current_price'] * 100
                    )
                
                self.recommendations.append(recommendation)
                
            except Exception as e:
                print(f"Kunne ikke hente data for {symbol}: {str(e)}")
                
    def filter_strong_buys(self):
        """Filtrer aktier med stærke købs-anbefalinger"""
        strong_buys = [
            rec for rec in self.recommendations
            if rec['recommendation'] in ['strongBuy', 'buy']
            and rec['analysts_total'] >= 3  # Minimum 3 analytikere
            and rec['potential_return'] > 0
        ]
        
        # Sorter efter potentielt afkast
        strong_buys.sort(key=lambda x: x['potential_return'], reverse=True)
        
        # Tag top 10
        self.top_stocks = strong_buys[:10]
        
    def generate_report(self):
        """Genererer rapport med top 10 aktier"""
        if not self.top_stocks:
            return "Ingen aktier fundet med stærke købs-anbefalinger"
            
        # Opret DataFrame for pæn visning
        df = pd.DataFrame(self.top_stocks)
        df = df[[
            'name', 'symbol', 'current_price', 
            'target_price', 'potential_return', 'analysts_total', 'buy_ratings'
        ]]
        
        # Formater kolonner
        df['potential_return'] = df['potential_return'].round(2).astype(str) + '%'
        df['current_price'] = df['current_price'].round(2).astype(str) + ' DKK'
        df['target_price'] = df['target_price'].round(2).astype(str) + ' DKK'
        
        # Omdøb kolonner til dansk
        df.columns = [
            'Virksomhed', 'Symbol', 'Nuværende Pris', 
            'Målpris', 'Potentielt Afkast', 'Antal Analytikere', 'Gennemsnitlig Rating'
        ]
        
        return df
        
    def save_to_json(self, filename='top_stocks.json'):
        """Gem resultater som JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'top_stocks': self.top_stocks
            }, f, ensure_ascii=False, indent=4)

def create_dashboard():
    # Konfigurer dark theme
    st.set_page_config(
        layout="wide",
        page_title="Aktie Anbefalinger",
        initial_sidebar_state="expanded"
    )

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
        section[data-testid="stSidebar"] .stMarkdown {
            color: #FAFAFA;
        }
        section[data-testid="stSidebar"] .stCheckbox {
            color: #FAFAFA;
        }
        section[data-testid="stSidebar"] .stSlider {
            color: #FAFAFA;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("Aktie Anbefalinger og Fremtidige Estimater")
    
    # Definér aktielister
    market_stocks = {
        'Danske': [
            'NOVO-B.CO', 'MAERSK-B.CO', 'CARL-B.CO', 'VWS.CO', 'DSV.CO',
            'DANSKE.CO', 'NZYM-B.CO', 'ORSTED.CO', 'COLO-B.CO', 'ISS.CO',
            'GN.CO', 'TRYG.CO', 'AMBU-B.CO', 'RBREW.CO', 'DEMANT.CO'
        ],
        'Amerikanske': [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM',
            'V', 'WMT', 'PG', 'MA', 'UNH', 'HD', 'BAC'
        ],
        'Europæiske': [
            'ASML.AS', 'LVMH.PA', 'SAP.DE', 'SIEMENS.DE', 'TOTALENERGIES.PA',
            'NESN.SW', 'ROG.SW', 'NOVN.SW', 'AIR.PA', 'BAS.DE'
        ]
    }
    
    # Sidebar filtre
    st.sidebar.header("Filtre")
    
    # Markedsvalg
    selected_markets = st.sidebar.multiselect(
        "Vælg markeder",
        options=list(market_stocks.keys()),
        default=list(market_stocks.keys())
    )
    
    # Tilføj nyt filter for risiko
    hide_risk = st.sidebar.checkbox("Fjern aktier med risiko for tab")
    
    # Eksisterende filtre
    show_only_strong_buy = st.sidebar.checkbox("Vis kun Strong Buy anbefalinger")
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
    
    # Hent aktiedata
    with st.spinner('Analyserer aktier...'):
        analyzer = StockAnalyzer()
        stock_data = []
        
        selected_stocks = []
        for market in selected_markets:
            selected_stocks.extend(market_stocks[market])
            
        for symbol in selected_stocks:
            data = analyzer.get_stock_data(symbol)
            if data:
                stock_data.append(data)
    
    # Opdater filtrering med nyt risikofilter
    filtered_data = [
        stock for stock in stock_data 
        if (not show_only_strong_buy or stock['recommendation'] == 'strongBuy')
        and stock['analysts_total'] >= min_analysts
        and stock['potential_return'] >= min_return
        and min_rsi <= stock['rsi'] <= max_rsi
        and (not hide_risk or stock['low_return'] >= 0)  # Nyt filter for risiko
    ]
    
    if not filtered_data:
        st.warning("Ingen aktier matcher de valgte kriterier. Prøv at justere filtrene.")
        return
        
    # Vis aktier
    for stock in filtered_data:
        recommendation_colors = {
            'strongBuy': '#00FF00',
            'buy': '#90EE90',
            'hold': '#FFD700',
            'sell': '#FFB6C6',
            'strongSell': '#FF0000'
        }
        
        header_color = recommendation_colors.get(stock['recommendation'], '#FFFFFF')
        
        with st.expander(f"{stock['name']} ({stock['symbol']})"):
            # Analytiker sektion med rating forklaring
            st.markdown(f"""
                <div style='background-color: #262730; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
                    <h2 style='color: {header_color}; margin-bottom: 10px;'>
                        {stock['recommendation_dk']}
                    </h2>
                    <p style='color: #FAFAFA; font-size: 16px;'>
                        Analytiker Rating: {stock['buy_rating']:.1f}/5.0
                    </p>
                    <p style='color: #FAFAFA; font-size: 16px;'>
                        Antal Analytikere: {stock['analysts_total']}
                    </p>
                    <div style='background-color: #1E1E1E; padding: 10px; border-radius: 5px; margin-top: 10px;'>
                        <p style='color: #FAFAFA; font-size: 14px; margin: 0;'>Rating Guide:</p>
                        <p style='color: #FAFAFA; font-size: 12px; margin: 2px 0;'>1.0-1.5: Stærk Køb (Bedst)</p>
                        <p style='color: #FAFAFA; font-size: 12px; margin: 2px 0;'>1.6-2.2: Køb</p>
                        <p style='color: #FAFAFA; font-size: 12px; margin: 2px 0;'>2.3-3.2: Hold</p>
                        <p style='color: #FAFAFA; font-size: 12px; margin: 2px 0;'>3.3-4.2: Sælg</p>
                        <p style='color: #FAFAFA; font-size: 12px; margin: 2px 0;'>4.3-5.0: Stærk Sælg</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Virksomhedsinformation
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if stock['company_info']['logo_url']:
                    st.image(stock['company_info']['logo_url'], width=200)
                st.markdown(f"""
                    <div style='background-color: #262730; padding: 10px; border-radius: 5px;'>
                        <p style='color: #FAFAFA;'>Sektor: {stock['company_info']['sector']}</p>
                        <p style='color: #FAFAFA;'>Industri: {stock['company_info']['industry']}</p>
                        <p style='color: #FAFAFA;'>Antal ansatte: {stock['company_info']['employees']}</p>
                    </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                    <div style='background-color: #262730; padding: 20px; border-radius: 10px;'>
                        <p style='color: #FAFAFA;'>{stock['company_info']['description']}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
            
            # Analytiker vurdering og estimater
            col3, col4 = st.columns(2)
            
            with col3:
                st.markdown("""
                    <div style='background-color: #262730; padding: 20px; border-radius: 10px;'>
                        <h3 style='color: #FAFAFA;'>Nuværende Status</h3>
                """, unsafe_allow_html=True)
                st.write(f"Aktuel Kurs: {stock['current_price']:.2f}")
                st.write(f"Konsensus Målkurs: {stock['target_price']:.2f}")
                st.write(f"Forventet Afkast: {stock['potential_return']:.1f}%")
                st.write(f"RSI: {stock['rsi']:.1f}")
                st.markdown("</div>", unsafe_allow_html=True)
            
            with col4:
                st.markdown("""
                    <div style='background-color: #262730; padding: 20px; border-radius: 10px;'>
                        <h3 style='color: #FAFAFA;'>12 Måneders Estimater</h3>
                """, unsafe_allow_html=True)
                st.write(f"Højeste Kursmål: {stock['high_target']:.2f} (+{stock['high_return']:.1f}%)")
                st.write(f"Laveste Kursmål: {stock['low_target']:.2f} ({stock['low_return']:.1f}%)")
                
                # Opdater gauge chart med mørkt tema
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = stock['potential_return'],
                    title = {'text': "Forventet Afkast %", 'font': {'color': '#FAFAFA'}},
                    gauge = {
                        'axis': {
                            'range': [stock['low_return'], stock['high_return']],
                            'tickfont': {'color': '#FAFAFA'}
                        },
                        'bar': {'color': "#00FF00"},
                        'bgcolor': "#262730",
                        'borderwidth': 2,
                        'bordercolor': "#4B4B4B",
                        'steps': [
                            {'range': [stock['low_return'], stock['potential_return']], 'color': "#1E1E1E"},
                            {'range': [stock['potential_return'], stock['high_return']], 'color': "#2E2E2E"}
                        ],
                    }
                ))
                
                fig.update_layout(
                    paper_bgcolor = '#0E1117',
                    font = {'color': '#FAFAFA'},
                    plot_bgcolor = '#0E1117'
                )
                
                st.plotly_chart(fig)
                st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    create_dashboard()

def vis_danske_aktier():
    import yfinance as yf
    msci = yf.download("^OMXC25")
    print("Tilgængelige danske aktier i OMXC25:")
    for symbol in msci.columns.levels[1]:
        print(f"- {symbol}.CPH")

# Kør denne funktion for at se listen
vis_danske_aktier() 