# Peach — C4 container view, Lab 6

```mermaid
flowchart LR
    User[Person reviewing an agenda] --> Browser[Peach Next.js static frontend]
    CF[CloudFront + private S3] --> Browser
    Browser -->|Sign in| Cognito[Amazon Cognito]
    Browser -->|Parse: HTTPS POST + Cognito ID token| Parser[Agenda parser Lambda\nOutside VPC, 512 MB, 30 seconds]
    Parser -->|Validated record_agenda suggestion\nBedrock Converse API| Bedrock[Amazon Bedrock / Nova Pro]
    Parser -->|JSON: user, model, version, tokens, latency, cost| Logs[CloudWatch Logs, 14 days]
    Parser -->|JWKS: verify signature and claims| Cognito
    Browser -->|Save: PUT meeting agenda + original suggestion| APICF[API CloudFront / ALB]
    subgraph VPC[Existing application VPC]
      APICF --> API[FastAPI on ECS Fargate\nOwner-scoped validation]
      API -->|One transaction| DB[(Existing Aurora PostgreSQL\nmeetings.agenda + ai_suggestion JSONB)]
    end
    Budget[AWS Budget: monthly $5 alert] --> Email[Owner email]
```

The parse arrow never reaches the database. Only the reviewed save path can write.
Peach uses owner isolation (one signed-in user), not a new organisation subsystem.
