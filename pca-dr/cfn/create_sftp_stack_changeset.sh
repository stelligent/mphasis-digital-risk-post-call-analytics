#!/bin/bash

STAMP=`date +%Y%m%d-%H%M%S`

aws cloudformation create-change-set \
    --debug \
    --stack-name pca-sftp-server \
    --change-set-name "pca-sftp-server-changeset-${STAMP}" \
    --template-body file://./aws-transfer-family-sftp.template.yaml \
    --parameters file://./aws-transfer-family-sftp-params.json \
    --capabilities CAPABILITY_IAM