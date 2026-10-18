# DevOps notes

## Terraform
Terraform provisions infrastructure as code. State is stored remotely (S3 + DynamoDB lock) so teams can collaborate safely.

## Kubernetes
Kubernetes schedules containers across nodes. A Deployment manages ReplicaSets; a Service gives pods a stable address; an Ingress routes external HTTP traffic.

## CI/CD
A pipeline builds, tests, scans (SAST, dependency and image scans) and deploys. Fail the build on critical vulnerabilities.
