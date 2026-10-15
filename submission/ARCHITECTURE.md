# Architecture

```mermaid
flowchart LR
    Scheduler[EventBridge Scheduler\npermanent state: DISABLED] -. one schedule .-> Queue[SQS Report Queue]
    Manual[make report-now / SendMessage] --> Queue
    Queue -->|event source mapping\npermanent state: Disabled| Worker[Worker Lambda\nARM64 container]
    Worker -->|read meeting rows| DB[(PostgreSQL\nAlembic 0004)]
    Worker -->|CSV: reports/{week}/weekly-meetings.csv| Bucket[(Private S3 bucket)]
    Bucket -->|Object Created under reports/| Rule[EventBridge rule]
    Rule --> Delivery[Delivery Lambda\nARM64 container]
    Delivery -->|get CSV + presigned link| Bucket
    Delivery --> SES[Amazon SES\nSandbox]
    SES --> Recipient[Verified test recipient\ninbox receipt not verified]
    Queue -. maxReceiveCount=3 .-> DLQ[SQS Report DLQ]
    Scheduler -. retry failure .-> SchedulerDLQ[Scheduler DLQ]
    Rule -. retry failure .-> DeliveryDLQ[Delivery DLQ]
```

The SQS worker queries PostgreSQL for an ISO week, writes a UTF-8 CSV to a deterministic S3 key, and skips an existing report. S3 EventBridge notification routes a new object to the delivery Lambda, which reads the CSV and sends it through SES. SQS and EventBridge have separate retry/DLQ paths.

The permanent Scheduler and production SQS event source mapping were both restored to disabled states after controlled runs. The S3 notification and EventBridge rule remain configured. The diagram intentionally distinguishes configured-but-disabled triggers from the active S3 event path.
