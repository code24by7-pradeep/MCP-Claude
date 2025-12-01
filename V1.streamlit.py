"""
Streamlit UI for Claude MCP Analytics with Visualizations
Run with: streamlit run streamlit_analytics_ui.py
"""

import streamlit as st
import anthropic
import json
from typing import Any, Dict, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Streamlit page config
st.set_page_config(page_title="📊 Analytics Q&A", layout="wide", initial_sidebar_state="expanded")

# Sidebar for API key
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Claude API Key", type="password", help="Get from https://console.anthropic.com/account/keys")
    databricks_url = st.text_input("Databricks Workspace URL", placeholder="https://your-workspace.cloud.databricks.com")
    databricks_token = st.text_input("Databricks Token", type="password")

# Main title
st.title("📊 Claude Analytics Q&A System")
st.markdown("Ask questions about your marketing analytics data using Claude AI + MCP tools")

# Mock data function for demo
def get_mock_data(tool_name):
    """Generate realistic demo data for each tool"""
    mock_data = {
        "q1_pages_never_viewed": [
            {"page_url": "/pricing", "page_type": "Product", "views": 0},
            {"page_url": "/case-study-old", "page_type": "Resource", "views": 0},
            {"page_url": "/discontinued-feature", "page_type": "Product", "views": 0},
            {"page_url": "/legacy-blog", "page_type": "Resource", "views": 0},
        ],
        "q2_forms_high_error_rate": [
            {"form_id": "contact_form_v1", "attempts": 245, "completed": 45, "error_rate": 81.6},
            {"form_id": "newsletter_signup", "attempts": 1200, "completed": 850, "error_rate": 29.2},
            {"form_id": "demo_request", "attempts": 450, "completed": 320, "error_rate": 28.9},
        ],
        "q3_high_bounce_pages": [
            {"entry_page": "/blog/outdated-post", "bounce_rate": 78.5, "sessions": 150},
            {"entry_page": "/pricing-old", "bounce_rate": 72.3, "sessions": 230},
            {"entry_page": "/temp-campaign", "bounce_rate": 68.9, "sessions": 102},
        ],
        "q4_high_engagement_accounts": [
            {"company_name": "TechCorp Inc", "account_stage": "Consideration", "avg_score": 92.5, "signals": 18},
            {"company_name": "Enterprise Solutions", "account_stage": "Decision", "avg_score": 88.3, "signals": 15},
            {"company_name": "Growth Ventures", "account_stage": "Awareness", "avg_score": 85.2, "signals": 12},
        ],
        "q5_converted_accounts": [
            {"account_name": "Fortune 500 Corp", "deal_value": 250000, "entry_page": "/solutions/enterprise", "stage": "Closed Won"},
            {"account_name": "Tech Startup LLC", "deal_value": 45000, "entry_page": "/product-demo", "stage": "Closed Won"},
            {"account_name": "Industries Global", "deal_value": 120000, "entry_page": "/case-studies", "stage": "Closed Won"},
        ],
        "q6_paid_media_data": [
            {"campaign_name": "Q4 LinkedIn Campaign", "platform": "LinkedIn", "spend": 15000, "clicks": 2300, "conv_rate": 8.5},
            {"campaign_name": "Google Search - Enterprise", "platform": "Google", "spend": 22000, "clicks": 5600, "conv_rate": 12.3},
            {"campaign_name": "LinkedIn Retargeting", "platform": "LinkedIn", "spend": 8500, "clicks": 1200, "conv_rate": 15.2},
        ],
        "q7_account_conversion_tracking": [
            {"account_name": "Global Tech Enterprises", "amount": 500000, "sessions": 47},
            {"account_name": "Digital Innovation Corp", "amount": 275000, "sessions": 32},
            {"account_name": "Cloud Systems Inc", "amount": 180000, "sessions": 28},
        ],
        "q8_exit_pages": [
            {"page_url": "/pricing", "page_type": "Conversion", "exits": 450},
            {"page_url": "/solutions", "page_type": "Solution", "exits": 320},
            {"page_url": "/resources/whitepaper", "page_type": "Resource", "exits": 210},
        ],
    }
    return mock_data.get(tool_name, [{"status": "executed"}])

# Define tools
TOOLS = [
    {"name": "q1_pages_never_viewed", "description": "Pages with no views in past 90 days", "input_schema": {"type": "object", "properties": {"days_back": {"type": "integer", "default": 90}}, "required": []}},
    {"name": "q2_forms_high_error_rate", "description": "Forms with high error rates", "input_schema": {"type": "object", "properties": {"min_error_rate": {"type": "integer", "default": 25}}, "required": []}},
    {"name": "q3_high_bounce_pages", "description": "Pages with high bounce rates", "input_schema": {"type": "object", "properties": {"min_bounce_rate": {"type": "integer", "default": 50}, "min_sessions": {"type": "integer", "default": 100}}, "required": []}},
    {"name": "q4_high_engagement_accounts", "description": "Accounts with high engagement", "input_schema": {"type": "object", "properties": {"min_engagement_score": {"type": "integer", "default": 75}, "stage": {"type": "string", "enum": ["Awareness", "Consideration", "Decision"]}}, "required": []}},
    {"name": "q5_converted_accounts", "description": "Converted accounts and their paths", "input_schema": {"type": "object", "properties": {"segment": {"type": "string", "enum": ["DCIO", "Enterprise", "Mid-Market", "Small Business"]}, "min_deal_value": {"type": "integer", "default": 0}}, "required": []}},
    {"name": "q6_paid_media_data", "description": "Paid media performance", "input_schema": {"type": "object", "properties": {"platform": {"type": "string", "enum": ["LinkedIn", "Google"]}, "metric": {"type": "string", "enum": ["roi", "cpc", "conversion_rate"], "default": "roi"}}, "required": []}},
    {"name": "q7_account_conversion_tracking", "description": "Account conversion tracking", "input_schema": {"type": "object", "properties": {"top_n": {"type": "integer", "default": 5}}, "required": []}},
    {"name": "q8_exit_pages", "description": "Exit pages performance", "input_schema": {"type": "object", "properties": {"page_type": {"type": "string", "enum": ["Product", "Solution", "Resource", "Conversion", "Archived"]}}, "required": []}}
]

# Template questions
template_questions = [
    "Tell me the pages which never had page views in past 90 days?",
    "What forms have high number of form errors?",
    "Which pages have high bounce rates?",
    "What accounts have the highest engagement scores?",
    "Tell me about accounts that converted",
    "What is the performance of our paid media campaigns?",
    "Tell me the accounts which converted and their paths",
    "Tell me the exit pages and their performance"
]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(message["content"])
    else:
        with st.chat_message("assistant"):
            st.write(message["content"])

# Input area with columns
col1, col2 = st.columns([4, 1])

with col1:
    # Quick template buttons
    st.write("**Quick Questions:**")
    cols = st.columns(4)
    for idx, question in enumerate(template_questions):
        col = cols[idx % 4]
        if col.button(question[:30] + "...", key=f"btn_{idx}"):
            user_input = question
        else:
            user_input = None

    # Or free text input
    if not user_input:
        user_input = st.chat_input("Ask a question about your analytics data...")

with col2:
    st.write("")
    st.write("")
    if st.button("🔄 Clear", key="clear_btn"):
        st.session_state.messages = []
        st.rerun()

# Process user input
if user_input and api_key:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # Process with Claude
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            client = anthropic.Anthropic(api_key=api_key)
            
            # Build messages for Claude
            messages = [{"role": "user", "content": user_input}]
            
            # Call Claude with tools
            response = client.messages.create(
                model="claude-opus-4-1",
                max_tokens=4096,
                tools=TOOLS,
                messages=messages
            )
            
            # Handle tool use
            iteration = 0
            while response.stop_reason == "tool_use" and iteration < 5:
                iteration += 1
                tool_use = next((b for b in response.content if b.type == "tool_use"), None)
                if not tool_use:
                    break
                
                # Show tool being used
                with st.spinner(f"🔧 Querying: {tool_use.name}"):
                    # Simulate tool execution with realistic demo data
                    result = get_mock_data(tool_use.name)
                
                # Display the raw data/visualization
                st.write(f"**📊 Data from {tool_use.name}:**")
                if isinstance(result, list) and len(result) > 0:
                    df = pd.DataFrame(result)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.json(result)
                
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": json.dumps(result)}]})
                
                response = client.messages.create(
                    model="claude-opus-4-1",
                    max_tokens=4096,
                    tools=TOOLS,
                    messages=messages
                )
            
            # Extract final answer
            final_answer = next((b.text for b in response.content if hasattr(b, "text")), "No response")
            
            with message_placeholder.container():
                st.write(final_answer)
            
            # Add to history
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
            
        except Exception as e:
            st.error(f"Error: {str(e)}")

elif user_input and not api_key:
    st.warning("⚠️ Please enter your Claude API key in the sidebar")

# Footer
st.divider()
st.markdown("""
### 📝 About this system
- **8 MCP Tools** for analytics questions
- **Claude AI** for intelligent analysis
- **Databricks** for data querying
- **Real-time** responses

### 🚀 Next Steps
1. Enter your Claude API key (from https://console.anthropic.com/account/keys)
2. Ask a question or click a template
3. Get instant AI-powered insights
""")
