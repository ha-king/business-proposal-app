from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_cognito as cognito,
    aws_secretsmanager as secretsmanager,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecr as ecr,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    SecretValue,
    CfnOutput,
)
from constructs import Construct
from config import Config

CUSTOM_HEADER_NAME = "X-Custom-Header"

class BusinessProposalStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, env_name: str = "prod", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        prefix = f"{Config.STACK_NAME}{env_name.title()}"

        # Cognito
        user_pool = cognito.UserPool(self, f"{prefix}UserPool")
        user_pool_client = cognito.UserPoolClient(self, f"{prefix}UserPoolClient",
                                                  user_pool=user_pool,
                                                  generate_secret=True)

        secret = secretsmanager.Secret(self, f"{prefix}ParamCognitoSecret",
                                       secret_object_value={
                                           "pool_id": SecretValue.unsafe_plain_text(user_pool.user_pool_id),
                                           "app_client_id": SecretValue.unsafe_plain_text(user_pool_client.user_pool_client_id),
                                           "app_client_secret": user_pool_client.user_pool_client_secret
                                       },
                                       secret_name=f"{Config.SECRETS_MANAGER_ID}-{env_name}")

        # VPC
        vpc = ec2.Vpc(self, f"{prefix}AppVpc", max_azs=2, nat_gateways=1)

        # Security Groups
        ecs_sg = ec2.SecurityGroup(self, f"{prefix}SecurityGroupECS", vpc=vpc)
        alb_sg = ec2.SecurityGroup(self, f"{prefix}SecurityGroupALB", vpc=vpc)
        ecs_sg.add_ingress_rule(peer=alb_sg, connection=ec2.Port.tcp(8501))

        # ECR Repository
        ecr_repo = ecr.Repository(self, f"{prefix}ECRRepo", repository_name=f"{Config.STACK_NAME.lower()}-app")
        
        # ECS
        cluster = ecs.Cluster(self, f"{prefix}Cluster", enable_fargate_capacity_providers=True, vpc=vpc)

        # ALB
        alb = elbv2.ApplicationLoadBalancer(self, f"{prefix}Alb", vpc=vpc, internet_facing=True, security_group=alb_sg)

        # Task Definition
        task_def = ecs.FargateTaskDefinition(self, f"{prefix}TaskDef", memory_limit_mib=2048, cpu=1024)
        
        # Build and push Docker image to ECR during CDK deployment
        image = ecs.ContainerImage.from_asset('.')
        
        task_def.add_container(f"{prefix}Container",
                              image=image,
                              port_mappings=[ecs.PortMapping(container_port=8501, protocol=ecs.Protocol.TCP)],
                              logging=ecs.LogDrivers.aws_logs(stream_prefix="BusinessProposal"),
                              environment={"ENVIRONMENT": env_name})

        # Service
        service = ecs.FargateService(self, f"{prefix}Service", cluster=cluster, task_definition=task_def,
                                    security_groups=[ecs_sg])

        # Bedrock Policy
        bedrock_policy = iam.Policy(self, f"{prefix}BedrockPolicy",
                                   statements=[iam.PolicyStatement(
                                       actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                                       resources=["*"])])
        task_def.task_role.attach_inline_policy(bedrock_policy)
        secret.grant_read(task_def.task_role)

        # CloudFront
        origin = origins.LoadBalancerV2Origin(alb, custom_headers={CUSTOM_HEADER_NAME: Config.CUSTOM_HEADER_VALUE})
        distribution = cloudfront.Distribution(self, f"{prefix}Distribution",
                                             default_behavior=cloudfront.BehaviorOptions(
                                                 origin=origin,
                                                 viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                                                 allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                                                 cache_policy=cloudfront.CachePolicy.CACHING_DISABLED))

        # ALB Listener
        listener = alb.add_listener(f"{prefix}Listener", port=80, open=True)
        listener.add_targets(f"{prefix}Targets", port=8501, protocol=elbv2.ApplicationProtocol.HTTP, targets=[service],
                           priority=1, conditions=[elbv2.ListenerCondition.http_header(CUSTOM_HEADER_NAME, [Config.CUSTOM_HEADER_VALUE])])
        listener.add_action("default", action=elbv2.ListenerAction.fixed_response(status_code=403, content_type="text/plain", message_body="Access denied"))

        # CI/CD Pipeline
        github_token = secretsmanager.Secret.from_secret_name_v2(
            self, f"{prefix}GitHubToken", secret_name="github-token")
        
        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()
        
        build_project = codebuild.Project(
            self, f"{prefix}Build",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "python": "3.12",
                            "nodejs": "20"
                        },
                        "commands": [
                            "npm install -g aws-cdk",
                            "pip install aws-cdk-lib constructs"
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo 'Building and deploying application with Docker image'",
                            "export CDK_DOCKER=docker",
                            "cdk deploy --require-approval never --app 'python3 cdk_app.py'"
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo 'Forcing ECS service update to use new container image'",
                            "aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment"
                        ]
                    }
                }
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            )
        )
        
        build_project.add_to_role_policy(iam.PolicyStatement(
            actions=["*"], resources=["*"]))
        
        codepipeline.Pipeline(
            self, f"{prefix}Pipeline",
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        codepipeline_actions.GitHubSourceAction(
                            action_name="GitHub_Source",
                            owner="ha-king",
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
        


        CfnOutput(self, "CloudFrontURL", value=distribution.domain_name)
        CfnOutput(self, "CognitoPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "ECRRepository", value=ecr_repo.repository_uri)
        CfnOutput(self, "ClusterName", value=cluster.cluster_name)
        CfnOutput(self, "ServiceName", value=service.service_name)