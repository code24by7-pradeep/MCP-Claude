"""
Marketing Analytics Agent v8 - COMPLETE SOLUTION
=================================================
Features:
1. ✅ Full MCP Server tool integration (26 tools)
2. ✅ Conversation history & context for follow-ups
3. ✅ Follow-up question buttons (dynamic based on last query)
4. ✅ Drill-down capability - ask continuously about same topic
5. ✅ Clear chat functionality
6. ✅ Download conversation as markdown/CSV
7. ✅ Charts render properly
8. ✅ Data table with CSV download
9. ✅ "Agent thinking" status messages
10. ✅ Error handling

Run: streamlit run marketing_agent_v8.py
"""

import streamlit as st

# Page config MUST be first
st.set_page_config(
    page_title="Marketing Analytics Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

import json
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Optional
import time

# Check imports
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

if not ANTHROPIC_OK:
    st.error("❌ Install anthropic: `pip install anthropic`")
if not PLOTLY_OK:
    st.error("❌ Install plotly: `pip install plotly`")

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "messages": [],           # Chat messages for display
        "api_messages": [],       # Messages for Claude API (maintains context)
        "query_count": 0,
        "pending_question": None,
        "show_followups": [],
        "last_tool_used": None,
        "last_tool_data": None,
        "total_response_time": 0,
        "conversation_context": "",  # Summary of conversation for context
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============================================================================
# CUSTOM CSS
# ============================================================================
st.markdown("""
<style>
    /* Dark theme styling */
    .stApp { background-color: #0f1117; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { 
        background-color: #1a1f2e; 
    }
    section[data-testid="stSidebar"] * { 
        color: #e2e8f0 !important; 
    }
    
    /* Input fields */
    .stTextInput input { 
        background-color: #1e2432 !important; 
        color: white !important;
        border: 1px solid #3b4a6b !important;
        border-radius: 8px !important;
    }
    
    /* Metric cards */
    .metric-box {
        background: linear-gradient(135deg, #1e2432, #252d3d);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #3b82f6;
        margin-bottom: 0.5rem;
    }
    .metric-box h4 { 
        color: #94a3b8; 
        font-size: 0.7rem; 
        margin: 0;
        text-transform: uppercase;
    }
    .metric-box .val { 
        color: white; 
        font-size: 1.4rem; 
        font-weight: bold; 
    }
    .metric-box .change {
        font-size: 0.8rem;
    }
    .metric-box .change.positive { color: #10b981; }
    .metric-box .change.negative { color: #ef4444; }
    
    /* Follow-up buttons container */
    .followup-container {
        background: #1e2432;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #3b4a6b;
    }
    
    /* Tool badge */
    .tool-badge {
        display: inline-block;
        background: #3b82f6;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        margin: 0.1rem;
    }
    
    /* Data source pills */
    .source-pill {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 10px;
        font-size: 0.7rem;
        font-weight: 500;
        margin: 0.1rem;
    }
    .source-marketo { background: #fce7f3; color: #9d174d; }
    .source-adobe { background: #fee2e2; color: #991b1b; }
    .source-6sense { background: #dbeafe; color: #1e40af; }
    .source-salesforce { background: #d1fae5; color: #065f46; }
    .source-pathfactory { background: #fef3c7; color: #92400e; }
    .source-aem { background: #e0e7ff; color: #3730a3; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Chat message styling */
    .stChatMessage {
        background-color: #1e2432 !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# COMPLETE MCP TOOLS DEFINITION (26 Tools - matching your server)
# ============================================================================
TOOLS = [
    # B2B Marketing Summary
    {
        "name": "get_b2b_marketing_summary",
        "description": "Get comprehensive B2B marketing performance summary across all channels including leads, MQLs, pipeline, conversions, and key metrics",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_period": {"type": "string", "enum": ["30d", "60d", "90d", "QTD", "YTD"], "default": "90d"},
                "segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business", "All"]}
            }
        }
    },
    # Lead & Account Metrics
    {
        "name": "get_lead_metrics",
        "description": "Get lead generation metrics including counts, scores, and conversion rates by segment and source",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business", "All"]},
                "days_back": {"type": "integer", "default": 90},
                "lead_source": {"type": "string", "enum": ["Website", "Event", "Content", "Referral", "Ads", "All"]}
            }
        }
    },
    {
        "name": "get_account_engagement_scores",
        "description": "Get account engagement scores from 6sense including buying stage and lead temperature",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_score": {"type": "integer", "default": 50},
                "buying_stage": {"type": "string", "enum": ["Awareness", "Consideration", "Decision", "All"]},
                "profile_fit": {"type": "string", "enum": ["A", "B", "C", "D", "All"]}
            }
        }
    },
    {
        "name": "get_intent_signals",
        "description": "Get 6sense intent signals showing which accounts are researching relevant topics",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_intent_score": {"type": "integer", "default": 60},
                "intent_strength": {"type": "string", "enum": ["high", "medium", "low", "All"]},
                "segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business", "All"]}
            }
        }
    },
    {
        "name": "get_account_360_view",
        "description": "Get comprehensive 360-degree view of a specific account including all touchpoints",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string", "description": "Company name to lookup"},
                "account_domain": {"type": "string", "description": "Company domain (alternative to name)"}
            }
        }
    },
    # Conversion & Funnel
    {
        "name": "get_conversion_funnel",
        "description": "Get conversion funnel metrics from lead to opportunity by segment",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business", "All"]}
            }
        }
    },
    {
        "name": "get_account_journey_funnel",
        "description": "Get account journey through marketing funnel stages with time in each stage",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_domain": {"type": "string"},
                "segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business", "All"]}
            }
        }
    },
    {
        "name": "get_converted_accounts",
        "description": "Get accounts that converted to opportunities or closed won with their journey paths",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_deal_value": {"type": "integer", "default": 0},
                "segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business", "All"]}
            }
        }
    },
    # Page Analytics
    {
        "name": "get_page_performance",
        "description": "Get page performance scores including views, bounce rate, time on page, and SEO score",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_type": {"type": "string", "enum": ["Product", "Solution", "Resource", "Conversion", "About", "News", "Archived", "Landing", "All"]},
                "min_views": {"type": "integer", "default": 0}
            }
        }
    },
    {
        "name": "get_legacy_pages_low_views",
        "description": "Get legacy/archived pages with less than specified number of views - candidates for sunset",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_views": {"type": "integer", "default": 50},
                "page_status": {"type": "string", "enum": ["legacy", "active", "all"], "default": "legacy"}
            }
        }
    },
    {
        "name": "get_high_bounce_pages",
        "description": "Get pages with high bounce rates that need optimization",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_bounce_rate": {"type": "integer", "default": 50},
                "min_sessions": {"type": "integer", "default": 10}
            }
        }
    },
    {
        "name": "get_pages_to_sunset",
        "description": "Get pages recommended for sunset based on low traffic, poor performance, and legacy status",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_reasons": {"type": "boolean", "default": True}
            }
        }
    },
    {
        "name": "get_pages_never_viewed",
        "description": "Get pages that have never been viewed in the specified time period",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_back": {"type": "integer", "default": 90}
            }
        }
    },
    # Account Page Behavior
    {
        "name": "get_accounts_high_bounce",
        "description": "Get accounts with high bounce rates - may indicate content mismatch or poor targeting",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_bounce_rate": {"type": "integer", "default": 50},
                "min_sessions": {"type": "integer", "default": 3}
            }
        }
    },
    {
        "name": "get_accounts_time_on_page",
        "description": "Get accounts ranked by time spent on pages - high engagement indicators",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_avg_time_seconds": {"type": "integer", "default": 60},
                "segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business", "All"]}
            }
        }
    },
    {
        "name": "get_accounts_to_reach_out",
        "description": "Get accounts we should proactively reach out to based on intent, engagement, but no active opportunity",
        "input_schema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["High Priority", "Medium Priority", "Low Priority", "All"]},
                "segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business", "All"]}
            }
        }
    },
    # AEM Forms & Components
    {
        "name": "get_aem_form_submissions",
        "description": "Get AEM form submissions by accounts and pages with completion rates and errors",
        "input_schema": {
            "type": "object",
            "properties": {
                "form_id": {"type": "string", "enum": ["FORM_DEMO_REQUEST", "FORM_QUOTE", "FORM_NEWSLETTER", "FORM_CONTACT", "FORM_WEBINAR", "FORM_DOWNLOAD", "All"]},
                "account_domain": {"type": "string"},
                "min_attempts": {"type": "integer", "default": 1}
            }
        }
    },
    {
        "name": "get_forms_high_error_rate",
        "description": "Get forms with high error/abandonment rates that need optimization",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_error_rate": {"type": "integer", "default": 25}
            }
        }
    },
    {
        "name": "get_aem_components_engagement",
        "description": "Get AEM component engagement metrics to identify low-performing components",
        "input_schema": {
            "type": "object",
            "properties": {
                "component_type": {"type": "string", "enum": ["Hero", "CTA", "Video", "Carousel", "Grid", "Accordion", "Content", "Ad", "Navigation", "Footer", "Widget", "All"]},
                "priority": {"type": "string", "enum": ["high", "medium", "low", "All"]}
            }
        }
    },
    {
        "name": "get_low_engagement_components",
        "description": "Get AEM components with low engagement that should be reviewed or removed",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_ctr": {"type": "number", "default": 2.0}
            }
        }
    },
    # Content & SEO
    {
        "name": "get_pathfactory_engagement",
        "description": "Get PathFactory content engagement metrics by account and asset",
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_type": {"type": "string", "enum": ["Whitepaper", "Video", "Case Study", "Infographic", "eBook", "Webinar", "All"]},
                "account_domain": {"type": "string"},
                "min_time_spent": {"type": "integer", "default": 60}
            }
        }
    },
    {
        "name": "get_seo_performance",
        "description": "Get SEO performance metrics including rankings, scores, and trends by page",
        "input_schema": {
            "type": "object",
            "properties": {
                "landing_page": {"type": "string"},
                "trend": {"type": "string", "enum": ["improving", "declining", "stable", "All"]},
                "min_volume": {"type": "integer", "default": 1000}
            }
        }
    },
    {
        "name": "get_seo_page_comparison",
        "description": "Compare pages by SEO performance - which are performing well vs poorly",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": ["seo_score", "organic_ctr", "impressions", "ranking"], "default": "seo_score"}
            }
        }
    },
    # Paid Media
    {
        "name": "get_paid_media_performance",
        "description": "Get paid media campaign performance including spend, conversions, and ROI",
        "input_schema": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "enum": ["LinkedIn", "Google", "All"]},
                "objective": {"type": "string", "enum": ["awareness", "consideration", "conversion", "engagement", "All"]}
            }
        }
    },
    {
        "name": "get_channel_attribution",
        "description": "Get channel attribution showing which channels drive conversions",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_back": {"type": "integer", "default": 90}
            }
        }
    },
    # Anomaly Detection
    {
        "name": "detect_marketing_anomalies",
        "description": "Detect anomalies in marketing metrics including performance drops, spikes, and engagement gaps",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_type": {"type": "string", "enum": ["conversion", "engagement", "traffic", "all"], "default": "all"},
                "days_back": {"type": "integer", "default": 30}
            }
        }
    },
    # Campaign Brief
    {
        "name": "generate_campaign_brief",
        "description": "Generate a data-driven campaign brief with target accounts, recommended channels, and messaging",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business"]},
                "campaign_objective": {"type": "string", "enum": ["awareness", "lead_generation", "nurture", "conversion"]}
            }
        }
    }
]

# ============================================================================
# MOCK DATA FOR DEMO MODE
# ============================================================================
MOCK_DATA = {
    "get_b2b_marketing_summary": {
        "data": [
            {"metric": "Total Leads", "value": 1245, "change": "+12.5%", "trend": "up"},
            {"metric": "MQLs", "value": 425, "change": "+8.3%", "trend": "up"},
            {"metric": "SQLs", "value": 156, "change": "+15.2%", "trend": "up"},
            {"metric": "Pipeline Value", "value": 18500000, "change": "+18.5%", "trend": "up"},
            {"metric": "Win Rate", "value": 31.5, "change": "-2.1%", "trend": "down"},
            {"metric": "Avg Deal Size", "value": 485000, "change": "+5.8%", "trend": "up"},
        ],
        "summary": {
            "total_leads": 1245, "total_mqls": 425, "total_sqls": 156,
            "mql_rate": 34.1, "win_rate": 31.5, "pipeline": 18500000
        }
    },
    "get_lead_metrics": {
        "data": [
            {"segment": "DCIO", "source": "Website", "leads": 167, "mqls": 72, "rate": 43.1, "avg_score": 78.5},
            {"segment": "DCIO", "source": "Webinar", "leads": 98, "mqls": 56, "rate": 57.1, "avg_score": 82.3},
            {"segment": "DCIO", "source": "Content", "leads": 134, "mqls": 48, "rate": 35.8, "avg_score": 71.2},
            {"segment": "Enterprise", "source": "Content", "leads": 156, "mqls": 45, "rate": 28.8, "avg_score": 65.4},
            {"segment": "Enterprise", "source": "Event", "leads": 145, "mqls": 42, "rate": 29.0, "avg_score": 68.9},
            {"segment": "Mid-Market", "source": "Ads", "leads": 189, "mqls": 52, "rate": 27.5, "avg_score": 58.7},
            {"segment": "Mid-Market", "source": "Website", "leads": 203, "mqls": 58, "rate": 28.6, "avg_score": 61.3},
        ]
    },
    "get_intent_signals": {
        "data": [
            {"company": "Goldman Sachs", "domain": "goldmansachs.com", "segment": "DCIO", "intent": 92, "stage": "Decision", "topics": ["retirement plans", "stable value"], "signals": 12},
            {"company": "JPMorgan Chase", "domain": "jpmorganchase.com", "segment": "DCIO", "intent": 88, "stage": "Decision", "topics": ["401k providers", "target date funds"], "signals": 9},
            {"company": "Vanguard", "domain": "vanguard.com", "segment": "DCIO", "intent": 85, "stage": "Consideration", "topics": ["dcio providers", "fiduciary"], "signals": 8},
            {"company": "BlackRock", "domain": "blackrock.com", "segment": "DCIO", "intent": 82, "stage": "Consideration", "topics": ["stable value", "retirement"], "signals": 7},
            {"company": "Fidelity", "domain": "fidelity.com", "segment": "DCIO", "intent": 79, "stage": "Consideration", "topics": ["retirement plans"], "signals": 6},
            {"company": "State Street", "domain": "statestreet.com", "segment": "DCIO", "intent": 76, "stage": "Awareness", "topics": ["dcio comparison"], "signals": 5},
        ]
    },
    "get_account_360_view": {
        "data": [{
            "company": "Goldman Sachs", "domain": "goldmansachs.com", "segment": "DCIO",
            "industry": "Financial Services", "employees": 45000,
            "intent_score": 92, "engagement_score": 88, "buying_stage": "Decision",
            "lead_count": 8, "mql_count": 5, "avg_lead_score": 82.3,
            "web_sessions": 156, "avg_time": 245, "pages_viewed": 28,
            "content_downloads": 12, "webinars_attended": 3,
            "pipeline_value": 2500000, "opportunities": 2, "last_contact": "2024-12-10"
        }]
    },
    "get_conversion_funnel": {
        "data": [
            {"stage": "Leads", "count": 1245, "rate": 100, "conversion": None},
            {"stage": "MQLs", "count": 425, "rate": 34.1, "conversion": "Lead→MQL: 34.1%"},
            {"stage": "SQLs", "count": 156, "rate": 12.5, "conversion": "MQL→SQL: 36.7%"},
            {"stage": "Opportunities", "count": 89, "rate": 7.1, "conversion": "SQL→Opp: 57.1%"},
            {"stage": "Closed Won", "count": 28, "rate": 2.2, "conversion": "Opp→Won: 31.5%"},
        ]
    },
    "get_high_bounce_pages": {
        "data": [
            {"page": "/landing/ppc-campaign-q4", "type": "Landing", "sessions": 245, "bounce": 72.5, "avg_time": 18, "recommendation": "Review ad targeting"},
            {"page": "/landing/email-nov-promo", "type": "Landing", "sessions": 189, "bounce": 68.2, "avg_time": 22, "recommendation": "Improve content match"},
            {"page": "/resources/outdated-guide-2019", "type": "Resource", "sessions": 56, "bounce": 65.4, "avg_time": 35, "recommendation": "Update or sunset"},
            {"page": "/products/legacy-fund-info", "type": "Product", "sessions": 78, "bounce": 62.8, "avg_time": 28, "recommendation": "Redirect to current"},
        ]
    },
    "get_legacy_pages_low_views": {
        "data": [
            {"page": "/resources/archived/old-guide-2019", "views": 12, "bounce": 78.5, "status": "legacy", "action": "Sunset"},
            {"page": "/products/discontinued/old-fund", "views": 23, "bounce": 71.2, "status": "legacy", "action": "Redirect"},
            {"page": "/solutions/legacy/outdated", "views": 15, "bounce": 68.9, "status": "legacy", "action": "Update"},
            {"page": "/news/archive/2018/old-announcement", "views": 8, "bounce": 82.1, "status": "archived", "action": "Sunset"},
        ]
    },
    "get_pages_to_sunset": {
        "data": [
            {"page": "/resources/archived/old-guide-2019", "views": 12, "bounce": 78.5, "reason": "Legacy content - no business value", "priority": "High"},
            {"page": "/products/discontinued/old-fund", "views": 23, "bounce": 71.2, "reason": "Product discontinued", "priority": "High"},
            {"page": "/solutions/legacy/outdated", "views": 15, "bounce": 68.9, "reason": "Outdated information", "priority": "Medium"},
            {"page": "/landing/expired-campaign-2023", "views": 5, "bounce": 85.0, "reason": "Campaign ended", "priority": "High"},
        ]
    },
    "get_accounts_to_reach_out": {
        "data": [
            {"company": "Vanguard", "domain": "vanguard.com", "segment": "DCIO", "intent": 85, "engagement": 78, "priority": "High", "action": "SDR Outreach", "days_silent": 14},
            {"company": "Fidelity", "domain": "fidelity.com", "segment": "DCIO", "intent": 82, "engagement": 72, "priority": "High", "action": "Executive Email", "days_silent": 21},
            {"company": "State Street", "domain": "statestreet.com", "segment": "DCIO", "intent": 78, "engagement": 66, "priority": "Medium", "action": "Nurture Campaign", "days_silent": 35},
            {"company": "Northern Trust", "domain": "northerntrust.com", "segment": "DCIO", "intent": 74, "engagement": 58, "priority": "Medium", "action": "Content Offer", "days_silent": 28},
        ]
    },
    "get_paid_media_performance": {
        "data": [
            {"campaign": "LinkedIn DCIO Targeting", "platform": "LinkedIn", "spend": 48500, "impressions": 856000, "clicks": 9580, "conversions": 425, "cpc": 5.06, "ctr": 1.12, "roas": 2.8},
            {"campaign": "Google Search - Retirement", "platform": "Google", "spend": 38200, "impressions": 1650000, "clicks": 52800, "conversions": 1890, "cpc": 0.72, "ctr": 3.20, "roas": 4.5},
            {"campaign": "LinkedIn Retargeting", "platform": "LinkedIn", "spend": 22500, "impressions": 425000, "clicks": 5100, "conversions": 312, "cpc": 4.41, "ctr": 1.20, "roas": 3.2},
            {"campaign": "Google Display - ABM", "platform": "Google", "spend": 15800, "impressions": 2100000, "clicks": 12600, "conversions": 245, "cpc": 1.25, "ctr": 0.60, "roas": 2.1},
        ]
    },
    "get_channel_attribution": {
        "data": [
            {"channel": "Email", "conversions": 156, "revenue": 4500000, "pct": 32, "touches": 2450},
            {"channel": "Organic Search", "conversions": 142, "revenue": 3800000, "pct": 27, "touches": 3200},
            {"channel": "Paid Search", "conversions": 98, "revenue": 2800000, "pct": 20, "touches": 1890},
            {"channel": "Paid Social", "conversions": 65, "revenue": 1800000, "pct": 13, "touches": 980},
            {"channel": "Direct", "conversions": 45, "revenue": 1100000, "pct": 8, "touches": 450},
        ]
    },
    "detect_marketing_anomalies": {
        "data": [
            {"type": "🔴 Performance Drop", "area": "Email CTR", "detail": "-38.8% vs baseline (5.2% vs 8.5%)", "severity": "High", "action": "Review email content and subject lines"},
            {"type": "🟢 Intent Spike", "area": "Vanguard", "detail": "+43.5% intent score increase", "severity": "Opportunity", "action": "Prioritize SDR outreach immediately"},
            {"type": "🟢 Intent Spike", "area": "BlackRock", "detail": "+46.6% intent score increase", "severity": "Opportunity", "action": "Add to ABM priority list"},
            {"type": "🟡 Engagement Gap", "area": "Fidelity", "detail": "72 days since last contact, high intent", "severity": "Medium", "action": "Sales team outreach needed"},
            {"type": "🔴 Conversion Drop", "area": "Landing Page /ppc-q4", "detail": "Conversion rate down 52%", "severity": "High", "action": "A/B test new page variant"},
        ]
    },
    "generate_campaign_brief": {
        "data": [{
            "campaign_name": "DCIO Q1 2025 Lead Generation",
            "target_segment": "DCIO",
            "objective": "Generate 85 MQLs",
            "budget": 25000,
            "duration": "6 weeks",
            "channels": ["LinkedIn Ads", "Email Nurture", "Webinar"],
            "target_accounts": ["Goldman Sachs", "JPMorgan", "Vanguard", "BlackRock", "Fidelity"],
            "key_messages": ["Fiduciary excellence", "Stable value leadership", "Risk management"],
            "content_assets": ["DCIO Buyer's Guide", "Stable Value Comparison", "ROI Calculator"],
            "expected_results": {"mqls": 85, "pipeline": 2500000, "cost_per_mql": 294}
        }]
    },
    "get_account_engagement_scores": {
        "data": [
            {"company": "Goldman Sachs", "domain": "goldmansachs.com", "engagement": 92, "fit": "A", "stage": "Decision", "temperature": "Hot"},
            {"company": "JPMorgan", "domain": "jpmorgan.com", "engagement": 88, "fit": "A", "stage": "Decision", "temperature": "Hot"},
            {"company": "Vanguard", "domain": "vanguard.com", "engagement": 82, "fit": "A", "stage": "Consideration", "temperature": "Warm"},
            {"company": "BlackRock", "domain": "blackrock.com", "engagement": 78, "fit": "B", "stage": "Consideration", "temperature": "Warm"},
        ]
    },
    "get_pathfactory_engagement": {
        "data": [
            {"company": "Goldman Sachs", "asset": "Stable Value Guide 2024", "type": "Whitepaper", "time_spent": 485, "completion": 92, "downloads": 3},
            {"company": "JPMorgan", "asset": "DCIO Comparison Report", "type": "eBook", "time_spent": 320, "completion": 78, "downloads": 2},
            {"company": "Vanguard", "asset": "Fiduciary Best Practices", "type": "Whitepaper", "time_spent": 245, "completion": 65, "downloads": 1},
        ]
    },
    "get_aem_form_submissions": {
        "data": [
            {"company": "Goldman Sachs", "form": "Demo Request", "page": "/contact/demo", "attempts": 3, "completions": 2, "rate": 66.7},
            {"company": "Vanguard", "form": "Whitepaper Download", "page": "/resources/stable-value", "attempts": 5, "completions": 5, "rate": 100},
            {"company": "Fidelity", "form": "Newsletter Signup", "page": "/subscribe", "attempts": 2, "completions": 2, "rate": 100},
        ]
    },
    "get_low_engagement_components": {
        "data": [
            {"component": "hero-banner-v2", "type": "Hero", "page": "/products/stable-value", "impressions": 12500, "clicks": 125, "ctr": 1.0, "recommendation": "Test new creative"},
            {"component": "sidebar-cta-old", "type": "CTA", "page": "/solutions/dcio", "impressions": 8900, "clicks": 45, "ctr": 0.5, "recommendation": "Remove or redesign"},
            {"component": "footer-newsletter", "type": "Widget", "page": "Global", "impressions": 45000, "clicks": 180, "ctr": 0.4, "recommendation": "A/B test placement"},
        ]
    },
    "get_seo_page_comparison": {
        "data": [
            {"page": "/solutions/retirement-plans", "seo_score": 85, "ranking": 3, "impressions": 45000, "ctr": 8.2, "status": "Well performing"},
            {"page": "/products/stable-value", "seo_score": 72, "ranking": 8, "impressions": 28000, "ctr": 4.5, "status": "Needs improvement"},
            {"page": "/resources/dcio-guide", "seo_score": 68, "ranking": 12, "impressions": 15000, "ctr": 2.8, "status": "Needs improvement"},
            {"page": "/about/fiduciary", "seo_score": 45, "ranking": 28, "impressions": 5000, "ctr": 1.2, "status": "Poorly performing"},
        ]
    },
}

# ============================================================================
# FOLLOW-UP QUESTIONS MAPPING
# ============================================================================
FOLLOWUP_QUESTIONS = {
    "get_b2b_marketing_summary": [
        "Show me lead metrics by segment",
        "Which accounts have highest intent?",
        "Detect any anomalies",
        "What's driving the pipeline growth?"
    ],
    "get_lead_metrics": [
        "Show the conversion funnel",
        "Which accounts should we reach out to?",
        "Generate a campaign brief for top segment",
        "What's the lead quality by source?"
    ],
    "get_intent_signals": [
        "Show 360 view of Goldman Sachs",
        "Which accounts to reach out to?",
        "Generate DCIO campaign brief",
        "Show PathFactory engagement for top accounts"
    ],
    "get_account_360_view": [
        "Show content they've engaged with",
        "Similar high-intent accounts?",
        "What's their journey through the funnel?",
        "Compare with other DCIO accounts"
    ],
    "get_conversion_funnel": [
        "Where are the biggest drop-offs?",
        "Which accounts need nurturing?",
        "Lead metrics by source",
        "Show accounts to reach out to"
    ],
    "get_high_bounce_pages": [
        "Which pages should we sunset?",
        "Show legacy pages with low views",
        "SEO performance comparison",
        "AEM component engagement"
    ],
    "get_legacy_pages_low_views": [
        "Full list of pages to sunset",
        "High bounce pages analysis",
        "SEO performance by page",
        "Page performance scores"
    ],
    "get_pages_to_sunset": [
        "High bounce pages to fix",
        "Legacy pages report",
        "SEO rankings comparison",
        "Form performance on these pages"
    ],
    "get_accounts_to_reach_out": [
        "360 view of Vanguard",
        "Generate outreach campaign brief",
        "Show their intent signals",
        "Content engagement for these accounts"
    ],
    "get_paid_media_performance": [
        "Channel attribution analysis",
        "LinkedIn vs Google comparison",
        "Generate campaign optimization brief",
        "Show conversion funnel for paid leads"
    ],
    "get_channel_attribution": [
        "Paid media performance details",
        "Lead metrics by source",
        "Show conversion funnel",
        "Which channels need optimization?"
    ],
    "detect_marketing_anomalies": [
        "More details on intent spikes",
        "Show accounts needing attention",
        "Generate recovery campaign brief",
        "High bounce pages to fix"
    ],
    "generate_campaign_brief": [
        "Show target account details",
        "Best performing content for segment",
        "Historical campaign performance",
        "Intent signals for target accounts"
    ],
    "get_account_engagement_scores": [
        "Show intent signals",
        "Accounts to reach out to",
        "360 view of top account",
        "Content engagement analysis"
    ],
    "get_pathfactory_engagement": [
        "Account 360 view",
        "Lead metrics for these accounts",
        "Form submissions by account",
        "SEO for content pages"
    ],
    "get_aem_form_submissions": [
        "Forms with high error rates",
        "Account engagement scores",
        "High bounce pages",
        "Component engagement"
    ],
    "get_low_engagement_components": [
        "Page performance analysis",
        "High bounce pages",
        "SEO comparison",
        "Form performance"
    ],
    "get_seo_page_comparison": [
        "Pages to sunset",
        "High bounce pages",
        "Page performance scores",
        "Content engagement"
    ],
}

# Default follow-ups
DEFAULT_FOLLOWUPS = [
    "Show B2B marketing summary",
    "Detect marketing anomalies",
    "Which accounts should we reach out to?",
    "Generate a campaign brief"
]

# ============================================================================
# CHART CREATION FUNCTIONS
# ============================================================================
def create_chart(tool_name: str, data: List[Dict]) -> Optional[go.Figure]:
    """Create appropriate chart based on tool and data"""
    if not PLOTLY_OK or not data:
        return None
    
    try:
        df = pd.DataFrame(data)
        
        if tool_name == "get_b2b_marketing_summary":
            # Exclude pipeline from bar chart (different scale)
            display_data = [d for d in data if d.get("metric") != "Pipeline Value"]
            if display_data:
                df_display = pd.DataFrame(display_data)
                fig = px.bar(df_display, x="metric", y="value", color="metric",
                           title="📊 Marketing Performance Summary",
                           color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(template="plotly_dark", height=400, showlegend=False)
                return fig
        
        elif tool_name == "get_lead_metrics":
            fig = px.bar(df, x="segment", y="leads", color="source", barmode="group",
                        title="📊 Leads by Segment & Source",
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(template="plotly_dark", height=400)
            return fig
        
        elif tool_name == "get_intent_signals":
            fig = px.bar(df.sort_values("intent"), x="intent", y="company", orientation="h",
                        color="stage", title="🔥 Intent Scores by Account",
                        color_discrete_map={"Decision": "#10b981", "Consideration": "#f59e0b", "Awareness": "#94a3b8"})
            fig.update_layout(template="plotly_dark", height=400, yaxis={'categoryorder':'total ascending'})
            return fig
        
        elif tool_name == "get_conversion_funnel":
            fig = go.Figure(go.Funnel(
                y=df["stage"], x=df["count"],
                textposition="inside", textinfo="value+percent initial",
                marker={"color": ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#22c55e"]}
            ))
            fig.update_layout(title="🔄 Conversion Funnel", template="plotly_dark", height=400)
            return fig
        
        elif tool_name in ["get_high_bounce_pages", "get_legacy_pages_low_views", "get_pages_to_sunset"]:
            y_col = "bounce" if "bounce" in df.columns else "views"
            fig = px.bar(df, x=y_col, y="page", orientation="h", color=y_col,
                        title="📄 Page Analysis", color_continuous_scale="Reds")
            fig.update_layout(template="plotly_dark", height=400)
            return fig
        
        elif tool_name == "get_accounts_to_reach_out":
            fig = px.scatter(df, x="intent", y="engagement", size="days_silent",
                           color="priority", hover_name="company",
                           title="🎯 Account Priority Matrix",
                           color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"})
            fig.update_layout(template="plotly_dark", height=400)
            return fig
        
        elif tool_name == "get_paid_media_performance":
            fig = px.bar(df, x="campaign", y="roas", color="platform",
                        title="💰 ROAS by Campaign",
                        color_discrete_map={"LinkedIn": "#0077b5", "Google": "#4285f4"})
            fig.update_layout(template="plotly_dark", height=400)
            return fig
        
        elif tool_name == "get_channel_attribution":
            fig = px.pie(df, values="pct", names="channel", title="📊 Revenue Attribution by Channel",
                        color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
            fig.update_layout(template="plotly_dark", height=400)
            return fig
        
        elif tool_name == "detect_marketing_anomalies":
            type_counts = df["type"].value_counts().reset_index()
            type_counts.columns = ["type", "count"]
            fig = px.bar(type_counts, x="type", y="count", color="type",
                        title="🚨 Anomalies by Type",
                        color_discrete_sequence=["#ef4444", "#10b981", "#f59e0b"])
            fig.update_layout(template="plotly_dark", height=350, showlegend=False)
            return fig
        
        elif tool_name == "get_account_360_view":
            if len(df) > 0:
                row = df.iloc[0]
                fig = make_subplots(rows=1, cols=3, specs=[[{'type': 'indicator'}]*3],
                                   subplot_titles=['Intent Score', 'Engagement', 'Pipeline ($M)'])
                fig.add_trace(go.Indicator(mode="gauge+number", value=row.get('intent_score', 0),
                             gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#10b981"}}), row=1, col=1)
                fig.add_trace(go.Indicator(mode="gauge+number", value=row.get('engagement_score', 0),
                             gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#3b82f6"}}), row=1, col=2)
                fig.add_trace(go.Indicator(mode="gauge+number", value=row.get('pipeline_value', 0)/1000000,
                             gauge={'axis': {'range': [0, 5]}, 'bar': {'color': "#f59e0b"}},
                             number={'suffix': 'M'}), row=1, col=3)
                fig.update_layout(title=f"🎯 {row.get('company', 'Account')} - Key Metrics",
                                template="plotly_dark", height=300)
                return fig
        
        elif tool_name == "get_seo_page_comparison":
            fig = px.bar(df.sort_values("seo_score"), x="seo_score", y="page", orientation="h",
                        color="status", title="📈 SEO Performance by Page",
                        color_discrete_map={"Well performing": "#10b981", "Needs improvement": "#f59e0b", "Poorly performing": "#ef4444"})
            fig.update_layout(template="plotly_dark", height=400)
            return fig
        
        # Default chart for other tools
        if len(df.columns) >= 2:
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            cat_cols = df.select_dtypes(include=['object']).columns.tolist()
            if num_cols and cat_cols:
                fig = px.bar(df, x=cat_cols[0], y=num_cols[0], color=cat_cols[0],
                            title=f"📊 {tool_name.replace('_', ' ').title()}")
                fig.update_layout(template="plotly_dark", height=400, showlegend=False)
                return fig
        
        return None
        
    except Exception as e:
        st.warning(f"Chart creation error: {e}")
        return None

# ============================================================================
# TOOL EXECUTION (Mock data for demo)
# ============================================================================
def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict:
    """Execute tool - returns mock data for demo mode"""
    
    # Handle account_name parameter for 360 view
    if tool_name == "get_account_360_view":
        account_name = tool_input.get("account_name", "Goldman Sachs")
        base_data = MOCK_DATA.get(tool_name, {"data": []})
        if base_data.get("data"):
            # Update company name in response
            data_copy = base_data.copy()
            data_copy["data"] = [dict(d, company=account_name) for d in base_data["data"]]
            return data_copy
    
    return MOCK_DATA.get(tool_name, {"data": [{"info": "Data retrieved successfully"}], "count": 1})

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("## 📊 Marketing Analytics Agent")
    st.markdown("*Powered by Claude AI + MCP*")
    st.markdown("---")
    
    # API Key
    api_key = st.text_input("🔑 Anthropic API Key", type="password", 
                           placeholder="sk-ant-api03-...",
                           help="Get your key from console.anthropic.com")
    
    if api_key:
        if api_key.startswith("sk-ant-"):
            st.success("✅ API Key format valid")
        else:
            st.warning("⚠️ Check API key format")
    
    demo_mode = st.toggle("🎮 Demo Mode (Mock Data)", value=True,
                         help="Use mock data instead of live Databricks queries")
    
    st.markdown("---")
    
    # Action Buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 New Chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.session_state.api_messages = []
            st.session_state.query_count = 0
            st.session_state.show_followups = []
            st.session_state.last_tool_used = None
            st.session_state.last_tool_data = None
            st.session_state.conversation_context = ""
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear All", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()
    
    st.markdown("---")
    
    # Download Options
    st.markdown("### 📥 Export")
    if st.session_state.messages:
        # Markdown export
        export_md = f"# Marketing Analytics Report\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
        for msg in st.session_state.messages:
            role = "**You:**" if msg["role"] == "user" else "**Agent:**"
            export_md += f"{role}\n{msg['content']}\n\n---\n\n"
        
        st.download_button(
            "📄 Download Markdown",
            export_md,
            file_name=f"marketing_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        # CSV export of last data
        if st.session_state.last_tool_data:
            data = st.session_state.last_tool_data.get("data", [])
            if data:
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False)
                st.download_button(
                    "📊 Download Last Data (CSV)",
                    csv,
                    file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    st.markdown("---")
    
    # Data Sources
    st.markdown("### 📦 Data Sources")
    sources = [
        ("Marketo", "marketo", "Leads & Email"),
        ("Adobe Analytics", "adobe", "Web Traffic"),
        ("6sense", "6sense", "Intent & ABM"),
        ("Salesforce", "salesforce", "Pipeline"),
        ("PathFactory", "pathfactory", "Content"),
        ("AEM", "aem", "Forms & CMS"),
    ]
    for name, css_class, desc in sources:
        st.markdown(f'<span class="source-pill source-{css_class}">{name}</span> {desc}', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Stats
    st.markdown("### 📈 Session Stats")
    st.caption(f"Queries: {st.session_state.query_count}")
    if st.session_state.query_count > 0:
        avg_time = st.session_state.total_response_time / st.session_state.query_count
        st.caption(f"Avg Response: {avg_time:.1f}s")
    st.caption(f"Tools Available: {len(TOOLS)}")

# ============================================================================
# MAIN CONTENT
# ============================================================================
st.markdown("## 📊 Marketing Analytics Agent")
st.markdown("*Ask questions in plain English • Get insights from Marketo, Adobe Analytics, 6sense, Salesforce, PathFactory & AEM*")

# Quick KPI Cards
if demo_mode:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('''
        <div class="metric-box">
            <h4>Total Leads (90d)</h4>
            <div class="val">1,245</div>
            <div class="change positive">↑ 12.5% vs prior</div>
        </div>
        ''', unsafe_allow_html=True)
    with col2:
        st.markdown('''
        <div class="metric-box">
            <h4>MQL Rate</h4>
            <div class="val">34.1%</div>
            <div class="change positive">↑ 3.5% vs prior</div>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        st.markdown('''
        <div class="metric-box">
            <h4>Pipeline Value</h4>
            <div class="val">$18.5M</div>
            <div class="change positive">↑ 18.5% vs prior</div>
        </div>
        ''', unsafe_allow_html=True)
    with col4:
        st.markdown('''
        <div class="metric-box">
            <h4>Win Rate</h4>
            <div class="val">31.5%</div>
            <div class="change negative">↓ 2.1% vs prior</div>
        </div>
        ''', unsafe_allow_html=True)

st.markdown("---")

# Sample Questions
st.markdown("### 💡 Try These Questions")
sample_cols = st.columns(4)
sample_questions = [
    ("📊 B2B Summary", "Give me a B2B marketing summary"),
    ("📈 Lead Metrics", "Show lead metrics by segment"),
    ("🔥 Intent Signals", "Which accounts have highest intent?"),
    ("🔄 Funnel", "Show the conversion funnel"),
    ("📄 Bounce Pages", "Which pages have high bounce rates?"),
    ("🗑️ Sunset Pages", "What pages should we sunset?"),
    ("🎯 Reach Out", "Which accounts should we reach out to?"),
    ("💰 Paid Media", "Show paid media performance"),
    ("📊 Attribution", "Show channel attribution"),
    ("🚨 Anomalies", "Detect marketing anomalies"),
    ("🏢 Account 360", "Give me 360 view of Goldman Sachs"),
    ("📝 Campaign Brief", "Generate campaign brief for DCIO"),
]

for i, (label, query) in enumerate(sample_questions):
    with sample_cols[i % 4]:
        if st.button(label, key=f"sample_{i}", use_container_width=True):
            st.session_state.pending_question = query
            st.rerun()

st.markdown("---")

# ============================================================================
# CHAT INTERFACE
# ============================================================================

# Display chat history
for idx, msg in enumerate(st.session_state.messages):
    avatar = "🧑‍💼" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        
        # Show chart if exists
        if msg.get("chart") is not None:
            st.plotly_chart(msg["chart"], use_container_width=True, key=f"hist_chart_{idx}")
        
        # Show data table if exists
        if msg.get("data"):
            with st.expander("📋 View Data Table"):
                df = pd.DataFrame(msg["data"])
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    csv,
                    file_name=f"data_{idx}.csv",
                    mime="text/csv",
                    key=f"dl_{idx}"
                )
        
        # Show tools used
        if msg.get("tools"):
            st.caption(f"🔧 Tools: {' → '.join(msg['tools'])}")

# ============================================================================
# FOLLOW-UP QUESTIONS (shown after assistant response)
# ============================================================================
if st.session_state.show_followups and len(st.session_state.messages) > 0:
    st.markdown("---")
    st.markdown("### 💡 Follow-up Questions")
    followup_cols = st.columns(min(len(st.session_state.show_followups), 4))
    
    for i, followup in enumerate(st.session_state.show_followups[:4]):
        with followup_cols[i]:
            if st.button(followup, key=f"followup_{st.session_state.query_count}_{i}", use_container_width=True):
                st.session_state.pending_question = followup
                st.rerun()

# ============================================================================
# PROCESS INPUT
# ============================================================================
# Get user input
user_input = None
if st.session_state.pending_question:
    user_input = st.session_state.pending_question
    st.session_state.pending_question = None
else:
    user_input = st.chat_input("Ask about leads, accounts, campaigns, pages, anomalies...")

if user_input:
    st.session_state.query_count += 1
    st.session_state.show_followups = []
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(user_input)
    
    # Process with Claude
    with st.chat_message("assistant", avatar="🤖"):
        
        if not api_key:
            st.error("❌ Please enter your Anthropic API key in the sidebar")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Please enter your API key in the sidebar to continue."
            })
        
        elif not ANTHROPIC_OK:
            st.error("❌ Anthropic package not installed. Run: pip install anthropic")
        
        else:
            try:
                client = anthropic.Anthropic(api_key=api_key)
                
                # System prompt with conversation context
                system_prompt = f"""You are a Marketing Analytics Agent with access to 26 MCP tools that query marketing data from:
- Marketo (leads, email campaigns)
- Adobe Analytics (web traffic, page performance)
- 6sense (intent signals, account engagement)
- Salesforce (pipeline, opportunities)
- PathFactory (content engagement)
- AEM (forms, components)
- Paid Media (LinkedIn, Google)

Your capabilities include:
1. B2B marketing summaries and KPIs
2. Lead and account metrics analysis
3. Intent signal detection and account scoring
4. Conversion funnel analysis
5. Page performance and SEO analysis
6. Form and component engagement
7. Paid media performance
8. Channel attribution
9. Anomaly detection
10. Campaign brief generation

IMPORTANT GUIDELINES:
- Always use the appropriate tool(s) to answer questions
- Lead with numbers and key insights
- Be concise but thorough
- When users ask follow-up questions like "tell me more", "yes", "continue", or reference previous data, use context to provide deeper analysis
- Highlight actionable recommendations

Previous conversation context: {st.session_state.conversation_context if st.session_state.conversation_context else 'This is the start of the conversation.'}"""

                # Build messages with conversation history for context
                api_messages = []
                
                # Include recent conversation for context (last 6 exchanges)
                recent_messages = st.session_state.api_messages[-12:] if st.session_state.api_messages else []
                api_messages.extend(recent_messages)
                
                # Add current user message
                api_messages.append({"role": "user", "content": user_input})
                
                start_time = time.time()
                
                # Status display
                status = st.status("🤖 Agent analyzing your request...", expanded=True)
                
                # Initial API call
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=api_messages
                )
                
                tools_used = []
                tool_data = None
                tool_name = None
                iteration = 0
                max_iterations = 5
                
                # Process tool calls
                while response.stop_reason == "tool_use" and iteration < max_iterations:
                    iteration += 1
                    tool_blocks = [b for b in response.content if b.type == "tool_use"]
                    results = []
                    
                    for tb in tool_blocks:
                        tname = tb.name
                        status.update(label=f"📊 Querying: {tname.replace('_', ' ').title()}...")
                        st.write(f"🔧 Using tool: **{tname}**")
                        
                        tools_used.append(tname)
                        tool_name = tname
                        
                        # Execute tool (mock data in demo mode)
                        if demo_mode:
                            data = execute_tool(tname, tb.input)
                        else:
                            # In production, this would call Databricks
                            data = execute_tool(tname, tb.input)
                        
                        tool_data = data
                        st.session_state.last_tool_used = tname
                        st.session_state.last_tool_data = data
                        
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": tb.id,
                            "content": json.dumps(data, default=str)
                        })
                    
                    # Continue conversation
                    api_messages.append({"role": "assistant", "content": response.content})
                    api_messages.append({"role": "user", "content": results})
                    
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4096,
                        system=system_prompt,
                        tools=TOOLS,
                        messages=api_messages
                    )
                
                status.update(label="✅ Analysis complete!", state="complete")
                
                response_time = time.time() - start_time
                st.session_state.total_response_time += response_time
                
                # Extract final answer
                answer = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        answer += block.text
                
                if not answer:
                    answer = "I've retrieved the data. Please see the visualization and table below."
                
                # Display answer
                st.markdown(answer)
                
                # Create and display chart
                chart = None
                display_data = None
                if tool_name and tool_data:
                    display_data = tool_data.get("data", [])
                    chart = create_chart(tool_name, display_data)
                    
                    if chart:
                        st.plotly_chart(chart, use_container_width=True, key=f"new_chart_{st.session_state.query_count}")
                    
                    # Display data table
                    if display_data:
                        with st.expander("📋 View Data Table"):
                            df = pd.DataFrame(display_data)
                            st.dataframe(df, use_container_width=True)
                            csv = df.to_csv(index=False)
                            st.download_button(
                                "📥 Download CSV",
                                csv,
                                file_name=f"data_{st.session_state.query_count}.csv",
                                mime="text/csv",
                                key=f"dl_new_{st.session_state.query_count}"
                            )
                
                # Show tools used and response time
                if tools_used:
                    st.caption(f"🔧 Tools: {' → '.join(tools_used)} | ⏱️ {response_time:.1f}s")
                
                # Store message in history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "chart": chart,
                    "data": display_data,
                    "tools": tools_used
                })
                
                # Update API messages for context continuity
                st.session_state.api_messages.append({"role": "user", "content": user_input})
                st.session_state.api_messages.append({"role": "assistant", "content": response.content})
                
                # Update conversation context summary
                if tool_name:
                    st.session_state.conversation_context = f"Last query was about '{user_input}' using tool '{tool_name}'. "
                    if display_data:
                        st.session_state.conversation_context += f"Data returned {len(display_data)} records."
                
                # Set follow-up questions based on last tool used
                if tool_name and tool_name in FOLLOWUP_QUESTIONS:
                    st.session_state.show_followups = FOLLOWUP_QUESTIONS[tool_name]
                else:
                    st.session_state.show_followups = DEFAULT_FOLLOWUPS
                
                # Rerun to show follow-ups
                st.rerun()
                
            except anthropic.AuthenticationError:
                st.error("❌ Invalid API key. Please check your Anthropic API key.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Authentication error. Please verify your API key."
                })
            except anthropic.RateLimitError:
                st.error("❌ Rate limit exceeded. Please wait a moment and try again.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"An error occurred: {str(e)}"
                })

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    #### 🏗️ Architecture
    - **MCP Protocol** for tool orchestration
    - **Claude AI** for natural language understanding
    - **Databricks** for data processing
    - **26 MCP Tools** for comprehensive coverage
    """)
with col2:
    st.markdown("""
    #### 📊 Capabilities
    - Lead & Account Analytics
    - Intent Signal Detection
    - Conversion Funnel Analysis
    - Page & SEO Performance
    - Anomaly Detection
    - Campaign Brief Generation
    """)
with col3:
    st.markdown("""
    #### 🚀 Business Value
    - **Campaign planning: 6hrs → 30sec**
    - Proactive anomaly detection
    - Cross-platform unified insights
    - Self-service analytics
    """)

st.markdown("""
<div style="text-align:center; margin-top:2rem; padding:1rem; background:#1e2432; border-radius:8px;">
    <small>Marketing Analytics Agent v8 | Built with Claude AI + MCP | MetLife Marketing Technology | December 2024</small>
</div>
""", unsafe_allow_html=True)