#!/usr/bin/env python3
import aws_cdk as cdk
from cdk_stack import BusinessProposalStack

app = cdk.App()
BusinessProposalStack(app, "BusinessProposalStack", env_name="prod")
app.synth()