#!/bin/bash

STAMP=`date +%Y%m%d-%H%M%S`

aws cloudformation create-change-set \
    --debug \
    --change-set-name "pca-dyanmodb-vpce-changeset-${STAMP}" \
    --stack-name pca-dynamodb-vpce \
    --template-body file://./dynamodb-vpc-gateway-endpoint-template.yaml \
    --parameters file://./dynamodb-vpc-gateway-endpoint-params.json \
