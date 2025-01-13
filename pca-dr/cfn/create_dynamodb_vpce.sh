aws cloudformation create-stack \
    --stack-name pca-dynamodb-vpce \
    --template-body file://./dynamodb-vpc-gateway-endpoint-template.yaml \
    --parameters file://./dynamodb-vpc-gateway-endpoint-params.json \
