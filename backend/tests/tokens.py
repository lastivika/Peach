import json
import os
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key()))
public["kid"] = "test-key"
os.environ.update(
    COGNITO_REGION="us-east-1",
    COGNITO_USER_POOL_ID="us-east-1_test",
    COGNITO_CLIENT_ID="test-client",
    COGNITO_JWKS=json.dumps({"keys": [public]}),
)


def make_token(sub="alice-sub", email="alice@example.com", **overrides):
    claims = dict(
        sub=sub,
        email=email,
        email_verified=True,
        token_use="id",
        iss="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
        aud="test-client",
        exp=int(time.time()) + 3600,
    )
    claims.update(overrides)
    return jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": "test-key"})


def auth():
    return {"Authorization": "Bearer " + make_token()}
