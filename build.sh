#!/bin/bash

if [ -z ${AWS_ACCOUNT_ID} ]; then
    echo "Environment Variable AWS_ACCOUNT_ID MUST be set"
    return
fi

./publish.sh ${PCA_DEPLOY_BUCKET} pca private
