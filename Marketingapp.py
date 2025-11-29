"""
Marketing Analytics Agent - Streamlit UI v3.1
Enhanced with 19+ Visualization Types for Hackathon Demo - December 2024

Run with: streamlit run streamlit_marketing_analytics_v3_1.py
"""

import warnings
warnings.filterwarnings('ignore')

# Suppress Streamlit threading warnings
import logging
logging.getLogger('streamlit.runtime.scriptrunner_utils.script_run_context').setLevel(logging.ERROR)

import streamlit as st

# Must set page config first before any other st commands
st.set_page_config(
    page_title="Marketing Analytics Agent | MetLife",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

import anthropic
import json
from typing import Any, Dict, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import numpy as np

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "query_count" not in st.session_state:
    st.session_state.query_count = 0
if "tools_used" not in st.session_state:
    st.session_state.tools_used = set()
if "total_response_time" not in st.session_state:
    st.session_state.total_response_time = 0
if "last_input" not in st.session_state:
    st.session_state.last_input = ""
if "demo_step" not in st.session_state:
    st.session_state.demo_step = 0
if "show_gallery" not in st.session_state:
    st.session_state.show_gallery = False

# ============================================================================
# CUSTOM CSS FOR BETTER STYLING
# ============================================================================
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 600;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #2d5a87;
        margin-bottom: 1rem;
    }
    .metric-card h3 {
        margin: 0;
        font-size: 0.85rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e3a5f;
        margin: 0.25rem 0;
    }
    
    /* Anomaly alert card */
    .anomaly-card {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #f59e0b;
        margin-bottom: 1rem;
    }
    .anomaly-card.high {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border-left-color: #ef4444;
    }
    .anomaly-card.opportunity {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border-left-color: #10b981;
    }
    
    /* Campaign brief card */
    .brief-card {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #3b82f6;
        margin-bottom: 1rem;
    }
    
    /* Tool badge */
    .tool-badge {
        display: inline-block;
        background: #e8f4f8;
        color: #2d5a87;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        margin: 0.25rem;
    }
    .tool-badge.new {
        background: #d1fae5;
        color: #065f46;
    }
    
    /* Query card */
    .query-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.2s;
    }
    .query-card:hover {
        background: #eef2ff;
        border-color: #2d5a87;
    }
    
    /* Data source pills */
    .source-pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
        margin: 0.1rem;
    }
    .source-marketo { background: #fce7f3; color: #9d174d; }
    .source-adobe { background: #fee2e2; color: #991b1b; }
    .source-6sense { background: #dbeafe; color: #1e40af; }
    .source-salesforce { background: #d1fae5; color: #065f46; }
    .source-pathfactory { background: #fef3c7; color: #92400e; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Button styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Feature highlight */
    .feature-highlight {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        display: inline-block;
        font-weight: 600;
        color: #92400e;
        margin-bottom: 1rem;
    }
    
    /* Gallery card */
    .gallery-card {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #22c55e;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ENHANCED VISUALIZATION FUNCTIONS (19 Chart Types)
# Using st.cache_data to prevent context threading issues
# ============================================================================

@st.cache_data(ttl=300)
def get_trend_data():
    """Generate trend data - cached to avoid threading issues"""
    dates = pd.date_range(start='2024-01-01', end='2024-11-30', freq='W')
    np.random.seed(42)
    return pd.DataFrame({
        'Date': dates,
        'Leads': np.cumsum(np.random.randint(20, 80, len(dates))) + 500,
        'MQLs': np.cumsum(np.random.randint(5, 25, len(dates))) + 150,
        'SQLs': np.cumsum(np.random.randint(2, 12, len(dates))) + 50,
        'Opportunities': np.cumsum(np.random.randint(1, 8, len(dates))) + 20
    })

def create_trend_line_chart(title="Lead Generation Trend"):
    """Multi-line trend chart showing metrics over time"""
    df = get_trend_data()
    
    fig = go.Figure()
    colors = {'Leads': '#3b82f6', 'MQLs': '#10b981', 'SQLs': '#f59e0b', 'Opportunities': '#ef4444'}
    
    for col in ['Leads', 'MQLs', 'SQLs', 'Opportunities']:
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df[col], name=col, mode='lines+markers',
            line=dict(width=3, color=colors[col]), marker=dict(size=6),
            hovertemplate=f'{col}: %{{y:,.0f}}<br>Date: %{{x|%b %d, %Y}}<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text=f"📈 {title}", font=dict(size=16)),
        xaxis_title="Date", yaxis_title="Count",
        hovermode='x unified', legend=dict(orientation='h', yanchor='bottom', y=1.02),
        template='plotly_white', height=400
    )
    return fig


@st.cache_data(ttl=300)
def get_area_data():
    """Generate area chart data - cached"""
    dates = pd.date_range(start='2024-01-01', end='2024-11-30', freq='M')
    np.random.seed(42)
    return pd.DataFrame({
        'Date': dates,
        'Email': np.random.randint(100, 300, len(dates)),
        'Paid Search': np.random.randint(80, 250, len(dates)),
        'Paid Social': np.random.randint(60, 200, len(dates)),
        'Organic': np.random.randint(50, 180, len(dates)),
        'Referral': np.random.randint(30, 100, len(dates))
    })


def create_stacked_area_chart(title="Channel Performance Over Time"):
    """Stacked area chart showing channel contribution"""
    df = get_area_data()
    
    fig = go.Figure()
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
    channels = ['Email', 'Paid Search', 'Paid Social', 'Organic', 'Referral']
    
    for i, channel in enumerate(channels):
        fig.add_trace(go.Scatter(
            x=df['Date'], y=df[channel], name=channel, stackgroup='one',
            fillcolor=colors[i], line=dict(width=0.5, color=colors[i])
        ))
    
    fig.update_layout(
        title=dict(text=f"📊 {title}", font=dict(size=16)),
        hovermode='x unified', template='plotly_white', height=400
    )
    return fig


@st.cache_data(ttl=300)
def get_heatmap_data():
    """Generate heatmap data - cached"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    hours = [f'{h}:00' for h in range(8, 20)]
    np.random.seed(42)
    data = np.random.randint(10, 100, size=(len(days), len(hours)))
    
    for i, day in enumerate(days):
        for j, hour in enumerate(hours):
            if day in ['Tuesday', 'Wednesday', 'Thursday']:
                data[i][j] += 30
            if 9 <= int(hour.split(':')[0]) <= 16:
                data[i][j] += 20
    return days, hours, data


def create_engagement_heatmap(title="Weekly Engagement Heatmap"):
    """Heatmap showing engagement patterns by day/hour"""
    days, hours, data = get_heatmap_data()
    
    fig = go.Figure(data=go.Heatmap(
        z=data, x=hours, y=days, colorscale='Blues',
        hovertemplate='Day: %{y}<br>Time: %{x}<br>Engagement: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=f"🔥 {title}", font=dict(size=16)),
        template='plotly_white', height=400
    )
    return fig


@st.cache_data(ttl=300)
def get_correlation_data():
    """Generate correlation data - cached"""
    channels = ['Email', 'Paid Search', 'Paid Social', 'Content', 'Webinar', 'ABM']
    np.random.seed(42)
    
    corr_matrix = np.eye(len(channels))
    for i in range(len(channels)):
        for j in range(i+1, len(channels)):
            val = np.random.uniform(0.2, 0.9)
            corr_matrix[i][j] = val
            corr_matrix[j][i] = val
    return channels, corr_matrix


def create_channel_correlation_heatmap(title="Channel Correlation Matrix"):
    """Correlation heatmap between different marketing channels"""
    channels, corr_matrix = get_correlation_data()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix, x=channels, y=channels, colorscale='RdYlGn',
        zmin=-1, zmax=1, text=np.round(corr_matrix, 2), texttemplate='%{text}'
    ))
    
    fig.update_layout(
        title=dict(text=f"🔗 {title}", font=dict(size=16)),
        template='plotly_white', height=400
    )
    return fig


def create_customer_journey_sankey(title="Customer Journey Flow"):
    """Sankey diagram showing lead flow through funnel stages"""
    labels = [
        "Website", "Paid Media", "Email", "Events", "Referral",
        "Known Lead", "Anonymous", "Engaged", "MQL", "Dormant",
        "SQL", "Opportunity", "Closed Won"
    ]
    
    source = [0, 0, 1, 1, 2, 2, 3, 4, 5, 5, 5, 6, 6, 7, 7, 8, 8, 10, 10, 11]
    target = [5, 6, 5, 6, 5, 7, 5, 5, 7, 8, 9, 7, 9, 8, 9, 10, 9, 11, 9, 12]
    value = [300, 150, 200, 100, 180, 50, 120, 80, 250, 150, 100, 80, 120, 180, 70, 120, 30, 90, 30, 60]
    
    node_colors = [
        '#3b82f6', '#3b82f6', '#3b82f6', '#3b82f6', '#3b82f6',
        '#10b981', '#94a3b8', '#f59e0b', '#22c55e', '#ef4444',
        '#8b5cf6', '#06b6d4', '#22c55e'
    ]
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5),
                  label=labels, color=node_colors),
        link=dict(source=source, target=target, value=value,
                  color=['rgba(59, 130, 246, 0.4)'] * len(source))
    )])
    
    fig.update_layout(
        title=dict(text=f"🔄 {title}", font=dict(size=16)),
        template='plotly_white', height=500
    )
    return fig


def create_budget_treemap(title="Marketing Budget Allocation"):
    """Treemap showing budget allocation across channels and campaigns"""
    data = {
        'Channel': ['Paid Media', 'Paid Media', 'Paid Media', 'Paid Media',
                   'Content', 'Content', 'Content', 'Events', 'Events',
                   'Email', 'Email', 'ABM', 'ABM'],
        'Campaign': ['LinkedIn Ads', 'Google Search', 'Display', 'Retargeting',
                    'Blog', 'Whitepapers', 'Videos', 'Webinars', 'Conferences',
                    'Nurture', 'Newsletter', 'Target Accounts', '1:1 Outreach'],
        'Budget': [50000, 40000, 25000, 15000, 20000, 15000, 25000, 30000, 45000, 10000, 8000, 35000, 20000],
        'ROI': [2.5, 3.2, 1.8, 2.8, 4.5, 5.2, 3.8, 3.5, 2.2, 6.5, 4.2, 4.8, 5.5]
    }
    
    df = pd.DataFrame(data)
    
    fig = px.treemap(df, path=['Channel', 'Campaign'], values='Budget', color='ROI',
                     color_continuous_scale='RdYlGn', title=f"💰 {title}")
    fig.update_layout(template='plotly_white', height=450)
    return fig


def create_lead_source_sunburst(title="Lead Source Breakdown"):
    """Sunburst chart for hierarchical lead source analysis"""
    data = {
        'Category': ['', '', '', '', '', 'Digital', 'Digital', 'Digital', 'Digital',
                    'Offline', 'Offline', 'Offline', 'Partner', 'Partner',
                    'Paid', 'Paid', 'Paid', 'Organic', 'Organic'],
        'Source': ['Digital', 'Offline', 'Partner', 'Paid', 'Organic',
                  'Website', 'Blog', 'Social', 'Email', 'Events', 'Trade Shows', 'Direct Mail',
                  'Referral', 'Reseller', 'Google Ads', 'LinkedIn', 'Display', 'SEO', 'Content'],
        'Leads': [0, 0, 0, 0, 0, 350, 180, 120, 200, 150, 80, 40, 90, 60, 280, 180, 80, 220, 150]
    }
    
    df = pd.DataFrame(data)
    fig = px.sunburst(df, path=['Category', 'Source'], values='Leads', color='Leads',
                      color_continuous_scale='Blues', title=f"🌞 {title}")
    fig.update_layout(template='plotly_white', height=450)
    return fig


def create_account_radar_chart(title="Account Comparison - Key Metrics"):
    """Radar chart comparing multiple accounts across dimensions"""
    categories = ['Lead Score', 'Intent Score', 'Engagement', 'Content Downloads', 'Web Visits', 'Email Response']
    
    accounts = {
        'Goldman Sachs': [85, 92, 88, 75, 90, 82],
        'JPMorgan': [78, 85, 72, 68, 75, 70],
        'Morgan Stanley': [72, 78, 80, 85, 65, 75]
    }
    
    fig = go.Figure()
    colors = ['#3b82f6', '#10b981', '#f59e0b']
    
    for i, (account, values) in enumerate(accounts.items()):
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]], theta=categories + [categories[0]],
            fill='toself',
            fillcolor=f'rgba({int(colors[i][1:3], 16)}, {int(colors[i][3:5], 16)}, {int(colors[i][5:7], 16)}, 0.2)',
            line=dict(color=colors[i], width=2), name=account
        ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=dict(text=f"🎯 {title}", font=dict(size=16)),
        template='plotly_white', height=450
    )
    return fig


def create_campaign_performance_radar(title="Campaign Performance Comparison"):
    """Radar chart comparing campaign types across KPIs"""
    categories = ['CTR', 'Open Rate', 'Conversion', 'Cost Efficiency', 'Reach', 'Engagement Time']
    
    campaigns = {
        'Email Nurture': [75, 85, 90, 95, 60, 80],
        'Paid Social': [65, 0, 70, 55, 95, 45],
        'Webinar': [80, 70, 85, 75, 40, 95],
        'Content Syndication': [55, 0, 65, 60, 85, 70]
    }
    
    fig = go.Figure()
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']
    
    for i, (campaign, values) in enumerate(campaigns.items()):
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]], theta=categories + [categories[0]],
            fill='toself',
            fillcolor=f'rgba({int(colors[i][1:3], 16)}, {int(colors[i][3:5], 16)}, {int(colors[i][5:7], 16)}, 0.15)',
            line=dict(color=colors[i], width=2), name=campaign
        ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=dict(text=f"📊 {title}", font=dict(size=16)),
        template='plotly_white', height=450
    )
    return fig


def create_pipeline_waterfall(title="Pipeline Value Changes - Q4"):
    """Waterfall chart showing pipeline changes"""
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
        x=["Starting Pipeline", "New Opps", "Upsells", "Lost Deals", "Pushed Out", "Closed Won", "Current Pipeline"],
        textposition="outside",
        text=["$12.4M", "+$3.2M", "+$1.5M", "-$1.8M", "-$0.9M", "-$2.5M", "$11.9M"],
        y=[12400000, 3200000, 1500000, -1800000, -900000, -2500000, 0],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#10b981"}},
        decreasing={"marker": {"color": "#ef4444"}},
        totals={"marker": {"color": "#3b82f6"}}
    ))
    
    fig.update_layout(
        title=dict(text=f"📉 {title}", font=dict(size=16)),
        template='plotly_white', height=400, showlegend=False
    )
    return fig


def create_lead_waterfall(title="Lead Funnel Progression"):
    """Waterfall showing lead progression through funnel"""
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        x=["Total Leads", "Unqualified", "Nurturing", "Sales Rejected", "In Progress", "Converted"],
        text=["+1,245", "-312", "-245", "-89", "-180", "419"],
        y=[1245, -312, -245, -89, -180, 0],
        connector={"line": {"color": "#94a3b8"}},
        increasing={"marker": {"color": "#10b981"}},
        decreasing={"marker": {"color": "#f59e0b"}},
        totals={"marker": {"color": "#22c55e"}}
    ))
    
    fig.update_layout(
        title=dict(text=f"🔄 {title}", font=dict(size=16)),
        template='plotly_white', height=400
    )
    return fig


@st.cache_data(ttl=300)
def get_lead_score_data():
    """Generate lead score data - cached"""
    np.random.seed(42)
    data = []
    segments = ['DCIO', 'Enterprise', 'Mid-Market', 'Small Business']
    means = [75, 65, 55, 45]
    stds = [12, 15, 18, 20]
    counts = [200, 250, 180, 150]
    
    for segment, mean, std, count in zip(segments, means, stds, counts):
        scores = np.clip(np.random.normal(mean, std, count), 0, 100)
        for score in scores:
            data.append({'Segment': segment, 'Lead Score': score})
    return pd.DataFrame(data)


def create_lead_score_distribution(title="Lead Score Distribution by Segment"):
    """Box plot showing lead score distributions"""
    df = get_lead_score_data()
    
    fig = px.box(df, x='Segment', y='Lead Score', color='Segment',
                 color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'],
                 title=f"📊 {title}")
    fig.update_layout(template='plotly_white', showlegend=False, height=400)
    return fig


@st.cache_data(ttl=300)
def get_violin_data():
    """Generate violin plot data - cached"""
    np.random.seed(42)
    data = []
    channels = ['Email', 'Content', 'Webinar', 'Social']
    
    for channel in channels:
        if channel == 'Webinar':
            times = np.random.exponential(45, 150) + 20
        elif channel == 'Content':
            times = np.random.exponential(8, 200) + 2
        elif channel == 'Email':
            times = np.random.exponential(2, 300) + 0.5
        else:
            times = np.random.exponential(3, 180) + 1
        
        for t in times:
            data.append({'Channel': channel, 'Engagement (min)': min(t, 120)})
    return pd.DataFrame(data)
    
    df = pd.DataFrame(data)
    
def create_engagement_violin(title="Engagement Time Distribution by Channel"):
    """Violin plot showing engagement time distributions"""
    df = get_violin_data()
    
    fig = px.violin(df, x='Channel', y='Engagement (min)', color='Channel', box=True, points='outliers',
                    color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'],
                    title=f"🎻 {title}")
    fig.update_layout(template='plotly_white', showlegend=False, height=400)
    return fig


@st.cache_data(ttl=300)
def get_parallel_data():
    """Generate parallel coordinates data - cached"""
    np.random.seed(42)
    n_accounts = 50
    
    intent_scores = np.random.randint(30, 100, n_accounts)
    engagement_scores = np.clip(intent_scores * 0.7 + np.random.randint(-10, 20, n_accounts), 0, 100)
    web_visits = np.clip(intent_scores * 2 + np.random.randint(-20, 50, n_accounts), 0, 250)
    content_downloads = np.clip(engagement_scores * 0.3 + np.random.randint(0, 10, n_accounts), 0, 40)
    lead_scores = np.clip((intent_scores + engagement_scores) / 2 + np.random.randint(-5, 15, n_accounts), 0, 100)
    
    return pd.DataFrame({
        'Intent Score': intent_scores,
        'Engagement': engagement_scores,
        'Web Visits': web_visits,
        'Content DLs': content_downloads,
        'Lead Score': lead_scores
    })


def create_account_parallel_coordinates(title="Account Multi-Dimensional Analysis"):
    """Parallel coordinates plot for account analysis"""
    df = get_parallel_data()
    
    fig = px.parallel_coordinates(df, dimensions=['Intent Score', 'Engagement', 'Web Visits', 'Content DLs', 'Lead Score'],
                                   color='Lead Score', color_continuous_scale='Viridis',
                                   title=f"📈 {title}")
    fig.update_layout(template='plotly_white', height=400)
    return fig


@st.cache_data(ttl=300)
def get_3d_scatter_data():
    """Generate 3D scatter data - cached"""
    np.random.seed(42)
    accounts = ['Goldman Sachs', 'JPMorgan', 'Morgan Stanley', 'BlackRock', 'Vanguard',
               'Fidelity', 'State Street', 'BNY Mellon', 'Northern Trust', 'TIAA',
               'Charles Schwab', 'T. Rowe Price', 'Capital Group', 'Invesco', 'Franklin']
    
    return pd.DataFrame({
        'Account': accounts,
        'Intent Score': np.random.randint(50, 100, len(accounts)),
        'Engagement Score': np.random.randint(40, 95, len(accounts)),
        'Pipeline Value': np.random.randint(500000, 3000000, len(accounts)),
        'Buying Stage': np.random.choice(['Awareness', 'Consideration', 'Decision'], len(accounts))
    })


def create_3d_account_scatter(title="3D Account Prioritization"):
    """3D scatter plot for account visualization"""
    df = get_3d_scatter_data()
    
    color_map = {'Awareness': '#94a3b8', 'Consideration': '#f59e0b', 'Decision': '#10b981'}
    
    fig = px.scatter_3d(df, x='Intent Score', y='Engagement Score', z='Pipeline Value',
                        color='Buying Stage', size='Pipeline Value', hover_name='Account',
                        color_discrete_map=color_map, title=f"🌐 {title}")
    fig.update_layout(template='plotly_white', height=500)
    return fig


@st.cache_data(ttl=300)
def get_animated_funnel_data():
    """Generate animated funnel data - cached"""
    np.random.seed(42)
    months = pd.date_range('2024-01', '2024-11', freq='M').strftime('%b %Y').tolist()
    
    data = []
    for i, month in enumerate(months):
        multiplier = 1 + i * 0.08
        data.append({'Month': month, 'Stage': 'Leads', 'Count': int(800 * multiplier + np.random.randint(-50, 50))})
        data.append({'Month': month, 'Stage': 'MQLs', 'Count': int(250 * multiplier + np.random.randint(-30, 30))})
        data.append({'Month': month, 'Stage': 'SQLs', 'Count': int(80 * multiplier + np.random.randint(-15, 15))})
        data.append({'Month': month, 'Stage': 'Opps', 'Count': int(30 * multiplier + np.random.randint(-8, 8))})
        data.append({'Month': month, 'Stage': 'Won', 'Count': int(12 * multiplier + np.random.randint(-4, 4))})
    return pd.DataFrame(data)


def create_animated_funnel(title="Animated Lead Funnel Over Time"):
    """Animated bar chart showing funnel progression"""
    df = get_animated_funnel_data()
    
    fig = px.bar(df, x='Stage', y='Count', color='Stage', animation_frame='Month',
                 range_y=[0, 1500], color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#22c55e'],
                 title=f"🎬 {title}")
    fig.update_layout(template='plotly_white', showlegend=False, height=450)
    return fig


def create_kpi_gauges(title="Real-Time Marketing KPIs"):
    """Multiple gauge charts for key metrics"""
    fig = make_subplots(rows=2, cols=3, specs=[[{'type': 'indicator'}] * 3, [{'type': 'indicator'}] * 3],
                        subplot_titles=['MQL Rate', 'Win Rate', 'Email CTR', 'Pipeline Coverage', 'CAC Ratio', 'NPS Score'])
    
    metrics = [
        {'value': 34.2, 'target': 30, 'max': 50, 'suffix': '%'},
        {'value': 28, 'target': 35, 'max': 50, 'suffix': '%'},
        {'value': 8.5, 'target': 7, 'max': 15, 'suffix': '%'},
        {'value': 3.2, 'target': 3, 'max': 5, 'suffix': 'x'},
        {'value': 2.8, 'target': 3.5, 'max': 5, 'suffix': 'x'},
        {'value': 72, 'target': 70, 'max': 100, 'suffix': ''}
    ]
    positions = [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)]
    
    for metric, pos in zip(metrics, positions):
        color = '#10b981' if metric['value'] >= metric['target'] else '#ef4444'
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta", value=metric['value'],
            number={'suffix': metric['suffix']},
            delta={'reference': metric['target'], 'relative': False},
            gauge={'axis': {'range': [0, metric['max']]}, 'bar': {'color': color},
                   'steps': [{'range': [0, metric['max'] * 0.5], 'color': '#fee2e2'},
                            {'range': [metric['max'] * 0.5, metric['max'] * 0.75], 'color': '#fef3c7'},
                            {'range': [metric['max'] * 0.75, metric['max']], 'color': '#d1fae5'}],
                   'threshold': {'line': {'color': 'black', 'width': 4}, 'thickness': 0.75, 'value': metric['target']}}
        ), row=pos[0], col=pos[1])
    
    fig.update_layout(title=dict(text=f"📊 {title}", font=dict(size=16)), template='plotly_white', height=450)
    return fig


def create_overlap_analysis(title="Lead Overlap: Marketo vs 6sense vs Salesforce"):
    """Approximated Venn diagram using circles"""
    fig = go.Figure()
    
    circles = [
        {'x': 0.35, 'y': 0.55, 'r': 0.25, 'color': 'rgba(59, 130, 246, 0.4)', 'label': 'Marketo'},
        {'x': 0.65, 'y': 0.55, 'r': 0.25, 'color': 'rgba(16, 185, 129, 0.4)', 'label': '6sense'},
        {'x': 0.5, 'y': 0.3, 'r': 0.25, 'color': 'rgba(245, 158, 11, 0.4)', 'label': 'Salesforce'}
    ]
    
    for circle in circles:
        theta = np.linspace(0, 2*np.pi, 100)
        x = circle['x'] + circle['r'] * np.cos(theta)
        y = circle['y'] + circle['r'] * np.sin(theta)
        fig.add_trace(go.Scatter(x=x, y=y, fill='toself', fillcolor=circle['color'],
                                  line=dict(color=circle['color'].replace('0.4', '1'), width=2),
                                  mode='lines', name=circle['label']))
    
    annotations = [
        {'x': 0.25, 'y': 0.65, 'text': 'Marketo<br><b>4,500</b>'},
        {'x': 0.75, 'y': 0.65, 'text': '6sense<br><b>3,200</b>'},
        {'x': 0.5, 'y': 0.15, 'text': 'Salesforce<br><b>2,800</b>'},
        {'x': 0.5, 'y': 0.55, 'text': 'All 3<br><b>1,200</b>'}
    ]
    
    for ann in annotations:
        fig.add_annotation(x=ann['x'], y=ann['y'], text=ann['text'], showarrow=False, font=dict(size=12))
    
    fig.update_layout(title=dict(text=f"🔗 {title}", font=dict(size=16)), showlegend=True,
                      xaxis=dict(visible=False, range=[0, 1]),
                      yaxis=dict(visible=False, range=[0, 1], scaleanchor='x'),
                      template='plotly_white', height=450)
    return fig


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Anthropic_logo.svg/200px-Anthropic_logo.svg.png", width=120)
    st.markdown("---")
    
    st.markdown("### ⚙️ Configuration")
    
    api_key = st.text_input("Claude API Key", type="password", placeholder="sk-ant-api03-...",
                            help="Get your key from console.anthropic.com")
    
    demo_mode = st.toggle("🎮 Demo Mode (Mock Data)", value=True,
                          help="Use realistic mock data instead of live Databricks")
    
    st.markdown("---")
    
    # Visualization Gallery Toggle
    st.markdown("### 📊 Visualization Gallery")
    if st.button("🎨 Open Chart Gallery", use_container_width=True, type="secondary"):
        st.session_state.show_gallery = not st.session_state.show_gallery
    
    st.markdown("---")
    
    st.markdown("### ✨ New Features")
    st.markdown("""
    <div class="feature-highlight">🎯 Campaign Brief Generator</div>
    <div class="feature-highlight">🚨 Anomaly Detection</div>
    <div class="feature-highlight">📊 19 Chart Types</div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 🎯 Demo Walkthrough")
    if st.button("▶️ Start Guided Demo", use_container_width=True, type="primary"):
        st.session_state.demo_step = 0
        st.session_state.messages = []
        st.session_state.query_count = 0
        st.session_state.tools_used = set()
        st.session_state.total_response_time = 0
        st.session_state.show_gallery = False
    
    demo_queries = [
        ("1️⃣ Lead Overview", "How many leads did we generate last month? Break down by segment."),
        ("2️⃣ Intent Signals", "Which accounts have the highest 6sense intent scores and are ready to buy?"),
        ("3️⃣ Campaign Brief", "Generate a campaign brief for a nurture campaign targeting DCIO segment to generate MQLs."),
        ("4️⃣ Anomaly Detection", "Detect any marketing anomalies in the past 30 days"),
        ("5️⃣ Account Deep Dive", "Give me a 360-degree view of Goldman Sachs"),
        ("6️⃣ Journey Analysis", "Show me the customer journey flow from lead to closed won"),
    ]
    
    st.caption("Click to run each demo step:")
    for label, query in demo_queries:
        if st.button(label, key=f"demo_{label}", use_container_width=True):
            st.session_state.pending_question = query
            st.session_state.show_gallery = False
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("### 📦 Connected Data Sources")
    sources = [("Marketo", "marketo", "Leads & Email"), ("Adobe Analytics", "adobe", "Web Traffic"),
               ("6sense", "6sense", "Intent & ABM"), ("Salesforce", "salesforce", "Pipeline"),
               ("PathFactory", "pathfactory", "Content"), ("AEM", "adobe", "Forms")]
    
    for name, css_class, desc in sources:
        st.markdown(f'<span class="source-pill source-{css_class}">{name}</span> <small style="color:#666">{desc}</small>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🛠️ Available Tools")
    st.caption(f"**18 MCP Tools** + **19 Chart Types**")

# ============================================================================
# MCP TOOLS DEFINITION
# ============================================================================
TOOLS = [
    {"name": "get_lead_metrics", "description": "Get lead counts, MQL counts, and lead scores from Marketo.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business"]},
                      "date_range_days": {"type": "integer", "default": 90}}, "required": []}},
    {"name": "get_conversion_funnel", "description": "Get funnel conversion rates from lead to MQL to opportunity.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business"]}}, "required": []}},
    {"name": "get_funnel_summary", "description": "Get comprehensive funnel summary with leads, web sessions, intent scores, content engagement, and pipeline.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}, "top_n": {"type": "integer", "default": 10}}, "required": []}},
    {"name": "get_campaign_performance", "description": "Get campaign-level performance metrics.",
     "input_schema": {"type": "object", "properties": {"channel": {"type": "string", "enum": ["Email", "Content", "Paid Social", "Paid Search", "ABM"]}}, "required": []}},
    {"name": "get_paid_media_performance", "description": "Get paid media campaign metrics - LinkedIn vs Google comparison.",
     "input_schema": {"type": "object", "properties": {"platform": {"type": "string", "enum": ["LinkedIn", "Google"]}}, "required": []}},
    {"name": "get_email_engagement", "description": "Get email campaign engagement metrics - open rates, click rates.",
     "input_schema": {"type": "object", "properties": {"date_range_days": {"type": "integer", "default": 30}}, "required": []}},
    {"name": "get_web_engagement", "description": "Get Adobe Analytics web engagement data.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}}, "required": []}},
    {"name": "get_content_engagement", "description": "Get PathFactory content engagement metrics.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}}, "required": []}},
    {"name": "get_intent_signals", "description": "Get 6sense intent data showing which accounts are researching relevant topics.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}, "buying_stage": {"type": "string", "enum": ["Awareness", "Consideration", "Decision"]}}, "required": []}},
    {"name": "get_account_engagement_scores", "description": "Get 6sense account engagement scores and buying stages.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}, "buying_stage": {"type": "string"}}, "required": []}},
    {"name": "get_form_performance", "description": "Get AEM form performance - completion rates, abandonment.",
     "input_schema": {"type": "object", "properties": {"form_id": {"type": "string"}}, "required": []}},
    {"name": "get_pipeline_metrics", "description": "Get Salesforce pipeline and opportunity data.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}}, "required": []}},
    {"name": "get_converted_accounts", "description": "Get accounts that converted with their marketing journey.",
     "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}}, "required": []}},
    {"name": "get_channel_attribution", "description": "Get multi-touch attribution showing channel influence.",
     "input_schema": {"type": "object", "properties": {"attribution_model": {"type": "string", "enum": ["first_touch", "last_touch", "linear"]}}, "required": []}},
    {"name": "get_account_360_view", "description": "Get complete 360-degree view of a specific account.",
     "input_schema": {"type": "object", "properties": {"company_name": {"type": "string"}}, "required": []}},
    {"name": "get_page_performance", "description": "Get page-level performance metrics.",
     "input_schema": {"type": "object", "properties": {"page_type": {"type": "string"}}, "required": []}},
    {"name": "generate_campaign_brief", "description": "Generate comprehensive campaign brief with data-driven recommendations.",
     "input_schema": {"type": "object", "properties": {"campaign_type": {"type": "string", "enum": ["email", "nurture", "webinar", "content_syndication"]},
                      "target_segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business"]},
                      "campaign_objective": {"type": "string"}}, "required": ["campaign_type", "target_segment", "campaign_objective"]}},
    {"name": "detect_marketing_anomalies", "description": "Detect marketing anomalies including performance drops, intent spikes, and engagement gaps.",
     "input_schema": {"type": "object", "properties": {"lookback_days": {"type": "integer", "default": 30},
                      "severity_filter": {"type": "string", "enum": ["all", "high", "medium"]}}, "required": []}}
]

# ============================================================================
# MOCK DATA FUNCTION
# ============================================================================
def get_mock_data(tool_name: str, tool_input: dict) -> dict:
    """Generate realistic mock data for demo mode"""
    
    mock_responses = {
        "get_lead_metrics": {
            "data": [
                {"segment": "DCIO", "lead_source": "Website", "total_leads": 245, "mqls": 89, "avg_lead_score": 72.5, "mql_rate_pct": 36.3},
                {"segment": "DCIO", "lead_source": "Webinar", "total_leads": 156, "mqls": 78, "avg_lead_score": 78.2, "mql_rate_pct": 50.0},
                {"segment": "Enterprise", "lead_source": "Content Download", "total_leads": 312, "mqls": 94, "avg_lead_score": 65.8, "mql_rate_pct": 30.1},
                {"segment": "Enterprise", "lead_source": "Paid Media", "total_leads": 189, "mqls": 45, "avg_lead_score": 58.3, "mql_rate_pct": 23.8},
                {"segment": "Mid-Market", "lead_source": "Event", "total_leads": 98, "mqls": 32, "avg_lead_score": 61.2, "mql_rate_pct": 32.7},
            ], "row_count": 5
        },
        "get_conversion_funnel": {
            "data": [
                {"segment": "DCIO", "total_leads": 401, "mqls": 167, "opportunities": 45, "closed_won": 18, "lead_to_mql_rate": 41.6, "mql_to_opp_rate": 26.9, "opp_to_won_rate": 40.0},
                {"segment": "Enterprise", "total_leads": 501, "mqls": 139, "opportunities": 28, "closed_won": 8, "lead_to_mql_rate": 27.7, "mql_to_opp_rate": 20.1, "opp_to_won_rate": 28.6},
                {"segment": "Mid-Market", "total_leads": 198, "mqls": 52, "opportunities": 12, "closed_won": 4, "lead_to_mql_rate": 26.3, "mql_to_opp_rate": 23.1, "opp_to_won_rate": 33.3},
            ], "row_count": 3
        },
        "get_funnel_summary": {
            "data": [
                {"company_name": "Goldman Sachs", "segment": "DCIO", "total_leads": 8, "mqls": 5, "avg_lead_score": 82.3, "web_sessions": 156, "avg_intent_score": 87.5, "buying_stage": "Decision", "content_engagements": 45, "total_pipeline_value": 2500000},
                {"company_name": "JPMorgan Chase", "segment": "DCIO", "total_leads": 6, "mqls": 4, "avg_lead_score": 79.1, "web_sessions": 134, "avg_intent_score": 82.3, "buying_stage": "Decision", "content_engagements": 38, "total_pipeline_value": 1800000},
                {"company_name": "Morgan Stanley", "segment": "DCIO", "total_leads": 5, "mqls": 3, "avg_lead_score": 75.8, "web_sessions": 98, "avg_intent_score": 78.9, "buying_stage": "Consideration", "content_engagements": 28, "total_pipeline_value": 1500000},
            ], "row_count": 3
        },
        "get_paid_media_performance": {
            "data": [
                {"platform": "LinkedIn", "campaign_name": "LinkedIn DCIO Targeting", "total_impressions": 856000, "total_clicks": 9580, "total_spend": 48500.00, "total_conversions": 425, "avg_cpc": 5.06, "avg_ctr": 1.12, "cost_per_conversion": 114.12},
                {"platform": "Google", "campaign_name": "Google Search - Retirement Plans", "total_impressions": 1650000, "total_clicks": 52800, "total_spend": 38200.00, "total_conversions": 1890, "avg_cpc": 0.72, "avg_ctr": 3.20, "cost_per_conversion": 20.21},
            ], "row_count": 2
        },
        "get_intent_signals": {
            "data": [
                {"company_name": "Goldman Sachs", "segment": "DCIO", "intent_keyword": "dcio providers", "max_intent_score": 92, "buying_stage": "Decision", "total_searches": 45, "signal_count": 12},
                {"company_name": "Fidelity Investments", "segment": "DCIO", "intent_keyword": "stable value funds", "max_intent_score": 88, "buying_stage": "Decision", "total_searches": 38, "signal_count": 9},
                {"company_name": "JPMorgan Chase", "segment": "DCIO", "intent_keyword": "retirement plan providers", "max_intent_score": 85, "buying_stage": "Consideration", "total_searches": 32, "signal_count": 8},
            ], "row_count": 3
        },
        "get_account_360_view": {
            "data": [{
                "company_name": tool_input.get("company_name", "Goldman Sachs"),
                "segment": "DCIO", "industry": "Financial Services", "employee_count": 45000,
                "lead_count": 8, "mql_count": 5, "avg_lead_score": 82.3, "web_sessions": 156,
                "max_intent_score": 92, "buying_stage": "Decision", "content_engagements": 45,
                "total_pipeline": 2500000, "closed_won_value": 1200000, "opportunity_count": 3
            }], "row_count": 1
        },
        "get_channel_attribution": {
            "data": [
                {"channel": "Email", "accounts_touched": 245, "accounts_converted": 18, "attributed_revenue": 4500000, "conversion_rate": 7.3},
                {"channel": "Paid Search", "accounts_touched": 312, "accounts_converted": 12, "attributed_revenue": 2800000, "conversion_rate": 3.8},
                {"channel": "Organic", "accounts_touched": 456, "accounts_converted": 15, "attributed_revenue": 3200000, "conversion_rate": 3.3},
                {"channel": "Paid Social", "accounts_touched": 189, "accounts_converted": 8, "attributed_revenue": 1800000, "conversion_rate": 4.2},
                {"channel": "Content", "accounts_touched": 278, "accounts_converted": 10, "attributed_revenue": 2100000, "conversion_rate": 3.6},
            ], "row_count": 5
        },
        "generate_campaign_brief": {
            "brief_metadata": {"generated_at": datetime.now().isoformat(), "campaign_type": tool_input.get("campaign_type", "nurture"),
                              "target_segment": tool_input.get("target_segment", "DCIO")},
            "historical_performance": [{"avg_ctr": 8.5, "avg_open_rate": 32.4, "avg_cvr": 24.6, "avg_cpl": 95.50}],
            "intent_signals": [
                {"company_name": "Goldman Sachs", "avg_intent_score": 92.0, "signal_count": 12, "top_keyword": "dcio providers"},
                {"company_name": "Fidelity Investments", "avg_intent_score": 88.0, "signal_count": 9, "top_keyword": "stable value funds"},
                {"company_name": "JPMorgan Chase", "avg_intent_score": 85.0, "signal_count": 8, "top_keyword": "retirement plans"},
            ],
            "content_performance": [
                {"asset_title": "Stable Value Funds Guide 2024", "asset_type": "Whitepaper", "conversion_rate": 28.5},
                {"asset_title": "DCIO Provider Comparison Report", "asset_type": "eBook", "conversion_rate": 27.3},
            ],
            "data": {"summary": {"high_intent_accounts": 47, "recommended_budget": 25000, "target_mqls": 85}},
            "row_count": 1
        },
        "detect_marketing_anomalies": {
            "anomaly_summary": {"scan_date": datetime.now().isoformat(), "total_anomalies": 12, "high_priority_count": 5},
            "email_performance_drops": [
                {"campaign_name": "Q4 Enterprise Nurture", "recent_ctr": 5.2, "baseline_ctr": 8.5, "pct_change": -38.8, "severity": "high"},
            ],
            "intent_spikes": [
                {"company_name": "Vanguard", "recent_score": 89.0, "baseline_score": 62.0, "pct_change": 43.5, "severity": "high"},
                {"company_name": "BlackRock", "recent_score": 85.0, "baseline_score": 58.0, "pct_change": 46.6, "severity": "high"},
            ],
            "engagement_gaps": [
                {"company_name": "Fidelity Investments", "avg_intent_score": 88.0, "days_since_contact": 72, "severity": "high"},
            ],
            "data": [
                {"type": "Performance Drops", "count": 2, "severity": "high"},
                {"type": "Intent Spikes", "count": 3, "severity": "opportunity"},
                {"type": "Engagement Gaps", "count": 3, "severity": "high"},
            ], "row_count": 8
        }
    }
    
    return mock_responses.get(tool_name, {"data": [], "row_count": 0})

# ============================================================================
# ENHANCED VISUALIZATION FUNCTION
# ============================================================================
def create_enhanced_visualization(tool_name: str, data: any) -> list:
    """Create multiple visualization types based on tool and data"""
    figures = []
    
    try:
        # Campaign Brief - Multiple Charts
        if tool_name == "generate_campaign_brief" and isinstance(data, dict):
            if "intent_signals" in data and data["intent_signals"]:
                intent_df = pd.DataFrame(data["intent_signals"])
                fig1 = px.bar(intent_df.sort_values("avg_intent_score", ascending=True),
                             x="avg_intent_score", y="company_name", orientation="h",
                             title="🎯 High-Intent Target Accounts", color="avg_intent_score", color_continuous_scale="Greens")
                figures.append(("Target Accounts", fig1))
            
            # Add Radar Chart for Campaign
            figures.append(("Campaign KPIs", create_campaign_performance_radar("Expected Performance vs Benchmarks")))
            figures.append(("Budget Allocation", create_budget_treemap("Recommended Budget Allocation")))
            return figures
        
        # Anomaly Detection - Multiple Charts
        elif tool_name == "detect_marketing_anomalies" and isinstance(data, dict):
            if "data" in data:
                summary_df = pd.DataFrame(data["data"])
                fig1 = px.pie(summary_df, values="count", names="type", title="🚨 Anomaly Distribution", hole=0.4)
                figures.append(("Anomaly Summary", fig1))
            
            if "intent_spikes" in data:
                spikes_df = pd.DataFrame(data["intent_spikes"])
                fig2 = px.bar(spikes_df, x="company_name", y=["baseline_score", "recent_score"],
                             title="📈 Intent Score Spikes (Opportunities!)", barmode="group")
                figures.append(("Intent Spikes", fig2))
            
            figures.append(("Engagement Heatmap", create_engagement_heatmap("Best Times to Reach Out")))
            return figures
        
        # Account 360 View - Multiple Charts
        elif tool_name == "get_account_360_view" and isinstance(data, dict):
            if "data" in data and data["data"]:
                row = data["data"][0] if isinstance(data["data"], list) else data["data"]
                
                # Gauges
                fig1 = make_subplots(rows=1, cols=3, specs=[[{'type': 'indicator'}]*3],
                                    subplot_titles=['Lead Score', 'Intent Score', 'Pipeline ($M)'])
                fig1.add_trace(go.Indicator(mode="gauge+number", value=row.get('avg_lead_score', 0),
                              gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#3b82f6"}}), row=1, col=1)
                fig1.add_trace(go.Indicator(mode="gauge+number", value=row.get('max_intent_score', 0),
                              gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#10b981"}}), row=1, col=2)
                fig1.add_trace(go.Indicator(mode="gauge+number", value=row.get('total_pipeline', 0)/1000000,
                              gauge={'axis': {'range': [0, 5]}, 'bar': {'color': "#f59e0b"}}, number={'suffix': 'M'}), row=1, col=3)
                fig1.update_layout(title=f"🎯 {row.get('company_name', 'Account')} - Key Metrics", height=300)
                figures.append(("Key Metrics", fig1))
                
                figures.append(("Account Comparison", create_account_radar_chart(f"{row.get('company_name', 'Account')} vs Peers")))
                figures.append(("Customer Journey", create_customer_journey_sankey("Engagement Journey")))
            return figures
        
        # Channel Attribution - Multiple Charts
        elif tool_name == "get_channel_attribution":
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
                fig1 = px.pie(df, values="attributed_revenue", names="channel", title="💰 Revenue by Channel", hole=0.4)
                figures.append(("Revenue Pie", fig1))
                
                fig2 = px.bar(df, x="channel", y=["accounts_touched", "accounts_converted"],
                             title="📊 Accounts Touched vs Converted", barmode="group")
                figures.append(("Conversion", fig2))
                
                figures.append(("Channel Correlation", create_channel_correlation_heatmap("Channel Synergies")))
            return figures
        
        # Intent Signals - Multiple Charts
        elif tool_name == "get_intent_signals":
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
                fig1 = px.scatter(df, x="max_intent_score", y="total_searches", size="signal_count",
                                 color="buying_stage", hover_name="company_name",
                                 title="🎯 Intent Signals: Score vs Search Volume")
                figures.append(("Intent Bubble", fig1))
                
                figures.append(("Account Radar", create_account_radar_chart("Top Accounts Comparison")))
                figures.append(("3D View", create_3d_account_scatter("Account Prioritization Matrix")))
            return figures
        
        # Funnel/Conversion - Multiple Charts
        elif tool_name == "get_conversion_funnel":
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
                fig1 = go.Figure()
                for _, row in df.iterrows():
                    fig1.add_trace(go.Funnel(name=row['segment'],
                                             y=['Leads', 'MQLs', 'Opportunities', 'Closed Won'],
                                             x=[row['total_leads'], row['mqls'], row['opportunities'], row['closed_won']]))
                fig1.update_layout(title="🔄 Conversion Funnel by Segment")
                figures.append(("Funnel", fig1))
                
                figures.append(("Journey Flow", create_customer_journey_sankey("Lead to Close Journey")))
                figures.append(("Waterfall", create_lead_waterfall("Funnel Drop-off Analysis")))
            return figures
        
        # Lead Metrics - Multiple Charts
        elif tool_name == "get_lead_metrics":
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
                fig1 = px.bar(df, x="segment", y="total_leads", color="lead_source",
                             title="📊 Lead Generation by Segment", barmode="stack")
                figures.append(("Lead Volume", fig1))
                
                figures.append(("Trend", create_trend_line_chart("Lead Generation Trend")))
                figures.append(("Distribution", create_lead_score_distribution("Lead Quality by Segment")))
                figures.append(("Source Sunburst", create_lead_source_sunburst("Lead Source Breakdown")))
            return figures
        
        # Paid Media - Multiple Charts
        elif tool_name == "get_paid_media_performance":
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(name='Spend ($)', x=df['platform'], y=df['total_spend'], marker_color='#fc8181'))
                fig1.add_trace(go.Bar(name='Conversions', x=df['platform'], y=df['total_conversions'], marker_color='#48bb78'))
                fig1.update_layout(title="💰 Spend vs Conversions", barmode='group')
                figures.append(("Spend vs Conversions", fig1))
                
                figures.append(("Channel Mix", create_stacked_area_chart("Channel Performance Over Time")))
                figures.append(("Budget Treemap", create_budget_treemap("Budget Allocation")))
            return figures
        
        # Pipeline Metrics
        elif tool_name == "get_pipeline_metrics":
            figures.append(("Pipeline Waterfall", create_pipeline_waterfall("Pipeline Changes This Quarter")))
            figures.append(("KPI Gauges", create_kpi_gauges("Pipeline Health Dashboard")))
            return figures
        
        # Default visualization for other tools
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list) and data["data"]:
            df = pd.DataFrame(data["data"])
            if len(df.columns) >= 2:
                num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                cat_cols = df.select_dtypes(include=['object']).columns.tolist()
                
                if num_cols and cat_cols:
                    fig = px.bar(df, x=cat_cols[0], y=num_cols[0], color=cat_cols[0] if len(cat_cols) > 0 else None,
                                title=f"📊 {tool_name.replace('_', ' ').title()}")
                    figures.append(("Bar Chart", fig))
        
        return figures
        
    except Exception as e:
        st.warning(f"Visualization error: {e}")
        return []

# ============================================================================
# MAIN HEADER
# ============================================================================
st.markdown("""
<div class="main-header">
    <h1>🎯 Marketing Analytics Agent</h1>
    <p>Ask questions in plain English • Get insights from Marketo, Adobe Analytics, 6sense, Salesforce & more</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# VISUALIZATION GALLERY MODE
# ============================================================================
if st.session_state.show_gallery:
    st.markdown("## 📊 Visualization Gallery - 19 Chart Types")
    st.markdown("*Click any chart category to explore. These are all available in the agent's responses.*")
    
    gallery_tab1, gallery_tab2, gallery_tab3, gallery_tab4, gallery_tab5 = st.tabs([
        "📈 Trends & Time", "🔥 Patterns & Flow", "🌳 Hierarchical", "🎯 Comparison", "📊 Distribution & KPIs"
    ])
    
    with gallery_tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_trend_line_chart(), use_container_width=True)
        with col2:
            st.plotly_chart(create_stacked_area_chart(), use_container_width=True)
        st.plotly_chart(create_animated_funnel(), use_container_width=True)
    
    with gallery_tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_engagement_heatmap(), use_container_width=True)
        with col2:
            st.plotly_chart(create_channel_correlation_heatmap(), use_container_width=True)
        st.plotly_chart(create_customer_journey_sankey(), use_container_width=True)
    
    with gallery_tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_budget_treemap(), use_container_width=True)
        with col2:
            st.plotly_chart(create_lead_source_sunburst(), use_container_width=True)
    
    with gallery_tab4:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_account_radar_chart(), use_container_width=True)
        with col2:
            st.plotly_chart(create_campaign_performance_radar(), use_container_width=True)
        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(create_account_parallel_coordinates(), use_container_width=True)
        with col4:
            st.plotly_chart(create_3d_account_scatter(), use_container_width=True)
    
    with gallery_tab5:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(create_pipeline_waterfall(), use_container_width=True)
            st.plotly_chart(create_lead_score_distribution(), use_container_width=True)
        with col2:
            st.plotly_chart(create_lead_waterfall(), use_container_width=True)
            st.plotly_chart(create_engagement_violin(), use_container_width=True)
        st.plotly_chart(create_kpi_gauges(), use_container_width=True)
        st.plotly_chart(create_overlap_analysis(), use_container_width=True)
    
    st.markdown("---")
    if st.button("← Back to Chat", type="primary"):
        st.session_state.show_gallery = False
        st.rerun()

else:
    # ============================================================================
    # QUICK METRICS ROW
    # ============================================================================
    if demo_mode:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<div class="metric-card"><h3>Total Leads (90d)</h3><div class="value">1,245</div><small style="color:#48bb78">↑ 12% vs prior</small></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-card"><h3>MQL Rate</h3><div class="value">34.2%</div><small style="color:#48bb78">↑ 3.5% vs prior</small></div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-card"><h3>Pipeline Value</h3><div class="value">$12.4M</div><small style="color:#48bb78">↑ 18% vs prior</small></div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div class="metric-card"><h3>Closed Won (QTD)</h3><div class="value">$8.5M</div><small style="color:#48bb78">↑ 24% vs prior</small></div>', unsafe_allow_html=True)

    # ============================================================================
    # NEW FEATURES SECTION
    # ============================================================================
    st.markdown("### ✨ New Capabilities")
    
    feat_col1, feat_col2, feat_col3 = st.columns(3)
    
    with feat_col1:
        st.markdown('<div class="brief-card"><h4>🎯 Campaign Brief Generator</h4><p>Generate data-driven briefs analyzing historical performance, intent signals, and content engagement.</p></div>', unsafe_allow_html=True)
        if st.button("🎯 Try Campaign Brief", key="try_brief", use_container_width=True):
            st.session_state.pending_question = "Generate a campaign brief for a nurture campaign targeting DCIO segment to generate MQLs."
            st.rerun()
    
    with feat_col2:
        st.markdown('<div class="anomaly-card"><h4>🚨 Anomaly Detection</h4><p>Detect performance drops, intent spikes, and engagement gaps automatically.</p></div>', unsafe_allow_html=True)
        if st.button("🚨 Run Anomaly Scan", key="try_anomaly", use_container_width=True):
            st.session_state.pending_question = "Detect any marketing anomalies in the past 30 days."
            st.rerun()
    
    with feat_col3:
        st.markdown('<div class="gallery-card"><h4>📊 19 Chart Types</h4><p>Line, Area, Heatmap, Sankey, Treemap, Sunburst, Radar, Waterfall, 3D, Animated & more!</p></div>', unsafe_allow_html=True)
        if st.button("📊 View Gallery", key="view_gallery", use_container_width=True):
            st.session_state.show_gallery = True
            st.rerun()

    st.markdown("---")

    # ============================================================================
    # SAMPLE QUESTIONS
    # ============================================================================
    st.markdown("### 💡 Try These Questions")
    
    sample_questions = {
        "🎯 Lead Generation": ["How many leads did we generate last month? Break it down by segment.", "What's our MQL conversion rate by lead source?"],
        "📊 Campaign Performance": ["Which campaigns have the highest ROI?", "Compare LinkedIn vs Google Ads performance - which gives better ROI?"],
        "🔥 Intent & ABM": ["Which accounts have the highest 6sense engagement scores and are ready to buy?", "What intent signals are we seeing from DCIO segment accounts?"],
        "💰 Pipeline & Revenue": ["Show me accounts that converted and what drove their conversion.", "What's our average deal size for DCIO segment?"],
        "🌟 Comprehensive": ["Give me a 360-degree view of Goldman Sachs.", "Summarize our B2B marketing performance across all channels."]
    }
    
    cols = st.columns(3)
    for i, (category, questions) in enumerate(sample_questions.items()):
        with cols[i % 3]:
            with st.expander(category, expanded=False):
                for q in questions:
                    if st.button(q, key=f"sample_{hash(q)}", use_container_width=True):
                        st.session_state.pending_question = q
                        st.rerun()

    st.markdown("---")

    # ============================================================================
    # CHAT INTERFACE
    # ============================================================================
    st.markdown("### 💬 Ask Your Question")
    
    input_col1, input_col2 = st.columns([6, 1])
    with input_col1:
        if st.session_state.pending_question:
            user_input = st.session_state.pending_question
            st.session_state.pending_question = None
        else:
            user_input = st.text_input("Your question", placeholder="Ask about leads, campaigns, anomalies, customer journeys...",
                                       label_visibility="collapsed", key="main_input")
    with input_col2:
        send_clicked = st.button("🚀 Ask", use_container_width=True, type="primary")
    
    action_col1, action_col2, action_col3 = st.columns([1, 1, 4])
    with action_col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.query_count = 0
            st.session_state.tools_used = set()
            st.session_state.total_response_time = 0
            st.rerun()
    with action_col2:
        if st.button("📥 Export", use_container_width=True) and st.session_state.messages:
            export_text = f"# Marketing Analytics - {datetime.now().strftime('%Y-%m-%d')}\n\n"
            for msg in st.session_state.messages:
                role = "**You:**" if msg["role"] == "user" else "**Agent:**"
                export_text += f"{role}\n{msg['content']}\n\n---\n\n"
            st.download_button("💾 Download", export_text, file_name=f"analytics_{datetime.now().strftime('%Y%m%d_%H%M')}.md")
    with action_col3:
        if st.session_state.query_count > 0:
            avg_time = st.session_state.total_response_time / st.session_state.query_count
            st.caption(f"📊 Queries: {st.session_state.query_count} | 🔧 Tools: {len(st.session_state.tools_used)} | ⏱️ Avg: {avg_time:.1f}s")

    st.markdown("---")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🧑‍💼" if message["role"] == "user" else "🤖"):
            st.markdown(message["content"])
            if "figures" in message and message["figures"]:
                if len(message["figures"]) > 1:
                    tabs = st.tabs([name for name, _ in message["figures"]])
                    for tab, (name, fig) in zip(tabs, message["figures"]):
                        with tab:
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.plotly_chart(message["figures"][0][1], use_container_width=True)
            if "dataframe" in message and message["dataframe"] is not None:
                with st.expander("📋 View Raw Data"):
                    st.dataframe(message["dataframe"], use_container_width=True)
            if "tools_called" in message and message["tools_called"]:
                st.caption(f"🔧 Tools: {' → '.join([f'`{t}`' for t in message['tools_called']])}")

    # Process input
    if (user_input and send_clicked) or (user_input and user_input != st.session_state.get("last_input", "")):
        if user_input != st.session_state.get("last_input", ""):
            st.session_state.last_input = user_input
            st.session_state.query_count += 1
            
            if not api_key:
                st.warning("⚠️ Please enter your Claude API key in the sidebar.")
                st.stop()
            
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            with st.chat_message("user", avatar="🧑‍💼"):
                st.markdown(user_input)
            
            with st.chat_message("assistant", avatar="🤖"):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    
                    system_prompt = """You are a Marketing Analytics Agent with access to tools that query marketing data across Marketo, Adobe Analytics, 6sense, PathFactory, AEM, Salesforce, and Paid Media platforms.

You have powerful capabilities including Campaign Brief Generator and Anomaly Detection. When answering:
1. Select appropriate tools for the question
2. Provide actionable insights with specific numbers
3. Be concise but thorough
4. Highlight important findings first

For journey/flow questions, the system will show Sankey diagrams.
For comparisons, radar charts will be displayed.
For hierarchical data, treemaps and sunbursts are available.
For trends, line and area charts are used.
For KPIs, gauges and waterfalls are shown."""

                    messages = [{"role": "user", "content": user_input}]
                    
                    start_time = time.time()
                    with st.status("🧠 Analyzing...", expanded=True) as status:
                        response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=4096,
                                                         system=system_prompt, tools=TOOLS, messages=messages)
                        
                        iteration = 0
                        last_tool_data = None
                        last_tool_name = None
                        tools_called = []
                        
                        while response.stop_reason == "tool_use" and iteration < 8:
                            iteration += 1
                            tool_uses = [b for b in response.content if b.type == "tool_use"]
                            tool_results = []
                            
                            for tool_use in tool_uses:
                                status.update(label=f"📊 Using {tool_use.name}...")
                                st.write(f"📊 **{tool_use.name}**")
                                tools_called.append(tool_use.name)
                                st.session_state.tools_used.add(tool_use.name)
                                
                                result = get_mock_data(tool_use.name, tool_use.input)
                                last_tool_name = tool_use.name
                                last_tool_data = result
                                
                                tool_results.append({"type": "tool_result", "tool_use_id": tool_use.id,
                                                    "content": json.dumps(result, default=str)})
                            
                            messages.append({"role": "assistant", "content": response.content})
                            messages.append({"role": "user", "content": tool_results})
                            
                            response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=4096,
                                                             system=system_prompt, tools=TOOLS, messages=messages)
                        
                        status.update(label="✅ Complete!", state="complete")
                    
                    response_time = time.time() - start_time
                    st.session_state.total_response_time += response_time
                    
                    final_answer = "".join([b.text for b in response.content if hasattr(b, "text")])
                    if not final_answer:
                        final_answer = "I couldn't generate a response. Please try rephrasing."
                    
                    st.markdown(final_answer)
                    
                    if tools_called:
                        st.caption(f"🔧 Tools: {' → '.join([f'`{t}`' for t in tools_called])} | ⏱️ {response_time:.1f}s")
                    
                    # Create enhanced visualizations
                    figures = []
                    df = None
                    if last_tool_data and last_tool_name:
                        figures = create_enhanced_visualization(last_tool_name, last_tool_data)
                        
                        if isinstance(last_tool_data, dict) and "data" in last_tool_data:
                            if isinstance(last_tool_data["data"], list):
                                df = pd.DataFrame(last_tool_data["data"])
                        
                        if figures:
                            if len(figures) > 1:
                                tabs = st.tabs([name for name, _ in figures])
                                for tab, (name, fig) in zip(tabs, figures):
                                    with tab:
                                        st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.plotly_chart(figures[0][1], use_container_width=True)
                        
                        if df is not None and len(df) > 0:
                            with st.expander("📋 View Raw Data"):
                                st.dataframe(df, use_container_width=True)
                    
                    st.session_state.messages.append({
                        "role": "assistant", "content": final_answer,
                        "figures": figures, "dataframe": df, "tools_called": tools_called
                    })
                    
                except anthropic.AuthenticationError:
                    st.error("❌ Invalid API key.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    # ============================================================================
    # FOOTER
    # ============================================================================
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 🏗️ Architecture\n- **MCP Protocol** for tool orchestration\n- **Claude AI** for natural language\n- **Databricks** for data processing\n- **18 MCP Tools** + **19 Chart Types**")
    with col2:
        st.markdown("#### 📊 Data Sources\n- Marketo • Adobe Analytics\n- 6sense • Salesforce\n- PathFactory • AEM Forms\n- LinkedIn & Google Ads")
    with col3:
        st.markdown("#### 🚀 Business Value\n- **Campaign planning: 6hrs → 30sec**\n- Proactive anomaly detection\n- Cross-platform insights\n- Self-service analytics")
    
    st.markdown('<div style="text-align:center;margin-top:2rem;padding:1rem;background:#f8fafc;border-radius:8px;"><small>Marketing Analytics Agent v3.1 | Built with Claude AI + MCP | MetLife Marketing Technology | December 2024</small></div>', unsafe_allow_html=True)