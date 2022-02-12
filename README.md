# rhods-shi-model

## KServe

This example relies on `KServe` for the model serving.
If you already a `KServe` installation running on Kubernetes, you can skip to "[Training the model](#training-the-model)".

### Local testing

If you want to test this locally, install `minikube`.

You can either run the automated install script [deploy.sh](deploy.sh) or follow the
step-by-step instructions.

Start `minikube` with _at least_ 6 CPUs.

```shell
minikube --memory=8192 --cpus=6 --kubernetes-version=v1.22.0 start
```

Enable `ingress` and `igress-dns` add-ons:

```shell
minikube addons enable ingress
minikube addons enable ingress-dns
```

Download `Istio` and install it

```shell
export ISTIO_VERSION=1.11.0
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -
istio-${ISTIO_VERSION}/bin/istioctl install -y
```

Instal `KNative` CRDs, serving core and Isto support:

```shell
export KNATIVE_VERSION="v0.26.0"
kubectl apply -f https://github.com/knative/serving/releases/download/${KNATIVE_VERSION}/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/${KNATIVE_VERSION}/serving-core.yaml
kubectl apply -f https://github.com/knative/net-istio/releases/download/${KNATIVE_VERSION}/net-istio.yaml
```

Install `cert-manager`

```shell
export CERTMANAGER_VERSION="v1.3.0"
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/${CERTMANAGER_VERSION}/cert-manager.yaml
```

Install `Kourier`

```shell
export KOURIER_VERSION="v1.2.0"
kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-${KOURIER_VERSION}/kourier.yaml
```

Patch `KNative`

```shell
kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress.class":"kourier.ingress.networking.knative.dev"}}'
```


Wait for `cert-manager` and install `KServe`

```shell
kubectl wait pod --all --for=condition=Ready --timeout=600s -n cert-manager
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.7.0/kserve.yaml
```


## Training the model

This example is made assuming the model is trained in Red Hat Open Data Science (RHODS).
However, it is also possible to train it locally, or even skip to [Deploying the model](#deploying-the-model) and use the pre-trained `model/model.bst` file.

### From Red Hat Open Data Science (RHODS)

From Red Hat Open Data Science (RHODS), clone this project
and run the [Jupyter notebook](notebooks/model-training.ipynb).

The last cells will save the model serialised model under `$PROJECT_ROOT/models`.

### Locally

You can also run the Jupyter notebook locally as above.

## Deploying the model

Once the model is trained, we can copy it to a persistent volume in order
for `KServe` to serve it.

### Persistent volume

Create the persistent volume

```shell
kubectl apply -f manifests/volume.yaml
```

Create the model storage pod

```shell
kubectl apply -f manifests/pv-model-store.yaml
```

Wait for model storage pod, and copy the model file to it, when ready.

```shell
kubectl wait --for=condition=ready pod model-store-pod --timeout=60s
kubectl cp model/model.bst model-store-pod:/pv/model.joblib -c model-store
```

### InferenceService deployment

Deploy model inference service

```shell
kubectl apply -f manifests/sklearn-pvc.yaml
```