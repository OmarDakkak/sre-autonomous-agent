# SRE Autonomous Agent - Demo Guide

Complete end-to-end demonstration of the autonomous incident response system.

## 🎯 Demo Scenario

**Incident:** Pod CrashLoopBackOff in production  
**Root Cause:** Missing DATABASE_URL environment variable  
**Resolution:** Automated remediation with human approval

---

## 📋 Pre-Demo Setup

### 1. Start Minikube (if not running)
```bash
cd /mnt/c/Users/TEST/Documents/projects/sre-autonomous-agent
minikube status
# If not running:
# minikube start --driver=docker
```

### 2. Reset the Environment
```bash
# Remove any existing approvals
rm -f approvals/*.json

# Remove DATABASE_URL from deployment (to create the incident)
kubectl set env deployment/api DATABASE_URL- -n payments

# Wait for pods to start crashing
sleep 10
kubectl get pods -n payments
# Expected: STATUS=CrashLoopBackOff
```

### 3. Start the UI
```bash
source venv/bin/activate
./run-ui-fast.sh
```

Open browser to: http://localhost:8501

---

## 🎬 Demo Script

### Part 1: The Incident Occurs (2 minutes)

**Narrator:**
> "We have a critical incident in our payments service. Let me show you what's happening in our Kubernetes cluster."

```bash
# Show the failing pod
kubectl get pods -n payments
kubectl describe pod <pod-name> -n payments | grep -A 10 "State:"
kubectl logs <pod-name> -n payments --tail=20
```

**What to show:**
- Pod in CrashLoopBackOff state
- Error message: "Missing DATABASE_URL environment variable"
- Pod restarting repeatedly

---

### Part 2: Create Approval Request (1 minute)

**Narrator:**
> "The SRE agent has analyzed the incident and determined the root cause. It's now creating an approval request for the remediation."

```bash
# Create the approval request
python create_test_approval.py
```

**Expected output:**
```
✅ Created test approval request: INC-TEST-001
   Root Cause: Missing environment variable DATABASE_URL
   Risk Level: low
   Namespace: payments
```

---

### Part 3: Human Review in UI (3 minutes)

**Narrator:**
> "Now, let's review the proposed remediation in our web interface."

**In the browser:**

1. **Navigate to Approvals Tab**
   - Show "Pending Approvals" section
   - Point out the incident details

2. **Expand the Incident**
   - **Root Cause:** Missing environment variable DATABASE_URL
   - **Proposed Action:** Add DATABASE_URL environment variable to deployment
   - **Risk Level:** low
   - **Created:** [timestamp]

3. **Click "View Remediation Details"**
   Show the JSON:
   ```json
   {
     "action_type": "config_change",
     "description": "Add DATABASE_URL environment variable to deployment",
     "risk_level": "low",
     "command": "kubectl set env deployment/api...",
     "value": "postgresql://db:5432/payments",
     "steps": [...]
   }
   ```

4. **Review the Actions Section**
   - Optional comment field
   - Approve button (green)
   - Reject button (red)

**Narrator:**
> "As an SRE, I can review the proposed fix. The risk is low, and the solution makes sense. Let me approve this remediation."

---

### Part 4: Automated Execution (2 minutes)

**Narrator:**
> "Watch what happens when I click Approve..."

1. **Click "✓ Approve"**

2. **Watch the messages appear:**
   ```
   ✅ Remediation approved!
   🔧 Executing remediation...
   ✅ Remediation executed successfully: Successfully applied config change to api
   ```

**Narrator:**
> "The system has automatically executed the fix. Let's verify what happened in Kubernetes."

```bash
# Show the deployment was updated
kubectl describe deployment api -n payments | grep DATABASE_URL

# Show new pods rolling out
kubectl get pods -n payments -w
# (Wait ~10 seconds for new pod to become Running)
```

**Expected:**
```
NAME                   READY   STATUS    RESTARTS   AGE
api-xxxxxxxxxx-xxxxx   1/1     Running   0          15s
```

---

### Part 5: Verify Resolution (1 minute)

**Narrator:**
> "Let's confirm the application is now healthy."

```bash
# Check pod status
kubectl get pods -n payments

# Check pod logs (should show successful startup)
kubectl logs <new-pod-name> -n payments

# Verify environment variable is set
kubectl exec <new-pod-name> -n payments -- env | grep DATABASE_URL
```

**Expected output:**
```
DATABASE_URL=postgresql://db:5432/payments
```

**In the UI:**
- Navigate to "Approved" tab
- Show the completed remediation with approval details

---

## 📊 Key Points to Highlight

### 1. **Human-in-the-Loop**
- ✅ System proposes fixes, humans approve
- ❌ No changes executed without approval
- 🔒 Safety first approach

### 2. **Automation After Approval**
- ⚡ Instant execution once approved
- 🤖 No manual kubectl commands needed
- 📝 Full audit trail maintained

### 3. **Risk Assessment**
- Low/Medium/High risk levels
- Different approval workflows based on risk
- Clear remediation details

### 4. **Complete Observability**
- Full incident history
- Approval audit trail
- Execution results tracked

---

## 🎭 Alternative Demo Scenarios

### Scenario A: Reject the Remediation
1. Click "✗ Reject" instead
2. Enter a reason: "Need to verify database connection first"
3. Show it moves to "Rejected" tab
4. Manual investigation required

### Scenario B: Show Historical Incidents
1. Navigate to "Incidents" tab
2. Show timeline chart
3. Click on past incidents
4. Show full incident details

### Scenario C: Manual Alert Submission
1. Navigate to "Submit Alert" tab
2. Fill in alert details manually
3. Submit and watch agent process it

---

## 🔧 Cleanup After Demo

```bash
# Keep the fix in place or reset for next demo
kubectl set env deployment/api DATABASE_URL- -n payments  # Reset
# OR
kubectl set env deployment/api DATABASE_URL=postgresql://db:5432/payments -n payments  # Keep

# Clean up approvals
rm -f approvals/*.json

# Stop UI (if needed)
pkill -f "streamlit run"
```

---

## 💡 Demo Tips

### Before the Demo
- ✅ Test the full flow once
- ✅ Have terminal and browser side-by-side
- ✅ Increase terminal font size
- ✅ Clear terminal history: `clear`
- ✅ Bookmark http://localhost:8501

### During the Demo
- 🗣️ Narrate each step clearly
- ⏸️ Pause after key actions
- 👁️ Point out important details
- ❓ Ask "What would you do?" before approving

### Common Issues
- **Pods not crashing?** Wait 30 seconds after removing DATABASE_URL
- **UI not loading?** Check if Streamlit is running: `ps aux | grep streamlit`
- **Import errors?** Restart Streamlit: `pkill -f streamlit && ./run-ui-fast.sh`

---

## 📸 Screenshot Opportunities

1. **Before:** Pod CrashLoopBackOff in terminal
2. **Approval UI:** Pending remediation with details expanded
3. **Execution:** Success messages in UI
4. **After:** Pod Running status in terminal
5. **Audit Trail:** Approved remediations list

---

## ⏱️ Timing

- **Quick Demo:** 5 minutes (skip explanations)
- **Standard Demo:** 10 minutes (with narration)
- **Deep Dive:** 20 minutes (with Q&A)

---

## 🎤 Opening and Closing

### Opening
> "Today I'll show you an autonomous SRE agent that can detect, diagnose, and fix Kubernetes incidents - with human oversight. This isn't ChatOps, it's reasoning + action."

### Closing
> "In just [X] minutes, we went from a critical incident to full resolution, with one click. The system did the heavy lifting: diagnosis, solution design, and execution - all under human control. This is the future of SRE automation."

---

## 📚 Additional Resources

- **Architecture:** See README.md
- **Code:** Browse /app directory
- **Policies:** Check /app/policies/guardrails.yaml
- **Tools:** Explore /app/tools for integrations

---

**Ready to demo? Follow the steps above and showcase the power of autonomous incident response!** 🚀
