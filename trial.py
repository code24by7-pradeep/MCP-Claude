"""
Marketing Analytics Agent v9 - HACKATHON DEMO VERSION
======================================================
Run: streamlit run marketing_agent_v9_complete.py
"""

import streamlit as st
st.set_page_config(page_title="Marketing Analytics Agent", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Any, Dict, List, Tuple
import time

try:
    import anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

# Session State
for key, val in {"messages": [], "api_messages": [], "query_count": 0, "pending_question": None, 
                 "show_followups": [], "last_tool_used": None, "last_tool_data": None, 
                 "conversation_context": ""}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# CSS
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #0f1117 0%, #1a1f2e 100%); }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1f2e 0%, #252d3d 100%); border-right: 1px solid #3b4a6b; }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    .main-header { background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 50%, #1e3a5f 100%); padding: 1.5rem 2rem; border-radius: 16px; margin-bottom: 1.5rem; border: 1px solid #3b4a6b; }
    .main-header h1 { margin: 0; font-size: 2.2rem; font-weight: 700; color: white; }
    .main-header p { margin: 0.5rem 0 0 0; color: #94a3b8; }
    .metric-card { background: linear-gradient(135deg, #1e2432 0%, #252d3d 100%); padding: 1.2rem; border-radius: 12px; border-left: 4px solid #3b82f6; margin-bottom: 0.5rem; }
    .metric-card h4 { color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase; }
    .metric-card .val { color: white; font-size: 1.6rem; font-weight: 700; margin: 0.3rem 0; }
    .metric-card .change { font-size: 0.85rem; }
    .metric-card .change.positive { color: #10b981; }
    .metric-card .change.negative { color: #ef4444; }
    .stTextInput input { background-color: #1e2432 !important; color: white !important; border: 1px solid #3b4a6b !important; border-radius: 10px !important; }
    .source-pill { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.7rem; font-weight: 600; margin: 0.15rem; }
    .source-marketo { background: #fce7f3; color: #9d174d; }
    .source-adobe { background: #fee2e2; color: #991b1b; }
    .source-6sense { background: #dbeafe; color: #1e40af; }
    .source-salesforce { background: #d1fae5; color: #065f46; }
    .source-pathfactory { background: #fef3c7; color: #92400e; }
    .source-aem { background: #e0e7ff; color: #3730a3; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Tools Definition
TOOLS = [
    {"name": "get_b2b_marketing_summary", "description": "Get B2B marketing summary", "input_schema": {"type": "object", "properties": {"time_period": {"type": "string"}, "segment": {"type": "string"}}}},
    {"name": "get_lead_metrics", "description": "Get lead metrics by segment", "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}, "lead_source": {"type": "string"}}}},
    {"name": "get_intent_signals", "description": "Get 6sense intent signals", "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}}}},
    {"name": "get_account_360_view", "description": "Get account 360 view", "input_schema": {"type": "object", "properties": {"account_name": {"type": "string"}}}},
    {"name": "get_conversion_funnel", "description": "Get conversion funnel", "input_schema": {"type": "object", "properties": {"segment": {"type": "string"}}}},
    {"name": "get_high_bounce_pages", "description": "Get high bounce pages", "input_schema": {"type": "object", "properties": {"min_bounce_rate": {"type": "integer"}}}},
    {"name": "get_pages_to_sunset", "description": "Get pages to sunset", "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_accounts_to_reach_out", "description": "Get accounts to reach out", "input_schema": {"type": "object", "properties": {"priority": {"type": "string"}}}},
    {"name": "get_paid_media_performance", "description": "Get paid media performance", "input_schema": {"type": "object", "properties": {"platform": {"type": "string"}}}},
    {"name": "get_channel_attribution", "description": "Get channel attribution", "input_schema": {"type": "object", "properties": {}}},
    {"name": "detect_marketing_anomalies", "description": "Detect anomalies", "input_schema": {"type": "object", "properties": {}}},
    {"name": "generate_campaign_brief", "description": "Generate campaign brief", "input_schema": {"type": "object", "properties": {"target_segment": {"type": "string"}}}},
    {"name": "get_pathfactory_engagement", "description": "Get PathFactory engagement", "input_schema": {"type": "object", "properties": {}}},
]

# Mock Data
def get_mock_data(tool_name: str, tool_input: Dict = None) -> Dict:
    mock = {
        "get_b2b_marketing_summary": {
            "data": [{"metric": "Total Leads", "value": 1245, "change": 12.5, "trend": "up"}, {"metric": "MQLs", "value": 425, "change": 8.3, "trend": "up"}, {"metric": "SQLs", "value": 156, "change": 15.2, "trend": "up"}, {"metric": "Pipeline", "value": 18500000, "change": 18.5, "trend": "up"}, {"metric": "Win Rate", "value": 31.5, "change": -2.1, "trend": "down"}],
            "trend_data": [{"month": "Jul", "leads": 180, "mqls": 58}, {"month": "Aug", "leads": 195, "mqls": 65}, {"month": "Sep", "leads": 210, "mqls": 72}, {"month": "Oct", "leads": 245, "mqls": 85}, {"month": "Nov", "leads": 268, "mqls": 92}, {"month": "Dec", "leads": 147, "mqls": 53}],
            "channel_breakdown": [{"channel": "Email", "leads": 312, "pct": 25}, {"channel": "Organic", "leads": 289, "pct": 23}, {"channel": "Paid Search", "leads": 234, "pct": 19}, {"channel": "Social", "leads": 178, "pct": 14}, {"channel": "Webinar", "leads": 145, "pct": 12}, {"channel": "Referral", "leads": 87, "pct": 7}],
            "segment_breakdown": [{"segment": "DCIO", "leads": 399, "mqls": 167, "rate": 41.9}, {"segment": "Enterprise", "leads": 501, "mqls": 139, "rate": 27.7}, {"segment": "Mid-Market", "leads": 345, "mqls": 119, "rate": 34.5}]
        },
        "get_lead_metrics": {
            "data": [{"segment": "DCIO", "source": "Website", "leads": 245, "mqls": 89, "rate": 36.3, "avg_score": 72.5}, {"segment": "DCIO", "source": "Webinar", "leads": 156, "mqls": 78, "rate": 50.0, "avg_score": 78.2}, {"segment": "Enterprise", "source": "Content", "leads": 312, "mqls": 94, "rate": 30.1, "avg_score": 65.8}, {"segment": "Enterprise", "source": "Paid Media", "leads": 189, "mqls": 45, "rate": 23.8, "avg_score": 58.3}, {"segment": "Mid-Market", "source": "Website", "leads": 203, "mqls": 58, "rate": 28.6, "avg_score": 61.3}],
            "quality_dist": [{"label": "Hot", "count": 89, "pct": 7}, {"label": "Warm", "count": 312, "pct": 25}, {"label": "Nurture", "count": 456, "pct": 37}, {"label": "Cold", "count": 278, "pct": 22}, {"label": "Unqualified", "count": 110, "pct": 9}],
            "weekly": [{"week": "W1", "leads": 285, "mqls": 98}, {"week": "W2", "leads": 312, "mqls": 105}, {"week": "W3", "leads": 298, "mqls": 102}, {"week": "W4", "leads": 350, "mqls": 120}]
        },
        "get_intent_signals": {
            "data": [{"company": "Goldman Sachs", "segment": "DCIO", "intent": 92, "stage": "Decision", "signals": 12}, {"company": "JPMorgan Chase", "segment": "DCIO", "intent": 88, "stage": "Decision", "signals": 9}, {"company": "Vanguard", "segment": "DCIO", "intent": 85, "stage": "Consideration", "signals": 8}, {"company": "BlackRock", "segment": "DCIO", "intent": 82, "stage": "Consideration", "signals": 7}, {"company": "Fidelity", "segment": "DCIO", "intent": 79, "stage": "Consideration", "signals": 6}],
            "stage_dist": [{"stage": "Decision", "count": 12, "pct": 15}, {"stage": "Consideration", "count": 35, "pct": 44}, {"stage": "Awareness", "count": 33, "pct": 41}],
            "topics": [{"topic": "retirement plans", "count": 45}, {"topic": "stable value", "count": 38}, {"topic": "401k providers", "count": 32}, {"topic": "target date", "count": 28}]
        },
        "get_account_360_view": {
            "data": [{"company": tool_input.get("account_name", "Goldman Sachs") if tool_input else "Goldman Sachs", "segment": "DCIO", "intent_score": 92, "engagement_score": 88, "buying_stage": "Decision", "lead_count": 8, "mql_count": 5, "web_sessions": 156, "content_downloads": 12, "pipeline_value": 2500000}],
            "timeline": [{"date": "Nov 1", "type": "Web Visit", "detail": "Viewed Stable Value page"}, {"date": "Nov 5", "type": "Content", "detail": "Downloaded DCIO Guide"}, {"date": "Nov 12", "type": "Webinar", "detail": "Attended Q4 Outlook"}, {"date": "Dec 2", "type": "Demo", "detail": "Requested product demo"}],
            "comparison": [{"company": "Goldman Sachs", "intent": 92, "engagement": 88, "pipeline": 2500000}, {"company": "JPMorgan", "intent": 88, "engagement": 82, "pipeline": 1800000}, {"company": "Vanguard", "intent": 85, "engagement": 78, "pipeline": 1500000}]
        },
        "get_conversion_funnel": {
            "data": [{"stage": "Visitors", "count": 45000, "rate": 100}, {"stage": "Known Leads", "count": 8500, "rate": 18.9}, {"stage": "Engaged", "count": 3200, "rate": 7.1}, {"stage": "MQLs", "count": 425, "rate": 0.94}, {"stage": "SQLs", "count": 156, "rate": 0.35}, {"stage": "Opportunities", "count": 89, "rate": 0.20}, {"stage": "Closed Won", "count": 28, "rate": 0.06}],
            "segment_funnels": {"DCIO": [{"stage": "Leads", "count": 399}, {"stage": "MQLs", "count": 167}, {"stage": "Won", "count": 18}], "Enterprise": [{"stage": "Leads", "count": 501}, {"stage": "MQLs", "count": 139}, {"stage": "Won", "count": 8}]},
            "velocity": [{"stage": "Lead to MQL", "avg_days": 14}, {"stage": "MQL to SQL", "avg_days": 21}, {"stage": "SQL to Opp", "avg_days": 18}, {"stage": "Opp to Close", "avg_days": 45}]
        },
        "get_high_bounce_pages": {
            "data": [{"page": "/landing/ppc-q4", "type": "Landing", "sessions": 245, "bounce": 72.5, "avg_time": 18}, {"page": "/landing/email-nov", "type": "Landing", "sessions": 189, "bounce": 68.2, "avg_time": 22}, {"page": "/resources/old-guide", "type": "Resource", "sessions": 56, "bounce": 65.4, "avg_time": 35}],
            "by_device": [{"device": "Mobile", "bounce": 68.5, "sessions": 1250}, {"device": "Desktop", "bounce": 45.2, "sessions": 2800}, {"device": "Tablet", "bounce": 52.3, "sessions": 450}]
        },
        "get_pages_to_sunset": {
            "data": [{"page": "/resources/archived/old-guide-2019", "views": 12, "bounce": 78.5, "reason": "Legacy content", "priority": "High"}, {"page": "/products/discontinued/old-fund", "views": 23, "bounce": 71.2, "reason": "Product discontinued", "priority": "High"}, {"page": "/solutions/legacy/outdated", "views": 15, "bounce": 68.9, "reason": "Outdated info", "priority": "Medium"}]
        },
        "get_accounts_to_reach_out": {
            "data": [{"company": "Vanguard", "segment": "DCIO", "intent": 85, "engagement": 78, "priority": "High", "action": "SDR Outreach", "days_silent": 14, "pipeline_potential": 1500000}, {"company": "Fidelity", "segment": "DCIO", "intent": 82, "engagement": 72, "priority": "High", "action": "Executive Email", "days_silent": 21, "pipeline_potential": 1200000}, {"company": "State Street", "segment": "DCIO", "intent": 78, "engagement": 66, "priority": "Medium", "action": "Nurture", "days_silent": 35, "pipeline_potential": 900000}],
            "priority_breakdown": [{"priority": "High", "count": 8, "potential": 12500000}, {"priority": "Medium", "count": 15, "potential": 8200000}, {"priority": "Low", "count": 22, "potential": 4800000}]
        },
        "get_paid_media_performance": {
            "data": [{"campaign": "LinkedIn DCIO", "platform": "LinkedIn", "spend": 48500, "impressions": 856000, "clicks": 9580, "conversions": 425, "ctr": 1.12, "roas": 2.8, "cpa": 114}, {"campaign": "Google Search", "platform": "Google", "spend": 38200, "impressions": 1650000, "clicks": 52800, "conversions": 1890, "ctr": 3.20, "roas": 4.5, "cpa": 20}, {"campaign": "LinkedIn Retarget", "platform": "LinkedIn", "spend": 22500, "impressions": 425000, "clicks": 5100, "conversions": 312, "ctr": 1.20, "roas": 3.2, "cpa": 72}],
            "platform_comp": [{"platform": "LinkedIn", "spend": 71000, "conversions": 737, "roas": 2.95}, {"platform": "Google", "spend": 54000, "conversions": 2135, "roas": 3.85}],
            "daily": [{"date": "Dec 1", "spend": 4200, "conversions": 145}, {"date": "Dec 2", "spend": 4500, "conversions": 162}, {"date": "Dec 3", "spend": 3800, "conversions": 128}, {"date": "Dec 4", "spend": 4100, "conversions": 152}]
        },
        "get_channel_attribution": {
            "data": [{"channel": "Email", "first_touch": 156, "last_touch": 189, "linear": 172, "revenue": 4500000, "pct": 32}, {"channel": "Organic", "first_touch": 189, "last_touch": 142, "linear": 165, "revenue": 3800000, "pct": 27}, {"channel": "Paid Search", "first_touch": 98, "last_touch": 112, "linear": 105, "revenue": 2800000, "pct": 20}, {"channel": "Social", "first_touch": 78, "last_touch": 65, "linear": 71, "revenue": 1800000, "pct": 13}],
            "paths": [{"path": "Organic → Email → Direct", "conversions": 45, "revenue": 1250000}, {"path": "Paid → Email → Direct", "conversions": 38, "revenue": 980000}, {"path": "Email → Webinar → Direct", "conversions": 32, "revenue": 850000}]
        },
        "detect_marketing_anomalies": {
            "data": [{"type": "🔴 Drop", "area": "Email CTR", "current": 5.2, "baseline": 8.5, "change": -38.8, "severity": "High", "action": "Review email content"}, {"type": "🟢 Spike", "area": "Vanguard Intent", "current": 89, "baseline": 62, "change": 43.5, "severity": "Opportunity", "action": "Prioritize SDR outreach"}, {"type": "🟢 Spike", "area": "BlackRock Intent", "current": 85, "baseline": 58, "change": 46.6, "severity": "Opportunity", "action": "Add to ABM"}, {"type": "🟡 Gap", "area": "Fidelity", "current": 72, "baseline": 14, "change": 414, "severity": "Medium", "action": "Sales outreach"}],
            "summary": {"total": 6, "high": 2, "opportunities": 2, "medium": 2}
        },
        "generate_campaign_brief": {
            "data": [{"campaign_name": f"{tool_input.get('target_segment', 'DCIO') if tool_input else 'DCIO'} Q1 2025", "target_segment": tool_input.get('target_segment', 'DCIO') if tool_input else 'DCIO', "budget": 25000, "duration": "6 weeks"}],
            "target_accounts": [{"company": "Vanguard", "intent": 85, "fit": "A"}, {"company": "Fidelity", "intent": 82, "fit": "A"}, {"company": "State Street", "intent": 78, "fit": "B"}],
            "channel_mix": [{"channel": "LinkedIn Ads", "budget": 10000, "expected_leads": 45}, {"channel": "Email Nurture", "budget": 5000, "expected_leads": 25}, {"channel": "Content Syndication", "budget": 6000, "expected_leads": 30}],
            "expected_results": {"leads": 120, "mqls": 45, "pipeline": 2500000, "cpl": 208}
        },
        "get_pathfactory_engagement": {
            "data": [{"company": "Goldman Sachs", "asset": "Stable Value Guide", "type": "Whitepaper", "time_spent": 485, "completion": 92}, {"company": "JPMorgan", "asset": "DCIO Comparison", "type": "eBook", "time_spent": 320, "completion": 78}, {"company": "Vanguard", "asset": "Best Practices", "type": "Whitepaper", "time_spent": 245, "completion": 65}],
            "by_type": [{"type": "Whitepaper", "avg_time": 340, "completion": 72}, {"type": "eBook", "avg_time": 280, "completion": 65}, {"type": "Video", "avg_time": 180, "completion": 58}]
        }
    }
    return mock.get(tool_name, {"data": [{"info": "Data retrieved"}]})

# Visualization Functions
def create_visualizations(tool_name: str, data: Dict) -> List[Tuple[str, go.Figure]]:
    figures = []
    try:
        if tool_name == "get_b2b_marketing_summary":
            # KPI Gauges
            summary = data.get("data", [])
            if summary:
                gauge_fig = make_subplots(rows=2, cols=3, specs=[[{'type': 'indicator'}]*3]*2, subplot_titles=[d['metric'] for d in summary[:6]])
                for i, d in enumerate(summary[:6]):
                    row, col = (i // 3) + 1, (i % 3) + 1
                    max_val = d['value'] * 1.5 if d['value'] > 0 else 100
                    gauge_fig.add_trace(go.Indicator(mode='gauge+number', value=d['value'], gauge=dict(axis=dict(range=[0, max_val]), bar=dict(color='#3b82f6' if d.get('trend') == 'up' else '#ef4444'))), row=row, col=col)
                gauge_fig.update_layout(template='plotly_dark', height=400, title="📊 Key Metrics")
                figures.append(("📊 KPIs", gauge_fig))
            
            # Trend Line
            trend = data.get("trend_data", [])
            if trend:
                df = pd.DataFrame(trend)
                line_fig = go.Figure()
                line_fig.add_trace(go.Scatter(x=df['month'], y=df['leads'], name='Leads', mode='lines+markers', line=dict(width=3, color='#3b82f6')))
                line_fig.add_trace(go.Scatter(x=df['month'], y=df['mqls'], name='MQLs', mode='lines+markers', line=dict(width=3, color='#10b981')))
                line_fig.update_layout(template='plotly_dark', height=350, title="📈 Monthly Trend")
                figures.append(("📈 Trend", line_fig))
            
            # Channel Pie
            channels = data.get("channel_breakdown", [])
            if channels:
                df = pd.DataFrame(channels)
                pie_fig = px.pie(df, values='leads', names='channel', title="🥧 Leads by Channel", hole=0.4)
                pie_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("🥧 Channels", pie_fig))
            
            # Segment Bar
            segments = data.get("segment_breakdown", [])
            if segments:
                df = pd.DataFrame(segments)
                bar_fig = px.bar(df, x='segment', y=['leads', 'mqls'], barmode='group', title="📊 By Segment")
                bar_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("📊 Segments", bar_fig))

        elif tool_name == "get_lead_metrics":
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                bar_fig = px.bar(df, x='segment', y='leads', color='source', barmode='stack', title="📊 Leads by Segment & Source")
                bar_fig.update_layout(template='plotly_dark', height=400)
                figures.append(("📊 Volume", bar_fig))
                
                rate_fig = px.bar(df, x='source', y='rate', color='segment', barmode='group', title="📈 MQL Rate by Source")
                rate_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("📈 MQL Rate", rate_fig))
                
                # Heatmap
                pivot = df.pivot_table(values='avg_score', index='segment', columns='source', aggfunc='mean')
                heat_fig = go.Figure(data=go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index, colorscale='Blues'))
                heat_fig.update_layout(template='plotly_dark', height=350, title="🔥 Score Heatmap")
                figures.append(("🔥 Heatmap", heat_fig))
            
            quality = data.get("quality_dist", [])
            if quality:
                df = pd.DataFrame(quality)
                pie_fig = px.pie(df, values='count', names='label', title="🎯 Lead Quality", hole=0.4)
                pie_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("🎯 Quality", pie_fig))
            
            weekly = data.get("weekly", [])
            if weekly:
                df = pd.DataFrame(weekly)
                line_fig = go.Figure()
                line_fig.add_trace(go.Scatter(x=df['week'], y=df['leads'], name='Leads', mode='lines+markers', line=dict(width=3, color='#3b82f6')))
                line_fig.add_trace(go.Scatter(x=df['week'], y=df['mqls'], name='MQLs', mode='lines+markers', line=dict(width=3, color='#10b981')))
                line_fig.update_layout(template='plotly_dark', height=300, title="📈 Weekly Trend")
                figures.append(("📈 Weekly", line_fig))

        elif tool_name == "get_intent_signals":
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                bar_fig = px.bar(df.sort_values('intent'), x='intent', y='company', orientation='h', color='stage', title="🔥 Intent Scores", color_discrete_map={"Decision": "#10b981", "Consideration": "#f59e0b", "Awareness": "#94a3b8"})
                bar_fig.update_layout(template='plotly_dark', height=400)
                figures.append(("🔥 Intent", bar_fig))
                
                # Radar
                radar_fig = go.Figure()
                for i, row in enumerate(main[:3]):
                    radar_fig.add_trace(go.Scatterpolar(r=[row['intent'], row['signals']*10, 80], theta=['Intent', 'Signals', 'Engagement'], fill='toself', name=row['company']))
                radar_fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), template='plotly_dark', height=400, title="🎯 Account Comparison")
                figures.append(("🎯 Radar", radar_fig))
            
            stages = data.get("stage_dist", [])
            if stages:
                df = pd.DataFrame(stages)
                pie_fig = px.pie(df, values='count', names='stage', title="🥧 Buying Stage", hole=0.4)
                pie_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("🥧 Stages", pie_fig))
            
            topics = data.get("topics", [])
            if topics:
                df = pd.DataFrame(topics)
                topic_fig = px.bar(df, x='count', y='topic', orientation='h', title="🔍 Research Topics")
                topic_fig.update_layout(template='plotly_dark', height=300)
                figures.append(("🔍 Topics", topic_fig))

        elif tool_name == "get_account_360_view":
            main = data.get("data", [{}])[0]
            # Gauges
            gauge_fig = make_subplots(rows=1, cols=4, specs=[[{'type': 'indicator'}]*4], subplot_titles=['Intent', 'Engagement', 'Lead Score', 'Pipeline ($M)'])
            for i, (k, v) in enumerate([('intent_score', main.get('intent_score', 0)), ('engagement_score', main.get('engagement_score', 0)), ('mql_count', main.get('mql_count', 0)*20), ('pipeline_value', main.get('pipeline_value', 0)/1000000)]):
                gauge_fig.add_trace(go.Indicator(mode='gauge+number', value=v, gauge=dict(axis=dict(range=[0, 100 if i < 3 else 5]), bar=dict(color='#3b82f6'))), row=1, col=i+1)
            gauge_fig.update_layout(template='plotly_dark', height=250, title=f"🎯 {main.get('company', 'Account')} Scorecard")
            figures.append(("🎯 Scorecard", gauge_fig))
            
            # Comparison
            comp = data.get("comparison", [])
            if comp:
                df = pd.DataFrame(comp)
                scatter_fig = px.scatter(df, x='intent', y='engagement', size='pipeline', hover_name='company', title="🔍 Peer Comparison")
                scatter_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("🔍 Comparison", scatter_fig))
            
            # Sankey
            labels = ["Website", "Paid", "Email", "Known", "Engaged", "MQL", "SQL", "Won"]
            sankey_fig = go.Figure(data=[go.Sankey(node=dict(pad=15, thickness=20, label=labels, color=['#3b82f6']*3 + ['#10b981', '#f59e0b', '#22c55e', '#8b5cf6', '#22c55e']), link=dict(source=[0,1,2,3,3,4,5,6], target=[3,3,4,4,5,5,6,7], value=[300,200,180,250,150,120,90,28]))])
            sankey_fig.update_layout(template='plotly_dark', height=400, title="🔄 Journey Flow")
            figures.append(("🔄 Journey", sankey_fig))

        elif tool_name == "get_conversion_funnel":
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                funnel_fig = go.Figure(go.Funnel(y=df['stage'], x=df['count'], textposition='inside', textinfo='value+percent initial', marker=dict(color=['#3b82f6', '#0ea5e9', '#06b6d4', '#10b981', '#22c55e', '#84cc16', '#eab308'][:len(df)])))
                funnel_fig.update_layout(template='plotly_dark', height=450, title="🔄 Conversion Funnel")
                figures.append(("🔄 Funnel", funnel_fig))
            
            segments = data.get("segment_funnels", {})
            if segments:
                seg_fig = go.Figure()
                for seg, stages in segments.items():
                    df = pd.DataFrame(stages)
                    seg_fig.add_trace(go.Bar(name=seg, x=df['stage'], y=df['count']))
                seg_fig.update_layout(template='plotly_dark', height=350, barmode='group', title="📊 By Segment")
                figures.append(("📊 Segments", seg_fig))
            
            velocity = data.get("velocity", [])
            if velocity:
                df = pd.DataFrame(velocity)
                vel_fig = px.bar(df, x='stage', y='avg_days', title="⏱️ Stage Velocity (Days)", color='avg_days', color_continuous_scale='Blues')
                vel_fig.update_layout(template='plotly_dark', height=300)
                figures.append(("⏱️ Velocity", vel_fig))

        elif tool_name == "get_paid_media_performance":
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                roas_fig = px.bar(df, x='campaign', y='roas', color='platform', title="💰 ROAS by Campaign", color_discrete_map={"LinkedIn": "#0077b5", "Google": "#4285f4"})
                roas_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("💰 ROAS", roas_fig))
                
                scatter_fig = px.scatter(df, x='spend', y='conversions', size='roas', color='platform', hover_name='campaign', title="📊 Spend vs Conversions")
                scatter_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("📊 Efficiency", scatter_fig))
                
                rate_fig = go.Figure()
                rate_fig.add_trace(go.Bar(name='CTR %', x=df['campaign'], y=df['ctr']))
                rate_fig.update_layout(template='plotly_dark', height=300, title="📈 CTR Comparison")
                figures.append(("📈 CTR", rate_fig))
            
            plat = data.get("platform_comp", [])
            if plat:
                df = pd.DataFrame(plat)
                pie_fig = px.pie(df, values='spend', names='platform', title="🥧 Budget Split", hole=0.4)
                pie_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("🥧 Budget", pie_fig))
            
            daily = data.get("daily", [])
            if daily:
                df = pd.DataFrame(daily)
                line_fig = go.Figure()
                line_fig.add_trace(go.Scatter(x=df['date'], y=df['spend'], name='Spend', mode='lines+markers', line=dict(width=3, color='#ef4444')))
                line_fig.add_trace(go.Scatter(x=df['date'], y=df['conversions'], name='Conversions', mode='lines+markers', line=dict(width=3, color='#10b981'), yaxis='y2'))
                line_fig.update_layout(template='plotly_dark', height=300, title="📈 Daily Trend", yaxis2=dict(overlaying='y', side='right'))
                figures.append(("📈 Daily", line_fig))

        elif tool_name == "get_channel_attribution":
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                pie_fig = px.pie(df, values='revenue', names='channel', title="🥧 Revenue Attribution", hole=0.4)
                pie_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("🥧 Revenue", pie_fig))
                
                attr_fig = go.Figure()
                attr_fig.add_trace(go.Bar(name='First Touch', x=df['channel'], y=df['first_touch']))
                attr_fig.add_trace(go.Bar(name='Last Touch', x=df['channel'], y=df['last_touch']))
                attr_fig.add_trace(go.Bar(name='Linear', x=df['channel'], y=df['linear']))
                attr_fig.update_layout(template='plotly_dark', height=350, barmode='group', title="📊 Attribution Models")
                figures.append(("📊 Models", attr_fig))
            
            paths = data.get("paths", [])
            if paths:
                df = pd.DataFrame(paths)
                path_fig = px.bar(df, x='revenue', y='path', orientation='h', title="🔄 Top Paths", color='conversions')
                path_fig.update_layout(template='plotly_dark', height=300)
                figures.append(("🔄 Paths", path_fig))

        elif tool_name == "detect_marketing_anomalies":
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                type_counts = df['type'].value_counts().reset_index()
                type_counts.columns = ['type', 'count']
                anom_fig = px.bar(type_counts, x='type', y='count', color='type', title="🚨 Anomalies by Type")
                anom_fig.update_layout(template='plotly_dark', height=300, showlegend=False)
                figures.append(("🚨 Summary", anom_fig))
                
                change_fig = px.bar(df, x='area', y='change', color='severity', title="📊 Change Magnitude", color_discrete_map={"High": "#ef4444", "Opportunity": "#10b981", "Medium": "#f59e0b"})
                change_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("📊 Impact", change_fig))
            
            summary = data.get("summary", {})
            if summary:
                gauge_fig = make_subplots(rows=1, cols=3, specs=[[{'type': 'indicator'}]*3], subplot_titles=['High Priority', 'Opportunities', 'Medium'])
                for i, (k, c) in enumerate([('high', '#ef4444'), ('opportunities', '#10b981'), ('medium', '#f59e0b')]):
                    gauge_fig.add_trace(go.Indicator(mode='number', value=summary.get(k, 0), number=dict(font=dict(size=48, color=c))), row=1, col=i+1)
                gauge_fig.update_layout(template='plotly_dark', height=200)
                figures.append(("📊 Priority", gauge_fig))

        elif tool_name == "generate_campaign_brief":
            channels = data.get("channel_mix", [])
            if channels:
                df = pd.DataFrame(channels)
                pie_fig = px.pie(df, values='budget', names='channel', title="🥧 Budget Allocation", hole=0.4)
                pie_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("🥧 Budget", pie_fig))
                
                leads_fig = px.bar(df, x='channel', y='expected_leads', color='channel', title="📈 Expected Leads")
                leads_fig.update_layout(template='plotly_dark', height=300, showlegend=False)
                figures.append(("📈 Leads", leads_fig))
            
            targets = data.get("target_accounts", [])
            if targets:
                df = pd.DataFrame(targets)
                target_fig = px.bar(df.sort_values('intent', ascending=True), x='intent', y='company', orientation='h', color='fit', title="🎯 Target Accounts")
                target_fig.update_layout(template='plotly_dark', height=300)
                figures.append(("🎯 Targets", target_fig))
            
            results = data.get("expected_results", {})
            if results:
                gauge_fig = make_subplots(rows=1, cols=3, specs=[[{'type': 'indicator'}]*3], subplot_titles=['Leads', 'MQLs', 'Pipeline ($M)'])
                gauge_fig.add_trace(go.Indicator(mode='number', value=results.get('leads', 0)), row=1, col=1)
                gauge_fig.add_trace(go.Indicator(mode='number', value=results.get('mqls', 0)), row=1, col=2)
                gauge_fig.add_trace(go.Indicator(mode='number', value=results.get('pipeline', 0)/1000000, number=dict(suffix='M')), row=1, col=3)
                gauge_fig.update_layout(template='plotly_dark', height=200, title="📊 Projections")
                figures.append(("📊 Results", gauge_fig))

        elif tool_name in ["get_high_bounce_pages", "get_pages_to_sunset"]:
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                metric = 'bounce' if 'bounce' in df.columns else 'views'
                bar_fig = px.bar(df, x=metric, y='page', orientation='h', color=metric, title=f"📄 Pages by {metric.title()}", color_continuous_scale='Reds' if metric == 'bounce' else 'Blues')
                bar_fig.update_layout(template='plotly_dark', height=400)
                figures.append(("📄 Overview", bar_fig))
            
            device = data.get("by_device", [])
            if device:
                df = pd.DataFrame(device)
                pie_fig = px.pie(df, values='sessions', names='device', title="📱 By Device", hole=0.4)
                pie_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("📱 Devices", pie_fig))

        elif tool_name == "get_accounts_to_reach_out":
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                scatter_fig = px.scatter(df, x='intent', y='engagement', size='pipeline_potential', color='priority', hover_name='company', title="🎯 Priority Matrix", color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"})
                scatter_fig.update_layout(template='plotly_dark', height=400)
                figures.append(("🎯 Matrix", scatter_fig))
                
                bar_fig = px.bar(df.sort_values('pipeline_potential'), x='pipeline_potential', y='company', orientation='h', color='priority', title="💰 Pipeline Potential")
                bar_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("💰 Potential", bar_fig))
            
            priority = data.get("priority_breakdown", [])
            if priority:
                df = pd.DataFrame(priority)
                pie_fig = px.pie(df, values='count', names='priority', title="🥧 Priority Mix", hole=0.4)
                pie_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("🥧 Priority", pie_fig))

        elif tool_name == "get_pathfactory_engagement":
            main = data.get("data", [])
            if main:
                df = pd.DataFrame(main)
                bar_fig = px.bar(df, x='company', y='time_spent', color='type', title="📚 Content Engagement")
                bar_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("📚 Engagement", bar_fig))
            
            by_type = data.get("by_type", [])
            if by_type:
                df = pd.DataFrame(by_type)
                type_fig = px.bar(df, x='type', y=['avg_time', 'completion'], barmode='group', title="📊 By Content Type")
                type_fig.update_layout(template='plotly_dark', height=350)
                figures.append(("📊 By Type", type_fig))

        # Default fallback
        if not figures:
            main = data.get("data", [])
            if main and isinstance(main, list):
                df = pd.DataFrame(main)
                if len(df.columns) >= 2:
                    num_cols = df.select_dtypes(include=['number']).columns.tolist()
                    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
                    if num_cols and cat_cols:
                        fig = px.bar(df, x=cat_cols[0], y=num_cols[0], title="📊 Data")
                        fig.update_layout(template='plotly_dark', height=400)
                        figures.append(("📊 Overview", fig))
    except Exception as e:
        st.warning(f"Chart error: {e}")
    return figures

# Follow-ups
FOLLOWUPS = {
    "get_b2b_marketing_summary": ["Lead metrics by segment", "Top intent accounts", "Detect anomalies", "Conversion funnel"],
    "get_lead_metrics": ["Conversion funnel", "Accounts to reach out", "Campaign brief", "Quality distribution"],
    "get_intent_signals": ["360 view top account", "Accounts to reach out", "Campaign brief", "Buying stages"],
    "get_account_360_view": ["Content engagement", "Similar accounts", "Funnel analysis", "PathFactory data"],
    "get_conversion_funnel": ["Drop-off analysis", "Lead metrics", "Accounts needing nurture", "Velocity metrics"],
    "get_high_bounce_pages": ["Pages to sunset", "SEO comparison", "Device breakdown", "Weekly trend"],
    "get_pages_to_sunset": ["High bounce pages", "Page performance", "Impact analysis", "SEO performance"],
    "get_accounts_to_reach_out": ["360 view top account", "Generate campaign", "Intent signals", "Content engagement"],
    "get_paid_media_performance": ["Channel attribution", "LinkedIn vs Google", "Daily trend", "Optimization brief"],
    "get_channel_attribution": ["Paid media details", "Journey paths", "Lead sources", "Funnel by channel"],
    "detect_marketing_anomalies": ["Intent spike details", "Account 360", "Recovery campaign", "Performance drops"],
    "generate_campaign_brief": ["Target accounts", "Historical performance", "Content assets", "Benchmarks"],
}
DEFAULT_FOLLOWUPS = ["B2B summary", "Detect anomalies", "Accounts to reach out", "Campaign brief"]

# Sidebar
with st.sidebar:
    st.markdown("## 🎯 Marketing Analytics Agent")
    st.markdown("---")
    api_key = st.text_input("🔑 API Key", type="password", placeholder="sk-ant-api03-...")
    if api_key and api_key.startswith("sk-ant-"):
        st.success("✅ Valid")
    demo_mode = st.toggle("🎮 Demo Mode", value=True)
    st.markdown("---")
    st.markdown("### 🎬 Demo Steps")
    for label, q in [("1️⃣ Overview", "B2B marketing summary"), ("2️⃣ Leads", "Lead metrics by segment"), ("3️⃣ Intent", "Top intent accounts"), ("4️⃣ Account", "360 view Goldman Sachs"), ("5️⃣ Funnel", "Conversion funnel"), ("6️⃣ Anomalies", "Detect anomalies"), ("7️⃣ Campaign", "Campaign brief for DCIO")]:
        if st.button(label, key=f"demo_{label}", use_container_width=True):
            st.session_state.pending_question = q
            st.rerun()
    st.markdown("---")
    st.markdown("### 📦 Data Sources")
    for n, c in [("Marketo", "marketo"), ("Adobe Analytics", "adobe"), ("6sense", "6sense"), ("Salesforce", "salesforce"), ("PathFactory", "pathfactory"), ("AEM", "aem")]:
        st.markdown(f'<span class="source-pill source-{c}">{n}</span>', unsafe_allow_html=True)
    st.markdown("---")
    if st.session_state.messages:
        export = f"# Report {datetime.now().strftime('%Y-%m-%d')}\n\n"
        for m in st.session_state.messages:
            export += f"**{'User' if m['role']=='user' else 'Agent'}:** {m['content']}\n\n---\n\n"
        st.download_button("📥 Export", export, file_name=f"report_{datetime.now().strftime('%Y%m%d')}.md", use_container_width=True)

# Main
st.markdown('<div class="main-header"><h1>🎯 Marketing Analytics Agent</h1><p>Ask questions in plain English • Get insights from Marketo, Adobe Analytics, 6sense, Salesforce, PathFactory & AEM</p></div>', unsafe_allow_html=True)

# KPIs
if demo_mode:
    cols = st.columns(4)
    for i, (t, v, c, tr) in enumerate([("LEADS (90D)", "1,245", "↑ 12.5%", "positive"), ("MQL RATE", "34.2%", "↑ 3.5%", "positive"), ("PIPELINE", "$18.5M", "↑ 18.5%", "positive"), ("WIN RATE", "31.5%", "↓ 2.1%", "negative")]):
        with cols[i]:
            st.markdown(f'<div class="metric-card"><h4>{t}</h4><div class="val">{v}</div><div class="change {tr}">{c}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# Samples
with st.expander("💡 Sample Questions", expanded=False):
    scols = st.columns(4)
    for i, q in enumerate(["B2B summary", "Lead metrics", "Intent signals", "Conversion funnel", "High bounce pages", "Pages to sunset", "Accounts to reach out", "Paid media", "Attribution", "Anomalies", "360 Goldman Sachs", "Campaign brief"]):
        with scols[i % 4]:
            if st.button(q, key=f"s_{i}", use_container_width=True):
                st.session_state.pending_question = q
                st.rerun()

# Input
st.markdown("### 💬 Ask Your Question")
c1, c2, c3, c4 = st.columns([6, 1, 1, 1])
with c1:
    user_input = st.text_input("Q", placeholder="Ask about leads, campaigns, accounts...", label_visibility="collapsed", key="main_input")
with c2:
    ask = st.button("🚀 Ask", use_container_width=True, type="primary")
with c3:
    if st.button("🆕 New", use_container_width=True):
        st.session_state.messages = []
        st.session_state.api_messages = []
        st.session_state.query_count = 0
        st.session_state.show_followups = []
        st.rerun()
with c4:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.messages = []
        st.session_state.show_followups = []
        st.rerun()

st.markdown("---")

# Chat History
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg.get("figures"):
            tabs = st.tabs([n for n, _ in msg["figures"]])
            for tab, (n, fig) in zip(tabs, msg["figures"]):
                with tab:
                    st.plotly_chart(fig, use_container_width=True, key=f"h_{idx}_{n}")
        if msg.get("data"):
            with st.expander("📋 Data"):
                df = pd.DataFrame(msg["data"])
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 CSV", df.to_csv(index=False), file_name=f"data_{idx}.csv", key=f"dl_{idx}")
        if msg.get("tools"):
            st.caption(f"🔧 {' → '.join(msg['tools'])}")

# Follow-ups
if st.session_state.show_followups:
    st.markdown("---")
    st.markdown("### 💡 Follow-ups")
    fcols = st.columns(min(len(st.session_state.show_followups), 4))
    for i, fu in enumerate(st.session_state.show_followups[:4]):
        with fcols[i]:
            if st.button(fu, key=f"fu_{st.session_state.query_count}_{i}", use_container_width=True):
                st.session_state.pending_question = fu
                st.rerun()

# Process
final_input = st.session_state.pending_question if st.session_state.pending_question else (user_input if user_input and ask else None)
if st.session_state.pending_question:
    st.session_state.pending_question = None

if final_input:
    st.session_state.query_count += 1
    st.session_state.show_followups = []
    st.session_state.messages.append({"role": "user", "content": final_input})
    
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(final_input)
    
    with st.chat_message("assistant", avatar="🤖"):
        if not api_key:
            st.error("❌ Enter API key")
        elif not ANTHROPIC_OK:
            st.error("❌ pip install anthropic")
        else:
            try:
                client = anthropic.Anthropic(api_key=api_key)
                system = f"You are a Marketing Analytics Agent with 13 MCP tools. Use appropriate tools. Lead with numbers. Be concise. Context: {st.session_state.conversation_context or 'New conversation'}"
                api_msgs = st.session_state.api_messages[-10:] + [{"role": "user", "content": final_input}]
                
                start = time.time()
                status = st.status("🤖 Analyzing...", expanded=True)
                
                response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=4096, system=system, tools=TOOLS, messages=api_msgs)
                
                tools_used, tool_data, tool_name = [], None, None
                iteration = 0
                while response.stop_reason == "tool_use" and iteration < 5:
                    iteration += 1
                    for tb in [b for b in response.content if b.type == "tool_use"]:
                        status.update(label=f"📊 {tb.name}...")
                        st.write(f"🔧 **{tb.name}**")
                        tools_used.append(tb.name)
                        tool_name = tb.name
                        tool_data = get_mock_data(tb.name, tb.input) if demo_mode else get_mock_data(tb.name, tb.input)
                        api_msgs.append({"role": "assistant", "content": response.content})
                        api_msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tb.id, "content": json.dumps(tool_data, default=str)}]})
                    response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=4096, system=system, tools=TOOLS, messages=api_msgs)
                
                status.update(label="✅ Done!", state="complete")
                
                answer = "".join([b.text for b in response.content if hasattr(b, "text")]) or "See visualizations below."
                st.markdown(answer)
                
                figures, display_data = [], None
                if tool_name and tool_data:
                    figures = create_visualizations(tool_name, tool_data)
                    display_data = tool_data.get("data", [])
                    if figures:
                        tabs = st.tabs([n for n, _ in figures])
                        for tab, (n, fig) in zip(tabs, figures):
                            with tab:
                                st.plotly_chart(fig, use_container_width=True, key=f"new_{n}_{st.session_state.query_count}")
                    if display_data:
                        with st.expander("📋 Data"):
                            df = pd.DataFrame(display_data)
                            st.dataframe(df, use_container_width=True)
                            st.download_button("📥 CSV", df.to_csv(index=False), file_name=f"data_{st.session_state.query_count}.csv", key=f"dl_new_{st.session_state.query_count}")
                
                if tools_used:
                    st.caption(f"🔧 {' → '.join(tools_used)} | ⏱️ {time.time()-start:.1f}s")
                
                st.session_state.messages.append({"role": "assistant", "content": answer, "figures": figures, "data": display_data, "tools": tools_used})
                st.session_state.api_messages = api_msgs + [{"role": "assistant", "content": response.content}]
                st.session_state.conversation_context = f"Last: '{final_input}' using '{tool_name}'"
                st.session_state.show_followups = FOLLOWUPS.get(tool_name, DEFAULT_FOLLOWUPS)
                st.rerun()
            except anthropic.AuthenticationError:
                st.error("❌ Invalid API key")
            except Exception as e:
                st.error(f"❌ {e}")

# Footer
st.markdown("---")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### 🏗️ Architecture\n- MCP Protocol\n- Claude AI\n- 13+ Tools\n- 15+ Chart Types")
with c2:
    st.markdown("#### 📊 Charts\n- Line, Bar, Pie\n- Funnel, Sankey\n- Heatmap, Radar\n- Gauge, Scatter")
with c3:
    st.markdown("#### 🚀 Value\n- 6hrs → 30sec\n- Anomaly detection\n- Cross-platform insights")

st.markdown('<div style="text-align:center;margin-top:2rem;padding:1rem;background:#1e2432;border-radius:10px;"><small style="color:#94a3b8;">Marketing Analytics Agent v9 | Claude AI + MCP | MetLife | Dec 2024</small></div>', unsafe_allow_html=True)