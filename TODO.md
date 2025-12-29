# 📋 TODO & Development Roadmap

## Phase 1: MVP (Current) ✅

- [x] Project structure setup
- [x] LangGraph state definition
- [x] Core agent implementations:
  - [x] Triage agent
  - [x] Hypothesis agent
  - [x] Diagnostics agent
  - [x] Remediation planner
  - [x] Postmortem writer
- [x] Kubernetes tools
- [x] Observability tools (Prometheus, Loki)
- [x] Guardrails policy
- [x] Example alert
- [x] Main workflow orchestration
- [x] Documentation

## Phase 1.5: Production Ready 🚧

### Critical Improvements
- [ ] Replace `eval()` with proper JSON parsing
- [ ] Add comprehensive error handling
- [ ] Implement proper logging (structured)
- [ ] Add unit tests for all agents
- [ ] Add integration tests
- [ ] Security hardening (secrets management)

### Slack Integration
- [ ] Slack webhook setup
- [ ] Send incident notifications
- [ ] Approval button UI
- [ ] Status update messages
- [ ] Postmortem sharing

### Webhook Server
- [ ] FastAPI server setup
- [ ] Alertmanager webhook handler
- [ ] PagerDuty webhook handler
- [ ] Authentication/authorization
- [ ] Rate limiting

## Phase 2: Multi-Incident Support

### New Incident Types
- [ ] OOMKilled (Out of Memory)
  - [ ] Memory metrics analysis
  - [ ] Resource limit recommendations
  - [ ] Hypothesis patterns
- [ ] ImagePullBackOff
  - [ ] Registry connectivity checks
  - [ ] Authentication validation
  - [ ] Image availability verification
- [ ] NodeNotReady
  - [ ] Node status checks
  - [ ] Resource exhaustion detection
  - [ ] Network diagnostics
- [ ] HighErrorRate
  - [ ] HTTP error analysis
  - [ ] Recent deployment correlation
  - [ ] Dependency checks

### Enhancements
- [ ] Incident type auto-detection
- [ ] Multi-incident correlation
- [ ] Pattern recognition across incidents

## Phase 3: Auto-Fix (Guardrailed)

### Safe Auto-Remediation
- [ ] Risk scoring algorithm
- [ ] Blast radius calculation
- [ ] Auto-fix for low-risk actions:
  - [ ] Pod restarts
  - [ ] Config rollbacks
  - [ ] Scale adjustments
- [ ] Automatic rollback on failure
- [ ] Canary deployment integration

### Advanced Guardrails
- [ ] Time-window restrictions
- [ ] Change velocity limits
- [ ] Dependency graph awareness
- [ ] Cost impact estimation

## Phase 4: Learning & Optimization

### Intelligence
- [ ] Incident pattern recognition
- [ ] Custom playbook generation
- [ ] Team-specific policies
- [ ] Historical data analysis
- [ ] MTTR prediction

### Integrations
- [ ] GitOps (ArgoCD, Flux)
- [ ] Service mesh (Istio, Linkerd)
- [ ] APM tools (Datadog, New Relic)
- [ ] Incident management (Opsgenie, VictorOps)

## Infrastructure & DevOps

### Deployment
- [ ] Kubernetes manifests
- [ ] Helm chart
- [ ] Terraform module
- [ ] Docker image
- [ ] CI/CD pipeline

### Monitoring
- [ ] Agent performance metrics
- [ ] Diagnostic tool latency
- [ ] Success/failure rates
- [ ] Cost tracking
- [ ] SLOs/SLIs

## Documentation

- [ ] API documentation
- [ ] Runbook for deployment
- [ ] Troubleshooting guide
- [ ] Architecture deep-dive
- [ ] Video tutorials

## Business & GTM

- [ ] Pricing page
- [ ] Case studies
- [ ] Demo environment
- [ ] Sales collateral
- [ ] Partner integrations

---

## Quick Wins (Next Sprint)

1. **Replace eval()** - Security risk
2. **Add proper logging** - Debugging essential
3. **Slack integration** - Demo impact
4. **Unit tests** - Confidence in changes
5. **Docker image** - Easy deployment
