"""
CLI Approval Tool

Command-line interface for approving/rejecting remediation actions.
"""

import sys
import argparse
from typing import Optional

from app.approval import get_approval_manager
from app.tools.remediation_executor import RemediationExecutor


def approve_remediation(incident_id: str, comment: Optional[str] = None):
    """Approve a pending remediation"""
    
    approval_manager = get_approval_manager()
    
    # Get the approval request
    pending = approval_manager.list_pending()
    request = next((r for r in pending if r.incident_id == incident_id), None)
    
    if not request:
        print(f"Error: No pending approval found for incident {incident_id}")
        return 1
    
    print("\n" + "="*80)
    print("REMEDIATION APPROVAL")
    print("="*80)
    print(f"\nIncident ID: {incident_id}")
    print(f"Root Cause: {request.root_cause}")
    print(f"Action: {request.remediation_action}")
    print(f"Risk Level: {request.risk_level}")
    print(f"Created: {request.created_at}")
    print("\n" + "="*80)
    
    # Confirm approval
    response = input("\nApprove this remediation? [y/N]: ")
    
    if response.lower() != 'y':
        print("Approval cancelled.")
        return 0
    
    # Approve
    approval_manager.approve(incident_id, "cli-user", comment)
    print(f"\n✓ Remediation approved for incident {incident_id}")
    
    # Execute remediation
    print("\nExecuting remediation...")
    executor = RemediationExecutor()
    
    success, message = executor.execute_remediation(
        incident_id,
        request.remediation_plan,
        request.alert_data
    )
    
    if success:
        print(f"\n✓ {message}")
        return 0
    else:
        print(f"\n✗ {message}")
        return 1


def reject_remediation(incident_id: str, reason: Optional[str] = None):
    """Reject a pending remediation"""
    
    approval_manager = get_approval_manager()
    
    # Get the approval request
    pending = approval_manager.list_pending()
    request = next((r for r in pending if r.incident_id == incident_id), None)
    
    if not request:
        print(f"Error: No pending approval found for incident {incident_id}")
        return 1
    
    print("\n" + "="*80)
    print("REMEDIATION REJECTION")
    print("="*80)
    print(f"\nIncident ID: {incident_id}")
    print(f"Root Cause: {request.root_cause}")
    print(f"Action: {request.remediation_action}")
    print("\n" + "="*80)
    
    # Get reason if not provided
    if not reason:
        reason = input("\nReason for rejection: ")
    
    # Reject
    approval_manager.reject(incident_id, "cli-user", reason)
    print(f"\n✓ Remediation rejected for incident {incident_id}")
    
    return 0


def list_pending():
    """List all pending approvals"""
    
    approval_manager = get_approval_manager()
    pending = approval_manager.list_pending()
    
    if not pending:
        print("\nNo pending approvals.")
        return 0
    
    print("\n" + "="*80)
    print(f"PENDING APPROVALS ({len(pending)})")
    print("="*80)
    
    for request in pending:
        print(f"\nIncident ID: {request.incident_id}")
        print(f"  Root Cause: {request.root_cause}")
        print(f"  Action: {request.remediation_action}")
        print(f"  Risk: {request.risk_level}")
        print(f"  Created: {request.created_at}")
        print(f"  Approval ID: {request.approval_id}")
    
    print("\n" + "="*80)
    print("\nTo approve: python -m app.cli.approve <incident_id>")
    print("To reject: python -m app.cli.approve --reject <incident_id>")
    
    return 0


def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="Approve or reject remediation actions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List pending approvals
  python -m app.cli.approve --list
  
  # Approve a remediation
  python -m app.cli.approve incident-123
  
  # Approve with comment
  python -m app.cli.approve incident-123 --comment "Approved after review"
  
  # Reject a remediation
  python -m app.cli.approve --reject incident-123 --reason "Too risky"
        """
    )
    
    parser.add_argument(
        "incident_id",
        nargs="?",
        help="Incident ID to approve/reject"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all pending approvals"
    )
    
    parser.add_argument(
        "--reject",
        action="store_true",
        help="Reject the remediation instead of approving"
    )
    
    parser.add_argument(
        "--comment",
        help="Comment for approval"
    )
    
    parser.add_argument(
        "--reason",
        help="Reason for rejection"
    )
    
    args = parser.parse_args()
    
    # List pending
    if args.list:
        return list_pending()
    
    # Need incident ID for approve/reject
    if not args.incident_id:
        parser.print_help()
        return 1
    
    # Reject
    if args.reject:
        return reject_remediation(args.incident_id, args.reason)
    
    # Approve (default)
    return approve_remediation(args.incident_id, args.comment)


if __name__ == "__main__":
    sys.exit(main())
