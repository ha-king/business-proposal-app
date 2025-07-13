#!/usr/bin/env python3
import aws_cdk as cdk
from pipeline_stack import BusinessProposalPipelineStack

app = cdk.App()
BusinessProposalPipelineStack(app, "BusinessProposalPipelineStack")
app.synth()