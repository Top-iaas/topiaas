#!/bin/bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

setup () {
    echo "settting up topiaas cluster ..."
    # minikube start --nodes 2  -p topiaas --mount --mount-string="$HOME/topiaas/portal:/app"
    kind create cluster --name topiaas --config $SCRIPT_DIR/../kind-k8s/cluster.yaml
    echo "Setting up RBAC and service accounts"
    kubectl apply -f $SCRIPT_DIR/../kubernetes/common/RBAC.yaml
    echo "Setting up ingress-nginx"
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
    
}
start () {
    # echo "Starting topiaas devenv ..."
    # minikube -p topiaas start --mount --mount-string="$HOME/topiaas/portal:/app"
    echo "starting control plane"
    docker start topiaas-control-plane
    echo "starting worker"
    docker start topiaas-worker
}
stop () {
    # echo "Stopping topiaas devenv ..."
    # minikube -p topiaas stop
    echo "stopping worker"
    docker stop topiaas-worker
    echo "stopping control plane"
    docker stop topiaas-control-plane
}
debug () {
    echo "ensuring debug-service"
    kubectl get svc topiaas-app-debug || kubectl apply -f kubernetes/development/topiaas-app/debug-service.yaml
    echo "port-forwarding ptvsd debug port onto localhost. Must keep this running"
    kubectl port-forward service/topiaas-app-debug 5555:5800
}
case $1 in
    setup) setup;;
    start) start;;
    stop) stop;;
    debug) debug;;
    *)
        echo "please choose one of the following [setup, start, stop]"
    ;;
esac