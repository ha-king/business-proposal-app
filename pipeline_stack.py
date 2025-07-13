from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct
from config import Config

class BusinessProposalPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        prefix = f"{Config.STACK_NAME}Pipeline"

        # GitHub token secret
        github_token = secretsmanager.Secret.from_secret_name_v2(
            self, f"{prefix}GitHubToken",
            secret_name="github-token"
        )

        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()

        # CodeBuild project
        build_project = codebuild.Project(
            self, f"{prefix}Build",
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            )
        )

        # Add permissions for CDK deployment
        build_project.add_to_role_policy(iam.PolicyStatement(
            actions=["*"],
            resources=["*"]
        ))

        # Pipeline
        pipeline = codepipeline.Pipeline(
            self, f"{prefix}Pipeline",
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.GitHubSourceAction(
                            action_name="GitHub_Source",
                            owner="your-github-username",
                            repo="business-proposal-app",
                            branch="main",
                            oauth_token=github_token.secret_value,
                            output=source_output
                        )
                    ]
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[
                        codepipeline_actions.CodeBuildAction(
                            action_name="Build",
                            project=build_project,
                            input=source_output,
                            outputs=[build_output]
                        )
                    ]
                )
            ]
        )