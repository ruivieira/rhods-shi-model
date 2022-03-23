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

eval "$(minikube docker-env)"

log "Enable ingress"
minikube addons enable ingress

log "Enable DNS"
minikube addons enable ingress-dns

log "Istall Kafka"
helm repo add confluentinc https://confluentinc.github.io/cp-helm-charts/
helm repo update
helm install my-kafka -f k8s/kafka-values.yaml --set cp-schema-registry.enabled=false,cp-kafka-rest.enabled=false,cp-kafka-connect.enabled=false confluentinc/cp-helm-charts

log "Install KNative Eventing Core"
kubectl apply -f https://github.com/knative/eventing/releases/download/${KNATIVE_VERSION}/eventing-crds.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/${KNATIVE_VERSION}/eventing-core.yaml

log "Install Kafka Event Source"
kubectl apply -f https://github.com/knative-sandbox/eventing-kafka/releases/download/${KNATIVE_VERSION}/source.yaml

log "Set addressable resolver"
kubectl apply -f k8s/addressable-resolver.yaml

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

cd model || exit

log "✨ Build custom model server"
minikube image build -t dev.local/rhods-shi-model:latest .

cd ..

log "Deploy model"
kubectl apply -f k8s/shi-model-pvc.yaml
