import streamlit as st
import boto3
import json
from datetime import datetime
from agents import ProposalAgent, MarketAnalysisAgent, PresentationAgent
from utils import generate_pdf, generate_pptx

st.set_page_config(page_title="Business Proposal Generator", layout="wide")

# Initialize AWS Bedrock client
@st.cache_resource
def init_bedrock():
    return boto3.client('bedrock-runtime', region_name='us-east-1')

def main():
    st.title("🚀 AI Business Proposal Generator")
    
    bedrock = init_bedrock()
    
    # Initialize agents
    proposal_agent = ProposalAgent(bedrock)
    market_agent = MarketAnalysisAgent(bedrock)
    presentation_agent = PresentationAgent(bedrock)
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("Project Details")
        company_name = st.text_input("Company Name")
        project_title = st.text_input("Project Title")
        industry = st.selectbox("Industry", ["Technology", "Healthcare", "Finance", "Retail", "Manufacturing", "Other"])
        budget_range = st.selectbox("Budget Range", ["$10K-50K", "$50K-100K", "$100K-500K", "$500K+"])
        timeline = st.selectbox("Timeline", ["1-3 months", "3-6 months", "6-12 months", "12+ months"])
        description = st.text_area("Project Description", height=100)
    
    if st.button("Generate Business Proposal", type="primary"):
        if company_name and project_title and description:
            with st.spinner("AI agents are working on your proposal..."):
                
                # Market Analysis
                st.subheader("📊 Market Analysis")
                market_data = market_agent.analyze_market(industry, description)
                st.write(market_data)
                
                # Business Proposal
                st.subheader("📋 Business Proposal")
                proposal_data = proposal_agent.generate_proposal(
                    company_name, project_title, industry, budget_range, timeline, description
                )
                st.write(proposal_data)
                
                # Generate documents
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📄 Generate PDF Report"):
                        pdf_buffer = generate_pdf(proposal_data, market_data)
                        st.download_button(
                            "Download PDF",
                            pdf_buffer,
                            f"{project_title}_proposal.pdf",
                            "application/pdf"
                        )
                
                with col2:
                    if st.button("📊 Generate Presentation"):
                        pptx_buffer = generate_pptx(proposal_data, market_data)
                        st.download_button(
                            "Download PPTX",
                            pptx_buffer,
                            f"{project_title}_presentation.pptx",
                            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                        )
        else:
            st.error("Please fill in all required fields")

if __name__ == "__main__":
    main()