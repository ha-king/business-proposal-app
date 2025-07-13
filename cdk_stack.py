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

        # ECS
        cluster = ecs.Cluster(self, f"{prefix}Cluster", enable_fargate_capacity_providers=True, vpc=vpc)

        # ALB
        alb = elbv2.ApplicationLoadBalancer(self, f"{prefix}Alb", vpc=vpc, internet_facing=True, security_group=alb_sg)

        # Task Definition
        task_def = ecs.FargateTaskDefinition(self, f"{prefix}TaskDef", memory_limit_mib=2048, cpu=1024)
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
        listener.add_targets(f"{prefix}Targets", port=8501, targets=[service],
                           conditions=[elbv2.ListenerCondition.http_header(CUSTOM_HEADER_NAME, [Config.CUSTOM_HEADER_VALUE])])
        listener.add_action("default", action=elbv2.ListenerAction.fixed_response(403, "text/plain", "Access denied"))

        CfnOutput(self, "CloudFrontURL", value=distribution.domain_name)
        CfnOutput(self, "CognitoPoolId", value=user_pool.user_pool_id)