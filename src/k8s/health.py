"""Cluster health monitoring and security audit features."""

import asyncio
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

from src.utils.logger import get_logger

logger = get_logger("health")


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: str  # "healthy", "warning", "critical"
    message: str
    details: Optional[str] = None


@dataclass
class ClusterHealthReport:
    """Overall cluster health report."""
    score: int  # 0-100
    checks: list[HealthCheck] = field(default_factory=list)
    
    @property
    def status_emoji(self) -> str:
        if self.score >= 90:
            return "🟢"
        elif self.score >= 70:
            return "🟡"
        elif self.score >= 50:
            return "🟠"
        else:
            return "🔴"
    
    def to_string(self) -> str:
        """Format the health report as a string."""
        lines = [
            f"{'═' * 50}",
            f"  CLUSTER HEALTH SCORE: {self.score}/100 {self.status_emoji}",
            f"{'═' * 50}",
            ""
        ]
        
        for check in self.checks:
            if check.status == "healthy":
                icon = "✅"
            elif check.status == "warning":
                icon = "⚠️"
            else:
                icon = "❌"
            
            lines.append(f"{icon} {check.name}: {check.message}")
            if check.details:
                lines.append(f"   └─ {check.details}")
        
        lines.append("")
        lines.append(f"{'═' * 50}")
        
        return "\n".join(lines)


@dataclass
class SecurityIssue:
    """Security issue found during audit."""
    severity: str  # "critical", "high", "medium", "low"
    category: str
    message: str
    resource: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class SecurityAuditReport:
    """Security audit report."""
    issues: list[SecurityIssue] = field(default_factory=list)
    
    @property
    def score(self) -> int:
        """Calculate security score based on issues."""
        base_score = 100
        for issue in self.issues:
            if issue.severity == "critical":
                base_score -= 25
            elif issue.severity == "high":
                base_score -= 15
            elif issue.severity == "medium":
                base_score -= 10
            else:
                base_score -= 5
        return max(0, base_score)
    
    def to_string(self) -> str:
        """Format the security report as a string."""
        lines = [
            f"{'═' * 50}",
            f"  SECURITY AUDIT SCORE: {self.score}/100",
            f"{'═' * 50}",
            ""
        ]
        
        if not self.issues:
            lines.append("✅ No security issues found!")
        else:
            # Group by severity
            for severity in ["critical", "high", "medium", "low"]:
                severity_issues = [i for i in self.issues if i.severity == severity]
                if severity_issues:
                    icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}[severity]
                    lines.append(f"\n{icon} {severity.upper()} ({len(severity_issues)} issues)")
                    lines.append("-" * 40)
                    for issue in severity_issues:
                        lines.append(f"  • {issue.message}")
                        if issue.resource:
                            lines.append(f"    Resource: {issue.resource}")
                        if issue.recommendation:
                            lines.append(f"    Fix: {issue.recommendation}")
        
        lines.append("")
        lines.append(f"{'═' * 50}")
        
        return "\n".join(lines)


class ClusterHealthChecker:
    """Performs cluster health checks."""
    
    def __init__(self, kubeconfig: Optional[str] = None):
        self.kubeconfig = kubeconfig
        self.kubectl_base = ["kubectl"]
        if kubeconfig:
            self.kubectl_base.extend(["--kubeconfig", kubeconfig])
    
    def _run_kubectl(self, args: list[str], timeout: int = 30) -> tuple[bool, str]:
        """Run kubectl command and return success status and output."""
        try:
            cmd = self.kubectl_base + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    async def check_nodes(self) -> HealthCheck:
        """Check node health."""
        success, output = self._run_kubectl(["get", "nodes", "-o", "wide"])
        
        if not success:
            return HealthCheck("Nodes", "critical", "Cannot get nodes", output)
        
        lines = output.strip().split("\n")[1:]  # Skip header
        total = len(lines)
        ready = sum(1 for line in lines if "Ready" in line and "NotReady" not in line)
        
        if ready == total:
            return HealthCheck("Nodes", "healthy", f"{ready}/{total} nodes ready")
        elif ready > 0:
            return HealthCheck("Nodes", "warning", f"{ready}/{total} nodes ready", 
                             f"{total - ready} node(s) not ready")
        else:
            return HealthCheck("Nodes", "critical", "No nodes ready")
    
    async def check_pods(self) -> HealthCheck:
        """Check pod health across all namespaces."""
        success, output = self._run_kubectl(["get", "pods", "--all-namespaces", "--no-headers"])
        
        if not success:
            return HealthCheck("Pods", "critical", "Cannot get pods", output)
        
        lines = output.strip().split("\n") if output.strip() else []
        total = len(lines)
        
        if total == 0:
            return HealthCheck("Pods", "healthy", "No pods running")
        
        running = sum(1 for line in lines if "Running" in line or "Completed" in line)
        pending = sum(1 for line in lines if "Pending" in line)
        failed = sum(1 for line in lines if "Error" in line or "CrashLoopBackOff" in line or "ImagePullBackOff" in line)
        
        if failed > 0:
            return HealthCheck("Pods", "critical", f"{running}/{total} healthy", 
                             f"{failed} failing, {pending} pending")
        elif pending > 0:
            return HealthCheck("Pods", "warning", f"{running}/{total} healthy",
                             f"{pending} pending")
        else:
            return HealthCheck("Pods", "healthy", f"{running}/{total} pods running")
    
    async def check_deployments(self) -> HealthCheck:
        """Check deployment health."""
        success, output = self._run_kubectl(["get", "deployments", "--all-namespaces", "--no-headers"])
        
        if not success:
            return HealthCheck("Deployments", "warning", "Cannot check deployments")
        
        lines = output.strip().split("\n") if output.strip() else []
        total = len(lines)
        
        if total == 0:
            return HealthCheck("Deployments", "healthy", "No deployments")
        
        healthy = 0
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                ready = parts[2]  # READY column like "3/3"
                nums = ready.split("/")
                if len(nums) == 2 and nums[0] == nums[1]:
                    healthy += 1
        
        if healthy == total:
            return HealthCheck("Deployments", "healthy", f"{healthy}/{total} fully available")
        else:
            return HealthCheck("Deployments", "warning", f"{healthy}/{total} fully available",
                             f"{total - healthy} deployment(s) degraded")
    
    async def check_services(self) -> HealthCheck:
        """Check service endpoints."""
        success, output = self._run_kubectl(["get", "endpoints", "--all-namespaces", "--no-headers"])
        
        if not success:
            return HealthCheck("Services", "warning", "Cannot check endpoints")
        
        lines = output.strip().split("\n") if output.strip() else []
        total = len(lines)
        
        if total == 0:
            return HealthCheck("Services", "healthy", "No services")
        
        empty = sum(1 for line in lines if "<none>" in line)
        
        if empty == 0:
            return HealthCheck("Services", "healthy", f"{total} services with endpoints")
        else:
            return HealthCheck("Services", "warning", f"{total - empty}/{total} have endpoints",
                             f"{empty} service(s) without endpoints")
    
    async def check_pvcs(self) -> HealthCheck:
        """Check PVC status."""
        success, output = self._run_kubectl(["get", "pvc", "--all-namespaces", "--no-headers"])
        
        if not success:
            return HealthCheck("Storage", "healthy", "No PVCs or cannot check")
        
        lines = output.strip().split("\n") if output.strip() else []
        
        if not lines or lines[0] == "":
            return HealthCheck("Storage", "healthy", "No PVCs")
        
        total = len(lines)
        bound = sum(1 for line in lines if "Bound" in line)
        pending = sum(1 for line in lines if "Pending" in line)
        
        if pending > 0:
            return HealthCheck("Storage", "warning", f"{bound}/{total} PVCs bound",
                             f"{pending} PVC(s) pending")
        else:
            return HealthCheck("Storage", "healthy", f"{bound}/{total} PVCs bound")
    
    async def get_health_report(self) -> ClusterHealthReport:
        """Generate comprehensive health report."""
        checks = await asyncio.gather(
            self.check_nodes(),
            self.check_pods(),
            self.check_deployments(),
            self.check_services(),
            self.check_pvcs(),
        )
        
        # Calculate score
        score = 100
        for check in checks:
            if check.status == "critical":
                score -= 25
            elif check.status == "warning":
                score -= 10
        
        return ClusterHealthReport(score=max(0, score), checks=list(checks))


class SecurityAuditor:
    """Performs security audits on the cluster."""
    
    def __init__(self, kubeconfig: Optional[str] = None):
        self.kubeconfig = kubeconfig
        self.kubectl_base = ["kubectl"]
        if kubeconfig:
            self.kubectl_base.extend(["--kubeconfig", kubeconfig])
    
    def _run_kubectl(self, args: list[str], timeout: int = 30) -> tuple[bool, str]:
        """Run kubectl command."""
        try:
            cmd = self.kubectl_base + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout or result.stderr
        except Exception as e:
            return False, str(e)
    
    async def check_privileged_pods(self) -> list[SecurityIssue]:
        """Check for privileged containers."""
        issues = []
        success, output = self._run_kubectl([
            "get", "pods", "--all-namespaces", "-o", 
            "jsonpath={range .items[*]}{.metadata.namespace}/{.metadata.name}: {.spec.containers[*].securityContext.privileged}{\"\\n\"}{end}"
        ])
        
        if success:
            for line in output.strip().split("\n"):
                if "true" in line.lower():
                    pod = line.split(":")[0]
                    issues.append(SecurityIssue(
                        severity="critical",
                        category="Privileged Containers",
                        message="Container running in privileged mode",
                        resource=pod,
                        recommendation="Remove privileged: true from securityContext"
                    ))
        
        return issues
    
    async def check_root_containers(self) -> list[SecurityIssue]:
        """Check for containers running as root."""
        issues = []
        success, output = self._run_kubectl([
            "get", "pods", "--all-namespaces", "-o",
            "jsonpath={range .items[*]}{.metadata.namespace}/{.metadata.name}: {.spec.containers[*].securityContext.runAsNonRoot}{\"\\n\"}{end}"
        ])
        
        if success:
            for line in output.strip().split("\n"):
                if line.strip() and "true" not in line.lower():
                    pod = line.split(":")[0]
                    if pod and "/" in pod:
                        issues.append(SecurityIssue(
                            severity="high",
                            category="Root Containers",
                            message="Container may run as root",
                            resource=pod,
                            recommendation="Set runAsNonRoot: true in securityContext"
                        ))
        
        return issues[:5]  # Limit to 5 to avoid noise
    
    async def check_resource_limits(self) -> list[SecurityIssue]:
        """Check for pods without resource limits."""
        issues = []
        success, output = self._run_kubectl([
            "get", "pods", "--all-namespaces", "-o",
            "jsonpath={range .items[*]}{.metadata.namespace}/{.metadata.name}: {.spec.containers[*].resources.limits}{\"\\n\"}{end}"
        ])
        
        if success:
            for line in output.strip().split("\n"):
                parts = line.split(":")
                if len(parts) >= 2:
                    pod = parts[0]
                    limits = ":".join(parts[1:]).strip()
                    if not limits or limits == "{}":
                        if pod and "/" in pod:
                            issues.append(SecurityIssue(
                                severity="medium",
                                category="Resource Limits",
                                message="No resource limits defined",
                                resource=pod,
                                recommendation="Add resources.limits.cpu and resources.limits.memory"
                            ))
        
        return issues[:5]  # Limit to 5
    
    async def check_default_service_account(self) -> list[SecurityIssue]:
        """Check for pods using default service account."""
        issues = []
        success, output = self._run_kubectl([
            "get", "pods", "--all-namespaces", "-o",
            "jsonpath={range .items[*]}{.metadata.namespace}/{.metadata.name}: {.spec.serviceAccountName}{\"\\n\"}{end}"
        ])
        
        if success:
            for line in output.strip().split("\n"):
                if ": default" in line:
                    pod = line.split(":")[0]
                    issues.append(SecurityIssue(
                        severity="low",
                        category="Service Accounts",
                        message="Using default service account",
                        resource=pod,
                        recommendation="Create dedicated service account with minimal permissions"
                    ))
        
        return issues[:3]  # Limit to 3
    
    async def check_network_policies(self) -> list[SecurityIssue]:
        """Check if network policies exist."""
        issues = []
        success, output = self._run_kubectl(["get", "networkpolicies", "--all-namespaces", "--no-headers"])
        
        if success:
            lines = output.strip().split("\n") if output.strip() else []
            if not lines or lines[0] == "":
                issues.append(SecurityIssue(
                    severity="medium",
                    category="Network Policies",
                    message="No network policies defined",
                    recommendation="Implement network policies to restrict pod-to-pod traffic"
                ))
        
        return issues
    
    async def get_audit_report(self) -> SecurityAuditReport:
        """Generate comprehensive security audit report."""
        all_issues = []
        
        checks = await asyncio.gather(
            self.check_privileged_pods(),
            self.check_root_containers(),
            self.check_resource_limits(),
            self.check_default_service_account(),
            self.check_network_policies(),
        )
        
        for check_issues in checks:
            all_issues.extend(check_issues)
        
        return SecurityAuditReport(issues=all_issues)
