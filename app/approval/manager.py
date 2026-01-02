"""
Approval State Management

Handles storing, retrieving, and managing approval requests
for remediation actions.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ApprovalStatus(Enum):
    """Approval status states"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """Approval request data structure"""
    incident_id: str
    incident_type: str
    root_cause: str
    remediation_action: str
    risk_level: str
    namespace: str
    pod: Optional[str]
    deployment: Optional[str]
    command: Optional[str]
    requires_pr: bool
    status: str = ApprovalStatus.PENDING.value
    requested_at: str = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.requested_at is None:
            self.requested_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalRequest':
        """Create from dictionary"""
        return cls(**data)


class ApprovalManager:
    """Manages approval requests and their state"""
    
    def __init__(self, storage_dir: str = "approvals"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def create_approval_request(self, incident_state: Dict[str, Any]) -> ApprovalRequest:
        """
        Create a new approval request from incident state
        """
        remediation = incident_state.get("remediation_plan", {})
        
        request = ApprovalRequest(
            incident_id=incident_state["incident_id"],
            incident_type=incident_state.get("incident_type", "Unknown"),
            root_cause=incident_state.get("root_cause", "Unknown"),
            remediation_action=remediation.get("description", ""),
            risk_level=remediation.get("risk_level", "unknown"),
            namespace=incident_state.get("alert", {}).get("commonLabels", {}).get("namespace", ""),
            pod=incident_state.get("alert", {}).get("commonLabels", {}).get("pod"),
            deployment=incident_state.get("alert", {}).get("commonLabels", {}).get("deployment"),
            command=remediation.get("command"),
            requires_pr=remediation.get("requires_pr", True)
        )
        
        # Save to file
        self._save_request(request)
        
        return request
    
    def _save_request(self, request: ApprovalRequest):
        """Save approval request to file"""
        filepath = self.storage_dir / f"{request.incident_id}.json"
        with open(filepath, "w") as f:
            json.dump(request.to_dict(), f, indent=2)
    
    def get_request(self, incident_id: str) -> Optional[ApprovalRequest]:
        """Retrieve approval request by incident ID"""
        filepath = self.storage_dir / f"{incident_id}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath) as f:
            data = json.load(f)
        
        return ApprovalRequest.from_dict(data)
    
    def approve(self, incident_id: str, approved_by: str = "user") -> bool:
        """Approve a remediation request"""
        request = self.get_request(incident_id)
        
        if not request:
            return False
        
        request.status = ApprovalStatus.APPROVED.value
        request.approved_at = datetime.utcnow().isoformat()
        request.approved_by = approved_by
        
        self._save_request(request)
        
        return True
    
    def reject(self, incident_id: str, reason: str = "", rejected_by: str = "user") -> bool:
        """Reject a remediation request"""
        request = self.get_request(incident_id)
        
        if not request:
            return False
        
        request.status = ApprovalStatus.REJECTED.value
        request.approved_at = datetime.utcnow().isoformat()
        request.approved_by = rejected_by
        request.rejection_reason = reason
        
        self._save_request(request)
        
        return True
    
    def list_pending(self) -> list[ApprovalRequest]:
        """List all pending approval requests"""
        pending = []
        
        for filepath in self.storage_dir.glob("*.json"):
            with open(filepath) as f:
                data = json.load(f)
            
            request = ApprovalRequest.from_dict(data)
            if request.status == ApprovalStatus.PENDING.value:
                pending.append(request)
        
        # Sort by requested time
        pending.sort(key=lambda r: r.requested_at, reverse=True)
        
        return pending
    
    def list_all(self) -> list[ApprovalRequest]:
        """List all approval requests"""
        requests = []
        
        for filepath in self.storage_dir.glob("*.json"):
            with open(filepath) as f:
                data = json.load(f)
            
            requests.append(ApprovalRequest.from_dict(data))
        
        requests.sort(key=lambda r: r.requested_at, reverse=True)
        
        return requests
    
    def is_approved(self, incident_id: str) -> bool:
        """Check if an incident has been approved"""
        request = self.get_request(incident_id)
        
        if not request:
            return False
        
        return request.status == ApprovalStatus.APPROVED.value
    
    def get_approval_status(self, incident_id: str) -> Optional[str]:
        """Get the approval status of an incident"""
        request = self.get_request(incident_id)
        
        if not request:
            return None
        
        return request.status


# Global approval manager instance
_approval_manager = None


def get_approval_manager() -> ApprovalManager:
    """Get the global approval manager instance"""
    global _approval_manager
    
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    
    return _approval_manager
