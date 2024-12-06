#!/bin/bash

if [ -z ${AWS_ACCOUNT_ID} ]; then
        echo "Environment Variable AWS_ACCOUNT_ID MUST be set"
        return
fi

aws cloudformation deploy \
        --stack-name PCA \
        --template-file ${PWD}/build/packaged.template \
        --s3-bucket ${PCA_DEPLOY_BUCKET} \
        --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
        --no-execute-changeset \
        --parameter-overrides \
                AdminEmail=${PCA_ADMIN_EMAIL} \
                EnableGui=true \
                TelephonyCTRType=${PCA_TELEPHONY_TYPE} \
                PCAVersion="${PCA_VERSION}" \
                PyZipName=python-utils-layer-v3.zip \
                PreloadBucketName=${PCA_PRELOAD_BUCKET_NAME} \
                PreloadObjectKeyRegex=${PCA_PRELOAD_OBJECT_KEY_REGEX}
