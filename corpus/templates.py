"""
templates.py

Filler-action template banks, one list per phase. These are NOT sourced
from HF's blog or OpenAI's report - they exist to fill the non-milestone
actions in a phase with schema-consistent, plausible content, matching
PLAN.md's "labelled a scaffold, not telemetry" framing. Every generated
row using one of these carries citation="synthetic filler..." so nobody
downstream mistakes it for a sourced fact.

Only `k8s` is populated for the Tue 8 feasibility prototype (TIMELINE.md
Section 1). The other 8 phases + `unclassified` need their own banks
before the Friday full build - copy this file's shape, don't invent a
new one.
"""

PHASE_TEMPLATES = {
    "k8s": [
        {
            "event": "kubectl auth can-i --list --as=system:serviceaccount:hf-dataset-server:default",
            "host_role": "hf-k8s-mgmt-connector",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1069.003",
            "mitre_tactic": "Discovery",
            "severity": "low",
        },
        {
            "event": "kubectl get pods -A -o wide",
            "host_role": "hf-k8s-mgmt-connector",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1613",
            "mitre_tactic": "Discovery",
            "severity": "low",
        },
        {
            "event": "kubectl get secrets -A (permission denied, retried against 3 namespaces)",
            "host_role": "hf-k8s-mgmt-connector",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1552.007",
            "mitre_tactic": "Credential Access",
            "severity": "medium",
        },
        {
            "event": "kubectl describe clusterrolebinding csi-hostpath-provisioner-role",
            "host_role": "hf-k8s-mgmt-connector",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1069.003",
            "mitre_tactic": "Discovery",
            "severity": "medium",
        },
        {
            "event": "curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            "host_role": "hf-dataset-server-worker",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1552.005",
            "mitre_tactic": "Credential Access",
            "severity": "high",
        },
        {
            "event": "kubectl get nodes -o json",
            "host_role": "hf-k8s-mgmt-connector",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1580",
            "mitre_tactic": "Discovery",
            "severity": "low",
        },
        {
            "event": "kubectl get csidrivers.storage.k8s.io,csinodes.storage.k8s.io",
            "host_role": "hf-k8s-mgmt-connector",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1613",
            "mitre_tactic": "Discovery",
            "severity": "low",
        },
        {
            "event": "kubectl exec -it dsw-7f3e2c -- /bin/sh",
            "host_role": "hf-dataset-server-worker",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1609",
            "mitre_tactic": "Execution",
            "severity": "medium",
        },
        {
            "event": "aws sts get-caller-identity (using node instance-role credentials)",
            "host_role": "hf-dataset-server-worker",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1528",
            "mitre_tactic": "Credential Access",
            "severity": "high",
        },
        {
            "event": "kubectl apply --dry-run=server -f privileged-pod.yaml",
            "host_role": "hf-k8s-mgmt-connector",
            "actor": "internal-only-research-agent",
            "mitre_technique": "T1610",
            "mitre_tactic": "Defense Evasion",
            "severity": "high",
        },
    ],
}
