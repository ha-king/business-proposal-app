import json
import boto3
from typing import Dict, Any

class BaseAgent:
    def __init__(self, bedrock_client):
        self.bedrock = bedrock_client
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    def invoke_model(self, prompt: str) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self.bedrock.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        
        return json.loads(response['body'].read())['content'][0]['text']

class ProposalAgent(BaseAgent):
    def generate_proposal(self, company: str, title: str, industry: str, budget: str, timeline: str, description: str) -> str:
        prompt = f"""
        Create a comprehensive business proposal for:
        Company: {company}
        Project: {title}
        Industry: {industry}
        Budget: {budget}
        Timeline: {timeline}
        Description: {description}
        
        Include: Executive Summary, Objectives, Scope, Methodology, Timeline, Budget Breakdown, Team, Deliverables, Risk Assessment.
        Format as structured text with clear sections.
        """
        return self.invoke_model(prompt)

class MarketAnalysisAgent(BaseAgent):
    def analyze_market(self, industry: str, description: str) -> str:
        prompt = f"""
        Conduct market analysis for {industry} industry project: {description}
        
        Include: Market Size, Growth Trends, Key Players, Opportunities, Threats, Target Audience, Competitive Landscape.
        Provide data-driven insights and actionable recommendations.
        """
        return self.invoke_model(prompt)

class PresentationAgent(BaseAgent):
    def create_slide_content(self, proposal: str, market_analysis: str) -> Dict[str, Any]:
        prompt = f"""
        Create presentation slide content from this proposal and market analysis:
        
        PROPOSAL: {proposal}
        MARKET ANALYSIS: {market_analysis}
        
        Return JSON with slides array, each slide having 'title' and 'content' fields.
        Create 8-10 slides covering key points.
        """
        response = self.invoke_model(prompt)
        try:
            return json.loads(response)
        except:
            return {"slides": [{"title": "Overview", "content": response}]}