COMPOSE := docker compose

.PHONY: cert-api deploy-lambda deploy-cognito destroy-database help up down build logs ps migrate revision test test-backend test-frontend lint fmt clean shell-backend shell-db deploy-backend destroy-backend logs-backend migrate-backend cert domain deploy-frontend destroy-frontend github-role report-now

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Start the whole stack (detached)
	$(COMPOSE) up -d --build

down: ## Stop the stack
	$(COMPOSE) down

clean: ## Stop the stack and wipe the database volume
	$(COMPOSE) down -v

build: ## Rebuild images
	$(COMPOSE) build

logs: ## Tail all logs
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

migrate: ## Apply migrations
	$(COMPOSE) exec backend alembic upgrade head

revision: ## Autogenerate a migration: make revision m="add x"
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(m)"

.PHONY: test-deploy

test: test-backend test-frontend test-deploy ## Run all tests

test-deploy: ## Test deployment safety without calling AWS
	python3 -m unittest discover -s tests -v

test-backend: ## Run backend tests
	$(COMPOSE) exec backend pytest

test-frontend: ## Run frontend tests
	$(COMPOSE) exec frontend pnpm test

lint: ## Lint both sides
	$(COMPOSE) exec -T backend ruff check .
	$(COMPOSE) exec -T backend ruff format --check .
	$(COMPOSE) exec -T frontend pnpm lint
	$(COMPOSE) exec -T frontend pnpm format:check

fmt: ## Format both sides
	$(COMPOSE) exec backend ruff format .
	$(COMPOSE) exec frontend pnpm format

shell-backend: ## Shell into the backend container
	$(COMPOSE) exec backend bash

shell-db: ## psql into the database
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-peach} -d $${POSTGRES_DB:-peach}

deploy-backend: ## Build a commit-SHA image, migrate once, and roll ECS Fargate behind CloudFront and ALB
	./scripts/deploy-backend.sh

destroy-backend: ## Delete ECS and ALB (confirmation required); keep the database
	./scripts/ecs-admin.sh destroy

destroy-database: ## Delete the legacy Lambda/database stack and its data (confirmation required)
	./scripts/destroy-backend.sh

logs-backend: ## Tail ECS application and migration logs
	./scripts/ecs-admin.sh logs

migrate-backend: deploy-backend ## Run the deployment contract, including the migration task

cert-api: ## Request the regional ACM API certificate and print its validation CNAME
	./scripts/cert-api.sh

deploy-lambda: ## Legacy deployment retained for rollback; not the lab backend
	./scripts/deploy-lambda.sh

deploy-cognito: ## Deploy Cognito managed login with email/password and Google
	./scripts/deploy-cognito.sh

cert: ## Request + DNS-validate a us-east-1 certificate for the frontend: make cert DOMAIN=app.example.com
	./scripts/domain-frontend.sh cert

domain: ## Assign a custom domain to the frontend: make domain DOMAIN=app.example.com
	./scripts/domain-frontend.sh domain

deploy-frontend: ## Build the static export against BACKEND_URL and ship it to S3 + CloudFront
	./scripts/deploy-frontend.sh

destroy-frontend: ## Delete the frontend stack (bucket + distribution)
	./scripts/destroy-frontend.sh

github-role: ## Create the IAM role GitHub Actions assumes to deploy (OIDC, no keys)
	./scripts/github-role.sh

report-now: ## Queue one intentional weekly report (may send email): make report-now WEEK=2026-W39
	@python3 -c 'import datetime, re, sys; w="$(WEEK)"; (sys.exit("WEEK must be a valid ISO week in YYYY-Www format") if not re.fullmatch(r"[0-9]{4}-W[0-9]{2}", w) else datetime.date.fromisocalendar(int(w[:4]), int(w[-2:]), 1))' 2>/dev/null || { echo 'Set WEEK to a valid ISO week, for example 2026-W39' >&2; exit 2; }
	@queue_url=$$(aws cloudformation describe-stacks --stack-name "$${REPORT_STACK:-peach-weekly-meetings-report}" --query "Stacks[0].Outputs[?OutputKey=='ReportQueueUrl'].OutputValue | [0]" --output text --region "$${AWS_REGION:-us-east-1}" --profile "$${AWS_PROFILE:-peach-lab}"); \
	  test -n "$$queue_url" && test "$$queue_url" != None || { echo 'Report stack or ReportQueueUrl output not found' >&2; exit 1; }; \
	  aws sqs send-message --queue-url "$$queue_url" --message-body '{"week":"$(WEEK)","source":"manual"}' --region "$${AWS_REGION:-us-east-1}" --profile "$${AWS_PROFILE:-peach-lab}" --query MessageId --output text
