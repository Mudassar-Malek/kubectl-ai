"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_kubeconfig():
    """Sample kubeconfig content for testing."""
    return {
        "apiVersion": "v1",
        "kind": "Config",
        "current-context": "minikube",
        "contexts": [
            {
                "name": "minikube",
                "context": {
                    "cluster": "minikube",
                    "user": "minikube",
                    "namespace": "default",
                },
            },
            {
                "name": "eks-prod",
                "context": {
                    "cluster": "arn:aws:eks:us-east-1:123456789:cluster/prod",
                    "user": "eks-admin",
                },
            },
            {
                "name": "aks-dev",
                "context": {
                    "cluster": "dev-aks.azmk8s.io",
                    "user": "aks-user",
                },
            },
            {
                "name": "gke-staging",
                "context": {
                    "cluster": "gke_my-project_us-central1_staging",
                    "user": "gke-user",
                },
            },
        ],
        "clusters": [
            {"name": "minikube", "cluster": {"server": "https://192.168.49.2:8443"}},
            {
                "name": "arn:aws:eks:us-east-1:123456789:cluster/prod",
                "cluster": {"server": "https://ABC123.eks.amazonaws.com"},
            },
            {
                "name": "dev-aks.azmk8s.io",
                "cluster": {"server": "https://dev-aks.azmk8s.io:443"},
            },
            {
                "name": "gke_my-project_us-central1_staging",
                "cluster": {"server": "https://35.192.0.1"},
            },
        ],
        "users": [
            {"name": "minikube", "user": {}},
            {"name": "eks-admin", "user": {}},
            {"name": "aks-user", "user": {}},
            {"name": "gke-user", "user": {}},
        ],
    }


@pytest.fixture
def sample_pod_output():
    """Sample kubectl get pods output."""
    return """NAME                     READY   STATUS    RESTARTS   AGE
nginx-6799fc88d8-abc12   1/1     Running   0          2d
redis-7b9c45f8-xyz34     1/1     Running   0          5d
api-server-5d6f7-def56   2/2     Running   1          1h
worker-8c9d0e-ghi78      0/1     Pending   0          5m
"""


@pytest.fixture
def sample_deployment_output():
    """Sample kubectl get deployments output."""
    return """NAME         READY   UP-TO-DATE   AVAILABLE   AGE
nginx        3/3     3            3           10d
redis        1/1     1            1           5d
api-server   2/3     3            2           2d
"""


@pytest.fixture
def sample_describe_output():
    """Sample kubectl describe pod output."""
    return """Name:         nginx-6799fc88d8-abc12
Namespace:    default
Priority:     0
Node:         minikube/192.168.49.2
Start Time:   Mon, 01 Jan 2024 10:00:00 +0000
Labels:       app=nginx
              pod-template-hash=6799fc88d8
Status:       Running
IP:           172.17.0.5
Containers:
  nginx:
    Image:          nginx:1.21
    Port:           80/TCP
    State:          Running
      Started:      Mon, 01 Jan 2024 10:00:05 +0000
    Ready:          True
    Restart Count:  0
Events:
  Type    Reason     Age   From               Message
  ----    ------     ----  ----               -------
  Normal  Scheduled  2d    default-scheduler  Successfully assigned default/nginx-6799fc88d8-abc12 to minikube
  Normal  Pulled     2d    kubelet            Container image "nginx:1.21" already present on machine
  Normal  Created    2d    kubelet            Created container nginx
  Normal  Started    2d    kubelet            Started container nginx
"""
