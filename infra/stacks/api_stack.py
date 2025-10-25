"""API Gateway and Lambda functions stack."""

from aws_cdk import Stack, Duration, CfnOutput
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_authorizers as apigw_auth
from aws_cdk import aws_apigatewayv2_integrations as apigw_integ
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_python_alpha as lambda_python
from aws_cdk import aws_secretsmanager as secrets
from aws_cdk import aws_iam as iam
from constructs import Construct


class ApiStack(Stack):
    """Stack for API Gateway and Lambda functions."""
    
    def __init__(self, scope: Construct, construct_id: str, 
                 users_table, trips_table, trip_states_table, user_pool, user_pool_client, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.users_table = users_table
        self.trips_table = trips_table
        self.trip_states_table = trip_states_table
        self.user_pool = user_pool
        self.user_pool_client = user_pool_client
        
        # Secrets Manager for INRIX API key
        self.inrix_secret = secrets.Secret(
            self,
            "InrixApiKeySecret",
            secret_name="odessey-inrix-api-key",
            description="INRIX API key for ETA predictions",
            removal_policy=kwargs.get("removal_policy", None)
        )
        
        # Lambda function for health check (no auth)
        self.health_handler = self._create_handler("HealthHandler", "src.handlers.health", "handler")
        
        # Create Lambdas for each endpoint
        self.init_handler = self._create_protected_handler("InitHandler", "src.handlers.init", "handler")
        self.classify_handler = self._create_protected_handler("ClassifyHandler", "src.handlers.classify", "handler")
        self.eta_handler = self._create_protected_handler("EtaHandler", "src.handlers.eta", "handler")
        self.plan_handler = self._create_protected_handler("PlanHandler", "src.handlers.plan", "handler")
        self.save_handler = self._create_protected_handler("SaveHandler", "src.handlers.save", "handler")
        self.get_trip_handler = self._create_protected_handler("GetTripHandler", "src.handlers.get_trip", "handler")
        self.signup_handler = self._create_handler("SignupHandler", "src.handlers.auth", "signup_handler")
        self.login_handler = self._create_handler("LoginHandler", "src.handlers.auth", "login_handler")
        
        # API Gateway
        api = apigw.HttpApi(
            self,
            "OdesseyApi",
            cors_preflight={
                "allow_origins": ["*"],
                "allow_methods": [apigw.CorsHttpMethod.ANY],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        )
        
        # Cognito authorizer - temporarily disabled for bootstrap
        # authorizer = apigw_auth.HttpUserPoolAuthorizer(
        #     "CognitoAuthorizer",
        #     user_pool=self.user_pool,
        #     user_pool_clients=[self.user_pool_client]
        # )
        
        # Add routes
        # Public routes
        api.add_routes(
            path="/health",
            methods=[apigw.HttpMethod.GET],
            integration=apigw_integ.HttpLambdaIntegration("HealthIntegration", self.health_handler)
        )
        
        api.add_routes(
            path="/auth/signup",
            methods=[apigw.HttpMethod.POST],
            integration=apigw_integ.HttpLambdaIntegration("SignupIntegration", self.signup_handler)
        )
        
        api.add_routes(
            path="/auth/login",
            methods=[apigw.HttpMethod.POST],
            integration=apigw_integ.HttpLambdaIntegration("LoginIntegration", self.login_handler)
        )
        
        # Protected routes (temporarily without auth for bootstrap)
        api.add_routes(
            path="/trip/init",
            methods=[apigw.HttpMethod.POST],
            integration=apigw_integ.HttpLambdaIntegration("InitIntegration", self.init_handler)
        )
        
        api.add_routes(
            path="/trip/classify",
            methods=[apigw.HttpMethod.POST],
            integration=apigw_integ.HttpLambdaIntegration("ClassifyIntegration", self.classify_handler)
        )
        
        api.add_routes(
            path="/trip/eta",
            methods=[apigw.HttpMethod.POST],
            integration=apigw_integ.HttpLambdaIntegration("EtaIntegration", self.eta_handler)
        )
        
        api.add_routes(
            path="/trip/plan",
            methods=[apigw.HttpMethod.POST],
            integration=apigw_integ.HttpLambdaIntegration("PlanIntegration", self.plan_handler)
        )
        
        api.add_routes(
            path="/trip/save",
            methods=[apigw.HttpMethod.POST],
            integration=apigw_integ.HttpLambdaIntegration("SaveIntegration", self.save_handler)
        )
        
        api.add_routes(
            path="/trip/{tripId}",
            methods=[apigw.HttpMethod.GET],
            integration=apigw_integ.HttpLambdaIntegration("GetTripIntegration", self.get_trip_handler)
        )
        
        # Output API URL
        CfnOutput(
            self,
            "ApiUrl",
            value=api.url,
            description="API Gateway URL"
        )
    
    def _create_handler(self, id: str, module: str, handler: str) -> lambda_.Function:
        """Create a Lambda handler with common configuration."""
        fn = lambda_python.PythonFunction(
            self,
            id,
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="src",
            index=f"handlers/{module.split('.')[-1]}.py",
            handler=handler,
            timeout=Duration.seconds(30),
            environment={
                "USERS_TABLE_NAME": self.users_table.table_name,
                "TRIPS_TABLE_NAME": self.trips_table.table_name,
                "TRIP_STATES_TABLE_NAME": self.trip_states_table.table_name,
                "COGNITO_USER_POOL_ID": self.user_pool.user_pool_id,
                "COGNITO_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "INRIX_SECRET_ARN": self.inrix_secret.secret_arn,
                "LOCATION_PLACE_INDEX_NAME": "odessey-place-index",  # Update with actual name
                "BEDROCK_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0"
            }
        )
        
        # Grant permissions
        self.users_table.grant_read_write_data(fn)
        self.trips_table.grant_read_write_data(fn)
        self.trip_states_table.grant_read_write_data(fn)
        self.inrix_secret.grant_read(fn)
        
        return fn
    
    def _create_protected_handler(self, id: str, module: str, handler: str) -> lambda_.Function:
        """Create a Lambda handler with all permissions (DynamoDB, Location, Bedrock)."""
        fn = self._create_handler(id, module, handler)
        
        # Grant Cognito permissions
        fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cognito-idp:GetUser"],
                resources=[self.user_pool.user_pool_arn]
            )
        )
        
        # Grant Amazon Location permissions
        fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["geo:SearchPlaceIndexForText"],
                resources=["*"]  # Will be restricted to specific index
            )
        )
        
        # Grant Bedrock permissions
        fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:*:*:foundation-model/*"]
            )
        )
        
        return fn

