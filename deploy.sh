#!/usr/bin/env sh

GREEN='\033[0;32m'
NC='\033[0m'

log() {
  echo "${GREEN}$1${NC}"
}

ISTIO_VERSION=1.11.0
KNATIVE_VERSION="v0.26.0"
CERTMANAGER_VERSION="v1.3.0"
KOURIER_VERSION="v1.2.0"

log "Start minikube"
minikube --memory=8192 --cpus=6 --kubernetes-version=v1.22.0 start

log "Enable ingress"
minikube addons enable ingress

log "Enable DNS"
minikube addons enable ingress-dns

log "Dowload Istio ${ISTIO_VERSION}"
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -

log "✨ Install Istio ${ISTIO_VERSION}"
istio-${ISTIO_VERSION}/bin/istioctl install -y

log "✨ Install KNative serving CRDs ${KNATIVE_VERSION}"
kubectl apply -f https://github.com/knative/serving/releases/download/${KNATIVE_VERSION}/serving-crds.yaml

log "✨ Install KNative serving core ${KNATIVE_VERSION}"
kubectl apply -f https://github.com/knative/serving/releases/download/${KNATIVE_VERSION}/serving-core.yaml

log "✨ Install KNative Istio ${KNATIVE_VERSION}"
kubectl apply -f https://github.com/knative/net-istio/releases/download/${KNATIVE_VERSION}/net-istio.yaml

log "✨ Install cert-manager ${CERTMANAGER_VERSION}"
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/${CERTMANAGER_VERSION}/cert-manager.yaml

log "✨ Install Kourier ${KOURIER_VERSION}"
kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-${KOURIER_VERSION}/kourier.yaml

log "🩹 Patch KNative"
kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress.class":"kourier.ingress.networking.knative.dev"}}'

log "😴 Wait for cert-manager"
kubectl wait pod --all --for=condition=Ready --timeout=600s -n cert-manager

log "✨ Install KServe"
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.7.0/kserve.yaml

log "Create persistent volume claim"
kubectl apply -f manifests/pvc.yaml

log "Create persistent volume"
kubectl apply -f manifests/pv.yaml

log "Create model storage pod"
kubectl apply -f manifests/pv-model-store.yaml

log "😴 Wait for model storage pod"
kubectl wait --for=condition=ready pod model-store-pod --timeout=60s

log "Copy model file to pod"
kubectl cp model/model.bst model-store-pod:/pv/model.joblib -c model-store

log "Deploy model"
kubectl apply -f manifests/shi-model-pvc.yaml