# AI Business Proposal Generator

Multi-agent AI-powered web application using Streamlit and Amazon Bedrock for generating business proposals and market analysis reports.

## Features

- **Multi-Agent Architecture**: Specialized AI agents for different tasks
- **Business Proposal Generation**: Comprehensive proposals with executive summary, objectives, scope, methodology, timeline, budget breakdown
- **Market Analysis**: Industry analysis with market size, trends, competitors, opportunities
- **PDF Reports**: Professional PDF documents with formatted content
- **PowerPoint Presentations**: Slide decks for presentations
- **Interactive Web Interface**: User-friendly Streamlit interface

## Agents

1. **ProposalAgent**: Generates detailed business proposals
2. **MarketAnalysisAgent**: Conducts market research and analysis
3. **PresentationAgent**: Creates presentation content structure

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS credentials with Bedrock access

3. Run the application:
```bash
streamlit run app.py
```

## Usage

1. Enter project details in the sidebar
2. Click "Generate Business Proposal"
3. Review AI-generated content
4. Download PDF report or PowerPoint presentation

## AWS Services Used

- Amazon Bedrock (Claude 3 Sonnet)
- AWS IAM for permissions